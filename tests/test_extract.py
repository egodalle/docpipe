from pathlib import Path

from docpipe.extract import extract_file, extract_text, sha256_text
from docpipe.models import Source

FIXTURES = Path(__file__).parent / "fixtures"


def test_markdown_strips_front_matter_and_hashes() -> None:
    path = FIXTURES / "good.md"
    text = extract_text(path)
    assert "title:" not in text
    assert "HNSW" in text
    result = extract_file(path, Source.pgvector, path.resolve().as_uri())
    assert result.empty is False
    assert result.char_count == len(text)
    assert result.content_hash == sha256_text(text)
    assert len(result.content_hash) == 64


def test_html_uses_doc_content() -> None:
    path = FIXTURES / "page.html"
    text = extract_text(path)
    assert "nav should go" not in text
    assert "JSONB stores JSON" in text


def test_empty_file_is_empty_extract() -> None:
    path = FIXTURES / "empty.md"
    result = extract_file(path, Source.postgres_docs, path.resolve().as_uri())
    assert result.empty is True
    assert result.char_count == 0
