import pytest

from app.services.dataset_store import dataset_store
from app.services.upload_limiter import upload_limiter


@pytest.fixture(autouse=True)
def isolate_in_memory_state():
    dataset_store.clear()
    upload_limiter.clear()
    yield
    dataset_store.clear()
    upload_limiter.clear()
