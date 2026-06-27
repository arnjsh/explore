"""Smoke tests: run every Streamlit page via AppTest and assert no exceptions.

This executes the page scripts in a headless test harness (no browser needed),
which catches import errors, bad API usage and runtime errors in the UI layer.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAGE_SCRIPTS = [PROJECT_ROOT / "streamlit_app.py"] + sorted(
    (PROJECT_ROOT / "pages").glob("*.py")
)


@pytest.mark.parametrize("script", PAGE_SCRIPTS, ids=lambda p: p.name)
def test_page_runs_without_exception(script: Path):
    at = AppTest.from_file(str(script), default_timeout=60)
    at.run()
    assert not at.exception, f"{script.name} raised: {at.exception}"
