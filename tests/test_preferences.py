"""Tests for custom_tags functionality in preferences.py (FXA-256)."""

from __future__ import annotations

import sys

import yaml
import pytest

from fx_alfred.core.preferences import (
    PreferencesError,
    add_custom_tags,
    load_custom_tags,
    preferences_path,
    remove_custom_tags,
)
from fx_alfred.core.schema import CONTROLLED_TAGS

pytestmark = pytest.mark.unit


# ── load_custom_tags ──────────────────────────────────────────────────────────


def test_load_custom_tags_empty_when_file_missing():
    """load_custom_tags() returns [] when preferences file doesn't exist."""
    assert not preferences_path().exists()
    assert load_custom_tags() == []


def test_load_custom_tags_empty_when_key_absent():
    """load_custom_tags() returns [] when custom_tags key is absent from file."""
    prefs = preferences_path()
    prefs.parent.mkdir(parents=True, exist_ok=True)
    prefs.write_text("starred_docs:\n- COR-1001\n", encoding="utf-8")
    assert load_custom_tags() == []


def test_load_custom_tags_returns_sorted_list():
    """load_custom_tags() returns sorted list after add_custom_tags."""
    add_custom_tags(["zzz", "aaa"])
    result = load_custom_tags()
    assert result == ["aaa", "zzz"]


# ── add_custom_tags ───────────────────────────────────────────────────────────


def test_add_custom_tags_single_tag():
    """add_custom_tags(['my-tag']) returns ['my-tag'] and persists it."""
    result = add_custom_tags(["my-tag"])
    assert result == ["my-tag"]
    assert load_custom_tags() == ["my-tag"]


def test_add_custom_tags_normalizes_to_lowercase():
    """add_custom_tags(['MyTag']) normalizes to 'mytag'."""
    result = add_custom_tags(["MyTag"])
    assert result == ["mytag"]
    assert load_custom_tags() == ["mytag"]


def test_add_custom_tags_dedupes():
    """add_custom_tags(['foo', 'foo']) deduplicates."""
    result = add_custom_tags(["foo", "foo"])
    assert result == ["foo"]


def test_add_custom_tags_is_idempotent():
    """Calling add_custom_tags twice with the same tag leaves the list unchanged."""
    add_custom_tags(["my-tag"])
    result = add_custom_tags(["my-tag"])
    assert result == ["my-tag"]


def test_add_custom_tags_accumulates():
    """Multiple add_custom_tags calls accumulate into a sorted set."""
    add_custom_tags(["alpha"])
    result = add_custom_tags(["beta"])
    assert result == ["alpha", "beta"]
    assert load_custom_tags() == ["alpha", "beta"]


def test_add_custom_tags_preserves_starred_docs():
    """add_custom_tags preserves starred_docs key when writing."""
    prefs = preferences_path()
    prefs.parent.mkdir(parents=True, exist_ok=True)
    prefs.write_text("starred_docs:\n- COR-1001\n", encoding="utf-8")
    add_custom_tags(["my-tag"])
    data = yaml.safe_load(prefs.read_text(encoding="utf-8"))
    assert data["starred_docs"] == ["COR-1001"]
    assert "my-tag" in data["custom_tags"]


def test_add_custom_tags_returns_sorted():
    """add_custom_tags returns the full sorted list after each call."""
    add_custom_tags(["zzz"])
    result = add_custom_tags(["aaa"])
    assert result == ["aaa", "zzz"]


def test_add_custom_tags_strips_whitespace():
    """add_custom_tags strips leading/trailing whitespace from each tag."""
    result = add_custom_tags(["  my-tag  "])
    assert result == ["my-tag"]


# ── remove_custom_tags ────────────────────────────────────────────────────────


def test_remove_custom_tags_removes_tag():
    """remove_custom_tags(['foo']) removes 'foo' from the list."""
    add_custom_tags(["foo", "bar"])
    result = remove_custom_tags(["foo"])
    assert result == ["bar"]
    assert load_custom_tags() == ["bar"]


def test_remove_custom_tags_idempotent_when_absent():
    """remove_custom_tags on a tag not present returns current list without error."""
    add_custom_tags(["bar"])
    result = remove_custom_tags(["nonexistent"])
    assert result == ["bar"]


def test_remove_custom_tags_when_file_missing():
    """remove_custom_tags returns [] when preferences file doesn't exist."""
    result = remove_custom_tags(["nonexistent"])
    assert result == []


def test_remove_custom_tags_preserves_starred_docs():
    """remove_custom_tags preserves starred_docs key."""
    prefs = preferences_path()
    prefs.parent.mkdir(parents=True, exist_ok=True)
    prefs.write_text(
        "custom_tags:\n- bar\n- foo\nstarred_docs:\n- COR-1001\n",
        encoding="utf-8",
    )
    result = remove_custom_tags(["foo"])
    assert result == ["bar"]
    data = yaml.safe_load(prefs.read_text(encoding="utf-8"))
    assert data["starred_docs"] == ["COR-1001"]
    assert data["custom_tags"] == ["bar"]


def test_remove_custom_tags_all_leaves_empty_list():
    """Removing the last custom tag leaves custom_tags as an empty list."""
    add_custom_tags(["only-tag"])
    result = remove_custom_tags(["only-tag"])
    assert result == []
    assert load_custom_tags() == []


# ── PreferencesError on malformed shape ───────────────────────────────────────


def test_load_custom_tags_raises_on_non_list():
    """PreferencesError raised when custom_tags is present but not a list."""
    prefs = preferences_path()
    prefs.parent.mkdir(parents=True, exist_ok=True)
    prefs.write_text("custom_tags: not-a-list\n", encoding="utf-8")
    with pytest.raises(PreferencesError, match="custom_tags"):
        load_custom_tags()


def test_add_custom_tags_raises_on_malformed_file():
    """PreferencesError propagates when custom_tags key has wrong shape."""
    prefs = preferences_path()
    prefs.parent.mkdir(parents=True, exist_ok=True)
    prefs.write_text("custom_tags: 42\n", encoding="utf-8")
    with pytest.raises(PreferencesError, match="custom_tags"):
        add_custom_tags(["new-tag"])


# ── allowed_tags (from core.vocab) ────────────────────────────────────────────


def test_allowed_tags_includes_controlled_tags():
    """allowed_tags() always includes all CONTROLLED_TAGS."""
    from fx_alfred.core.vocab import allowed_tags

    assert CONTROLLED_TAGS.issubset(allowed_tags())


def test_allowed_tags_includes_custom_tags_after_add():
    """allowed_tags() includes custom tags after add_custom_tags."""
    from fx_alfred.core.vocab import allowed_tags

    add_custom_tags(["my-custom-tag"])
    assert "my-custom-tag" in allowed_tags()


def test_allowed_tags_union_correctness():
    """allowed_tags() == CONTROLLED_TAGS | set(load_custom_tags())."""
    from fx_alfred.core.vocab import allowed_tags

    add_custom_tags(["custom-foo", "custom-bar"])
    expected = CONTROLLED_TAGS | {"custom-foo", "custom-bar"}
    assert allowed_tags() == expected


def test_allowed_tags_without_custom_tags_equals_controlled():
    """allowed_tags() with no custom_tags equals CONTROLLED_TAGS."""
    from fx_alfred.core.vocab import allowed_tags

    assert allowed_tags() == set(CONTROLLED_TAGS)


def test_add_custom_tags_no_write_when_empty_input():
    """add_custom_tags([]) does not create the preferences file."""
    assert not preferences_path().exists()
    result = add_custom_tags([])
    assert result == []
    assert not preferences_path().exists()


def test_add_custom_tags_no_write_when_all_already_present():
    """add_custom_tags with all-existing tags does not rewrite the file."""
    add_custom_tags(["foo"])
    prefs = preferences_path()
    mtime_before = prefs.stat().st_mtime_ns
    result = add_custom_tags(["foo"])
    assert result == ["foo"]
    assert prefs.stat().st_mtime_ns == mtime_before


# ── Permission preservation (FXA-274) ───────────────────────────────────────


@pytest.mark.skipif(
    sys.platform == "win32", reason="permission bits not portable on Windows"
)
def test_atomic_write_preserves_file_mode():
    """_atomic_write preserves the existing preferences file's permission mode (FXA-274).

    Regression: tempfile.mkstemp creates with mode 0o600; os.replace keeps that
    mode, so a preferences.yaml with mode 0o640 (group-readable) is silently
    narrowed to owner-only after any write operation.
    """
    prefs_path = preferences_path()
    prefs_path.parent.mkdir(parents=True, exist_ok=True)
    prefs_path.write_text("starred_docs:\n- COR-1001\n", encoding="utf-8")
    prefs_path.chmod(0o640)
    assert (prefs_path.stat().st_mode & 0o777) == 0o640  # precondition

    add_custom_tags(["test-tag"])

    mode = prefs_path.stat().st_mode
    assert (mode & 0o777) == 0o640, f"Expected 0o640, got {oct(mode & 0o777)}"
    # Verify content was actually written (the write path did execute)
    assert "test-tag" in prefs_path.read_text()
