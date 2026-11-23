from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def setup_dataset():
    raw = b"customer_id,order_id,date,sales,category\nC1,O1,2025-01-01,10,A\nC1,O2,2025-02-01,20,B\nC2,O3,2025-01-05,30,A\nC2,O4,2025-03-05,40,B\n"
    response = client.post("/api/datasets/upload", files={"file": ("customers.csv", raw, "text/csv")})
    dataset_id = response.json()["dataset_id"]
    mapping = {"customer_id":"customer_id","transaction_id":"order_id","transaction_date":"date","revenue":"sales","category":"category","attributes":[],"currency":"IDR"}
    configured = client.post(f"/api/customer-360/{dataset_id}/configure", json=mapping)
    assert configured.status_code == 200
    return dataset_id


def test_customer_360_workflow_and_exports():
    dataset_id = setup_dataset()
    query = {"filters":{},"active_days":90,"page":1,"page_size":25,"search":"","sort_by":"monetary","sort_direction":"desc"}
    for endpoint in ("overview","revenue","behavior","customers","insights","cohorts"):
        response = client.post(f"/api/customer-360/{dataset_id}/{endpoint}", json=query)
        assert response.status_code == 200, response.text
    rfm = client.post(f"/api/customer-360/{dataset_id}/rfm", json={**query,"scoring_groups":5,"minimum_transactions":1})
    assert rfm.status_code == 200
    profile = client.get(f"/api/customer-360/{dataset_id}/customers/C1")
    assert profile.status_code == 200
    exported = client.post(f"/api/customer-360/{dataset_id}/export", json={"export_type":"customers","filters":{}})
    assert exported.status_code == 200 and "text/csv" in exported.headers["content-type"]


def test_customer_mapping_validation_and_missing_configuration():
    response = client.post(
        "/api/datasets/upload",
        files={"file": ("small.csv", b"customer_id,value\nC1,1\nC2,2\n", "text/csv")},
    )
    dataset_id = response.json()["dataset_id"]
    unconfigured = client.post(f"/api/customer-360/{dataset_id}/overview", json={"filters": {}})
    assert unconfigured.status_code == 409
    invalid = client.post(
        f"/api/customer-360/{dataset_id}/configure",
        json={"customer_id": "missing_column", "attributes": [], "currency": "IDR"},
    )
    assert invalid.status_code == 422


def test_customer_exports_apply_aggregate_filters_and_empty_queries_work():
    dataset_id = setup_dataset()
    filters = {"minimum_revenue": 50}
    for export_type in ("customers", "rfm"):
        exported = client.post(
            f"/api/customer-360/{dataset_id}/export",
            json={"export_type": export_type, "filters": filters},
        )
        assert exported.status_code == 200
        assert "C2" in exported.text
        assert "C1" not in exported.text

    query = {"filters": {"date_from": "2030-01-01"}}
    for endpoint in ("overview", "revenue", "behavior", "customers", "insights", "cohorts"):
        response = client.post(f"/api/customer-360/{dataset_id}/{endpoint}", json=query)
        assert response.status_code == 200, response.text
    rfm = client.post(f"/api/customer-360/{dataset_id}/rfm", json={**query, "minimum_transactions": 1})
    assert rfm.status_code == 200
    assert rfm.json()["total_customers"] == 0


def test_mapping_change_invalidates_cached_customer_results():
    dataset_id = setup_dataset()
    query = {"filters": {}}
    initial = client.post(f"/api/customer-360/{dataset_id}/overview", json=query)
    assert initial.json()["summary"]["customers"] == 2
    remapped = client.post(
        f"/api/customer-360/{dataset_id}/configure",
        json={"customer_id": "order_id", "transaction_id": "order_id", "revenue": "sales", "attributes": []},
    )
    assert remapped.status_code == 200
    refreshed = client.post(f"/api/customer-360/{dataset_id}/overview", json=query)
    assert refreshed.json()["summary"]["customers"] == 4
