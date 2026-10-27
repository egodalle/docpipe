from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator

_SOURCE_RE = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


class Source(str, Enum):
    postgres_docs = "postgres-docs"
    pgvector = "pgvector"


def source_value(source: str | Source) -> str:
    if isinstance(source, Enum):
        return str(source.value)
    return str(source)


def normalize_source(value: str) -> str:
    slug = (value or "").strip().lower()
    if not _SOURCE_RE.fullmatch(slug):
        raise ValueError("source must be a lowercase slug (a-z, 0-9, hyphen)")
    return slug


class Status(str, Enum):
    live = "live"
    tombstoned = "tombstoned"
    quarantined = "quarantined"


class LicenseRow(BaseModel):
    file: str
    source: str
    license: str
    license_url: str
    origin_url: str

    @field_validator("file")
    @classmethod
    def no_path_escape(cls, value: str) -> str:
        if "/" in value or "\\" in value or value in {".", ".."}:
            raise ValueError("file must be a basename")
        return value

    @field_validator("source")
    @classmethod
    def source_slug(cls, value: str) -> str:
        return normalize_source(source_value(value))


class ExtractResult(BaseModel):
    uri: str
    source: str
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
