from __future__ import annotations

import random

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile

from ..schemas.datasets import SheetRequest
from ..services.dataset_store import DatasetCapacityError, DatasetSession, dataset_store
from ..services.file_service import parse_bytes, create_session, validate_frame
from ..services.upload_limiter import check_upload_rate
from ..services.profiling_service import profile_dataset
from ..utils.serialization import records

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def require_dataset(dataset_id: str) -> DatasetSession:
    session = dataset_store.get(dataset_id)
    if not session:
        raise HTTPException(404, "Dataset session not found or expired. Upload the file again.")
    return session


def metadata(session: DatasetSession) -> dict:
    if "profile" not in session.cache:
        session.cache["profile"] = profile_dataset(session.frame)
    columns, summary = session.cache["profile"]
    return {
        "dataset_id": session.dataset_id,
        "file": {
            "name": session.name, "size": session.size,
            "size_display": f"{session.size / 1024:.1f} KB", "type": session.suffix,
        },
        "summary": summary, "columns": columns,
        "sheets": session.sheets, "active_sheet": session.active_sheet,
        "expires_in_seconds": dataset_store.ttl_seconds,
    }


@router.post("/upload")
async def upload_dataset(request: Request, file: UploadFile = File(...)):
    check_upload_rate(request)
    stats = dataset_store.stats()
    if stats["sessions"] >= stats["maximum_sessions"]:
        raise HTTPException(
            429,
            f"The server already has {stats['maximum_sessions']} active datasets. "
            "Please clear an existing dataset or wait for an inactive session to expire.",
        )
    session = await create_session(file)
    try:
        dataset_store.put(session)
    except DatasetCapacityError as exc:
        raise HTTPException(429, str(exc)) from exc
    return {**metadata(session), "preview": records(session.frame.head(25))}


@router.get("/{dataset_id}/schema")
def dataset_schema(dataset_id: str):
    return metadata(require_dataset(dataset_id))


@router.get("/{dataset_id}/preview")
def dataset_preview(
    dataset_id: str,
    mode: str = Query("first", pattern="^(first|last|random)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
):
    session = require_dataset(dataset_id)
    frame = session.frame
    if mode == "last":
        sample = frame.tail(limit)
    elif mode == "random":
        sample = frame.sample(n=min(limit, len(frame)), random_state=random.randint(0, 2**16))
    else:
        sample = frame.iloc[offset:offset + limit]
    return {
        "dataset_id": dataset_id, "mode": mode, "offset": offset,
        "limit": limit, "total_rows": len(frame), "rows": records(sample),
    }


@router.post("/{dataset_id}/sheet")
def select_sheet(dataset_id: str, request: SheetRequest):
    session = require_dataset(dataset_id)
    if session.suffix != ".xlsx":
        raise HTTPException(409, "Worksheet selection is only available for XLSX files.")
    frame, sheets, active = parse_bytes(session.raw, session.suffix, request.sheet)
    validate_frame(frame)
    session.frame, session.sheets, session.active_sheet = frame, sheets, active
    session.cache.clear()
    return {**metadata(session), "preview": records(frame.head(25))}


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str):
    if not dataset_store.delete(dataset_id):
        raise HTTPException(404, "Dataset session not found.")
    return {"deleted": True, "dataset_id": dataset_id}
