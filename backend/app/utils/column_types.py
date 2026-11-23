from __future__ import annotations

import re

import pandas as pd

ID_PATTERN = re.compile(r"(^id$|_id$|^uuid$|uuid$)", re.I)


def detect_kind(series: pd.Series) -> str:
    clean = series.dropna()
    if not len(clean) or clean.nunique() <= 1:
        return "constant"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    parsed = pd.to_datetime(clean.astype(str), errors="coerce", format="mixed")
    if len(clean) >= 3 and parsed.notna().mean() > 0.9:
        return "date"
    return "categorical"


def likely_identifier(name: str, series: pd.Series) -> bool:
    unique = int(series.nunique(dropna=True))
    return bool(ID_PATTERN.search(name)) or (len(series) > 10 and unique / len(series) > 0.98)
