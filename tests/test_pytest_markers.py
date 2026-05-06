"""Tests for pytest marker taxonomy configuration."""

import pytest


pytestmark = pytest.mark.unit

CATEGORY_MARKERS = {"unit", "cli", "integration", "docs", "slow"}


def test_marker_taxonomy_registered(pytestconfig):
    configured = set()
    for marker in pytestconfig.getini("markers"):
        configured.add(marker.split(":", 1)[0])

    assert CATEGORY_MARKERS <= configured


def test_collected_tests_have_category_marker(request):
    uncategorized = []
    for item in request.session.items:
        marker_names = {marker.name for marker in item.iter_markers()}
        if not marker_names & CATEGORY_MARKERS:
            uncategorized.append(item.nodeid)

    assert uncategorized == []
