from docpipe.config import EMBEDDING_BATCH
from docpipe.embed import _pack_batches


def test_pack_batches_respects_size_and_token_budget() -> None:
    texts = ["abcd" * 10] * 30  # ~10 tokens each at chars/4
    batches = _pack_batches(texts, batch_size=5, max_tokens=40)
    assert batches
    assert all(len(batch) <= 5 for batch in batches)
    assert sum(len(batch) for batch in batches) == 30
    assert EMBEDDING_BATCH <= 16
