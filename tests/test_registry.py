"""FXA-2330: user-level Project SOP Registry (core logic).

Pure registry semantics: parse/render, upsert idempotency, root
canonicalization, atomic save, prune of dead roots. The commands-layer
trigger (guide/list/read/status) is covered in the per-command tests.
"""

from pathlib import Path

import pytest

from fx_alfred.core.registry import (
    REGISTRY_FILENAME,
    RegistryEntry,
    load_registry,
    parse_registry,
    prune_missing_roots,
    registry_path,
    render_registry,
    save_registry,
    upsert,
)

pytestmark = pytest.mark.unit

TODAY = "2026-09-02"


def _entry(prefix="FXA", root="/Users/frank/Projects/alfred", n=3, seen=TODAY):
    return RegistryEntry(prefix=prefix, root=root, doc_count=n, last_seen=seen)


# ---------------------------------------------------------------- parse


def test_parse_extracts_table_rows():
    text = render_registry(
        [_entry(), _entry(prefix="PFC", root="/Users/frank/Projects/marvin", n=7)],
        today=TODAY,
    )
    entries = parse_registry(text)
    assert entries == [
        _entry(),
        _entry(prefix="PFC", root="/Users/frank/Projects/marvin", n=7),
    ]


def test_parse_tolerates_non_table_prose():
    text = "# noise\n\n| PRJ | Root | Docs | Last Seen |\n|-----|------|------|-----------|\n| FXA | /repo | 2 | 2026-01-01 |\n\nfree prose | pipe line\n"
    entries = parse_registry(text)
    assert entries == [RegistryEntry("FXA", "/repo", 2, "2026-01-01")]


def test_render_round_trips_and_mentions_doc_id():
    entries = [_entry(), _entry(prefix="PFC", root="/x/y", n=1)]
    text = render_registry(entries, today=TODAY)
    assert "USR-9000" in text  # addressable via af read USR-9000
    assert parse_registry(text) == entries
    # af validate contract (COR-0002): every doc carries a Change History table
    assert "## Change History" in text
    assert "| Date | Change | By |" in text


def test_load_missing_file_returns_empty(tmp_path):
    assert load_registry(tmp_path / "nope.md") == []


def test_load_bad_json_lines_do_not_crash(tmp_path):
    p = tmp_path / REGISTRY_FILENAME
    p.write_text("garbage \x00 no table at all\n", encoding="utf-8")
    assert load_registry(p) == []


# ---------------------------------------------------------------- upsert


def test_upsert_appends_new_project(tmp_path):
    entries, changed = upsert([], root=tmp_path, prefix_counts={"FXA": 4}, today=TODAY)
    assert changed is True
    assert entries == [
        RegistryEntry(
            prefix="FXA", root=str(tmp_path.resolve()), doc_count=4, last_seen=TODAY
        )
    ]


def test_upsert_multiple_prefixes_one_row_each(tmp_path):
    entries, changed = upsert(
        [], root=tmp_path, prefix_counts={"PFC": 2, "NRV": 5}, today=TODAY
    )
    assert changed is True
    assert [(e.prefix, e.doc_count) for e in entries] == [("NRV", 5), ("PFC", 2)]


def test_upsert_is_idempotent_same_day_same_counts(tmp_path):
    entries, _ = upsert([], root=tmp_path, prefix_counts={"FXA": 4}, today=TODAY)
    entries2, changed = upsert(
        entries, root=tmp_path, prefix_counts={"FXA": 4}, today=TODAY
    )
    assert changed is False
    assert entries2 == entries


def test_upsert_updates_count_and_last_seen(tmp_path):
    entries, _ = upsert([], root=tmp_path, prefix_counts={"FXA": 4}, today="2026-08-01")
    entries2, changed = upsert(
        entries, root=tmp_path, prefix_counts={"FXA": 9}, today=TODAY
    )
    assert changed is True
    assert entries2 == [
        RegistryEntry(
            prefix="FXA", root=str(tmp_path.resolve()), doc_count=9, last_seen=TODAY
        )
    ]


def test_upsert_canonicalizes_root_via_resolve(tmp_path):
    link = tmp_path.parent / "linked-root"
    link.symlink_to(tmp_path)
    entries, _ = upsert([], root=tmp_path, prefix_counts={"FXA": 1}, today=TODAY)
    entries2, changed = upsert(
        entries, root=link, prefix_counts={"FXA": 1}, today=TODAY
    )
    assert changed is False  # symlinked visit must not fork a second row
    assert len(entries2) == 1


def test_upsert_preserves_other_projects(tmp_path):
    other = _entry(prefix="WUK", root="/Users/frank/Projects/wukong", n=8)
    entries, _ = upsert([], root=tmp_path, prefix_counts={"FXA": 1}, today=TODAY)
    entries = [other] + entries
    entries2, changed = upsert(
        entries, root=tmp_path, prefix_counts={"FXA": 2}, today=TODAY
    )
    assert changed is True
    assert other in entries2  # untouched projects survive the rewrite


def test_upsert_drops_prefixes_that_lost_all_docs(tmp_path):
    entries, _ = upsert(
        [], root=tmp_path, prefix_counts={"FXA": 1, "OLD": 2}, today=TODAY
    )
    entries2, changed = upsert(
        entries, root=tmp_path, prefix_counts={"FXA": 3}, today=TODAY
    )
    assert changed is True
    assert [e.prefix for e in entries2 if e.root == str(tmp_path.resolve())] == ["FXA"]


# ---------------------------------------------------------------- save/load


def test_registry_path_is_usr_alfred_fixed_slot(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    p = registry_path()
    assert p == tmp_path / ".alfred" / REGISTRY_FILENAME
    assert p.name == "USR-9000-REF-Project-SOP-Registry.md"


def test_save_then_load_round_trip(tmp_path):
    p = tmp_path / REGISTRY_FILENAME
    entries = [_entry(), _entry(prefix="PFC", root="/x", n=2)]
    save_registry(p, entries, today=TODAY)
    assert load_registry(p) == entries


def test_save_replaces_atomically_no_tmp_left_behind(tmp_path):
    reg_dir = tmp_path / "reg"
    reg_dir.mkdir()
    p = reg_dir / REGISTRY_FILENAME
    save_registry(p, [_entry()], today=TODAY)
    save_registry(p, [_entry(n=5)], today=TODAY)
    leftovers = [f.name for f in reg_dir.iterdir() if f.name != REGISTRY_FILENAME]
    assert leftovers == []
    assert load_registry(p) == [_entry(n=5)]


def test_save_failure_leaves_original_intact(tmp_path):
    reg_dir = tmp_path / "reg"
    reg_dir.mkdir()
    p = reg_dir / REGISTRY_FILENAME
    save_registry(p, [_entry()], today=TODAY)
    original = p.read_text(encoding="utf-8")
    reg_dir.chmod(0o500)  # unwritable dir → temp-file creation fails pre-replace
    try:
        with pytest.raises(OSError):
            save_registry(p, [_entry(n=9)], today=TODAY)
    finally:
        reg_dir.chmod(0o755)
    assert p.read_text(encoding="utf-8") == original
    leftovers = [f.name for f in reg_dir.iterdir() if f.name != REGISTRY_FILENAME]
    assert leftovers == []


# ---------------------------------------------------------------- prune


def test_prune_removes_dead_roots_keeps_live(tmp_path):
    live = _entry(prefix="FXA", root=str(tmp_path), n=1)
    dead = _entry(prefix="OLD", root=str(tmp_path / "gone"), n=1)
    kept, removed = prune_missing_roots([live, dead])
    assert kept == [live]
    assert removed == [dead]
