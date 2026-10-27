from __future__ import annotations

import argparse
import subprocess
import sys

from docpipe.config import GCS_BUCKET, LICENSES_CSV, RAW_DIR
from docpipe.fetch import fetch_corpus
from docpipe.ingest import ingest_corpus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docpipe")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="Download licensed files into data/raw")
    sub.add_parser("ingest", help="Extract, hash, and load documents on local Postgres")
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
            f"inserted={report.inserted} skipped={report.skipped} "
            f"quarantined={report.quarantined} "
            f"empty_extract_rate={report.empty_extract_rate:.2%}"
        )
        return 0
    if args.cmd == "upload-gcs":
        _upload_gcs(args.bucket)
        return 0
    return 1


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
