import pandas as pd

from app.schemas.customer_360 import CustomerFilters, CustomerMapping
from app.services.customer_analytics_service import (
    behavior_analysis, cohort_analysis, customer_page, customer_profile,
    generated_customer_insights, overview, revenue_analysis, rfm_analysis,
    suggest_mapping, validate_mapping,
)


def fixture():
    rows = []
    for customer in range(1, 7):
        for month in range(1, 5):
            rows.append({
                "customer_id": f"C{customer}", "order_id": f"O{customer}-{month}",
                "date": f"2025-{month:02d}-{customer:02d}", "sales": customer * month * 10,
                "qty": month, "product": f"P{month % 2}", "category": "Food" if month % 2 else "Home",
                "channel": "Online" if customer % 2 else "Store", "email": f"c{customer}@example.com",
            })
    return pd.DataFrame(rows)


def mapping():
    return CustomerMapping(customer_id="customer_id", transaction_id="order_id", transaction_date="date", revenue="sales", quantity="qty", product="product", category="category", channel="channel", attributes=["email"])


def test_mapping_overview_revenue_and_behavior():
    frame = fixture(); mapped = mapping(); filters = CustomerFilters()
    assert suggest_mapping(list(frame.columns))["customer_id"] == "customer_id"
    assert validate_mapping(frame, mapped)["available"]["rfm"] is True
    assert overview(frame, mapped, filters, 90)["summary"]["customers"] == 6
    assert revenue_analysis(frame, mapped, filters)["pareto"][1]["customer_percentile"] == 20
    assert behavior_analysis(frame, mapped, filters)["products"]


def test_rfm_cohorts_customer_page_profile_and_insights():
    frame = fixture(); mapped = mapping(); filters = CustomerFilters()
    rfm = rfm_analysis(frame, mapped, filters, 5, None, 1)
    assert rfm["total_customers"] == 6
    assert all(row["segment"] for row in rfm["customers"])
    cohorts = cohort_analysis(frame, mapped, filters)
    assert cohorts["matrix"][0]["month_0"] == 100
    page = customer_page(frame, mapped, filters, 1, 2, "C", "monetary", "desc")
    assert page["total"] == 6 and len(page["rows"]) == 2
    profile = customer_profile(frame, mapped, "C1")
    assert profile["attributes"]["email"].startswith("c***@")
    output = generated_customer_insights(frame, mapped, filters)
    assert output["findings"]


def test_empty_filtered_customer_results_are_safe():
    frame = fixture(); mapped = mapping()
    filters = CustomerFilters(date_from="2030-01-01")
    assert overview(frame, mapped, filters, 90)["summary"]["customers"] == 0
    assert revenue_analysis(frame, mapped, filters)["top_customers"] == []
    assert rfm_analysis(frame, mapped, filters, 5, None, 1)["total_customers"] == 0
    assert cohort_analysis(frame, mapped, filters)["matrix"] == []
    assert customer_page(frame, mapped, filters, 1, 25, "", "monetary", "desc")["rows"] == []
