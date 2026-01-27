"""Quality test configuration.

Quality tests:
- Slower but bounded: <30s per test
- Minimal mocks (only when unavoidable)
- Real services (storage, file system)
- REAL LLMs - actual model calls, not mocked
- BDD-style (Given/When/Then)
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _quality_marker(request: pytest.FixtureRequest) -> None:
    """Auto-apply quality marker and timeout to all tests in this directory."""
    request.node.add_marker(pytest.mark.quality)
    request.node.add_marker(pytest.mark.timeout(30))
