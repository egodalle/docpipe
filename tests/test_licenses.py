from docpipe.licenses import load_licenses
from docpipe.models import Source


def test_seed_corpus_is_licensed_and_sized() -> None:
    rows = load_licenses()
    assert 20 <= len(rows) <= 50
    sources = {row.source for row in rows}
    assert sources == {Source.postgres_docs, Source.pgvector}
    assert all(row.license and row.license_url and row.origin_url for row in rows)
