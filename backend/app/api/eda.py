from __future__ import annotations

import json

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from .datasets import require_dataset
from ..schemas.eda import (
    CorrelationRequest, DistributionRequest, ExportRequest, OutlierRequest,
    ProfileRequest, RelationshipRequest, TargetRequest, TypeOverridesRequest,
)
from ..utils.csv_security import protect_csv
from ..services.advanced_eda_service import (
    correlation, distribution, insights, outliers, readiness, relationship,
    target_analysis,
)
from ..services.data_quality_service import analyze_quality
from ..services.eda_profiling_service import detailed_profile
from ..services.profiling_service import profile_dataset
from ..services.dataset_store import cached_analysis

router = APIRouter(prefix="/api/eda", tags=["exploratory-data-analysis"])


def validate_overrides(frame, overrides: dict[str, str]) -> None:
    missing = sorted(set(overrides) - set(frame.columns))
    if missing:
        raise HTTPException(422, f"Unknown override columns: {', '.join(missing)}")


@router.get("/{dataset_id}/overview")
def overview(dataset_id: str):
    session = require_dataset(dataset_id)
    if "profile" not in session.cache:
        session.cache["profile"] = profile_dataset(session.frame)
    columns, summary = session.cache["profile"]
    return {"dataset_id": dataset_id, "summary": summary, "columns": columns}


@router.post("/{dataset_id}/profile")
def profile(dataset_id: str, request: ProfileRequest):
    session = require_dataset(dataset_id)
    validate_overrides(session.frame, request.overrides)
    try:
        profiles = cached_analysis(session, "eda.profile", request.model_dump(mode="json"), lambda: detailed_profile(session.frame, request.overrides, request.columns))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    session.cache["eda_overrides"] = request.overrides
    return {"dataset_id": dataset_id, "profiles": profiles, "overrides": request.overrides}


@router.post("/{dataset_id}/quality")
def quality(dataset_id: str, request: TypeOverridesRequest):
    session = require_dataset(dataset_id)
    validate_overrides(session.frame, request.overrides)
    result = cached_analysis(session, "eda.quality", request.model_dump(mode="json"), lambda: analyze_quality(session.frame, request.overrides))
    return {"dataset_id": dataset_id, **result}


def run(service, *args):
    try:
        return service(*args)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/{dataset_id}/distribution")
def analyze_distribution(dataset_id: str, request: DistributionRequest):
    session = require_dataset(dataset_id); validate_overrides(session.frame, request.overrides)
    result = cached_analysis(session, "eda.distribution", request.model_dump(mode="json"), lambda: run(distribution, session.frame, request.column, request.overrides, request.bins, request.top_n, request.date_frequency))
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/correlation")
def analyze_correlation(dataset_id: str, request: CorrelationRequest):
    session = require_dataset(dataset_id); validate_overrides(session.frame, request.overrides)
    result = cached_analysis(session, "eda.correlation", request.model_dump(mode="json"), lambda: run(correlation, session.frame, request.overrides, request.method, request.threshold, request.columns))
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/relationship")
def analyze_relationship(dataset_id: str, request: RelationshipRequest):
    session = require_dataset(dataset_id); validate_overrides(session.frame, request.overrides)
    result = cached_analysis(session, "eda.relationship", request.model_dump(mode="json"), lambda: run(relationship, session.frame, request.x, request.y, request.group, request.overrides))
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/outliers")
def analyze_outliers(dataset_id: str, request: OutlierRequest):
    session = require_dataset(dataset_id); validate_overrides(session.frame, request.overrides)
    result = cached_analysis(session, "eda.outliers", request.model_dump(mode="json"), lambda: run(outliers, session.frame, request.overrides, request.method, request.threshold, request.column, request.limit))
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/target-analysis")
def analyze_target(dataset_id: str, request: TargetRequest):
    session = require_dataset(dataset_id); validate_overrides(session.frame, request.overrides)
    result = cached_analysis(session, "eda.target", request.model_dump(mode="json"), lambda: run(target_analysis, session.frame, request.target, request.overrides, request.problem_type))
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/readiness")
def analyze_readiness(dataset_id: str, request: TargetRequest):
    session = require_dataset(dataset_id); validate_overrides(session.frame, request.overrides)
    result = cached_analysis(session, "eda.readiness", request.model_dump(mode="json"), lambda: run(readiness, session.frame, request.overrides, request.target))
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/insights")
def generated_insights(dataset_id: str, request: TypeOverridesRequest):
    session = require_dataset(dataset_id); validate_overrides(session.frame, request.overrides)
    result = cached_analysis(session, "eda.insights", request.model_dump(mode="json"), lambda: run(insights, session.frame, request.overrides))
    return {"dataset_id": dataset_id, "insights": result}


@router.post("/{dataset_id}/export")
def export_analysis(dataset_id: str, request: ExportRequest):
    session = require_dataset(dataset_id); validate_overrides(session.frame, request.overrides)
    name = f"eda_{request.export_type}"
    if request.export_type == "profiles":
        data = detailed_profile(session.frame, request.overrides)
        rows = [{**{key: value for key, value in item.items() if key not in {"statistics", "examples"}}, **item["statistics"]} for item in data]
        payload, media, suffix = protect_csv(pd.DataFrame(rows)).to_csv(index=False), "text/csv", "csv"
    elif request.export_type == "quality":
        payload, media, suffix = protect_csv(pd.DataFrame(analyze_quality(session.frame, request.overrides)["issues"])).to_csv(index=False), "text/csv", "csv"
    elif request.export_type == "correlation":
        data = run(correlation, session.frame, request.overrides, request.method, 0.0, None)
        payload, media, suffix = protect_csv(pd.DataFrame(data["matrix"])).to_csv(index=False), "text/csv", "csv"
    elif request.export_type == "outliers":
        method = request.method if request.method in {"iqr", "zscore"} else "iqr"
        data = run(outliers, session.frame, request.overrides, method, request.threshold, None, 10000)
        payload, media, suffix = protect_csv(pd.DataFrame(data["rows"])).to_csv(index=False), "text/csv", "csv"
    else:
        payload, media, suffix = json.dumps({"readiness": readiness(session.frame, request.overrides), "insights": insights(session.frame, request.overrides)}, indent=2), "application/json", "json"
    return Response(payload, media_type=media, headers={"Content-Disposition": f'attachment; filename="{name}.{suffix}"'})
