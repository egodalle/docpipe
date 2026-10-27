from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml


def _repo_root() -> Path:
    env = os.environ.get("DOCS_ROOT")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    src_layout = here.parents[2]
    for candidate in (src_layout, Path.cwd(), Path("/app")):
        if (candidate / "config.yaml").is_file():
            return candidate
    return src_layout


ROOT = _repo_root()
DATA_DIR = ROOT / "data"
LICENSES_CSV = DATA_DIR / "licenses.csv"
RAW_DIR = DATA_DIR / "raw"
QUARANTINE_DIR = DATA_DIR / "quarantine"
CONFIG_PATH = Path(os.environ.get("DOCS_CONFIG") or (ROOT / "config.yaml"))
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
    generation_location: str
    refuse_min_score: float
    question_max_chars: int
    k_default: int
    k_max: int
    max_context_chars: int
    unique_documents: bool
    eval_pool_k: int
    hybrid_retrieval: bool
    rrf_k: int
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
    serve = raw.get("serve") or {}
    evaluation = raw.get("eval") or {}
    retrieval = raw.get("retrieval") or {}
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
        generation_model=str(generation.get("model") or "gemini-3-flash-preview"),
        generation_location=str(generation.get("location") or "global"),
        refuse_min_score=float(serve.get("refuse_min_score") or 0.60),
        question_max_chars=int(serve.get("question_max_chars") or 2000),
        k_default=int(serve.get("k_default") or 5),
        k_max=int(serve.get("k_max") or 8),
        max_context_chars=int(serve.get("max_context_chars") or 6000),
        unique_documents=bool(evaluation.get("unique_documents") or False),
        eval_pool_k=int(evaluation.get("pool_k") or 15),
        hybrid_retrieval=bool(retrieval.get("hybrid", True)),
        rrf_k=int(retrieval.get("rrf_k") or 60),
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
GENERATION_LOCATION = _CFG.generation_location
REFUSE_MIN_SCORE = _CFG.refuse_min_score
QUESTION_MAX_CHARS = _CFG.question_max_chars
K_DEFAULT = _CFG.k_default
K_MAX = _CFG.k_max
MAX_CONTEXT_CHARS = _CFG.max_context_chars
UNIQUE_DOCUMENTS = _CFG.unique_documents
EVAL_POOL_K = _CFG.eval_pool_k
HYBRID_RETRIEVAL = _CFG.hybrid_retrieval
RRF_K = _CFG.rrf_k
CHUNK_STRATEGY = _CFG.chunk_strategy
CHUNK_SIZE = _CFG.chunk_size
CHUNK_OVERLAP = _CFG.chunk_overlap
GCP_PROJECT = _CFG.gcp_project
GCP_LOCATION = _CFG.gcp_location
