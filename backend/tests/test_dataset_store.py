import time

import pandas as pd
import pytest

from app.services.dataset_store import DatasetCapacityError, DatasetSession, DatasetStore


def session(identifier):
    return DatasetSession(identifier, "sample.csv", ".csv", "text/csv", 4, b"a\n1", pd.DataFrame({"a": [1]}), [], "CSV")


def test_store_rejects_capacity_and_expiration_cleanup():
    store = DatasetStore(ttl_seconds=1, maximum_sessions=2)
    store.put(session("one")); store.put(session("two"))
    with pytest.raises(DatasetCapacityError):
        store.put(session("three"))
    assert store.get("one") is not None
    assert store.stats()["sessions"] == 2
    store.get("two").last_accessed = time.time() - 2
    assert store.cleanup() == 1
    assert store.get("two") is None
    store.put(session("three"))
    assert store.get("three") is not None
