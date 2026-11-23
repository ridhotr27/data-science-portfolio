from __future__ import annotations

import pandas as pd

from ..utils.column_types import detect_kind, likely_identifier
from ..utils.problem_type import suggest_problem
from ..utils.serialization import json_value


def profile_dataset(frame: pd.DataFrame) -> tuple[list[dict], dict]:
    kinds = {name: detect_kind(frame[name]) for name in frame.columns}
    columns = []
    for name in frame.columns:
        series = frame[name]
        unique = int(series.nunique(dropna=True))
        columns.append({
            "name": str(name),
            "dtype": kinds[name],
            "original_dtype": str(series.dtype),
            "unique": unique,
            "unique_pct": round(unique / len(frame) * 100, 2),
            "non_null": int(series.notna().sum()),
            "missing": int(series.isna().sum()),
            "missing_pct": round(float(series.isna().mean() * 100), 2),
            "examples": [str(json_value(value))[:80] for value in series.dropna().drop_duplicates().head(3)],
            "likely_id": likely_identifier(str(name), series),
            "problem_suggestion": suggest_problem(series),
        })
    summary = {
        "rows": len(frame),
        "columns": len(frame.columns),
        "missing_values": int(frame.isna().sum().sum()),
        "duplicates": int(frame.duplicated().sum()),
        "memory_bytes": int(frame.memory_usage(index=True, deep=True).sum()),
    }
    for kind in ("numeric", "categorical", "date", "boolean", "constant"):
        summary[f"{kind}_columns"] = sum(value == kind for value in kinds.values())
    summary["high_cardinality_columns"] = sum(
        item["dtype"] == "categorical" and item["unique"] > min(50, len(frame) * 0.5)
        for item in columns
    )
    return columns, summary
