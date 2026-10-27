from __future__ import annotations

import re
from collections.abc import Sequence

from docpipe.models import SearchHit

CHUNK_ID_RE = re.compile(
    r"\[([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\]",
    re.IGNORECASE,
)


def cited_chunk_ids(answer: str | None) -> list[str]:
    if not answer:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for match in CHUNK_ID_RE.findall(answer):
        value = match.lower()
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def citation_ok(
    *,
    refused: bool,
    answer: str | None,
    hits: Sequence[SearchHit],
) -> bool:
    """Refuse must not answer. An answer must cite only retrieved chunk ids."""
    if refused:
        return answer is None
    if not answer or not hits:
        return False
    allowed = {hit.chunk_id.lower() for hit in hits}
    cited = cited_chunk_ids(answer)
    if not cited:
        return False
    return all(chunk_id in allowed for chunk_id in cited)
