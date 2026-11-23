import numpy as np
import pandas as pd

from app.services.data_quality_service import analyze_quality
from app.services.eda_profiling_service import detailed_profile


def fixture():
    return pd.DataFrame({
        "customer_id": ["a", "b", "c", "d", "e"],
        "amount": [0, 10, 20, 30, 1000],
        "segment": ["A", "A", "B", "A", None],
        "event_date": ["2026-01-01", "invalid", "2026-01-03", None, "2026-01-05"],
        "blank": ["", " ", "ok", "ok", "ok"],
        "rate_pct": [10, 20, 130, 40, np.inf],
        "constant": [1, 1, 1, 1, 1],
    })


def test_detailed_numeric_categorical_and_date_profiles():
    profiles = {item["name"]: item for item in detailed_profile(fixture(), {"event_date": "date"})}
    assert profiles["amount"]["statistics"]["median"] == 20
    assert profiles["segment"]["statistics"]["category_count"] == 2
    assert profiles["event_date"]["statistics"]["invalid_date_count"] == 1
    assert profiles["customer_id"]["likely_id"] is True


def test_quality_findings_have_evidence_and_actions():
    result = analyze_quality(fixture(), {"event_date": "date"})
    codes = {item["code"] for item in result["issues"]}
    assert {"missing_values", "constant_column", "invalid_dates", "whitespace_values", "infinite_values", "impossible_percentage"} <= codes
    assert all(item["detail"] and item["suggested_action"] for item in result["issues"])
