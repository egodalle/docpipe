from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
LICENSES_CSV = DATA_DIR / "licenses.csv"
RAW_DIR = DATA_DIR / "raw"
QUARANTINE_DIR = DATA_DIR / "quarantine"
CONFIG_PATH = ROOT / "config.yaml"
SQL_DIR = ROOT / "sql"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://docpipe:docpipe@127.0.0.1:5433/docpipe",
)
GCS_BUCKET = os.environ.get("DOCS_BUCKET", "docpipe-p1-corpus-129492415939")
EMPTY_EXTRACT_FAIL = 0.05
USER_AGENT = "DocPipe/0.1 (https://github.com/egodalle/docpipe)"

SQL_DIM = 768


@dataclass(frozen=True)
class AppConfig:
    embedding_model: str
    embedding_dim: int
    embedding_batch_size: int
    generation_model: str
    chunk_strategy: str
    chunk_size: int
    chunk_overlap: int
    gcp_project: str
    gcp_location: str


@lru_cache(maxsize=1)
def load_config() -> AppConfig:
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    embedding = raw["embedding"]
    chunk = raw["chunk"]
    gcp = raw["gcp"]
    generation = raw.get("generation") or {}
    dim = int(embedding["dim"])
    if dim != SQL_DIM:
        raise ValueError(
            f"config embedding.dim {dim} != sql/001_init.sql vector({SQL_DIM}); "
            "ALTER embeddings and amend ADR 0003 before changing this"
        )
    return AppConfig(
        embedding_model=str(embedding["model"]),
        embedding_dim=dim,
        embedding_batch_size=int(embedding.get("batch_size") or 100),
        generation_model=str(generation.get("model") or "gemini-2.0-flash"),
        chunk_strategy=str(chunk["strategy"]),
        chunk_size=int(chunk["size"]),
        chunk_overlap=int(chunk["overlap"]),
        gcp_project=os.environ.get("GOOGLE_CLOUD_PROJECT") or str(gcp["project"]),
        gcp_location=os.environ.get("GCP_REGION") or str(gcp["location"]),
    )


_CFG = load_config()
EMBEDDING_MODEL = _CFG.embedding_model
EMBEDDING_DIM = _CFG.embedding_dim
EMBEDDING_BATCH = _CFG.embedding_batch_size
GENERATION_MODEL = _CFG.generation_model
CHUNK_STRATEGY = _CFG.chunk_strategy
CHUNK_SIZE = _CFG.chunk_size
CHUNK_OVERLAP = _CFG.chunk_overlap
GCP_PROJECT = _CFG.gcp_project
GCP_LOCATION = _CFG.gcp_location
