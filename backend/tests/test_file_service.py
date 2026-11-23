import io

import pandas as pd
import pytest
from fastapi import HTTPException

from app.services.file_service import MAX_COLUMNS, MAX_ROWS, parse_bytes, validate_frame


def test_csv_parsing_and_duplicate_headers():
    frame, sheets, active = parse_bytes(b"a,a\n1,2\n3,4\n", ".csv")
    assert list(frame.columns) == ["a", "a_duplicated_0"] or list(frame.columns) == ["a", "a.1"]
    assert sheets == []
    assert active == "CSV"


def test_xlsx_parsing_and_sheet_selection():
    raw = io.BytesIO()
    with pd.ExcelWriter(raw, engine="openpyxl") as writer:
        pd.DataFrame({"first": [1]}).to_excel(writer, sheet_name="One", index=False)
        pd.DataFrame({"second": [2]}).to_excel(writer, sheet_name="Two", index=False)
    frame, sheets, active = parse_bytes(raw.getvalue(), ".xlsx", "Two")
    assert sheets == ["One", "Two"]
    assert active == "Two"
    assert list(frame.columns) == ["second"]


def test_empty_frame_rejected():
    with pytest.raises(HTTPException):
        validate_frame(pd.DataFrame(columns=["a"]))


def test_excessively_wide_dataset_rejected():
    frame = pd.DataFrame([[1] * (MAX_COLUMNS + 1)], columns=[f"column_{index}" for index in range(MAX_COLUMNS + 1)])
    with pytest.raises(HTTPException) as caught:
        validate_frame(frame)
    assert caught.value.status_code == 413


def test_row_and_column_boundaries():
    validate_frame(pd.DataFrame({"value": range(MAX_ROWS)}))
    validate_frame(pd.DataFrame([[1] * MAX_COLUMNS], columns=[f"column_{index}" for index in range(MAX_COLUMNS)]))
    with pytest.raises(HTTPException) as caught:
        validate_frame(pd.DataFrame({"value": range(MAX_ROWS + 1)}))
    assert caught.value.status_code == 413
