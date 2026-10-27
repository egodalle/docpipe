from __future__ import annotations

import argparse
import subprocess
import sys

from docpipe.config import (
    CHUNK_STRATEGY,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    GCS_BUCKET,
    LICENSES_CSV,
    RAW_DIR,
)
from docpipe.fetch import fetch_corpus
from docpipe.index import chunk_corpus, embed_corpus, index_corpus
from docpipe.ingest import ingest_corpus
from docpipe.search import ask_neighbors, run_example_queries
from docpipe.sync import sync_corpus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docpipe")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="Download licensed files into data/raw")
    sub.add_parser("ingest", help="Extract, hash, and load documents on local Postgres")
    sub.add_parser("chunk", help="Split live documents with recursive_400_80")
    sub.add_parser("embed", help="Batch-embed new chunks on Vertex; skip known hashes")
    sub.add_parser("index", help="Chunk + embed + HNSW after ingest")
    sub.add_parser("sync", help="Incremental ingest + index (insert/update/tombstone)")
    search = sub.add_parser("search", help="k-NN search; log hits without an LLM answer")
    search.add_argument("question", nargs="?", help="Question to embed and search")
    search.add_argument("--examples", action="store_true", help="Run the five D3 queries")
    search.add_argument("-k", type=int, default=5)
    gcs = sub.add_parser("upload-gcs", help="Copy data/raw and licenses.csv to GCS")
    gcs.add_argument("--bucket", default=GCS_BUCKET)
    args = parser.parse_args(argv)

    if args.cmd == "fetch":
        paths = fetch_corpus()
        print(f"fetched {len(paths)} files into {RAW_DIR}")
        return 0
    if args.cmd == "ingest":
        report = ingest_corpus()
        print(
            "ingest "
            f"inserted={report.inserted} updated={report.updated} "
            f"skipped={report.skipped} tombstoned={report.tombstoned} "
            f"quarantined={report.quarantined} "
            f"empty_extract_rate={report.empty_extract_rate:.2%}"
        )
        return 0
    if args.cmd == "sync":
        report = sync_corpus()
        print(
            "sync "
            f"inserted={report.ingest.inserted} updated={report.ingest.updated} "
            f"skipped={report.ingest.skipped} tombstoned={report.ingest.tombstoned} "
            f"quarantined={report.ingest.quarantined} "
            f"chunked={report.index.chunked} embedded={report.index.embedded} "
            f"index_skipped={report.index.skipped}"
        )
        return 0
    if args.cmd == "chunk":
        report = chunk_corpus()
        print(
            "chunk "
            f"strategy={CHUNK_STRATEGY} chunked={report.chunked} "
            f"chunk_rows={report.chunk_rows} skipped={report.skipped} "
            f"chunks={report.chunks}"
        )
        return 0
    if args.cmd == "embed":
        report = embed_corpus()
        print(
            "embed "
            f"model={report.model} dim={report.dim} "
            f"embedded={report.embedded} embeddings={report.embeddings}"
        )
        return 0
    if args.cmd == "index":
        report = index_corpus()
        print(
            "index "
            f"strategy={CHUNK_STRATEGY} model={report.model} dim={report.dim} "
            f"chunked={report.chunked} embedded={report.embedded} "
            f"skipped={report.skipped} chunks={report.chunks} "
            f"embeddings={report.embeddings}"
        )
        return 0
    if args.cmd == "search":
        if args.examples:
            results = run_example_queries(k=args.k)
            _print_examples(results)
            return 0
        if not args.question:
            parser.error("search requires a question or --examples")
        result = ask_neighbors(args.question, k=args.k)
        _print_result(result)
        return 0
    if args.cmd == "upload-gcs":
        _upload_gcs(args.bucket)
        return 0
    return 1


def _print_result(result) -> None:
    print(
        f"search model={result.model} dim={EMBEDDING_DIM} "
        f"k={len(result.hits)} latency_ms={result.latency_ms} "
        f"request_id={result.request_id}"
    )
    for rank, hit in enumerate(result.hits, start=1):
        snippet = " ".join(hit.body.split())[:160]
        print(
            f"{rank}. score={hit.score:.4f} source={hit.source} "
            f"uri={hit.uri}\n   {snippet}"
        )


def _print_examples(results) -> None:
    print(f"logged {len(results)} queries model={EMBEDDING_MODEL} dim={EMBEDDING_DIM}")
    for result in results:
        top = result.hits[0] if result.hits else None
        if top is None:
            print(f"- {result.question!r} → no hits")
            continue
        snippet = " ".join(top.body.split())[:120]
        print(
            f"- {result.question!r}\n"
            f"  top={top.uri} score={top.score:.4f} {snippet}"
        )


def _upload_gcs(bucket: str) -> None:
    if not RAW_DIR.exists():
        raise FileNotFoundError(RAW_DIR)
    prefix = f"gs://{bucket}"
    subprocess.run(
        ["gsutil", "-m", "rsync", "-r", str(RAW_DIR), f"{prefix}/raw"],
        check=True,
    )
    subprocess.run(
        ["gsutil", "cp", str(LICENSES_CSV), f"{prefix}/licenses.csv"],
        check=True,
    )
    print(f"uploaded corpus to {prefix}")


if __name__ == "__main__":
    sys.exit(main())
