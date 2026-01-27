"""Integration test configuration.

Integration tests:
- Moderate speed: <5s per test
- Minimal mocks (only when unavoidable)
- Real services (storage, file system)
- NO LLMs - use mock model adapters for LLM calls
- BDD-style (Given/When/Then)
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _integration_marker(request: pytest.FixtureRequest) -> None:
    """Auto-apply integration marker and timeout to all tests in this directory."""
    request.node.add_marker(pytest.mark.integration)
    request.node.add_marker(pytest.mark.timeout(5))
