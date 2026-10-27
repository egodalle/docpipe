from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Protocol

from docpipe.config import GCP_PROJECT

BQ_DATASET = os.environ.get("BQ_DATASET", "docpipe_p1")
BQ_TABLE = os.environ.get("BQ_QUERY_LOGS_TABLE", "query_logs")


def skip_bq() -> bool:
    return os.environ.get("DOCS_SKIP_BQ", "") == "1"


class BqSink(Protocol):
    def write_query_log(self, row: dict) -> None:
        ...


class NullBqSink:
    def write_query_log(self, row: dict) -> None:
        return None


class BigQueryLog:
    def __init__(self, project: str | None = None, dataset: str | None = None) -> None:
        self.project = project or GCP_PROJECT
        self.dataset = dataset or BQ_DATASET
        self.table = BQ_TABLE
        self._client = None
        self._ensured = False

    @property
    def table_id(self) -> str:
        return f"{self.project}.{self.dataset}.{self.table}"

    def write_query_log(self, row: dict) -> None:
        if skip_bq():
            return
        client = self._client_obj()
        self._ensure_table(client)
        errors = client.insert_rows_json(self.table_id, [row])
        if errors:
            raise RuntimeError(f"BigQuery insert failed: {errors}")

    def _client_obj(self):
        if self._client is None:
            from google.cloud import bigquery

            self._client = bigquery.Client(project=self.project)
        return self._client

    def _ensure_table(self, client) -> None:
        if self._ensured:
            return
        from google.cloud import bigquery

        schema = [
            bigquery.SchemaField("request_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("question", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chunk_ids", "STRING", mode="REPEATED"),
            bigquery.SchemaField("scores", "FLOAT64", mode="REPEATED"),
            bigquery.SchemaField("answer", "STRING"),
            bigquery.SchemaField("refused", "BOOL", mode="REQUIRED"),
            bigquery.SchemaField("latency_ms", "INT64"),
            bigquery.SchemaField("model", "STRING"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
        ]
        table = bigquery.Table(self.table_id, schema=schema)
        client.create_table(table, exists_ok=True)
        self._ensured = True


def query_log_row(
    *,
    request_id: str,
    question: str,
    chunk_ids: list[str],
    scores: list[float],
    answer: str | None,
    refused: bool,
    latency_ms: int,
    model: str,
) -> dict:
    return {
        "request_id": request_id,
        "question": question,
        "chunk_ids": list(chunk_ids),
        "scores": [float(score) for score in scores],
        "answer": answer,
        "refused": refused,
        "latency_ms": latency_ms,
        "model": model,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def default_bq_sink() -> BqSink:
    if skip_bq():
        return NullBqSink()
    return BigQueryLog()


def write_bq_rows(table: str, schema: list, rows: list[dict]) -> None:
    if skip_bq() or not rows:
        return
    from google.cloud import bigquery

    client = bigquery.Client(project=GCP_PROJECT)
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.{table}"
    client.create_table(bigquery.Table(table_id, schema=schema), exists_ok=True)
    errors = client.insert_rows_json(table_id, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert failed for {table}: {errors}")
