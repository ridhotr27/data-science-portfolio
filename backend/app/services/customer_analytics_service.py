from __future__ import annotations

import math
import re
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from ..schemas.customer_360 import CustomerFilters, CustomerMapping
from ..utils.serialization import json_value, records

SENSITIVE = re.compile(r"(email|e-mail|phone|mobile|telephone|full.?name|first.?name|last.?name)", re.I)
ROLE_HINTS = {
    "customer_id": ["customer_id", "customerid", "customer", "user_id", "member_id", "client_id"],
    "transaction_id": ["transaction_id", "order_id", "invoice", "receipt_id"],
    "transaction_date": ["transaction_date", "order_date", "date", "purchase_date"],
    "revenue": ["revenue", "sales", "amount", "total", "net_sales"],
    "quantity": ["quantity", "qty", "units"],
    "unit_price": ["unit_price", "price"],
    "product": ["product", "product_name", "item"],
    "category": ["category", "product_category"],
    "store": ["store", "branch", "outlet"],
    "channel": ["channel", "sales_channel"],
    "registration_date": ["registration_date", "signup_date", "join_date"],
    "city": ["city", "location"],
    "gender": ["gender", "sex"],
    "age": ["age"],
}


def suggest_mapping(columns: list[str]) -> dict[str, str | None]:
    normalized = {re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_"): name for name in columns}
    suggestions = {}
    for role, hints in ROLE_HINTS.items():
        suggestions[role] = next((normalized[hint] for hint in hints if hint in normalized), None)
    return suggestions


def validate_mapping(frame: pd.DataFrame, mapping: CustomerMapping) -> dict:
    values = [value for key, value in mapping.model_dump().items() if key not in {"currency", "attributes"} and value]
    values.extend(mapping.attributes)
    missing = sorted(set(values) - set(frame.columns))
    if missing: raise ValueError(f"Mapped columns do not exist: {', '.join(missing)}")
    available = {
        "overview": True, "customer_summary": True,
        "revenue": bool(mapping.revenue or (mapping.quantity and mapping.unit_price)),
        "rfm": bool(mapping.transaction_date and (mapping.revenue or (mapping.quantity and mapping.unit_price))),
        "retention": bool(mapping.transaction_date),
        "behavior": bool(mapping.transaction_id or mapping.product or mapping.category or mapping.channel or mapping.store),
        "clv": bool(mapping.revenue or (mapping.quantity and mapping.unit_price)),
    }
    reasons = {key: None for key in available}
    if not available["revenue"]: reasons["revenue"] = "Map revenue, or both quantity and unit price."
    if not available["rfm"]: reasons["rfm"] = "RFM requires transaction date and revenue."
    if not available["retention"]: reasons["retention"] = "Retention requires a transaction date."
    if not available["behavior"]: reasons["behavior"] = "Map a transaction, product, category, store, or channel column."
    return {"available": available, "reasons": reasons}


def prepare(frame: pd.DataFrame, mapping: CustomerMapping) -> pd.DataFrame:
    work = frame.copy(deep=False)
    work["_customer_id"] = work[mapping.customer_id].astype(str)
    work = work[work[mapping.customer_id].notna() & work["_customer_id"].str.strip().ne("")]
    if mapping.transaction_date:
        work["_date"] = pd.to_datetime(work[mapping.transaction_date], errors="coerce", format="mixed")
    if mapping.revenue:
        work["_revenue"] = pd.to_numeric(work[mapping.revenue], errors="coerce").fillna(0)
    elif mapping.quantity and mapping.unit_price:
        work["_revenue"] = pd.to_numeric(work[mapping.quantity], errors="coerce").fillna(0) * pd.to_numeric(work[mapping.unit_price], errors="coerce").fillna(0)
    else:
        work["_revenue"] = 0.0
    work["_quantity"] = pd.to_numeric(work[mapping.quantity], errors="coerce").fillna(0) if mapping.quantity else 0.0
    work["_transaction"] = work[mapping.transaction_id].astype(str) if mapping.transaction_id else work.index.astype(str)
    return work


def mode_value(series: pd.Series) -> Any:
    mode = series.dropna().mode()
    return json_value(mode.iloc[0]) if len(mode) else None


def score_series(series: pd.Series, groups: int, higher_is_better: bool = True) -> pd.Series:
    ranked = series.rank(method="first", ascending=True)
    bins = min(groups, max(1, ranked.nunique()))
    if bins == 1: return pd.Series(groups, index=series.index, dtype=int)
    score = pd.qcut(ranked, q=bins, labels=False, duplicates="drop") + 1
    scaled = np.ceil(score / bins * groups).astype(int)
    return scaled if higher_is_better else groups + 1 - scaled


def segment_name(row: pd.Series, groups: int) -> str:
    high, mid = max(groups - 1, 2), max(int(np.ceil(groups / 2)), 2)
    r, f, m = row["r_score"], row["f_score"], row["m_score"]
    if r >= high and f >= high and m >= high: return "Champions"
    if r >= mid and f >= high: return "Loyal Customers"
    if r >= high and f >= mid: return "Potential Loyalists"
    if r >= high and f <= mid: return "New Customers"
    if r >= mid and f <= mid: return "Promising"
    if r < mid and f >= high and m >= high: return "Cannot Lose Them"
    if r < mid and f >= mid: return "At Risk"
    if r == 1 and f <= mid: return "Lost Customers"
    if r < mid and f < mid: return "Hibernating"
    return "Customers Needing Attention"


def customer_table(work: pd.DataFrame, mapping: CustomerMapping, groups: int = 5, reference_date: date | None = None) -> pd.DataFrame:
    if work.empty:
        columns = [
            "customer_id", "first_transaction", "last_transaction", "frequency", "monetary",
            "total_quantity", "average_transaction_value", "recency", "preferred_category",
            "preferred_channel", "preferred_store", "favorite_product", "r_score", "f_score",
            "m_score", "rfm_score", "segment", "historical_clv", "customer_lifespan_months",
            "estimated_annual_clv",
        ] + [f"attribute__{attribute}" for attribute in mapping.attributes]
        return pd.DataFrame(columns=columns)
    grouped = work.groupby("_customer_id", dropna=False)
    result = grouped.agg(
        first_transaction=("_date", "min") if "_date" in work else ("_transaction", lambda _: pd.NaT),
        last_transaction=("_date", "max") if "_date" in work else ("_transaction", lambda _: pd.NaT),
        frequency=("_transaction", "nunique"),
        monetary=("_revenue", "sum"),
        total_quantity=("_quantity", "sum"),
    )
    result["average_transaction_value"] = result["monetary"] / result["frequency"].replace(0, np.nan)
    reference = pd.Timestamp(reference_date) if reference_date else (work["_date"].max() + pd.Timedelta(days=1) if "_date" in work and work["_date"].notna().any() else pd.Timestamp.today().normalize())
    result["recency"] = (reference - result["last_transaction"]).dt.days if "_date" in work else np.nan
    for output, source in (("preferred_category", mapping.category), ("preferred_channel", mapping.channel), ("preferred_store", mapping.store), ("favorite_product", mapping.product)):
        result[output] = grouped[source].agg(mode_value) if source else None
    for attribute in mapping.attributes:
        safe = f"attribute__{attribute}"
        result[safe] = grouped[attribute].agg(mode_value)
    result["r_score"] = score_series(result["recency"].fillna(result["recency"].max() or 0), groups, False)
    result["f_score"] = score_series(result["frequency"], groups, True)
    result["m_score"] = score_series(result["monetary"], groups, True)
    result["rfm_score"] = result[["r_score", "f_score", "m_score"]].astype(str).agg("".join, axis=1)
    result["segment"] = result.apply(segment_name, axis=1, groups=groups)
    result["historical_clv"] = result["monetary"]
    if "_date" in work:
        lifespan = ((result["last_transaction"] - result["first_transaction"]).dt.days / 30).clip(lower=1)
        result["customer_lifespan_months"] = lifespan
        result["estimated_annual_clv"] = result["average_transaction_value"] * (result["frequency"] / lifespan) * 12
    else:
        result["customer_lifespan_months"] = None
        result["estimated_annual_clv"] = None
    return result.reset_index().rename(columns={"_customer_id": "customer_id"})


def apply_filters(work: pd.DataFrame, mapping: CustomerMapping, filters: CustomerFilters) -> pd.DataFrame:
    result = work
    if "_date" in result:
        if filters.date_from: result = result[result["_date"] >= pd.Timestamp(filters.date_from)]
        if filters.date_to: result = result[result["_date"] <= pd.Timestamp(filters.date_to)]
    for values, source in ((filters.stores, mapping.store), (filters.channels, mapping.channel), (filters.categories, mapping.category), (filters.cities, mapping.city), (filters.genders, mapping.gender)):
        if values and source: result = result[result[source].astype(str).isin(values)]
    if mapping.age:
        age = pd.to_numeric(result[mapping.age], errors="coerce")
        if filters.age_min is not None: result = result[age >= filters.age_min]
        if filters.age_max is not None: result = result[age <= filters.age_max]
    return result


def overview(frame: pd.DataFrame, mapping: CustomerMapping, filters: CustomerFilters, active_days: int) -> dict:
    work = apply_filters(prepare(frame, mapping), mapping, filters)
    customers = customer_table(work, mapping) if len(work) else pd.DataFrame()
    if len(customers):
        if filters.minimum_revenue is not None: customers = customers[customers.monetary >= filters.minimum_revenue]
        if filters.minimum_transactions is not None: customers = customers[customers.frequency >= filters.minimum_transactions]
    revenue = float(work[work["_customer_id"].isin(customers.customer_id)]["_revenue"].sum()) if len(customers) else 0
    latest = work["_date"].max() if "_date" in work and work["_date"].notna().any() else None
    active = int((customers.last_transaction >= latest - pd.Timedelta(days=active_days)).sum()) if latest is not None and len(customers) else None
    returning = int((customers.frequency > 1).sum()) if len(customers) else 0
    summary = {
        "rows": len(work), "customers": len(customers), "transactions": int(work["_transaction"].nunique()),
        "revenue": revenue, "average_transaction_value": revenue / max(int(work["_transaction"].nunique()), 1),
        "average_revenue_per_customer": revenue / max(len(customers), 1),
        "median_revenue_per_customer": float(customers.monetary.median()) if len(customers) else 0,
        "new_customers": len(customers) - returning, "returning_customers": returning,
        "active_customers": active, "inactive_customers": len(customers) - active if active is not None else None,
        "date_from": json_value(work["_date"].min()) if "_date" in work else None,
        "date_to": json_value(work["_date"].max()) if "_date" in work else None,
        "products": int(work[mapping.product].nunique()) if mapping.product else None,
        "categories": int(work[mapping.category].nunique()) if mapping.category else None,
    }
    return {"summary": summary, "result_count": len(work)}


def revenue_analysis(frame: pd.DataFrame, mapping: CustomerMapping, filters: CustomerFilters) -> dict:
    work = apply_filters(prepare(frame, mapping), mapping, filters)
    customers = work.groupby("_customer_id")["_revenue"].sum().sort_values(ascending=False)
    total = customers.sum()
    pareto = []
    for percentile in (10, 20, 30):
        count = max(1, math.ceil(len(customers) * percentile / 100))
        contribution = float(customers.head(count).sum() / total * 100) if total else 0
        pareto.append({"customer_percentile": percentile, "revenue_contribution_pct": round(contribution, 2)})
    def group(source):
        if not source: return []
        values = work.groupby(source, dropna=False)["_revenue"].sum().sort_values(ascending=False).head(20)
        return [{"label": str(key), "revenue": float(value)} for key, value in values.items()]
    trend = []
    if "_date" in work:
        values = work.dropna(subset=["_date"]).set_index("_date")["_revenue"].resample("ME").sum()
        trend = [{"period": str(index.to_period("M")), "revenue": float(value)} for index, value in values.items()]
    return {"top_customers": [{"customer_id": str(key), "revenue": float(value)} for key, value in customers.head(20).items()], "pareto": pareto, "by_category": group(mapping.category), "by_channel": group(mapping.channel), "by_store": group(mapping.store), "trend": trend}


def rfm_analysis(frame: pd.DataFrame, mapping: CustomerMapping, filters: CustomerFilters, groups: int, reference_date: date | None, minimum_transactions: int) -> dict:
    work = apply_filters(prepare(frame, mapping), mapping, filters)
    table = customer_table(work, mapping, groups, reference_date)
    table = table[table.frequency >= minimum_transactions]
    if filters.segments: table = table[table.segment.isin(filters.segments)]
    if filters.minimum_revenue is not None: table = table[table.monetary >= filters.minimum_revenue]
    if filters.minimum_transactions is not None: table = table[table.frequency >= filters.minimum_transactions]
    grouped = table.groupby("segment", dropna=False).agg(customers=("customer_id", "count"), revenue=("monetary", "sum"), average_recency=("recency", "mean"), average_frequency=("frequency", "mean"), average_monetary=("monetary", "mean")).reset_index()
    grouped["customer_pct"] = grouped.customers / max(len(table), 1) * 100
    return {
        "segments": records(grouped.sort_values("customers", ascending=False)),
        "customers": records(table.sort_values("monetary", ascending=False).head(100)),
        "total_customers": len(table),
        "rules": [
            "Scores use rank-based quantile groups so tied values are handled deterministically.",
            "Higher frequency and monetary values receive higher scores.",
            "More recent customers receive higher recency scores.",
            "Champions have high scores across recency, frequency, and monetary value.",
            "At Risk and Cannot Lose Them customers purchased less recently but previously had meaningful frequency or value.",
            "Estimated annual CLV extrapolates observed average order value and purchase frequency; it is not guaranteed future revenue.",
        ],
    }


def behavior_analysis(frame: pd.DataFrame, mapping: CustomerMapping, filters: CustomerFilters) -> dict:
    work = apply_filters(prepare(frame, mapping), mapping, filters)
    transaction_count = max(work["_transaction"].nunique(), 1)
    def frequency(source, name):
        if not source: return []
        counts = work[source].fillna("(Missing)").astype(str).value_counts().head(20)
        return [{name: str(key), "count": int(value)} for key, value in counts.items()]
    day = []
    hour = []
    if "_date" in work:
        day_counts = work["_date"].dt.day_name().value_counts()
        day = [{"label": key, "count": int(value)} for key, value in day_counts.items()]
        if work["_date"].dt.hour.nunique() > 1:
            hour_counts = work["_date"].dt.hour.value_counts().sort_index()
            hour = [{"label": str(key), "count": int(value)} for key, value in hour_counts.items()]
    return {
        "summary": {
            "average_basket_value": float(work.groupby("_transaction")["_revenue"].sum().mean()) if len(work) else 0,
            "average_items_per_transaction": float(work.groupby("_transaction")["_quantity"].sum().mean()) if mapping.quantity and len(work) else None,
            "products_per_customer": float(work.groupby("_customer_id")[mapping.product].nunique().mean()) if mapping.product and len(work) else None,
            "transactions": transaction_count,
        },
        "products": frequency(mapping.product, "label"), "categories": frequency(mapping.category, "label"),
        "channels": frequency(mapping.channel, "label"), "stores": frequency(mapping.store, "label"),
        "purchase_day": day, "purchase_hour": hour,
    }


def cohort_analysis(frame: pd.DataFrame, mapping: CustomerMapping, filters: CustomerFilters) -> dict:
    if not mapping.transaction_date: raise ValueError("Cohort analysis requires a transaction date.")
    work = apply_filters(prepare(frame, mapping), mapping, filters).dropna(subset=["_date"])
    if work.empty: return {"matrix": [], "average_retention": [], "new_returning_trend": []}
    work["_period"] = work["_date"].dt.to_period("M")
    work["_cohort"] = work.groupby("_customer_id")["_period"].transform("min")
    work["_month_number"] = (work["_period"].dt.year - work["_cohort"].dt.year) * 12 + work["_period"].dt.month - work["_cohort"].dt.month
    counts = work.groupby(["_cohort", "_month_number"])["_customer_id"].nunique().unstack(fill_value=0)
    sizes = counts.iloc[:, 0].replace(0, np.nan)
    retention = counts.divide(sizes, axis=0) * 100
    matrix = [{"cohort": str(index), "cohort_size": int(counts.loc[index].iloc[0]), **{f"month_{int(column)}": round(float(value), 2) for column, value in row.items()}} for index, row in retention.iterrows()]
    averages = [{"month": int(column), "retention_pct": round(float(retention[column].mean()), 2)} for column in retention.columns]
    first_period = work.groupby("_customer_id")["_period"].min()
    monthly = []
    for period, subset in work.groupby("_period"):
        customers = set(subset["_customer_id"])
        new = sum(first_period.get(customer) == period for customer in customers)
        monthly.append({"period": str(period), "new_customers": new, "returning_customers": len(customers) - new})
    return {"matrix": matrix, "average_retention": averages, "new_returning_trend": monthly}


def mask_value(column: str, value: Any) -> Any:
    if value is None or not SENSITIVE.search(column): return json_value(value)
    text = str(value)
    if "@" in text:
        local, domain = text.split("@", 1)
        return f"{local[:1]}***@{domain}"
    return f"{text[:1]}***{text[-1:]}" if len(text) > 1 else "***"


def customer_profile(frame: pd.DataFrame, mapping: CustomerMapping, customer_id: str) -> dict:
    work = prepare(frame, mapping)
    rows = work[work["_customer_id"] == str(customer_id)]
    if rows.empty: raise ValueError("Customer not found.")
    summary = customer_table(rows, mapping).iloc[0].to_dict()
    attributes = {name: mask_value(name, mode_value(rows[name])) for name in mapping.attributes}
    transactions = rows.sort_values("_date", ascending=False) if "_date" in rows else rows
    safe_columns = [column for column in frame.columns if not SENSITIVE.search(column)]
    trend = []
    if "_date" in rows:
        values = rows.dropna(subset=["_date"]).set_index("_date")["_revenue"].resample("ME").sum()
        trend = [{"period": str(index.to_period("M")), "revenue": float(value)} for index, value in values.items()]
    return {"summary": {key: json_value(value) for key, value in summary.items()}, "attributes": attributes, "recent_transactions": records(transactions[safe_columns].head(25)), "revenue_trend": trend, "masked_columns": [column for column in frame.columns if SENSITIVE.search(column)]}


def customer_page(frame: pd.DataFrame, mapping: CustomerMapping, filters: CustomerFilters, page: int, page_size: int, search: str, sort_by: str, direction: str) -> dict:
    table = customer_table(apply_filters(prepare(frame, mapping), mapping, filters), mapping)
    if filters.segments: table = table[table.segment.isin(filters.segments)]
    if filters.minimum_revenue is not None: table = table[table.monetary >= filters.minimum_revenue]
    if filters.minimum_transactions is not None: table = table[table.frequency >= filters.minimum_transactions]
    if search: table = table[table.customer_id.astype(str).str.contains(search, case=False, regex=False)]
    allowed = set(table.columns)
    sort = sort_by if sort_by in allowed else "monetary"
    table = table.sort_values(sort, ascending=direction == "asc", na_position="last")
    total = len(table); start = (page - 1) * page_size
    return {"total": total, "page": page, "page_size": page_size, "rows": records(table.iloc[start:start + page_size])}


def generated_customer_insights(frame: pd.DataFrame, mapping: CustomerMapping, filters: CustomerFilters) -> dict:
    work = apply_filters(prepare(frame, mapping), mapping, filters)
    table = customer_table(work, mapping)
    findings, recommendations = [], []
    if len(table) and table.monetary.sum():
        top_count = max(1, math.ceil(len(table) * .2))
        contribution = table.nlargest(top_count, "monetary").monetary.sum() / table.monetary.sum() * 100
        findings.append(f"The top 20% of customers generated {contribution:.1f}% of historical revenue.")
        if contribution >= 60: recommendations.append("Review differentiated retention treatment for high-value customers while monitoring concentration risk.")
    at_risk = table[table.segment.isin(["At Risk", "Cannot Lose Them"])]
    if len(table):
        findings.append(f"At Risk and Cannot Lose Them segments contain {len(at_risk) / len(table) * 100:.1f}% of customers and contributed {at_risk.monetary.sum() / max(table.monetary.sum(), 1) * 100:.1f}% of historical revenue.")
        if len(at_risk): recommendations.append("Consider a targeted re-engagement campaign for historically valuable customers whose recent activity has declined.")
    if mapping.category and len(work):
        category = work[mapping.category].value_counts().index[0]
        findings.append(f"{category} is the most frequently recorded product category.")
    if "_date" in work and len(work):
        retention = cohort_analysis(frame, mapping, filters)["average_retention"]
        if len(retention) > 2 and retention[2]["retention_pct"] < retention[1]["retention_pct"]:
            findings.append(f"Average cohort retention falls from {retention[1]['retention_pct']:.1f}% in month 1 to {retention[2]['retention_pct']:.1f}% in month 2.")
            recommendations.append("Review onboarding and follow-up activity before the second post-acquisition month.")
    return {"findings": findings, "recommendations": recommendations}
