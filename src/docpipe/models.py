from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Source(str, Enum):
    postgres_docs = "postgres-docs"
    pgvector = "pgvector"


class Status(str, Enum):
    live = "live"
    tombstoned = "tombstoned"
    quarantined = "quarantined"


class LicenseRow(BaseModel):
    file: str
    source: Source
    license: str
    license_url: str
    origin_url: str

    @field_validator("file")
    @classmethod
    def no_path_escape(cls, value: str) -> str:
        if "/" in value or "\\" in value or value in {".", ".."}:
            raise ValueError("file must be a basename")
        return value


class ExtractResult(BaseModel):
    uri: str
    source: Source
    text: str
    content_hash: str
    bytes: int = Field(ge=0)
    char_count: int = Field(ge=0)
    empty: bool


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    uri: str
    source: str
    ordinal: int
    body: str
    score: float
