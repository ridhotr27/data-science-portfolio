from __future__ import annotations

from pydantic import BaseModel, Field


class SheetRequest(BaseModel):
    sheet: str = Field(min_length=1, max_length=200)


class PreviewQuery(BaseModel):
    mode: str = "first"
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=25, ge=1, le=100)
