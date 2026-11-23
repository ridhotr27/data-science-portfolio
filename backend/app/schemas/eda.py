from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ColumnKind = Literal["numeric", "categorical", "date", "boolean"]


class TypeOverridesRequest(BaseModel):
    overrides: dict[str, ColumnKind] = Field(default_factory=dict)


class ProfileRequest(TypeOverridesRequest):
    columns: list[str] | None = None


class DistributionRequest(TypeOverridesRequest):
    column: str
    bins: int = Field(default=20, ge=5, le=100)
    top_n: int = Field(default=10, ge=5, le=30)
    date_frequency: Literal["day", "week", "month", "quarter", "year"] = "month"


class CorrelationRequest(TypeOverridesRequest):
    method: Literal["pearson", "spearman"] = "pearson"
    threshold: float = Field(default=0.7, ge=0, le=1)
    columns: list[str] | None = None


class RelationshipRequest(TypeOverridesRequest):
    x: str
    y: str
    group: str | None = None


class OutlierRequest(TypeOverridesRequest):
    method: Literal["iqr", "zscore"] = "iqr"
    threshold: float = Field(default=1.5, gt=0, le=10)
    column: str | None = None
    limit: int = Field(default=50, ge=1, le=200)


class TargetRequest(TypeOverridesRequest):
    target: str
    problem_type: Literal["auto", "binary_classification", "multiclass_classification", "regression", "time_series_regression"] = "auto"


class ExportRequest(TypeOverridesRequest):
    export_type: Literal["profiles", "quality", "correlation", "outliers", "summary"]
    method: Literal["pearson", "spearman", "iqr", "zscore"] = "pearson"
    threshold: float = Field(default=1.5, gt=0, le=10)
