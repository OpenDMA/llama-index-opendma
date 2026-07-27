"""Integration test configuration."""

from __future__ import annotations

import os

import pytest


@pytest.fixture
def tutorial_endpoint() -> str:
    endpoint = os.environ.get("OPENDMA_TUTORIAL_ENDPOINT")
    if endpoint is None:
        pytest.skip("OPENDMA_TUTORIAL_ENDPOINT is not set")
    return endpoint
