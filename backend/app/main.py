from __future__ import annotations

import io
import json
import os
import threading
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .api.datasets import metadata as dataset_metadata
from .api.datasets import router as datasets_router
from .api.eda import router as eda_router
from .api.customer_360 import router as customer_360_router
from .services.dataset_store import DatasetCapacityError, dataset_store
from .services.file_service import create_session
from .services.upload_limiter import check_upload_rate
from .utils.serialization import json_value

jobs: dict[str, dict] = {}
load_dotenv()
ENABLE_XGBOOST = os.getenv("ENABLE_XGBOOST", "false").lower() in {"1", "true", "yes", "on"}
if ENABLE_XGBOOST:
    import joblib

    from .ml import train
    from .utils.csv_security import protect_csv

app = FastAPI(title="Portfolio Analytics API", version="1.1.0")
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", frontend_origin).split(",")
    if origin.strip()
]
if "http://127.0.0.1:5173" not in allowed_origins and frontend_origin == "http://localhost:5173":
    allowed_origins.append("http://127.0.0.1:5173")
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=False, allow_methods=["GET","POST","DELETE"], allow_headers=["Content-Type"])
app.include_router(datasets_router)
app.include_router(eda_router)
app.include_router(customer_360_router)


class TrainRequest(BaseModel):
    dataset_id: str
    target: str
    features: list[str] = Field(min_length=1)
    problem_type: str
    config: dict


def require_xgboost_enabled() -> None:
    if not ENABLE_XGBOOST:
        raise HTTPException(503, "XGBoost is temporarily unavailable. Please try the EDA or Customer 360 workspace instead.")


@app.get("/api/health")
def health(): return {"status":"ok", "datasets": dataset_store.stats()}


@app.post("/api/ml/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    require_xgboost_enabled()
    check_upload_rate(request)
    session = await create_session(file)
    if len(session.frame) < 10:
        raise HTTPException(400, "The dataset needs at least 10 rows for model training.")
    try:
        dataset_store.put(session)
    except DatasetCapacityError as exc:
        raise HTTPException(429, str(exc)) from exc
    return {**dataset_metadata(session), "preview": [
        {str(key): json_value(value) for key, value in row.items()}
        for row in session.frame.head(50).to_dict("records")
    ]}


def run_job(job_id: str, request: TrainRequest):
    job = jobs[job_id]
    def progress(state, amount, message):
        if job.get("cancel_requested"): raise RuntimeError("Training was cancelled.")
        job.update(state=state,progress=amount,message=message)
    try:
        session = dataset_store.get(request.dataset_id)
        if not session:
            raise ValueError("Dataset session expired. Upload the file again.")
        trained, interpretation, tuning = train(session.frame, request.target, request.features, request.problem_type, request.config, progress)
        job.update(state="completed", progress=100, message="Completed", trained=trained, interpretation=interpretation, tuning=tuning)
    except Exception as exc:
        job.update(state="cancelled" if job.get("cancel_requested") else "failed", error=str(exc), message="Cancelled" if job.get("cancel_requested") else "Training failed")


@app.post("/api/ml/train")
def start_training(request: TrainRequest):
    require_xgboost_enabled()
    if not dataset_store.get(request.dataset_id): raise HTTPException(404, "Dataset session not found. Upload the file again.")
    if request.problem_type not in {"binary_classification","multiclass_classification","regression"}: raise HTTPException(422, "Invalid problem type.")
    job_id = uuid.uuid4().hex
    jobs[job_id] = {"job_id":job_id,"state":"queued","progress":0,"message":"Waiting to start","cancel_requested":False}
    threading.Thread(target=run_job,args=(job_id,request),daemon=True).start()
    return {"job_id":job_id}


@app.get("/api/ml/train/{job_id}/status")
def status(job_id: str):
    require_xgboost_enabled()
    job = jobs.get(job_id)
    if not job: raise HTTPException(404,"Training job not found.")
    return {k:v for k,v in job.items() if k not in {"trained","interpretation","tuning"}}


@app.post("/api/ml/train/{job_id}/cancel")
def cancel(job_id: str):
    require_xgboost_enabled()
    if job_id not in jobs: raise HTTPException(404,"Training job not found.")
    jobs[job_id]["cancel_requested"] = True
    return {"status":"cancellation_requested"}


@app.get("/api/ml/results/{job_id}")
def results(job_id: str):
    require_xgboost_enabled()
    job = jobs.get(job_id)
    if not job or job.get("state") != "completed": raise HTTPException(409,"Results are not ready.")
    trained = job["trained"]
    return {"job_id":job_id,"metrics":trained.metrics,"feature_importance":trained.importance,"summary":trained.summary,"warnings":trained.warnings,"interpretation":job["interpretation"],"tuning":job["tuning"],"predictions":[{str(k):json_value(v) for k,v in r.items()} for r in trained.predictions.head(100).to_dict("records")]}


@app.post("/api/ml/predict/{job_id}")
async def predict(job_id: str, file: UploadFile = File(...)):
    require_xgboost_enabled()
    job = jobs.get(job_id)
    if not job or job.get("state") != "completed": raise HTTPException(404,"Trained model not found.")
    incoming = await create_session(file)
    df = incoming.frame
    trained = job["trained"]
    missing = sorted(set(trained.features)-set(df.columns))
    if missing: raise HTTPException(422,f"Missing required columns: {', '.join(missing)}")
    try:
        encoded = trained.pipeline.predict(df[trained.features])
        pred = trained.label_encoder.inverse_transform(encoded.astype(int)) if trained.label_encoder else encoded
        output=df.copy(); output["predicted_target"]=pred
        if trained.label_encoder is not None: output["prediction_probability"]=trained.pipeline.predict_proba(df[trained.features]).max(axis=1)
    except Exception as exc: raise HTTPException(422,"New data contains incompatible values or data types.") from exc
    job["new_predictions"]=output
    return {"rows":len(output),"unexpected_columns":sorted(set(df.columns)-set(trained.features))}


def download_job(job_id: str):
    job=jobs.get(job_id)
    if not job or job.get("state")!="completed": raise HTTPException(404,"Completed job not found.")
    return job


@app.get("/api/ml/download/{job_id}/predictions")
def download_predictions(job_id: str):
    require_xgboost_enabled()
    raw=protect_csv(download_job(job_id)["trained"].predictions).to_csv(index=False)
    return Response(raw,media_type="text/csv",headers={"Content-Disposition":'attachment; filename="xgboost_predictions.csv"'})


@app.get("/api/ml/download/{job_id}/new-predictions")
def download_new_predictions(job_id: str):
    require_xgboost_enabled()
    job=download_job(job_id)
    if "new_predictions" not in job: raise HTTPException(404,"No new-data predictions are available.")
    return Response(protect_csv(job["new_predictions"]).to_csv(index=False),media_type="text/csv",headers={"Content-Disposition":'attachment; filename="new_data_predictions.csv"'})


@app.get("/api/ml/download/{job_id}/metrics")
def download_metrics(job_id: str):
    require_xgboost_enabled()
    return Response(json.dumps(download_job(job_id)["trained"].metrics,indent=2),media_type="application/json",headers={"Content-Disposition":'attachment; filename="xgboost_metrics.json"'})


@app.get("/api/ml/download/{job_id}/model")
def download_model(job_id: str):
    require_xgboost_enabled()
    trained=download_job(job_id)["trained"]; buffer=io.BytesIO()
    joblib.dump({"pipeline":trained.pipeline,"label_encoder":trained.label_encoder,"features":trained.features,"target":trained.target,"problem_type":trained.problem_type},buffer)
    return Response(buffer.getvalue(),media_type="application/octet-stream",headers={"Content-Disposition":'attachment; filename="trusted_xgboost_pipeline.joblib"'})
