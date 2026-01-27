"""Root test configuration.

This conftest.py provides shared fixtures and configuration for all test tiers.
Each tier (unit, integration, quality) has its own conftest with tier-specific setup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (<250ms)")
    config.addinivalue_line("markers", "integration: Integration tests (<5s)")
    config.addinivalue_line("markers", "quality: Quality tests (<30s)")
