from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..utils.column_types import detect_kind, likely_identifier
from ..utils.serialization import json_value


def _mode(series: pd.Series) -> tuple[Any, int]:
    modes = series.dropna().mode()
    if modes.empty:
        return None, 0
    value = modes.iloc[0]
    return json_value(value), int((series == value).sum())


def _numeric_profile(series: pd.Series) -> dict:
    numeric = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if numeric.empty:
        return {}
    quartiles = numeric.quantile([0.25, 0.5, 0.75])
    return {
        "minimum": json_value(numeric.min()), "maximum": json_value(numeric.max()),
        "mean": json_value(numeric.mean()), "median": json_value(numeric.median()),
        "standard_deviation": json_value(numeric.std()),
        "q1": json_value(quartiles.loc[0.25]), "q3": json_value(quartiles.loc[0.75]),
        "zero_pct": round(float((numeric == 0).mean() * 100), 2),
        "negative_pct": round(float((numeric < 0).mean() * 100), 2),
    }


def _date_profile(series: pd.Series) -> dict:
    parsed = pd.to_datetime(series, errors="coerce", format="mixed")
    valid = parsed.dropna()
    if valid.empty:
        return {"invalid_date_count": int(series.notna().sum())}
    return {
        "earliest": json_value(valid.min()), "latest": json_value(valid.max()),
        "date_range_days": int((valid.max() - valid.min()).days),
        "invalid_date_count": int((series.notna() & parsed.isna()).sum()),
    }


def detailed_profile(frame: pd.DataFrame, overrides: dict[str, str] | None = None, selected: list[str] | None = None) -> list[dict]:
    overrides = overrides or {}
    names = selected or list(frame.columns)
    missing = sorted(set(names) - set(frame.columns))
    if missing:
        raise ValueError(f"Unknown columns: {', '.join(missing)}")
    profiles = []
    for name in names:
        series = frame[name]
        detected = detect_kind(series)
        kind = overrides.get(name, detected)
        unique = int(series.nunique(dropna=True))
        common, common_count = _mode(series)
        item = {
            "name": name, "detected_type": detected, "effective_type": kind,
            "original_type": str(series.dtype), "non_null": int(series.notna().sum()),
            "null_count": int(series.isna().sum()),
            "null_pct": round(float(series.isna().mean() * 100), 2),
            "unique": unique, "unique_pct": round(unique / len(frame) * 100, 2),
            "most_frequent": common, "most_frequent_count": common_count,
            "examples": [str(json_value(value))[:80] for value in series.dropna().drop_duplicates().head(3)],
            "likely_id": likely_identifier(name, series),
        }
        if kind == "numeric":
            item["statistics"] = _numeric_profile(series)
        elif kind == "date":
            item["statistics"] = _date_profile(series)
        elif kind in {"categorical", "boolean"}:
            counts = series.fillna("(Missing)").astype(str).value_counts()
            rare_limit = max(2, int(len(series) * 0.01))
            item["statistics"] = {
                "category_count": unique,
                "rare_category_count": int((counts < rare_limit).sum()),
                "top_categories": [
                    {"value": str(value)[:100], "count": int(count), "pct": round(int(count) / len(series) * 100, 2)}
                    for value, count in counts.head(10).items()
                ],
            }
        else:
            item["statistics"] = {}
        profiles.append(item)
    return profiles
