from __future__ import annotations

import pytest

from docpipe.corpus import reset_active_corpus


@pytest.fixture(autouse=True)
def _reset_corpus() -> None:
    reset_active_corpus()
    yield
    reset_active_corpus()
