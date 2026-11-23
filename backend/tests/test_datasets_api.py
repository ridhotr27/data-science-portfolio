from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dataset_upload_preview_schema_delete():
    response = client.post(
        "/api/datasets/upload",
        files={"file": ("sample.csv", b"id,value\n1,10\n2,20\n3,\n", "text/csv")},
    )
    assert response.status_code == 200
    payload = response.json()
    dataset_id = payload["dataset_id"]
    assert payload["summary"]["rows"] == 3
    assert payload["summary"]["missing_values"] == 1
    assert client.get(f"/api/datasets/{dataset_id}/schema").status_code == 200
    preview = client.get(f"/api/datasets/{dataset_id}/preview?limit=2").json()
    assert len(preview["rows"]) == 2
    assert client.delete(f"/api/datasets/{dataset_id}").status_code == 200
    assert client.get(f"/api/datasets/{dataset_id}/schema").status_code == 404


def test_invalid_extension_and_empty_file():
    invalid = client.post("/api/datasets/upload", files={"file": ("bad.txt", b"x", "text/plain")})
    assert invalid.status_code == 415
    empty = client.post("/api/datasets/upload", files={"file": ("empty.csv", b"", "text/csv")})
    assert empty.status_code == 400


def test_mime_content_and_pagination_validation():
    wrong_mime = client.post("/api/datasets/upload", files={"file": ("bad.csv", b"a\n1\n", "image/png")})
    assert wrong_mime.status_code == 415
    binary = client.post("/api/datasets/upload", files={"file": ("bad.csv", b"a\x00b\n1\n", "text/csv")})
    assert binary.status_code == 415
    dataset = client.post("/api/datasets/upload", files={"file": ("ok.csv", b"a\n1\n2\n3\n", "text/csv")}).json()
    invalid_limit = client.get(f"/api/datasets/{dataset['dataset_id']}/preview?limit=101")
    assert invalid_limit.status_code == 422
