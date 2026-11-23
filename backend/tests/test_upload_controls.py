import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.services.file_service import MAX_BYTES
from app.services.upload_limiter import UploadRateLimiter


client = TestClient(app)


def test_exact_file_size_boundary_is_accepted():
    raw = b"value\n" + b"x" * (MAX_BYTES - len(b"value\n") - 1) + b"\n"
    assert len(raw) == MAX_BYTES
    response = client.post(
        "/api/datasets/upload",
        files={"file": ("boundary.csv", raw, "text/csv")},
    )
    assert response.status_code == 200, response.text


def test_upload_size_limit_and_session_capacity():
    oversized = client.post(
        "/api/datasets/upload",
        files={"file": ("large.csv", b"a\n" + b"1" * MAX_BYTES, "text/csv")},
    )
    assert oversized.status_code == 413
    assert "5 MB" in oversized.json()["detail"]

    identifiers = []
    for index in range(3):
        response = client.post(
            "/api/datasets/upload",
            files={"file": (f"sample-{index}.csv", b"a\n1\n", "text/csv")},
        )
        assert response.status_code == 200
        identifiers.append(response.json()["dataset_id"])
    rejected = client.post(
        "/api/datasets/upload",
        files={"file": ("fourth.csv", b"a\n1\n", "text/csv")},
    )
    assert rejected.status_code == 429
    assert "3 active datasets" in rejected.json()["detail"]


def test_upload_rate_limiter_boundary():
    limiter = UploadRateLimiter(maximum=2, window_seconds=60)
    limiter.check("client", now=1)
    limiter.check("client", now=2)
    with pytest.raises(HTTPException) as caught:
        limiter.check("client", now=3)
    assert caught.value.status_code == 429
    limiter.check("client", now=62)


def test_xgboost_endpoints_are_disabled():
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("sample.csv", b"a\n1\n", "text/csv")},
    )
    assert upload.status_code == 503
    assert "temporarily unavailable" in upload.json()["detail"].lower()
    assert client.get("/api/ml/train/unknown/status").status_code == 503
    assert client.get("/api/ml/results/unknown").status_code == 503
    assert client.get("/api/ml/download/unknown/metrics").status_code == 503
