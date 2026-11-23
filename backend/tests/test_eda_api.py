from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def upload():
    response = client.post(
        "/api/datasets/upload",
        files={"file": ("eda.csv", b"id,amount,date\n1,10,2026-01-01\n2,,bad\n3,30,2026-01-03\n", "text/csv")},
    )
    assert response.status_code == 200
    return response.json()["dataset_id"]


def test_eda_overview_profile_quality_and_override_validation():
    dataset_id = upload()
    assert client.get(f"/api/eda/{dataset_id}/overview").status_code == 200
    profile = client.post(f"/api/eda/{dataset_id}/profile", json={"overrides": {"date": "date"}})
    assert profile.status_code == 200
    date = next(item for item in profile.json()["profiles"] if item["name"] == "date")
    assert date["statistics"]["invalid_date_count"] == 1
    quality = client.post(f"/api/eda/{dataset_id}/quality", json={"overrides": {"date": "date"}})
    assert quality.status_code == 200
    assert any(item["code"] == "invalid_dates" for item in quality.json()["issues"])
    invalid = client.post(f"/api/eda/{dataset_id}/profile", json={"overrides": {"missing": "numeric"}})
    assert invalid.status_code == 422


def test_advanced_eda_endpoints_and_export():
    dataset_id = upload()
    distribution = client.post(f"/api/eda/{dataset_id}/distribution", json={"column": "amount", "bins": 5, "overrides": {}})
    assert distribution.status_code == 200
    outliers = client.post(f"/api/eda/{dataset_id}/outliers", json={"method": "iqr", "threshold": 1.5, "overrides": {}})
    assert outliers.status_code == 200
    target = client.post(f"/api/eda/{dataset_id}/target-analysis", json={"target": "amount", "problem_type": "auto", "overrides": {}})
    assert target.status_code == 200
    exported = client.post(f"/api/eda/{dataset_id}/export", json={"export_type": "profiles", "method": "pearson", "threshold": 1.5, "overrides": {}})
    assert exported.status_code == 200
    assert "text/csv" in exported.headers["content-type"]
