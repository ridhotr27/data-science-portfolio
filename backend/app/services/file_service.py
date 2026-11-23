from __future__ import annotations

import io
import re
import uuid
from pathlib import Path

import pandas as pd
from fastapi import HTTPException, UploadFile

from .dataset_store import DatasetSession

try:
    import polars as pl
except ImportError:  # Keeps a friendly fallback for an environment not upgraded yet.
    pl = None

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000
MAX_COLUMNS = 50
ALLOWED_SUFFIXES = {".csv", ".xlsx"}
ALLOWED_MIME_TYPES = {
    ".csv": {"text/csv", "application/csv", "text/plain", "application/vnd.ms-excel", "application/octet-stream", ""},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream", ""},
}


def clean_name(name: str | None) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", Path(name or "dataset").name)[:120]


def normalize_headers(frame: pd.DataFrame) -> pd.DataFrame:
    if not len(frame.columns):
        raise HTTPException(400, "The dataset has no headers.")
    normalized: list[str] = []
    seen: dict[str, int] = {}
    for index, value in enumerate(frame.columns):
        base = str(value).strip()
        if not base or base.lower().startswith("unnamed:"):
            base = f"column_{index + 1}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        normalized.append(base if count == 0 else f"{base}_{count + 1}")
    frame.columns = normalized
    return frame


def parse_bytes(raw: bytes, suffix: str, sheet: str | None = None) -> tuple[pd.DataFrame, list[str], str]:
    try:
        if suffix == ".csv":
            if pl is not None:
                polars_frame = pl.read_csv(io.BytesIO(raw), try_parse_dates=True)
                frame = pd.DataFrame(polars_frame.to_dict(as_series=False))
            else:
                frame = pd.read_csv(io.BytesIO(raw))
            return normalize_headers(frame), [], "CSV"
        workbook = pd.ExcelFile(io.BytesIO(raw), engine="openpyxl")
        sheets = [str(item) for item in workbook.sheet_names]
        if not sheets:
            raise HTTPException(400, "The workbook does not contain any worksheets.")
        active = sheet or sheets[0]
        if active not in sheets:
            raise HTTPException(422, "The selected worksheet does not exist.")
        frame = pd.read_excel(workbook, sheet_name=active)
        return normalize_headers(frame), sheets, active
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, "The file could not be parsed. Check its format, encoding, and headers.") from exc


def validate_frame(frame: pd.DataFrame) -> None:
    if frame.empty:
        raise HTTPException(400, "The dataset contains no data rows.")
    if len(frame) > MAX_ROWS:
        raise HTTPException(413, f"The dataset exceeds the {MAX_ROWS:,}-row limit.")
    if len(frame.columns) > MAX_COLUMNS:
        raise HTTPException(413, f"The dataset exceeds the {MAX_COLUMNS:,}-column limit.")
    if not len(frame.columns):
        raise HTTPException(400, "The dataset has no usable columns.")


async def create_session(file: UploadFile) -> DatasetSession:
    name = clean_name(file.filename)
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(415, "Unsupported file type. Use CSV or XLSX.")
    mime = (file.content_type or "").lower()
    if mime not in ALLOWED_MIME_TYPES[suffix]:
        raise HTTPException(415, f"The reported MIME type is not valid for {suffix.upper()} files.")
    raw = await file.read(MAX_BYTES + 1)
    if not raw:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "The file exceeds the 5 MB limit.")
    if suffix == ".xlsx" and not raw.startswith(b"PK"):
        raise HTTPException(415, "The file content is not a valid XLSX workbook.")
    if suffix == ".csv" and b"\x00" in raw[:8192]:
        raise HTTPException(415, "The file appears to be binary rather than CSV text.")
    frame, sheets, active = parse_bytes(raw, suffix)
    validate_frame(frame)
    return DatasetSession(
        dataset_id=uuid.uuid4().hex, name=name, suffix=suffix, mime_type=mime,
        size=len(raw), raw=raw, frame=frame, sheets=sheets, active_sheet=active,
    )
