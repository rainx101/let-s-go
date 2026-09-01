"""Shared pytest fixtures (DRY setup for tests)."""

import pytest


@pytest.fixture
def sample_costs() -> list[float]:
    """A small set of item costs in the home currency."""
    return [500.0, 300.0, 120.0]
