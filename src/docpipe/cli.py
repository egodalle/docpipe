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
from docpipe.ask import ask
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
    sync_p = sub.add_parser("sync", help="Incremental ingest + index (insert/update/tombstone)")
    sync_p.add_argument(
        "--corpus",
        default=None,
        help="Directory of docs (licenses.csv+raw, nested folders, or flat html/md/txt)",
    )
    search = sub.add_parser("search", help="k-NN search; log hits without an LLM answer")
    search.add_argument("question", nargs="?", help="Question to embed and search")
    search.add_argument("--examples", action="store_true", help="Run the five D3 queries")
    search.add_argument("-k", type=int, default=5)
    ask_p = sub.add_parser("ask", help="Retrieve + refuse or answer with citations")
    ask_p.add_argument("question", help="Question to answer from retrieved chunks")
    ask_p.add_argument("-k", type=int, default=None)
    ask_p.add_argument("--source", default=None)
    serve = sub.add_parser("serve", help="Run the demo UI plus /ask /health /stats")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    ev = sub.add_parser("eval", help="Score recall@5 against eval/golden.json")
    ev.add_argument("--unique-documents", action="store_true")
    ev.add_argument("--raw", action="store_true", help="Force raw top-k (no unique collapse)")
    ev.add_argument("-k", type=int, default=5)
    ev.add_argument("--pool-k", type=int, default=None)
    ev.add_argument("--no-persist", action="store_true")
    ev.add_argument("--compare", action="store_true", help="Raw top-k vs unique documents")
    ev.add_argument(
        "--compare-hybrid",
        action="store_true",
        help="Unique vector vs unique hybrid (RRF)",
    )
    ev.add_argument("--hybrid", action="store_true", help="Force hybrid retrieval")
    ev.add_argument("--vector", action="store_true", help="Force vector-only retrieval")
    ev.add_argument(
        "--refuse",
        action="store_true",
        help="Score eval/refuse.json (off-corpus questions must refuse)",
    )
    ev.add_argument("--seed-ingest-run", action="store_true")
    ev.add_argument("--run-id", default=None)
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
        corpus = None
        if args.corpus:
            from docpipe.corpus import discover_corpus, set_active_corpus

            corpus = discover_corpus(args.corpus)
            set_active_corpus(corpus)
            print(f"corpus path={corpus.root} layout={corpus.layout} files={len(corpus.files)}")
        report = sync_corpus(corpus=corpus)
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
    if args.cmd == "ask":
        result = ask(args.question, k=args.k, source=args.source)
        _print_ask(result)
        return 0
    if args.cmd == "serve":
        import uvicorn

        uvicorn.run("docpipe.api:app", host=args.host, port=args.port)
        return 0
    if args.cmd == "eval":
        from docpipe.evalrun import (
            RECALL_BAR,
            compare_hybrid,
            compare_tunes,
            format_refuse_report,
            format_report,
            run_eval,
            run_refuse_eval,
            seed_ingest_run_bq,
        )

        if args.seed_ingest_run:
            ingest_id = seed_ingest_run_bq()
            print(f"seeded ingest_runs run_id={ingest_id}")
        if args.refuse:
            if args.compare or args.compare_hybrid:
                parser.error("--refuse cannot be combined with --compare")
            report = run_refuse_eval(
                k=args.k,
                persist=not args.no_persist,
                run_id=args.run_id,
                hybrid=True if args.hybrid else (False if args.vector else None),
            )
            print(format_refuse_report(report))
            return 0 if report.meets_bar else 2
        if args.compare and args.compare_hybrid:
            parser.error("use only one of --compare / --compare-hybrid")
        if args.compare:
            baseline, unique, winner = compare_tunes(
                k=args.k,
                persist_winner=not args.no_persist,
            )
            print(format_report(baseline))
            print(format_report(unique))
            print(
                f"winner unique_documents={winner.unique_documents} "
                f"recall@5={winner.recall_at_5:.3f} run_id={winner.run_id}"
            )
            return 0 if winner.meets_bar else 2
        if args.compare_hybrid:
            vector, hybrid, winner = compare_hybrid(
                k=args.k,
                persist_winner=not args.no_persist,
            )
            print(format_report(vector))
            print(format_report(hybrid))
            print(
                f"winner hybrid={winner.hybrid} "
                f"recall@5={winner.recall_at_5:.3f} run_id={winner.run_id}"
            )
            return 0 if winner.meets_bar else 2
        if args.unique_documents and args.raw:
            parser.error("use only one of --unique-documents / --raw")
        if args.hybrid and args.vector:
            parser.error("use only one of --hybrid / --vector")
        unique_flag: bool | None
        if args.unique_documents:
            unique_flag = True
        elif args.raw:
            unique_flag = False
        else:
            unique_flag = None
        hybrid_flag: bool | None
        if args.hybrid:
            hybrid_flag = True
        elif args.vector:
            hybrid_flag = False
        else:
            hybrid_flag = None
        report = run_eval(
            unique_documents=unique_flag,
            hybrid=hybrid_flag,
            k=args.k,
            pool_k=args.pool_k,
            persist=not args.no_persist,
            run_id=args.run_id,
        )
        print(format_report(report))
        return 0 if report.recall_at_5 >= RECALL_BAR else 2
    if args.cmd == "upload-gcs":
        _upload_gcs(args.bucket)
        return 0
    return 1


def _print_ask(result) -> None:
    status = "refused" if result.refused else "answered"
    print(
        f"ask {status} mode={result.retrieval_mode} citation_ok={result.citation_ok} "
        f"model={result.model} latency_ms={result.latency_ms} "
        f"request_id={result.request_id}"
    )
    if result.answer:
        print(result.answer)
    for rank, cite in enumerate(result.citations, start=1):
        print(
            f"{rank}. score={cite.score:.4f} source={cite.source} "
            f"license={cite.license or '-'} uri={cite.uri}\n"
            f"   {cite.snippet}"
        )


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
