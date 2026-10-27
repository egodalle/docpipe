from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from docpipe.bqlog import skip_bq, write_bq_rows
from docpipe.config import EVAL_POOL_K, HYBRID_RETRIEVAL, ROOT, UNIQUE_DOCUMENTS
from docpipe.embed import EmbeddingClient, VertexEmbeddingClient
from docpipe.models import SearchHit
from docpipe.retrieve import pick_topk, retrieve_hits, uri_basename
from docpipe.store import connect, insert_eval_result

GOLDEN_PATH = ROOT / "eval" / "golden.json"
RECALL_BAR = 0.70


@dataclass
class GoldenItem:
    id: str
    question: str
    expected_uris: list[str]


@dataclass
class ItemScore:
    question_id: str
    question: str
    recall_at_5: bool
    citation_hit: bool
    latency_ms: int
    retrieved: list[str]


@dataclass
class EvalReport:
    run_id: str
    unique_documents: bool
    pool_k: int
    k: int
    n: int
    hits: int
    recall_at_5: float
    hybrid: bool = False
    items: list[ItemScore] = field(default_factory=list)

    @property
    def meets_bar(self) -> bool:
        return self.recall_at_5 >= RECALL_BAR


def load_golden(path: Path | None = None) -> list[GoldenItem]:
    raw = json.loads((path or GOLDEN_PATH).read_text(encoding="utf-8"))
    items = [
        GoldenItem(
            id=str(row["id"]),
            question=str(row["question"]),
            expected_uris=[str(u) for u in row["expected_uris"]],
        )
        for row in raw["items"]
    ]
    if not 20 <= len(items) <= 30:
        raise ValueError(f"golden set must have 20–30 items, got {len(items)}")
    return items


def expected_in_hits(expected_uris: list[str], hits: list[SearchHit]) -> bool:
    retrieved = {uri_basename(hit.uri) for hit in hits}
    return any(name in retrieved for name in expected_uris)


def run_eval(
    *,
    unique_documents: bool | None = None,
    k: int = 5,
    pool_k: int | None = None,
    database_url: str | None = None,
    embedding_client: EmbeddingClient | None = None,
    golden_path: Path | None = None,
    run_id: str | None = None,
    persist: bool = True,
    hybrid: bool | None = None,
) -> EvalReport:
    items = load_golden(golden_path)
    use_unique = UNIQUE_DOCUMENTS if unique_documents is None else unique_documents
    use_hybrid = HYBRID_RETRIEVAL if hybrid is None else hybrid
    fetch_k = pool_k if pool_k is not None else (EVAL_POOL_K if use_unique else k)
    fetch_k = max(fetch_k, k)
    client = embedding_client or VertexEmbeddingClient()
    rid = run_id or f"eval-{uuid.uuid4().hex[:10]}"
    scores: list[ItemScore] = []
    for item in items:
        started = time.perf_counter()
        vector = client.embed_query(item.question)
        with connect(database_url) as conn:
            top = retrieve_hits(
                conn,
                question=item.question,
                query_embedding=vector,
                k=k,
                hybrid=use_hybrid,
                unique_documents=use_unique,
                pool_k=fetch_k,
            )
        hit = expected_in_hits(item.expected_uris, top)
        latency_ms = int((time.perf_counter() - started) * 1000)
        scores.append(
            ItemScore(
                question_id=item.id,
                question=item.question,
                recall_at_5=hit,
                citation_hit=hit,
                latency_ms=latency_ms,
                retrieved=[uri_basename(h.uri) for h in top],
            )
        )
    n_hits = sum(1 for row in scores if row.recall_at_5)
    report = EvalReport(
        run_id=rid,
        unique_documents=use_unique,
        pool_k=fetch_k,
        k=k,
        n=len(scores),
        hits=n_hits,
        recall_at_5=n_hits / len(scores) if scores else 0.0,
        hybrid=use_hybrid,
        items=scores,
    )
    if persist:
        persist_eval(report, database_url=database_url)
    return report


def format_report(report: EvalReport) -> str:
    gate = "PASS" if report.meets_bar else "FAIL"
    lines = [
        f"eval run_id={report.run_id} unique_documents={report.unique_documents} "
        f"hybrid={report.hybrid} pool_k={report.pool_k} k={report.k} n={report.n} "
        f"hits={report.hits} recall@5={report.recall_at_5:.3f} bar={RECALL_BAR:.2f} {gate}"
    ]
    misses = [item for item in report.items if not item.recall_at_5]
    if misses:
        lines.append("misses:")
        for item in misses:
            lines.append(
                f"- {item.question_id} retrieved={item.retrieved}"
            )
    return "\n".join(lines)


class _CachedQueryClient:
    def __init__(self, inner: EmbeddingClient) -> None:
        self.inner = inner
        self.model_name = inner.model_name
        self.dim = inner.dim
        self._queries: dict[str, list[float]] = {}

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.inner.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        if text not in self._queries:
            self._queries[text] = self.inner.embed_query(text)
        return self._queries[text]


def compare_tunes(
    *,
    k: int = 5,
    database_url: str | None = None,
    embedding_client: EmbeddingClient | None = None,
    golden_path: Path | None = None,
    persist_winner: bool = True,
) -> tuple[EvalReport, EvalReport, EvalReport]:
    client = _CachedQueryClient(embedding_client or VertexEmbeddingClient())
    baseline = run_eval(
        unique_documents=False,
        hybrid=False,
        k=k,
        pool_k=k,
        database_url=database_url,
        embedding_client=client,
        golden_path=golden_path,
        persist=False,
        run_id=f"eval-raw-{uuid.uuid4().hex[:8]}",
    )
    unique = run_eval(
        unique_documents=True,
        hybrid=False,
        k=k,
        pool_k=EVAL_POOL_K,
        database_url=database_url,
        embedding_client=client,
        golden_path=golden_path,
        persist=False,
        run_id=f"eval-unique-{uuid.uuid4().hex[:8]}",
    )
    winner = unique if unique.recall_at_5 > baseline.recall_at_5 else baseline
    if persist_winner:
        persist_eval(winner, database_url=database_url)
    return baseline, unique, winner


def compare_hybrid(
    *,
    k: int = 5,
    database_url: str | None = None,
    embedding_client: EmbeddingClient | None = None,
    golden_path: Path | None = None,
    persist_winner: bool = True,
) -> tuple[EvalReport, EvalReport, EvalReport]:
    client = _CachedQueryClient(embedding_client or VertexEmbeddingClient())
    vector = run_eval(
        unique_documents=True,
        hybrid=False,
        k=k,
        pool_k=EVAL_POOL_K,
        database_url=database_url,
        embedding_client=client,
        golden_path=golden_path,
        persist=False,
        run_id=f"eval-vector-{uuid.uuid4().hex[:8]}",
    )
    hybrid = run_eval(
        unique_documents=True,
        hybrid=True,
        k=k,
        pool_k=EVAL_POOL_K,
        database_url=database_url,
        embedding_client=client,
        golden_path=golden_path,
        persist=False,
        run_id=f"eval-hybrid-{uuid.uuid4().hex[:8]}",
    )
    winner = hybrid if hybrid.recall_at_5 >= vector.recall_at_5 else vector
    if persist_winner:
        persist_eval(winner, database_url=database_url)
    return vector, hybrid, winner


def persist_eval(report: EvalReport, database_url: str | None = None) -> None:
    with connect(database_url) as conn:
        for row in report.items:
            insert_eval_result(
                conn,
                run_id=report.run_id,
                question_id=row.question_id,
                recall_at_5=row.recall_at_5,
                citation_hit=row.citation_hit,
                latency_ms=row.latency_ms,
            )
    if skip_bq():
        return
    from datetime import datetime, timezone

    from google.cloud import bigquery

    schema = [
        bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("question_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("recall_at_5", "BOOL"),
        bigquery.SchemaField("citation_hit", "BOOL"),
        bigquery.SchemaField("latency_ms", "INT64"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "run_id": report.run_id,
            "question_id": item.question_id,
            "recall_at_5": item.recall_at_5,
            "citation_hit": item.citation_hit,
            "latency_ms": item.latency_ms,
            "created_at": now,
        }
        for item in report.items
    ]
    write_bq_rows("eval_results", schema, rows)


def seed_ingest_run_bq(
    *,
    empty_extract_rate: float = 0.0,
    files_reprocessed: int = 0,
    corpus_unchanged: bool = True,
    run_id: str | None = None,
) -> str:
    rid = run_id or f"ingest-{uuid.uuid4().hex[:10]}"
    if skip_bq():
        return rid
    from datetime import datetime, timezone

    from google.cloud import bigquery

    schema = [
        bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("finished_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("empty_extract_rate", "FLOAT64"),
        bigquery.SchemaField("files_reprocessed", "INT64"),
        bigquery.SchemaField("corpus_unchanged", "BOOL"),
    ]
    write_bq_rows(
        "ingest_runs",
        schema,
        [
            {
                "run_id": rid,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "empty_extract_rate": empty_extract_rate,
                "files_reprocessed": files_reprocessed,
                "corpus_unchanged": corpus_unchanged,
            }
        ],
    )
    return rid
