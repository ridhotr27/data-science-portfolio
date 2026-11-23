from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class CustomerMapping(BaseModel):
    customer_id: str
    transaction_date: str | None = None
    transaction_id: str | None = None
    revenue: str | None = None
    quantity: str | None = None
    unit_price: str | None = None
    product: str | None = None
    category: str | None = None
    store: str | None = None
    channel: str | None = None
    registration_date: str | None = None
    city: str | None = None
    gender: str | None = None
    age: str | None = None
    attributes: list[str] = Field(default_factory=list)
    currency: str = Field(default="IDR", max_length=8)


class CustomerFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    segments: list[str] = Field(default_factory=list)
    stores: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    genders: list[str] = Field(default_factory=list)
    age_min: float | None = None
    age_max: float | None = None
    minimum_revenue: float | None = None
    minimum_transactions: int | None = Field(default=None, ge=0)


class CustomerQuery(BaseModel):
    filters: CustomerFilters = Field(default_factory=CustomerFilters)
    active_days: int = Field(default=90, ge=1, le=730)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    search: str = Field(default="", max_length=200)
    sort_by: str = "monetary"
    sort_direction: Literal["asc", "desc"] = "desc"


class RfmRequest(CustomerQuery):
    reference_date: date | None = None
    scoring_groups: int = Field(default=5, ge=3, le=10)
    minimum_transactions: int = Field(default=1, ge=1)


class ExportRequest(BaseModel):
    export_type: Literal["customers", "rfm", "cohorts", "summary", "insights"]
    filters: CustomerFilters = Field(default_factory=CustomerFilters)
