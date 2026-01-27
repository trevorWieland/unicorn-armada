"""Unit test configuration.

Unit tests:
- Fast: <250ms per test
- Mocks allowed and encouraged
- No external services (no network, no file I/O, no databases)
- Test isolated logic and algorithms
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _unit_marker(request: pytest.FixtureRequest) -> None:
    """Auto-apply unit marker and timeout to all tests in this directory."""
    request.node.add_marker(pytest.mark.unit)
    request.node.add_marker(pytest.mark.timeout(1))  # 1s timeout (250ms target)
