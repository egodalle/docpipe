from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from docpipe.ask import AskValidationError, ask
from docpipe.bqlog import BqSink, default_bq_sink
from docpipe.config import (
    DATABASE_URL,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    GENERATION_MODEL,
    K_DEFAULT,
    K_MAX,
    QUESTION_MAX_CHARS,
    REFUSE_MIN_SCORE,
)
from docpipe.embed import EmbeddingClient, VertexEmbeddingClient
from docpipe.generate import Generator, VertexGenerator
from docpipe.store import connect, counts

STATIC_DIR = Path(__file__).resolve().parent / "static"
app = FastAPI(title="DocPipe", version="1.0.0")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=QUESTION_MAX_CHARS)
    source: str | None = None
    k: int | None = Field(default=None, ge=1, le=K_MAX)
    request_id: str | None = None


class CitationOut(BaseModel):
    uri: str
    chunk_id: str
    snippet: str
    score: float


class AskResponse(BaseModel):
    request_id: str
    answer: str | None
    refused: bool
    citations: list[CitationOut]
    latency_ms: int


def get_embedding_client() -> EmbeddingClient:
    return VertexEmbeddingClient()


def get_generator() -> Generator:
    return VertexGenerator()


def get_bq() -> BqSink:
    return default_bq_sink()


@app.exception_handler(RequestValidationError)
async def validation_handler(_request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "invalid request"})


@app.get("/health")
def health() -> dict:
    try:
        with connect() as conn:
            conn.execute("SELECT 1")
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"ok": True, "db": "up", "database": "local" if ":5433" in DATABASE_URL else "configured"}


@app.get("/stats")
def stats() -> dict:
    try:
        with connect() as conn:
            payload = counts(conn)
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    payload.update(
        {
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dim": EMBEDDING_DIM,
            "generation_model": GENERATION_MODEL,
            "refuse_min_score": REFUSE_MIN_SCORE,
            "k_default": K_DEFAULT,
        }
    )
    return payload


@app.post("/ask", response_model=AskResponse)
def post_ask(
    body: AskRequest,
    embedding_client: Annotated[EmbeddingClient, Depends(get_embedding_client)],
    generator: Annotated[Generator, Depends(get_generator)],
    bq: Annotated[BqSink, Depends(get_bq)],
) -> AskResponse:
    try:
        result = ask(
            body.question,
            k=body.k,
            source=body.source,
            request_id=body.request_id,
            embedding_client=embedding_client,
            generator=generator,
            bq=bq,
        )
    except AskValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="ask unavailable")
    return AskResponse(
        request_id=result.request_id,
        answer=result.answer,
        refused=result.refused,
        citations=[
            CitationOut(
                uri=item.uri,
                chunk_id=item.chunk_id,
                snippet=item.snippet,
                score=item.score,
            )
            for item in result.citations
        ],
        latency_ms=result.latency_ms,
    )


@app.get("/", include_in_schema=False)
def demo() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@app.get("/api")
def root() -> dict:
    return {
        "service": "docpipe",
        "ask": "POST /ask",
        "health": "GET /health",
        "stats": "GET /stats",
        "question_max_chars": QUESTION_MAX_CHARS,
        "k_max": K_MAX,
    }


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
