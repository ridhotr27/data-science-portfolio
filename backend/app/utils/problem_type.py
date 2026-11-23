from __future__ import annotations

import pandas as pd


def suggest_problem(series: pd.Series) -> dict[str, str]:
    clean = series.dropna()
    unique = series.nunique(dropna=True)
    if unique == 2:
        return {"type": "binary_classification", "reason": "The target contains exactly two unique values."}
    if not pd.api.types.is_numeric_dtype(clean) or unique <= min(20, max(3, int(len(clean) * 0.05))):
        return {"type": "multiclass_classification", "reason": f"The target contains {unique} discrete values."}
    return {"type": "regression", "reason": "The target is numeric with many distinct values, suggesting a continuous outcome."}
