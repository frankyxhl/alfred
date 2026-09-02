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
    assert "| Date" in text and "Change" in text and "By" in text


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


# ------------------------------------------------- PR #338 review round 1


def test_parse_accepts_windows_roots():
    """R1 P1 (registry.py:33): Windows drive-letter roots must round trip."""
    entry = _entry(root="C:\\Users\\alice\\repo")
    text = render_registry([entry], today=TODAY)
    assert parse_registry(text) == [entry]


def test_pipe_in_root_round_trips():
    """R1 P2 (registry.py:99): '|' in a root must be escaped symmetrically."""
    entry = _entry(root="/tmp/a|b")
    text = render_registry([entry], today=TODAY)
    assert "| `/tmp/a\\|b` |" in text  # canonical backticked cell carries the escape
    assert parse_registry(text) == [entry]


def test_load_unreadable_file_raises_not_empty(tmp_path):
    """R1 P2 (registry.py:123): read failure must propagate, not wipe the catalog."""
    p = tmp_path / REGISTRY_FILENAME
    p.write_text(render_registry([_entry()], today=TODAY), encoding="utf-8")
    p.chmod(0o000)
    try:
        with pytest.raises(OSError):
            load_registry(p)
    finally:
        p.chmod(0o644)


def test_prune_keeps_roots_when_existence_inconclusive(tmp_path, monkeypatch):
    """R1 P2 (registry.py:191): stat errors other than missing ⇒ keep the row."""
    import fx_alfred.core.registry as reg

    live = _entry(prefix="FXA", root=str(tmp_path), n=1)
    unreachable = _entry(prefix="NFS", root="/mnt/flaky", n=1)
    dead = _entry(prefix="OLD", root=str(tmp_path / "gone"), n=1)

    real_stat = reg.os.stat

    def fake_stat(path, *a, **kw):
        if str(path) == "/mnt/flaky":
            raise PermissionError(13, "Permission denied")
        return real_stat(path, *a, **kw)

    monkeypatch.setattr(reg.os, "stat", fake_stat)
    kept, removed = reg.prune_missing_roots([live, unreachable, dead])
    assert kept == [live, unreachable]  # unreachable mount is NOT pruned
    assert removed == [dead]


def test_save_refuses_occupied_slot_other_filename(tmp_path):
    """R1 P1 (registry.py:135): a pre-existing different USR-9000 doc blocks the slot."""
    from fx_alfred.core.registry import RegistrySlotConflictError

    (tmp_path / "USR-9000-SOP-Custom-Thing.md").write_text("# mine", encoding="utf-8")
    p = tmp_path / REGISTRY_FILENAME
    with pytest.raises(RegistrySlotConflictError):
        save_registry(p, [_entry()], today=TODAY)
    assert not p.exists()  # nothing written


def test_save_refuses_foreign_doc_in_registry_filename(tmp_path):
    """R1 P1: same filename but not registry-shaped ⇒ occupied, never overwritten."""
    from fx_alfred.core.registry import RegistrySlotConflictError

    p = tmp_path / REGISTRY_FILENAME
    p.write_text("# someone else's USR-9000\n\nno table, no marker\n", encoding="utf-8")
    with pytest.raises(RegistrySlotConflictError):
        save_registry(p, [_entry()], today=TODAY)
    assert "someone else's" in p.read_text(encoding="utf-8")


def test_save_allows_existing_registry_doc(tmp_path):
    """Normal rewrite path: our own registry doc is never 'occupied'."""
    p = tmp_path / REGISTRY_FILENAME
    save_registry(p, [_entry()], today=TODAY)
    save_registry(p, [_entry(n=7)], today=TODAY)  # must not raise
    assert load_registry(p) == [_entry(n=7)]


# ------------------------------------------------- PR #338 rounds 2-3


def test_parse_accepts_unc_roots():
    """R2 P2: UNC and extended-length Windows roots must round trip."""
    for root in (r"\\server\share\repo", r"\\?\C:\repo"):
        entry = _entry(root=root)
        text = render_registry([entry], today=TODAY)
        assert parse_registry(text) == [entry], root


def test_save_preserves_existing_registry_mode(tmp_path):
    """R2 P2: atomic replace must not reset an existing 0640 to mkstemp's 0600."""
    p = tmp_path / REGISTRY_FILENAME
    save_registry(p, [_entry()], today=TODAY)
    p.chmod(0o640)
    save_registry(p, [_entry(n=5)], today=TODAY)
    assert (p.stat().st_mode & 0o777) == 0o640


def test_save_new_registry_respects_umask(tmp_path):
    """R2 P2: first creation honors the umask like a plain open(path,'w')."""
    import os as _os

    old = _os.umask(0o022)
    try:
        p = tmp_path / REGISTRY_FILENAME
        save_registry(p, [_entry()], today=TODAY)
        assert (p.stat().st_mode & 0o777) == 0o644
    finally:
        _os.umask(old)


def test_save_refuses_occupied_slot_in_nested_usr_dir(tmp_path):
    """R2 P1: a nested USR-9000 doc (recursive USR scan scope) blocks the slot."""
    from fx_alfred.core.registry import RegistrySlotConflictError

    nested = tmp_path / "team"
    nested.mkdir()
    (nested / "USR-9000-SOP-Custom.md").write_text("# team doc", encoding="utf-8")
    p = tmp_path / REGISTRY_FILENAME
    with pytest.raises(RegistrySlotConflictError):
        save_registry(p, [_entry()], today=TODAY)
    assert not p.exists()


def test_slot_scan_ignores_logs_dir(tmp_path):
    """logs/ is excluded from USR scans, so a USR-9000 there cannot collide."""
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "USR-9000-SOP-Logged.md").write_text("# log", encoding="utf-8")
    p = tmp_path / REGISTRY_FILENAME
    save_registry(p, [_entry()], today=TODAY)  # must not raise
    assert p.exists()


def test_prune_removes_roots_that_became_files(tmp_path):
    """R2 P2: a regular file occupying the old root path is not a project root."""
    ghost = tmp_path / "was-a-repo"
    ghost.write_text("now a file", encoding="utf-8")
    live = _entry(prefix="FXA", root=str(tmp_path), n=1)
    dead = _entry(prefix="GONE", root=str(ghost), n=1)
    kept, removed = prune_missing_roots([live, dead])
    assert kept == [live]
    assert removed == [dead]


# ------------------------------------------------- PR #338 round 4


def test_trailing_whitespace_root_round_trips():
    """R4 P2: a root ending in space/tab must not be rstripped into a phantom row."""
    for root in ("/tmp/a ", "/tmp/a\tb"):
        entry = _entry(root=root)
        text = render_registry([entry], today=TODAY)
        assert parse_registry(text) == [entry], repr(root)


def test_legacy_bare_rows_still_parse():
    """R4 P2 companion: hand-written bare rows (pre-backtick format) keep parsing."""
    text = "| FXA | /Users/frank/Projects/alfred | 3 | 2026-09-02 |\n"
    assert parse_registry(text) == [_entry()]


def test_slot_scan_ignores_rules_logs_paths(tmp_path):
    """R4 P2: mirror the scanner's rules+logs exclusion in the slot guard."""
    deep = tmp_path / "team" / "rules" / "logs"
    deep.mkdir(parents=True)
    (deep / "USR-9000-SOP-Old.md").write_text("# old", encoding="utf-8")
    p = tmp_path / REGISTRY_FILENAME
    save_registry(p, [_entry()], today=TODAY)  # must not raise
    assert p.exists()


def test_save_refuses_table_bearing_foreign_doc(tmp_path):
    """R5 P1: parseable rows alone are NOT proof of registry ownership —
    a custom doc at the filename (even table-shaped) must never be replaced."""
    from fx_alfred.core.registry import RegistrySlotConflictError

    p = tmp_path / REGISTRY_FILENAME
    p.write_text(
        "# my custom doc\n\nprecious prose\n\n"
        "| FXA | /Users/frank/Projects/alfred | 3 | 2026-09-02 |\n",
        encoding="utf-8",
    )
    with pytest.raises(RegistrySlotConflictError):
        save_registry(p, [_entry()], today=TODAY)
    assert "precious prose" in p.read_text(encoding="utf-8")  # untouched


# ------------------------------------------------- PR #338 rounds 5-6


def test_backslash_pipe_root_round_trips():
    """R5 P2: a root containing backslash-then-pipe must round trip."""
    entry = _entry(root="/tmp/a\\|b")
    text = render_registry([entry], today=TODAY)
    assert parse_registry(text) == [entry]


def test_backtick_root_round_trips():
    """R6 P2: a root containing a backtick must not break the code span."""
    entry = _entry(root="/tmp/a`b")
    text = render_registry([entry], today=TODAY)
    assert parse_registry(text) == [entry]


def test_trailing_backslash_root_round_trips():
    """R6 P2 companion: root ending in a backslash must not eat the closing tick."""
    entry = _entry(root="C:\\dir\\")
    text = render_registry([entry], today=TODAY)
    assert parse_registry(text) == [entry]


def test_dangling_symlink_slot_is_occupied(tmp_path):
    """R6 P2: a dangling symlink at the registry path must never be replaced."""
    from fx_alfred.core.registry import RegistrySlotConflictError

    p = tmp_path / REGISTRY_FILENAME
    p.symlink_to(tmp_path / "does-not-exist")
    with pytest.raises(RegistrySlotConflictError):
        save_registry(p, [_entry()], today=TODAY)
    assert p.is_symlink() and not p.exists()  # link itself untouched


# ------------------------------------------------- PR #338 round 7


def test_prj_doc_with_canonical_filename_still_blocks(tmp_path, monkeypatch):
    """R7 P1: the self-exemption must not cover a PRJ doc that merely carries
    the canonical filename — that still duplicates USR-9000 across layers."""
    proj = tmp_path / "proj"
    rules = proj / "rules"
    rules.mkdir(parents=True)
    (rules / "USR-9000-REF-Project-SOP-Registry.md").write_text(
        render_registry([_entry(root=str(proj))], today=TODAY), encoding="utf-8"
    )
    from click.testing import CliRunner

    from fx_alfred.cli import cli

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--root", str(proj)], catch_exceptions=False)
    assert result.exit_code == 0
    assert not (Path.home() / ".alfred" / REGISTRY_FILENAME).exists()


def test_foreign_doc_mentioning_fxa2330_is_not_ours(tmp_path):
    """R7 P1: a prose doc that merely mentions FXA-2330 is NOT the registry."""
    from fx_alfred.core.registry import RegistrySlotConflictError

    p = tmp_path / REGISTRY_FILENAME
    p.write_text(
        "# notes\n\nWe follow FXA-2330 for the registry design.\n\n"
        "| FXA | /Users/frank/Projects/alfred | 3 | 2026-09-02 |\n",
        encoding="utf-8",
    )
    with pytest.raises(RegistrySlotConflictError):
        save_registry(p, [_entry()], today=TODAY)


def test_legacy_registry_without_marker_still_ours(tmp_path):
    """R7 P1 companion: pre-marker registries (exact template line) upgrade in
    place instead of being rejected as foreign."""
    p = tmp_path / REGISTRY_FILENAME
    legacy = render_registry([_entry()], today=TODAY).replace(
        "<!-- af:project-sop-registry v1 -->\n", ""
    )
    p.write_text(legacy, encoding="utf-8")
    save_registry(p, [_entry(n=9)], today=TODAY)  # must not raise
    assert load_registry(p) == [_entry(n=9)]


def test_rendered_tables_are_column_aligned():
    """R7 P2: generated tables must match canonical fmt alignment — pipes at
    identical positions within each table block."""
    text = render_registry(
        [_entry(), _entry(prefix="PFC", root="/x", n=100)], today=TODAY
    )
    lines = text.splitlines()
    table_blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.startswith("|"):
            current.append(line)
        else:
            if current:
                table_blocks.append(current)
                current = []
    if current:
        table_blocks.append(current)
    assert len(table_blocks) == 2  # entries + history
    for block in table_blocks:
        positions = {tuple(i for i, ch in enumerate(row) if ch == "|") for row in block}
        assert len(positions) == 1, block


# ------------------------------------------------- PR #338 round 8


def test_newline_in_root_round_trips():
    """R8 P2: line-breaking chars in a root must not split the table row."""
    for root in ("/tmp/a\nb", "/tmp/a\rb", "/tmp/a\u2028b", "/tmp/a\u2029b"):
        entry = _entry(root=root)
        text = render_registry([entry], today=TODAY)
        assert parse_registry(text) == [entry], repr(root)
        assert parse_registry(text) == [entry], repr(root)


def test_windows_newline_lookalike_round_trips():
    """R8 P2 companion: `C:\\new` (backslash-n) must not decode to a newline."""
    entry = _entry(root="C:\\new")
    text = render_registry([entry], today=TODAY)
    assert parse_registry(text) == [entry]


def test_slot_scan_ignores_non_file_occupants(tmp_path):
    """R8 P2: a directory named USR-9000-*.md is not a document — no conflict."""
    (tmp_path / "USR-9000-Backup.md").mkdir()
    p = tmp_path / REGISTRY_FILENAME
    save_registry(p, [_entry()], today=TODAY)  # must not raise
    assert p.exists()


# ------------------------------------------------- PR #338 round 9


def test_all_splitlines_separators_round_trip():
    """R9 P2: every separator str.splitlines() splits on must be encoded."""
    seps = ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85"]
    for sep in seps:
        root = "/tmp/a" + sep + "b"
        entry = _entry(root=root)
        text = render_registry([entry], today=TODAY)
        # the rendered row must survive a splitlines() pass intact
        rows = [ln for ln in text.splitlines() if ln.startswith("| FXA")]
        assert len(rows) == 1, repr(sep)
        assert parse_registry(text) == [entry], repr(sep)


def test_fifo_at_registry_slot_is_occupied(tmp_path):
    """R9 P2: a non-regular file at the canonical path is occupied — and must
    be detected WITHOUT opening it (a FIFO would hang read_text)."""
    import os

    from fx_alfred.core.registry import RegistrySlotConflictError, slot_conflict

    p = tmp_path / REGISTRY_FILENAME
    os.mkfifo(p)
    assert slot_conflict(p) == p  # decided by lstat, never by open()
    with pytest.raises(RegistrySlotConflictError):
        save_registry(p, [_entry()], today=TODAY)


def test_prefix_only_legacy_line_is_not_ours(tmp_path):
    """R12 P1 (data loss): a prose line that merely STARTS with the legacy
    signature prefix must not mark a foreign doc as Alfred-owned."""
    from fx_alfred.core.registry import RegistrySlotConflictError

    p = tmp_path / REGISTRY_FILENAME
    p.write_text(
        "# my doc\n\n"
        "Auto-maintained by `af` (FXA-2330) says the registry is neat, "
        "but this is my own document.\n\n"
        "| PRJ | Root | Docs | Last Seen |\n"
        "|-----|------|------|-----------|\n"
        "| FXA | `/Users/frank/Projects/alfred` | 3 | 2026-09-02 |\n",
        encoding="utf-8",
    )
    with pytest.raises(RegistrySlotConflictError):
        save_registry(p, [_entry()], today=TODAY)
    assert "my own document" in p.read_text(encoding="utf-8")


def test_single_legacy_line_is_not_ours(tmp_path):
    """R13 P1 (data loss): quoting ONLY the first signature line must not
    mark a foreign doc as Alfred-owned — the complete preamble block is
    required."""
    from fx_alfred.core.registry import RegistrySlotConflictError

    p = tmp_path / REGISTRY_FILENAME
    p.write_text(
        "# my doc\n\n"
        "Auto-maintained by `af` (FXA-2330): one row per (PRJ prefix, project\n"
        "but then I wrote my own entirely different continuation here.\n\n"
        "| PRJ | Root | Docs | Last Seen |\n"
        "|-----|------|------|-----------|\n"
        "| FXA | `/Users/frank/Projects/alfred` | 3 | 2026-09-02 |\n",
        encoding="utf-8",
    )
    with pytest.raises(RegistrySlotConflictError):
        save_registry(p, [_entry()], today=TODAY)
    assert "my own entirely different continuation" in p.read_text(encoding="utf-8")


# ------------------------------------------------- PR #338 round 14


def test_scan_does_not_crash_when_prj_uses_acid_9000(tmp_path):
    """R14 P1: after the global registry exists, a project whose PRJ layer
    carries its own USR-9000 doc must still scan (no LayerValidationError)."""
    from click.testing import CliRunner

    from fx_alfred.cli import cli

    proj_a = tmp_path / "a"
    (proj_a / "rules").mkdir(parents=True)
    (proj_a / "rules" / "ALF-2201-PRP-A.md").write_text("# a", encoding="utf-8")
    proj_b = tmp_path / "b"
    (proj_b / "rules").mkdir(parents=True)
    (proj_b / "rules" / "USR-9000-SOP-B.md").write_text("# b", encoding="utf-8")

    runner = CliRunner()
    import os

    old = os.getcwd()
    os.chdir(proj_a)
    try:
        r1 = runner.invoke(cli, ["list"], catch_exceptions=False)
        assert r1.exit_code == 0  # A creates the global registry
        assert (Path.home() / ".alfred" / REGISTRY_FILENAME).exists()
        os.chdir(proj_b)
        r2 = runner.invoke(cli, ["list"], catch_exceptions=False)
        assert r2.exit_code == 0, r2.output
        assert "USR-9000-SOP-B" in r2.output or "USR-9000" in r2.output
    finally:
        os.chdir(old)


def test_render_includes_what_is_it_section():
    """R14: generated REF carries the canonical `## What Is It?` heading."""
    text = render_registry([_entry()], today=TODAY)
    assert "## What Is It?" in text


def test_fully_qualified_usr9000_prefers_prj_doc(tmp_path):
    """R15: `af read USR-9000` with BOTH the global registry and a PRJ
    USR-9000 doc resolves to the PRJ doc (layer precedence), never ambiguous."""
    import os

    from click.testing import CliRunner

    from fx_alfred.cli import cli

    proj_b = tmp_path / "b"
    (proj_b / "rules").mkdir(parents=True)
    (proj_b / "rules" / "USR-9000-SOP-B.md").write_text("# b doc", encoding="utf-8")
    proj_a = tmp_path / "a"
    (proj_a / "rules").mkdir(parents=True)
    (proj_a / "rules" / "ALF-2201-PRP-A.md").write_text("# a", encoding="utf-8")

    runner = CliRunner()
    old = os.getcwd()
    os.chdir(proj_a)
    try:
        assert runner.invoke(cli, ["list"], catch_exceptions=False).exit_code == 0
        assert (Path.home() / ".alfred" / REGISTRY_FILENAME).exists()
        os.chdir(proj_b)
        result = runner.invoke(cli, ["read", "USR-9000"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert "# b doc" in result.output  # PRJ doc wins over the global registry
    finally:
        os.chdir(old)


def test_prune_survives_nul_in_root():
    """R15: os.stat raises ValueError (not OSError) for embedded NUL —
    prune must not crash; a NUL path can never exist, so it is pruned."""
    nul = _entry(prefix="NUL", root="/tmp/a\x00b", n=1)
    live = _entry(prefix="FXA", root="/definitely/not", n=1)
    kept, removed = prune_missing_roots([nul, live])
    assert nul in removed


def test_nested_usr9000_still_duplicates(tmp_path):
    """R16 P2: the registry exemption must be scoped to registry-vs-PRJ —
    a NESTED USR doc with id USR-9000 next to the global registry is still
    a same-layer duplicate and must fail layer validation."""
    import os

    from click.testing import CliRunner

    from fx_alfred.cli import cli

    proj_a = tmp_path / "a"
    (proj_a / "rules").mkdir(parents=True)
    (proj_a / "rules" / "ALF-2201-PRP-A.md").write_text("# a", encoding="utf-8")

    runner = CliRunner()
    old = os.getcwd()
    os.chdir(proj_a)
    try:
        assert runner.invoke(cli, ["list"], catch_exceptions=False).exit_code == 0
        reg = Path.home() / ".alfred" / REGISTRY_FILENAME
        assert reg.exists()
        nested = Path.home() / ".alfred" / "custom"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "USR-9000-SOP-Other.md").write_text("# other", encoding="utf-8")
        result = runner.invoke(cli, ["list"])  # duplicate -> ClickException
        assert result.exit_code != 0
        assert "Duplicate USR-9000" in result.output
    finally:
        os.chdir(old)
