from __future__ import annotations

import json

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from .datasets import require_dataset
from ..schemas.customer_360 import CustomerMapping, CustomerQuery, ExportRequest, RfmRequest
from ..services.customer_analytics_service import (
    apply_filters, behavior_analysis, cohort_analysis, customer_page, customer_profile,
    customer_table, generated_customer_insights, overview, prepare,
    revenue_analysis, rfm_analysis, suggest_mapping, validate_mapping,
)
from ..services.dataset_store import cached_analysis, invalidate_analysis
from ..utils.csv_security import protect_csv

router = APIRouter(prefix="/api/customer-360", tags=["customer-360"])


def configured(dataset_id: str):
    session = require_dataset(dataset_id)
    raw = session.cache.get("customer_360_mapping")
    if not raw: raise HTTPException(409, "Configure Customer 360 column mappings first.")
    return session, CustomerMapping.model_validate(raw)


def execute(function, *args):
    try: return function(*args)
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc


@router.get("/{dataset_id}/suggestions")
def suggestions(dataset_id: str):
    session = require_dataset(dataset_id)
    return {"dataset_id": dataset_id, "suggestions": suggest_mapping(list(session.frame.columns))}


@router.post("/{dataset_id}/configure")
def configure(dataset_id: str, mapping: CustomerMapping):
    session = require_dataset(dataset_id)
    availability = execute(validate_mapping, session.frame, mapping)
    invalidate_analysis(session, "customer360.")
    session.cache["customer_360_mapping"] = mapping.model_dump()
    return {"dataset_id": dataset_id, "mapping": mapping.model_dump(), **availability}


@router.post("/{dataset_id}/overview")
def customer_overview(dataset_id: str, query: CustomerQuery):
    session, mapping = configured(dataset_id)
    result = cached_analysis(session, "customer360.overview", query.model_dump(mode="json"), lambda: overview(session.frame, mapping, query.filters, query.active_days))
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/revenue")
def customer_revenue(dataset_id: str, query: CustomerQuery):
    session, mapping = configured(dataset_id)
    result = cached_analysis(session, "customer360.revenue", query.model_dump(mode="json"), lambda: revenue_analysis(session.frame, mapping, query.filters))
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/rfm")
def customer_rfm(dataset_id: str, request: RfmRequest):
    session, mapping = configured(dataset_id)
    result = cached_analysis(session, "customer360.rfm", request.model_dump(mode="json"), lambda: rfm_analysis(session.frame, mapping, request.filters, request.scoring_groups, request.reference_date, request.minimum_transactions))
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/cohorts")
def customer_cohorts(dataset_id: str, query: CustomerQuery):
    session, mapping = configured(dataset_id)
    result = cached_analysis(session, "customer360.cohorts", query.model_dump(mode="json"), lambda: execute(cohort_analysis, session.frame, mapping, query.filters))
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/behavior")
def customer_behavior(dataset_id: str, query: CustomerQuery):
    session, mapping = configured(dataset_id)
    result = cached_analysis(session, "customer360.behavior", query.model_dump(mode="json"), lambda: behavior_analysis(session.frame, mapping, query.filters))
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/customers")
def customers(dataset_id: str, query: CustomerQuery):
    session, mapping = configured(dataset_id)
    result = cached_analysis(session, "customer360.customers", query.model_dump(mode="json"), lambda: customer_page(session.frame, mapping, query.filters, query.page, query.page_size, query.search, query.sort_by, query.sort_direction))
    return {"dataset_id": dataset_id, **result}


@router.get("/{dataset_id}/customers/{customer_id}")
def one_customer(dataset_id: str, customer_id: str):
    session, mapping = configured(dataset_id)
    result = cached_analysis(session, "customer360.profile", customer_id, lambda: execute(customer_profile, session.frame, mapping, customer_id))
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/insights")
def customer_insights(dataset_id: str, query: CustomerQuery):
    session, mapping = configured(dataset_id)
    result = cached_analysis(session, "customer360.insights", query.model_dump(mode="json"), lambda: generated_customer_insights(session.frame, mapping, query.filters))
    return {"dataset_id": dataset_id, **result}


@router.post("/{dataset_id}/export")
def customer_export(dataset_id: str, request: ExportRequest):
    session, mapping = configured(dataset_id)
    if request.export_type in {"customers", "rfm"}:
        work = apply_filters(prepare(session.frame, mapping), mapping, request.filters)
        table = customer_table(work, mapping)
        if request.filters.segments: table = table[table.segment.isin(request.filters.segments)]
        if request.filters.minimum_revenue is not None: table = table[table.monetary >= request.filters.minimum_revenue]
        if request.filters.minimum_transactions is not None: table = table[table.frequency >= request.filters.minimum_transactions]
        payload, media, suffix = protect_csv(table).to_csv(index=False), "text/csv", "csv"
    elif request.export_type == "cohorts":
        data = execute(cohort_analysis, session.frame, mapping, request.filters)
        payload, media, suffix = protect_csv(pd.DataFrame(data["matrix"])).to_csv(index=False), "text/csv", "csv"
    else:
        data = generated_customer_insights(session.frame, mapping, request.filters)
        if request.export_type == "summary": data["overview"] = overview(session.frame, mapping, request.filters, 90)["summary"]
        payload, media, suffix = json.dumps(data, indent=2), "application/json", "json"
    return Response(payload, media_type=media, headers={"Content-Disposition": f'attachment; filename="customer_360_{request.export_type}.{suffix}"'})
