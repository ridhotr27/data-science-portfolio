import pandas as pd

from app.services.advanced_eda_service import (
    correlation, distribution, insights, outliers, readiness, relationship,
    target_analysis,
)


def fixture():
    return pd.DataFrame({
        "x": list(range(1, 21)),
        "y": [value * 2 for value in range(1, 21)],
        "category": ["a", "b"] * 10,
        "target": [0, 1] * 10,
        "date": pd.date_range("2025-01-01", periods=20, freq="D").astype(str),
    })


def test_distribution_correlation_and_relationship():
    frame = fixture()
    assert len(distribution(frame, "x", {}, 10, 10, "month")["histogram"]) >= 5
    result = correlation(frame, {}, "pearson", .9, ["x", "y"])
    assert result["strong_pairs"][0]["correlation"] == 1
    relation = relationship(frame, "category", "y", None, {})
    assert relation["chart"] == "bar"


def test_outliers_target_readiness_and_insights():
    frame = fixture()
    frame.loc[len(frame)] = [1000, 2000, "a", 0, "2026-01-01"]
    result = outliers(frame, {}, "iqr", 1.5, "x", 10)
    assert result["total_rows"] == 1
    target = target_analysis(frame, "target", {}, "auto")
    assert target["problem_type"] == "binary_classification"
    assert readiness(frame, {}, "target")["status"] in {"Ready", "Ready with warnings", "Requires data cleaning"}
    assert any(item["source"] == "correlation" for item in insights(frame, {}))
