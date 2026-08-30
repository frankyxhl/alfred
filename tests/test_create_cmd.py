import json
from pathlib import Path
from unittest.mock import patch

import pytest


from click.testing import CliRunner

from fx_alfred.cli import cli


pytestmark = [pytest.mark.cli, pytest.mark.integration]


def test_create_sop_without_rules_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "My SOP"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (tmp_path / "rules" / "TST-2100-SOP-My-SOP.md").exists()


def test_create_rejects_lowercase_prefix(tmp_path, monkeypatch):
    (tmp_path / "rules").mkdir()
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["create", "sop", "--prefix", "tst", "--acid", "2100", "--title", "Bad"]
    )
    assert result.exit_code != 0


def test_create_rejects_invalid_acid(tmp_path, monkeypatch):
    (tmp_path / "rules").mkdir()
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["create", "sop", "--prefix", "TST", "--acid", "21", "--title", "Bad"]
    )
    assert result.exit_code != 0


def test_create_rejects_cor_prefix(tmp_path, monkeypatch):
    (tmp_path / "rules").mkdir()
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["create", "sop", "--prefix", "COR", "--acid", "2100", "--title", "Bad"]
    )
    assert result.exit_code != 0
    assert "COR prefix is reserved" in result.output


def test_create_sop(tmp_path, monkeypatch):
    (tmp_path / "rules").mkdir()
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "My New SOP"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    created = tmp_path / "rules" / "TST-2100-SOP-My-New-SOP.md"
    assert created.exists()
    content = created.read_text()
    assert "SOP-2100" in content
    assert "My New SOP" in content


def test_create_refuses_duplicate(tmp_path, monkeypatch):
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-2100-SOP-Existing.md").write_text("# existing")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "Duplicate"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0


def test_create_with_root_option(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--root",
            str(tmp_path),
            "create",
            "sop",
            "--prefix",
            "TST",
            "--acid",
            "2100",
            "--title",
            "Root Test",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (tmp_path / "rules" / "TST-2100-SOP-Root-Test.md").exists()


def test_create_with_root_after_subcommand(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "--root",
            str(tmp_path),
            "sop",
            "--prefix",
            "TST",
            "--acid",
            "2100",
            "--title",
            "Root Test",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (tmp_path / "rules" / "TST-2100-SOP-Root-Test.md").exists()


# ── v0.4.0 tests ────────────────────────────────────────────────────────────


def test_create_prefix_acid_collision_same_prefix(tmp_path, monkeypatch):
    """Same prefix + acid is rejected."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-2100-SOP-Existing.md").write_text("# existing")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "Dup"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "TST-2100 already exists" in result.output


def test_create_prefix_acid_collision_different_prefix_allowed(tmp_path, monkeypatch):
    """Different prefix with same acid is allowed."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "AAA-2100-SOP-Existing.md").write_text("# existing")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "BBB", "--acid", "2100", "--title", "New Doc"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (tmp_path / "rules" / "BBB-2100-SOP-New-Doc.md").exists()


def test_create_rejects_acid_0000(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "0000", "--title", "Index"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "0000 is reserved" in result.output


def test_create_all_7_types(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    types_and_acids = [
        ("sop", "2101"),
        ("adr", "2102"),
        ("prp", "2103"),
        ("ref", "2104"),
        ("chg", "2105"),
        ("pln", "2106"),
        ("inc", "2107"),
    ]
    for doc_type, acid in types_and_acids:
        result = runner.invoke(
            cli,
            [
                "create",
                doc_type,
                "--prefix",
                "TST",
                "--acid",
                acid,
                "--title",
                f"Test {doc_type.upper()}",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, f"Failed for type {doc_type}: {result.output}"
        expected = (
            tmp_path
            / "rules"
            / f"TST-{acid}-{doc_type.upper()}-Test-{doc_type.upper()}.md"
        )
        assert expected.exists(), f"File not found for type {doc_type}"


def test_create_case_insensitive(tmp_path, monkeypatch):
    """doc_type argument is case-insensitive."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "SOP", "--prefix", "TST", "--acid", "2100", "--title", "My SOP"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (tmp_path / "rules" / "TST-2100-SOP-My-SOP.md").exists()


def test_create_with_area(tmp_path, monkeypatch):
    """--area auto-assigns next available ACID in the area."""
    rules = tmp_path / "rules"
    rules.mkdir()
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--area", "21", "--title", "Auto ACID"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # area 21 → starts at 2100
    assert (tmp_path / "rules" / "TST-2100-SOP-Auto-ACID.md").exists()


def test_create_area_00_starts_at_0001(tmp_path, monkeypatch):
    """area=00 starts at 0001 (0000 is reserved)."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--area", "00", "--title", "Zero Area"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (tmp_path / "rules" / "TST-0001-SOP-Zero-Area.md").exists()


def test_create_area_and_acid_mutually_exclusive(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "TST",
            "--acid",
            "2100",
            "--area",
            "21",
            "--title",
            "Bad",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "Cannot specify both" in result.output


def test_create_auto_indexes_after_create(tmp_path, monkeypatch):
    """After creating a doc, the index file is generated."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "Indexed"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    index_path = tmp_path / "rules" / "TST-0000-REF-Document-Index.md"
    assert index_path.exists(), "Index file should be created automatically"


def test_create_area_full_error(tmp_path, monkeypatch):
    """When all 100 slots in an area are taken, raise an error."""
    rules = tmp_path / "rules"
    rules.mkdir()
    # Fill area 21: 2100–2199 = 100 slots
    for i in range(2100, 2200):
        (rules / f"TST-{i:04d}-SOP-Doc-{i}.md").write_text("# doc")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--area", "21", "--title", "Overflow"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "full" in result.output


def test_create_area_fills_gap(tmp_path, monkeypatch):
    """--area fills first available slot, not max+1."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-2100-SOP-First.md").write_text("# first")
    (rules / "TST-2102-SOP-Third.md").write_text("# third")
    # Gap at 2101
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--area", "21", "--title", "Fill Gap"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (rules / "TST-2101-SOP-Fill-Gap.md").exists()


def test_create_auto_index_warning_on_failure(tmp_path, monkeypatch):
    """Create succeeds even if auto-index fails, with warning."""
    rules = tmp_path / "rules"
    rules.mkdir()
    monkeypatch.chdir(tmp_path)

    # Monkeypatch index_cmd in the index_cmd module so the lazy import picks it up
    import fx_alfred.commands.index_cmd as idx_mod

    def _boom(*args, **kwargs):
        raise RuntimeError("index generation failed")

    monkeypatch.setattr(idx_mod, "index_cmd", _boom)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "Test"],
    )
    # File must be created even though index failed
    assert result.exit_code == 0
    assert (rules / "TST-2100-SOP-Test.md").exists()
    # Warning should appear in combined output (click sends err=True to output in CliRunner)
    assert "Warning: Failed to update index: index generation failed" in result.output


# ── v0.4.1 tests ────────────────────────────────────────────────────────────


def test_create_layer_user_writes_to_user_dir(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "USR",
            "--acid",
            "3000",
            "--title",
            "User Doc",
            "--layer",
            "user",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (user_alfred / "USR-3000-SOP-User-Doc.md").exists()


def test_create_layer_user_with_subdir(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "USR",
            "--acid",
            "3000",
            "--title",
            "Sub Doc",
            "--layer",
            "user",
            "--subdir",
            "my-project",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (user_alfred / "my-project" / "USR-3000-SOP-Sub-Doc.md").exists()


def test_create_subdir_nested(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "USR",
            "--acid",
            "3000",
            "--title",
            "Nested",
            "--layer",
            "user",
            "--subdir",
            "team/foo",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (user_alfred / "team" / "foo" / "USR-3000-SOP-Nested.md").exists()


def test_create_subdir_dot_writes_to_user_root(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "USR",
            "--acid",
            "3000",
            "--title",
            "Dot",
            "--layer",
            "user",
            "--subdir",
            ".",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (user_alfred / "USR-3000-SOP-Dot.md").exists()


def test_create_subdir_without_layer_user_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "TST",
            "--acid",
            "2100",
            "--title",
            "Bad",
            "--subdir",
            "foo",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "--subdir is only valid" in result.output


def test_create_subdir_absolute_path_errors(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    (fake_home / ".alfred").mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "USR",
            "--acid",
            "3000",
            "--title",
            "Bad",
            "--layer",
            "user",
            "--subdir",
            "/etc",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "safe relative path" in result.output


def test_create_subdir_dotdot_errors(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    (fake_home / ".alfred").mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "USR",
            "--acid",
            "3000",
            "--title",
            "Bad",
            "--layer",
            "user",
            "--subdir",
            "../escape",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "safe relative path" in result.output


def test_create_layer_user_with_root_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--root",
            str(tmp_path),
            "create",
            "sop",
            "--prefix",
            "USR",
            "--acid",
            "3000",
            "--title",
            "Bad",
            "--layer",
            "user",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "Cannot use --root" in result.output


def test_create_cwd_alfred_no_layer_errors(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.chdir(user_alfred)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "Bad"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "Refusing" in result.output


def test_create_root_alfred_layer_project_errors(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--root",
            str(user_alfred),
            "create",
            "sop",
            "--prefix",
            "TST",
            "--acid",
            "2100",
            "--title",
            "Bad",
            "--layer",
            "project",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "Refusing" in result.output


def test_create_layer_user_no_auto_index(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "USR",
            "--acid",
            "3000",
            "--title",
            "No Index",
            "--layer",
            "user",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # No index file should be created in user layer
    assert not (user_alfred / "USR-0000-REF-Document-Index.md").exists()


def test_create_acid_collision_suggests_area(tmp_path, monkeypatch):
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-2100-SOP-Existing.md").write_text("# existing")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "Dup"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "--area" in result.output


def test_create_user_doc_found_by_list(tmp_path, monkeypatch):
    """End-to-end: user-layer doc discovered by af list as USR."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_alfred = fake_home / ".alfred"
    user_alfred.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    # Create in user layer
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "USR",
            "--acid",
            "3000",
            "--title",
            "User Doc",
            "--layer",
            "user",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # Now list and verify it shows as USR
    result = runner.invoke(cli, ["list"], catch_exceptions=False)
    assert "USR" in result.output
    assert "USR-3000" in result.output


# ── v0.4.2 tests ────────────────────────────────────────────────────────────


def test_create_warns_on_index_failure(sample_project, monkeypatch):
    """Create succeeds even when index_cmd raises, and emits a warning."""
    import fx_alfred.commands.index_cmd as index_module

    def boom(*args, **kwargs):
        raise RuntimeError("simulated index failure")

    monkeypatch.setattr(index_module, "index_cmd", boom)
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "Test"],
        catch_exceptions=False,
    )
    # File must be created and command must succeed
    assert result.exit_code == 0
    assert (sample_project / "rules" / "TST-2100-SOP-Test.md").exists()
    # Warning must appear in output (stderr is mixed in by CliRunner by default)
    combined = result.output + (
        result.stderr if hasattr(result, "stderr") and result.stderr else ""
    )
    assert "Warning" in combined or "index" in combined.lower()


# ── CHG-2121: Document Format Contract compliance ──────────────────────────


# Expected required fields for all types + type-specific optional fields
_FORMAT_CONTRACT_EXPECTATIONS = {
    "sop": {
        "status": "Active",
        "optional_fields": [],
    },
    "prp": {
        "status": "Draft",
        "optional_fields": [],
    },
    "chg": {
        "status": "Proposed",
        "optional_fields": ["Date", "Requested by", "Priority", "Change Type"],
    },
    "adr": {
        "status": "Proposed",
        "optional_fields": [],
    },
    "ref": {
        "status": "Active",
        "optional_fields": [],
    },
    "pln": {
        "status": "Draft",
        "optional_fields": [],
    },
    "inc": {
        "status": "Open",
        "optional_fields": ["Date", "Severity"],
    },
}


def _create_and_read(tmp_path, monkeypatch, doc_type, acid):
    """Helper: create a document and return its content."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            doc_type,
            "--prefix",
            "TST",
            "--acid",
            acid,
            "--title",
            f"Contract {doc_type.upper()}",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"create failed for {doc_type}: {result.output}"
    filename = f"TST-{acid}-{doc_type.upper()}-Contract-{doc_type.upper()}.md"
    path = tmp_path / "rules" / filename
    assert path.exists(), f"File not found: {path}"
    return path.read_text()


@pytest.mark.parametrize(
    "doc_type,acid",
    [
        ("sop", "3001"),
        ("prp", "3002"),
        ("chg", "3003"),
        ("adr", "3004"),
        ("ref", "3005"),
        ("pln", "3006"),
        ("inc", "3007"),
    ],
)
def test_template_has_required_fields(tmp_path, monkeypatch, doc_type, acid):
    """COR-0002: All templates must include Applies to, Last updated, Last reviewed, Status."""
    content = _create_and_read(tmp_path, monkeypatch, doc_type, acid)
    for field in ["Applies to", "Last updated", "Last reviewed", "Status"]:
        assert f"**{field}:**" in content, (
            f"{doc_type} template missing required field: {field}"
        )


@pytest.mark.parametrize(
    "doc_type,acid",
    [
        ("sop", "3011"),
        ("prp", "3012"),
        ("chg", "3013"),
        ("adr", "3014"),
        ("ref", "3015"),
        ("pln", "3016"),
        ("inc", "3017"),
    ],
)
def test_template_field_format_no_list_prefix(tmp_path, monkeypatch, doc_type, acid):
    """COR-0002: Fields use **Key:** Value format, not - **Key:** Value."""
    content = _create_and_read(tmp_path, monkeypatch, doc_type, acid)
    lines = content.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- **") and ":**" in stripped:
            # Allow list items inside body sections (e.g., Impact Analysis)
            # Only flag metadata lines that look like fields
            field_name = stripped.split(":**")[0].replace("- **", "")
            if field_name in (
                "Applies to",
                "Last updated",
                "Last reviewed",
                "Status",
                "Date",
                "Requested by",
                "Priority",
                "Change Type",
                "Severity",
            ):
                pytest.fail(
                    f"{doc_type}: metadata field '{field_name}' uses list prefix '- '"
                )


@pytest.mark.parametrize(
    "doc_type,acid",
    [
        ("sop", "3021"),
        ("prp", "3022"),
        ("chg", "3023"),
        ("adr", "3024"),
        ("ref", "3025"),
        ("pln", "3026"),
        ("inc", "3027"),
    ],
)
def test_template_correct_default_status(tmp_path, monkeypatch, doc_type, acid):
    """COR-0002: Each type has a specific default status value."""
    content = _create_and_read(tmp_path, monkeypatch, doc_type, acid)
    expected_status = _FORMAT_CONTRACT_EXPECTATIONS[doc_type]["status"]
    assert f"**Status:** {expected_status}" in content, (
        f"{doc_type} should have Status: {expected_status}"
    )


def test_chg_template_retains_optional_fields(tmp_path, monkeypatch):
    """CHG-2121: CHG template must have Date, Requested by, Priority, Change Type."""
    content = _create_and_read(tmp_path, monkeypatch, "chg", "3030")
    for field in ["Date", "Requested by", "Priority", "Change Type"]:
        assert f"**{field}:**" in content, (
            f"CHG template missing optional field: {field}"
        )


def test_inc_template_retains_optional_fields(tmp_path, monkeypatch):
    """CHG-2121: INC template must have Date and Severity."""
    content = _create_and_read(tmp_path, monkeypatch, "inc", "3031")
    for field in ["Date", "Severity"]:
        assert f"**{field}:**" in content, (
            f"INC template missing optional field: {field}"
        )


@pytest.mark.parametrize(
    "doc_type,acid",
    [
        ("sop", "3041"),
        ("prp", "3042"),
        ("chg", "3043"),
        ("adr", "3044"),
        ("ref", "3045"),
        ("pln", "3046"),
        ("inc", "3047"),
    ],
)
def test_template_field_order(tmp_path, monkeypatch, doc_type, acid):
    """COR-0002: Required fields appear before --- separator in correct order."""
    content = _create_and_read(tmp_path, monkeypatch, doc_type, acid)
    lines = content.splitlines()

    # Find positions of required fields (before first ---)
    field_positions = {}
    separator_pos = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "---" and separator_pos is None and i > 0:
            separator_pos = i
            break
        for field in ["Applies to", "Last updated", "Last reviewed", "Status"]:
            if stripped.startswith(f"**{field}:**"):
                field_positions[field] = i

    # All required fields must appear before the separator
    for field in ["Applies to", "Last updated", "Last reviewed", "Status"]:
        assert field in field_positions, (
            f"{doc_type}: required field '{field}' not found before first ---"
        )
        assert field_positions[field] < separator_pos, (
            f"{doc_type}: field '{field}' appears after --- separator"
        )

    # Check order: Applies to < Last updated < Last reviewed < Status
    assert field_positions["Applies to"] < field_positions["Last updated"], (
        f"{doc_type}: 'Applies to' must come before 'Last updated'"
    )
    assert field_positions["Last updated"] < field_positions["Last reviewed"], (
        f"{doc_type}: 'Last updated' must come before 'Last reviewed'"
    )
    assert field_positions["Last reviewed"] < field_positions["Status"], (
        f"{doc_type}: 'Last reviewed' must come before 'Status'"
    )


# ── CHG FXA-2160: Replace assert with ClickException ────────────────────────


def test_spec_mode_acid_none_raises_click_exception(tmp_path, monkeypatch):
    """When _next_acid_in_area returns None in spec-file mode, raise ClickException."""
    rules = tmp_path / "rules"
    rules.mkdir()
    monkeypatch.chdir(tmp_path)

    # Create a minimal spec file that uses --area (triggers _next_acid_in_area)
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(
        "type: SOP\n"
        "prefix: TST\n"
        "area: '21'\n"
        "title: Test Spec\n"
        "metadata:\n"
        "  Applies to: test\n"
        "  Last updated: '2026-01-01'\n"
        "  Last reviewed: '2026-01-01'\n"
        "  Status: Active\n"
        "sections:\n"
        "  What Is It?: A test SOP\n"
        "  Why: Testing\n"
        "  When to Use: Always\n"
        "  When NOT to Use: Never\n"
        "  Steps: Step 1\n"
    )

    runner = CliRunner()

    # Mock _next_acid_in_area to return None (simulating unexpected failure)
    with patch("fx_alfred.commands.create_cmd._next_acid_in_area", return_value=None):
        result = runner.invoke(
            cli,
            ["create", "--spec", str(spec_file)],
        )
        assert result.exit_code != 0
        assert "spec-file mode" in result.output


def test_cli_mode_acid_none_raises_click_exception(tmp_path, monkeypatch):
    """When _next_acid_in_area returns None in CLI mode, raise ClickException."""
    rules = tmp_path / "rules"
    rules.mkdir()
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()

    # Mock _next_acid_in_area to return None (simulating unexpected failure)
    with patch("fx_alfred.commands.create_cmd._next_acid_in_area", return_value=None):
        result = runner.invoke(
            cli,
            [
                "create",
                "sop",
                "--prefix",
                "TST",
                "--area",
                "21",
                "--title",
                "CLI Test",
            ],
        )
        assert result.exit_code != 0
        assert "CLI mode" in result.output


# ── FXA-2314: write-path redirect for mapped context (fix) ────────────────────


def test_create_mapped_root_project_layer_writes_to_subdir(tmp_path):
    """In a mapped context, create writes the new doc to ~/.alfred/<NAME>/, not <repo>/rules/.

    Expected behavior after the fix: when --root points to a repo registered in
    projects.json, project-layer writes are redirected to ~/.alfred/<NAME>/ so
    that reads and writes are symmetric.
    """
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)

    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()

    subdir = alfred / "MYP"
    subdir.mkdir()

    (alfred / "projects.json").write_text(
        json.dumps({"projects": {str(ext_repo.resolve()): "MYP"}}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "chg",
            "--root",
            str(ext_repo),
            "--prefix",
            "MYP",
            "--acid",
            "2100",
            "--title",
            "My Change",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    # File must land in ~/.alfred/MYP/, not in <repo>/rules/
    expected = subdir / "MYP-2100-CHG-My-Change.md"
    assert expected.exists(), (
        f"Expected new doc at {expected} (in ~/.alfred/MYP/), "
        f"but it was not created there. Output: {result.output}"
    )
    # <repo>/rules/ must NOT be created at all
    assert not (ext_repo / "rules").exists(), (
        "<repo>/rules/ must not be created when root is a mapped context"
    )


def test_create_unmapped_root_still_writes_to_rules(tmp_path):
    """Regression guard: an unmapped root still writes to <root>/rules/."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    # No projects.json — this root is not mapped

    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "chg",
            "--root",
            str(ext_repo),
            "--prefix",
            "TST",
            "--acid",
            "2100",
            "--title",
            "My Change",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (ext_repo / "rules" / "TST-2100-CHG-My-Change.md").exists()


def test_create_layer_user_subdir_unaffected_by_mapping(tmp_path):
    """Regression guard: --layer user --subdir <NAME> still writes to ~/.alfred/<NAME>/ regardless of mapping."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)

    ext_repo = tmp_path / "ext_repo"
    ext_repo.mkdir()

    # Register ext_repo as MYP — this mapping must NOT interfere with --layer user --subdir MYP
    (alfred / "projects.json").write_text(
        json.dumps({"projects": {str(ext_repo.resolve()): "MYP"}}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "MYP",
            "--acid",
            "3000",
            "--title",
            "User Subdir Doc",
            "--layer",
            "user",
            "--subdir",
            "MYP",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (alfred / "MYP" / "MYP-3000-SOP-User-Subdir-Doc.md").exists()


# ── FXA-265: Filename validation on create ──────────────────────────────────


def test_create_rejects_title_that_slugifies_to_empty(tmp_path, monkeypatch):
    """Title '???' slugifies to empty string, producing an invalid filename.

    Before the fix, af create silently writes TST-9998-SOP-.md which is
    invisible to af read / af list / the index (FILENAME_PATTERN title group
    requires at least one character).
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "9998", "--title", "???"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0, (
        f"Expected non-zero exit for empty-slug title, got 0. Output: {result.output}"
    )
    # Error message must mention the offending title or slug
    assert "???" in result.output or "slug" in result.output.lower(), (
        f"Error should mention the title or slug issue. Output: {result.output}"
    )
    # No file should exist on disk (the write must be blocked before filesystem IO)
    bad_path = tmp_path / "rules" / "TST-9998-SOP-.md"
    assert not bad_path.exists(), f"File was created at {bad_path} but should not exist"
    # af read should also report not found (sanity: file isn't accidentally readable)
    read_result = runner.invoke(cli, ["read", "TST-9998"], catch_exceptions=False)
    assert read_result.exit_code != 0, (
        f"af read should not find TST-9998, got exit {read_result.exit_code}"
    )


def test_create_rejects_spec_with_title_that_slugifies_to_empty(tmp_path, monkeypatch):
    """Spec-file path: title '???' slugifies to empty — filename fails validation."""
    monkeypatch.chdir(tmp_path)

    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(
        "type: SOP\n"
        "prefix: TST\n"
        "acid: '9998'\n"
        "title: '???'\n"
        "metadata:\n"
        "  Applies to: test\n"
        "  Last updated: '2026-01-01'\n"
        "  Last reviewed: '2026-01-01'\n"
        "  Status: Active\n"
        "sections:\n"
        "  What Is It?: Test\n"
        "  Why: Test\n"
        "  When to Use: Test\n"
        "  When NOT to Use: Test\n"
        "  Steps: Test\n"
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "--spec", str(spec_file)],
        catch_exceptions=False,
    )
    assert result.exit_code != 0, (
        f"Expected non-zero exit for spec with empty-slug title, got 0. "
        f"Output: {result.output}"
    )
    # Error message must mention the offending title or slug
    assert "???" in result.output or "slug" in result.output.lower(), (
        f"Error should mention the title or slug issue. Output: {result.output}"
    )
    # No file should exist on disk
    bad_path = tmp_path / "rules" / "TST-9998-SOP-.md"
    assert not bad_path.exists(), f"File was created at {bad_path} but should not exist"


def test_create_rejects_title_dashes_and_spaces(tmp_path, monkeypatch):
    """Title '- - -' slugifies to empty string — filename fails validation.

    All characters are either hyphens or spaces; slugify strips leading/trailing
    hyphens and collapses runs, leaving an empty string.
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "9999", "--title", "- - -"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0, (
        f"Expected non-zero exit for dash-only title, got 0. Output: {result.output}"
    )
    # Error message must be actionable — check for common keywords
    combined = result.output.lower()
    assert any(
        word in combined for word in ("- - -", "slug", "filename", "title", "empty")
    ), f"Error should mention the title or slug issue. Output: {result.output}"
    # No file should exist on disk
    bad_path = tmp_path / "rules" / "TST-9999-SOP-.md"
    assert not bad_path.exists(), f"File was created at {bad_path} but should not exist"


def test_create_rejects_whitespace_only_title(tmp_path):
    """Title '   ' slugifies to "" via the early-return branch in slugify().

    slugify("   ") → strip() → empty string → return "" immediately (line 12-13).
    This is a distinct code path from "???" (unsafe chars stripped) and "- - -"
    (hyphens collapsed after whitespace replacement), so it deserves its own
    coverage pin.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--root",
            str(tmp_path),
            "create",
            "sop",
            "--prefix",
            "TST",
            "--acid",
            "9995",
            "--title",
            "   ",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code != 0, (
        f"Expected non-zero exit for whitespace-only title, got 0. "
        f"Output: {result.output}"
    )
    # Error message must be actionable
    combined = result.output.lower()
    assert any(
        word in combined for word in ("slug", "filename", "title", "empty", "invalid")
    ), f"Error should mention the title or slug issue. Output: {result.output}"
    # No file should exist on disk
    bad_path = tmp_path / "rules" / "TST-9995-SOP-.md"
    assert not bad_path.exists(), f"File was created at {bad_path} but should not exist"


def test_create_allows_title_with_unsafe_chars_that_slugify_nonempty(
    tmp_path, monkeypatch
):
    """Title 'a?b' slugifies to 'ab' (non-empty) — must still create successfully.

    Regression guard: filename validation must not over-block titles that
    produce a valid slug after unsafe characters are stripped.
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "9997", "--title", "a?b"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (
        f"Title 'a?b' should slugify to 'ab' (non-empty) and succeed. "
        f"Output: {result.output}"
    )
    expected = tmp_path / "rules" / "TST-9997-SOP-ab.md"
    assert expected.exists(), f"Expected file at {expected} but it does not exist"


def test_create_dry_run_rejects_title_that_slugifies_to_empty(tmp_path, monkeypatch):
    """Guard-before-dry-run: title '???' slugifies to empty — reject before echoing content.

    The filename validation fires before the dry-run block, so we expect:
    - non-zero exit
    - actionable error referencing the title or slug
    - no file written to disk
    - no dry-run content echoed ("Dry run", "Created", document body absent)
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "TST",
            "--acid",
            "9996",
            "--title",
            "???",
            "--dry-run",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code != 0, (
        f"Expected non-zero exit for empty-slug title with --dry-run, got 0. "
        f"Output: {result.output}"
    )
    # Error message must mention the offending title or slug
    assert "???" in result.output or "slug" in result.output.lower(), (
        f"Error should mention the title or slug issue. Output: {result.output}"
    )
    # No file should exist on disk (validation fires before filesystem IO)
    bad_path = tmp_path / "rules" / "TST-9996-SOP-.md"
    assert not bad_path.exists(), f"File was created at {bad_path} but should not exist"
    # Dry-run content MUST NOT be echoed — the guard fires before it
    assert "Dry run" not in result.output, (
        f"Dry-run content was echoed despite failed validation. Output: {result.output}"
    )
    assert "Created" not in result.output, (
        f"'Created' appeared in output despite failed validation. Output: {result.output}"
    )


def test_create_spec_dry_run_rejects_title_that_slugifies_to_empty(
    tmp_path, monkeypatch
):
    """Guard-before-dry-run spec path: title '???' slugifies to empty — reject before echo.

    Same contract as the non-spec dry-run test but via --spec with --dry-run flag.
    """
    monkeypatch.chdir(tmp_path)

    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(
        "type: SOP\n"
        "prefix: TST\n"
        "acid: '9996'\n"
        "title: '???'\n"
        "metadata:\n"
        "  Applies to: test\n"
        "  Last updated: '2026-01-01'\n"
        "  Last reviewed: '2026-01-01'\n"
        "  Status: Active\n"
        "sections:\n"
        "  What Is It?: Test\n"
        "  Why: Test\n"
        "  When to Use: Test\n"
        "  When NOT to Use: Test\n"
        "  Steps: Test\n"
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "--spec", str(spec_file), "--dry-run"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0, (
        f"Expected non-zero exit for spec with empty-slug title + --dry-run, got 0. "
        f"Output: {result.output}"
    )
    # Error message must mention the offending title or slug
    assert "???" in result.output or "slug" in result.output.lower(), (
        f"Error should mention the title or slug issue. Output: {result.output}"
    )
    # No file should exist on disk
    bad_path = tmp_path / "rules" / "TST-9996-SOP-.md"
    assert not bad_path.exists(), f"File was created at {bad_path} but should not exist"
    # Dry-run content MUST NOT be echoed
    assert "Dry run" not in result.output, (
        f"Dry-run content was echoed despite failed validation. Output: {result.output}"
    )
    assert "Created" not in result.output, (
        f"'Created' appeared in output despite failed validation. Output: {result.output}"
    )


def test_create_without_acid_or_area_assigns_next_sequential(tmp_path, monkeypatch):
    """No --acid and no --area: the simplest mode — max existing ACID for the
    prefix + 1, starting at 0001 on an empty project (0000 is the index)."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--title", "First"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "rules" / "TST-0001-SOP-First.md").exists()

    result = runner.invoke(
        cli,
        ["create", "ref", "--prefix", "TST", "--title", "Second"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "rules" / "TST-0002-REF-Second.md").exists()


def test_sequential_acid_continues_after_the_highest_existing_number(
    tmp_path, monkeypatch
):
    """Area-numbered documents already in the project set the high-water mark:
    with TST-2100 present the next sequential number is 2101, never a gap-fill."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "Area Doc"],
        catch_exceptions=False,
    )
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--title", "Next"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "rules" / "TST-2101-SOP-Next.md").exists()


def test_create_empty_area_is_rejected_not_treated_as_sequential(tmp_path, monkeypatch):
    """`--area ""` (an unset shell variable) must fail validation, not silently
    switch to sequential numbering."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["create", "sop", "--prefix", "TST", "--area", "", "--title", "Empty Area"]
    )
    assert result.exit_code != 0
    assert "--area must be exactly 2 digits" in result.output
    assert (
        not list((tmp_path / "rules").glob("TST-*"))
        if (tmp_path / "rules").exists()
        else True
    )


def _register_subproject(tmp_path):
    alfred = Path.home() / ".alfred"
    sub = alfred / "MYP"
    sub.mkdir(parents=True, exist_ok=True)
    other_repo = tmp_path / "other_repo"
    other_repo.mkdir()
    (alfred / "projects.json").write_text(
        json.dumps({"projects": {str(other_repo.resolve()): "MYP"}}), encoding="utf-8"
    )
    return sub


def test_sequential_acid_sees_registered_user_subdir_from_outside_its_project(
    tmp_path, monkeypatch
):
    """`--layer user --subdir MYP` run outside MYP's mapped project: the USR scan
    hides MYP, so allocation must scan the write target itself (max 0005 → 0006)."""
    sub = _register_subproject(tmp_path)
    (sub / "TST-0005-SOP-Old.md").write_text("# SOP-0005: Old\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "TST",
            "--layer",
            "user",
            "--subdir",
            "MYP",
            "--title",
            "New",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (sub / "TST-0006-SOP-New.md").exists()


def test_explicit_acid_collision_is_detected_in_registered_user_subdir(
    tmp_path, monkeypatch
):
    sub = _register_subproject(tmp_path)
    (sub / "TST-0006-SOP-Taken.md").write_text("# SOP-0006: Taken\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "TST",
            "--acid",
            "0006",
            "--layer",
            "user",
            "--subdir",
            "MYP",
            "--title",
            "Dup",
        ],
    )
    assert result.exit_code != 0
    assert "already exists" in result.output
    assert not (sub / "TST-0006-SOP-Dup.md").exists()


def test_project_layer_allocation_ignores_archived_docs_in_nested_dirs(
    tmp_path, monkeypatch
):
    """Project layer scans rules/ non-recursively; allocation must not pick up
    rules/archive/ (an archived TST-9999 would otherwise exhaust the range)."""
    rules = tmp_path / "rules"
    (rules / "archive").mkdir(parents=True)
    (rules / "archive" / "TST-9999-SOP-Archived.md").write_text(
        "# SOP-9999: Archived\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--title", "Fresh"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (rules / "TST-0001-SOP-Fresh.md").exists()


def test_user_subdir_allocation_excludes_the_callers_project_layer(
    tmp_path, monkeypatch
):
    """Run from registered project B (PRJ docs live in ~/.alfred/B) writing to
    --layer user --subdir A: B's documents must not shape A's numbering."""
    alfred = Path.home() / ".alfred"
    a = alfred / "A"
    b = alfred / "B"
    a.mkdir(parents=True, exist_ok=True)
    b.mkdir(parents=True, exist_ok=True)
    repo_b = tmp_path / "repo_b"
    repo_b.mkdir()
    repo_a = tmp_path / "repo_a"
    repo_a.mkdir()
    # Both A and B are registered units. (An UNREGISTERED A would be global
    # USR, where B's IDs must stay in range — see the global-write test.)
    (alfred / "projects.json").write_text(
        json.dumps(
            {"projects": {str(repo_b.resolve()): "B", str(repo_a.resolve()): "A"}}
        ),
        encoding="utf-8",
    )
    (b / "TST-0500-SOP-In-B.md").write_text("# SOP-0500: In B\n", encoding="utf-8")
    (a / "TST-0005-SOP-In-A.md").write_text("# SOP-0005: In A\n", encoding="utf-8")
    monkeypatch.chdir(repo_b)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "TST",
            "--layer",
            "user",
            "--subdir",
            "A",
            "--title",
            "Next In A",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (a / "TST-0006-SOP-Next-In-A.md").exists(), sorted(
        p.name for p in a.iterdir()
    )


def test_global_user_write_keeps_caller_project_ids_out_of_the_range(
    tmp_path, monkeypatch
):
    """`--layer user` from an ordinary (unmapped) project: the new document is
    globally visible USR, so it must not reuse an ACID the caller's rules/
    already holds (a USR/PRJ duplicate breaks the next scan)."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-0001-SOP-Local.md").write_text(
        "# SOP-0001: Local\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--layer", "user", "--title", "Global"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (Path.home() / ".alfred" / "TST-0002-SOP-Global.md").exists()


def test_nested_subdir_of_registered_project_allocates_across_the_whole_project(
    tmp_path, monkeypatch
):
    """`--subdir A/foo` with A registered: A is one PRJ unit scanned recursively,
    so allocation must see A/ and its siblings, not only A/foo."""
    sub = _register_subproject(tmp_path)  # registers MYP
    (sub / "TST-0005-SOP-Top.md").write_text("# SOP-0005: Top\n", encoding="utf-8")
    (sub / "bar").mkdir()
    (sub / "bar" / "TST-0007-SOP-Sibling.md").write_text(
        "# SOP-0007: Sibling\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "TST",
            "--layer",
            "user",
            "--subdir",
            "MYP/foo",
            "--title",
            "Nested",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (sub / "foo" / "TST-0008-SOP-Nested.md").exists(), sorted(
        str(p.relative_to(sub)) for p in sub.rglob("*.md")
    )


def test_global_user_write_sees_ids_in_every_registered_unit(tmp_path, monkeypatch):
    """A global USR document must not reuse an ACID held by ANY registered unit
    (a later scan from that unit would combine both and fail layer validation)."""
    sub = _register_subproject(tmp_path)  # MYP registered, caller unmapped
    (sub / "TST-0001-SOP-In-Unit.md").write_text(
        "# SOP-0001: In Unit\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--layer", "user", "--title", "Global"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (Path.home() / ".alfred" / "TST-0002-SOP-Global.md").exists()


def test_symlinked_registered_unit_is_recognised(tmp_path, monkeypatch):
    """`~/.alfred/<NAME>` may be a symlink to external storage; the unit must
    still be recognised (lexically) and scanned before allocating."""
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    external = tmp_path / "external_store"
    external.mkdir()
    (alfred / "LNK").symlink_to(external, target_is_directory=True)
    other_repo = tmp_path / "other_repo"
    other_repo.mkdir()
    (alfred / "projects.json").write_text(
        json.dumps({"projects": {str(other_repo.resolve()): "LNK"}}), encoding="utf-8"
    )
    (external / "TST-0005-SOP-Old.md").write_text("# SOP-0005: Old\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "TST",
            "--layer",
            "user",
            "--subdir",
            "LNK",
            "--title",
            "Via Link",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (external / "TST-0006-SOP-Via-Link.md").exists(), sorted(
        p.name for p in external.iterdir()
    )


def test_create_refuses_scanner_invisible_user_destination(tmp_path, monkeypatch):
    """`logs/` under ~/.alfred (or under a registered unit) is skipped by the
    scanner, so documents written there could never be seen again: reject."""
    _register_subproject(tmp_path)  # MYP
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    for subdir in ("logs", "logs/x", "MYP/logs"):
        result = runner.invoke(
            cli,
            [
                "create",
                "sop",
                "--prefix",
                "TST",
                "--layer",
                "user",
                "--subdir",
                subdir,
                "--title",
                "Lost",
            ],
        )
        assert result.exit_code != 0, subdir
        assert "excluded from document scanning" in result.output, subdir
    assert not list((Path.home() / ".alfred").rglob("TST-*"))


def test_create_serialises_allocation_with_a_target_lock(tmp_path, monkeypatch):
    """Allocation + write run under a per-target lock so two concurrent creates
    cannot pick the same next ACID. A held lock makes the second create fail
    fast instead of allocating."""
    fcntl = pytest.importorskip(
        "fcntl"
    )  # POSIX-only lock; the fallback has its own test

    from fx_alfred.commands.create_cmd import lock_path_for

    rules = tmp_path / "rules"
    rules.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AF_CREATE_LOCK_TIMEOUT", "0.2")
    lock_path = lock_path_for(rules)
    with open(lock_path, "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        runner = CliRunner()
        result = runner.invoke(
            cli, ["create", "sop", "--prefix", "TST", "--title", "Blocked"]
        )
        assert result.exit_code != 0
        assert "another af create" in result.output
        assert not list(rules.glob("TST-*"))
    assert not list(rules.glob(".*")), "no lock file inside the target"
    # Lock released → the same create succeeds.
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--title", "Blocked"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (rules / "TST-0001-SOP-Blocked.md").exists()


def test_every_create_takes_the_same_machine_wide_lock(tmp_path, monkeypatch):
    """Allocation scopes overlap (a global user create numbers against every
    registered unit AND the caller's rules/), so there is exactly one lock."""
    from fx_alfred.commands.create_cmd import lock_path_for

    sub = _register_subproject(tmp_path)
    alfred = Path.home() / ".alfred"
    rules = tmp_path / "rules"
    assert (
        lock_path_for(sub / "foo")
        == lock_path_for(alfred / "x")
        == lock_path_for(rules)
    )
    assert lock_path_for(rules).parent != rules


def test_create_lock_falls_back_without_fcntl(tmp_path, monkeypatch):
    """Without the POSIX fcntl module (Windows) the lock must still work via an
    exclusive-create lock file, and `af create` must stay importable."""
    from fx_alfred.commands import create_cmd

    monkeypatch.setattr(create_cmd, "fcntl", None)
    rules = tmp_path / "rules"
    rules.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AF_CREATE_LOCK_TIMEOUT", "0.2")
    marker = create_cmd.lock_path_for(rules).with_suffix(".excl")
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("held", encoding="utf-8")
    try:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["create", "sop", "--prefix", "TST", "--title", "Blocked"]
        )
        assert result.exit_code != 0
        assert "another af create" in result.output
        assert not list(rules.glob("TST-*"))
    finally:
        marker.unlink()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--title", "Blocked"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (rules / "TST-0001-SOP-Blocked.md").exists()
    assert not marker.exists(), "fallback lock file must be released"


def test_stale_fallback_lock_marker_is_reclaimed(tmp_path, monkeypatch):
    """A fallback marker left behind by a killed process must not block
    creation forever: markers older than AF_CREATE_LOCK_STALE are reclaimed."""

    from fx_alfred.commands import create_cmd

    monkeypatch.setattr(create_cmd, "fcntl", None)
    monkeypatch.setenv("AF_CREATE_LOCK_TIMEOUT", "0.2")
    monkeypatch.setenv("AF_CREATE_LOCK_STALE", "1")
    rules = tmp_path / "rules"
    rules.mkdir()
    monkeypatch.chdir(tmp_path)
    marker = create_cmd.lock_path_for(rules).with_suffix(".excl")
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("999999 0", encoding="utf-8")  # pid 999999: not alive
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--title", "Reclaimed"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (rules / "TST-0001-SOP-Reclaimed.md").exists()
    assert not marker.exists()


def test_symlink_into_scanner_invisible_logs_is_rejected(tmp_path, monkeypatch):
    """`~/.alfred/safe` → `~/.alfred/logs`: lexically fine, but the write lands
    in the excluded logs tree. Resolve before judging."""
    alfred = Path.home() / ".alfred"
    (alfred / "logs").mkdir(parents=True, exist_ok=True)
    (alfred / "safe").symlink_to(alfred / "logs", target_is_directory=True)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create",
            "sop",
            "--prefix",
            "TST",
            "--layer",
            "user",
            "--subdir",
            "safe",
            "--title",
            "Hidden",
        ],
    )
    assert result.exit_code != 0
    assert "excluded from document scanning" in result.output
    assert not list((alfred / "logs").glob("TST-*"))


def test_lock_file_lives_in_the_users_alfred_dir_not_tmpdir(tmp_path, monkeypatch):
    """TMPDIR varies per process/service; ~/.alfred is the one per-user place
    every process touching the namespace shares, so the lock lives there."""
    from fx_alfred.commands.create_cmd import lock_path_for

    monkeypatch.setenv("TMPDIR", str(tmp_path / "private-tmp"))
    assert lock_path_for(tmp_path) == Path.home() / ".alfred" / ".af-create.lock"


def test_index_regeneration_runs_inside_the_create_lock(tmp_path, monkeypatch):
    """The derived PREFIX-0000 index is written from a scan; if that ran after
    the lock was released, two creates could interleave and lose the newest
    document from the index. Assert the lock is still held during it."""
    fcntl = pytest.importorskip(
        "fcntl"
    )  # POSIX-only lock; the fallback has its own test

    from fx_alfred.commands import create_cmd

    rules = tmp_path / "rules"
    rules.mkdir()
    monkeypatch.chdir(tmp_path)
    seen = {}

    def fake_index_update(ctx):
        with open(create_cmd.lock_path_for(rules), "a+") as probe:
            try:
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
                seen["held"] = False
                fcntl.flock(probe, fcntl.LOCK_UN)
            except OSError:
                seen["held"] = True

    monkeypatch.setattr(create_cmd, "invoke_index_update", fake_index_update)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--title", "Indexed"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert seen.get("held") is True


def test_dry_run_writes_nothing_not_even_a_lock_file(tmp_path, monkeypatch):
    rules = tmp_path / "rules"
    rules.mkdir()
    monkeypatch.chdir(tmp_path)
    alfred = Path.home() / ".alfred"
    before = sorted(p.name for p in alfred.iterdir()) if alfred.exists() else None
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--title", "Preview", "--dry-run"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert not list(rules.glob("TST-*"))
    after = sorted(p.name for p in alfred.iterdir()) if alfred.exists() else None
    assert after == before, "dry run must not create ~/.alfred or a lock file"


def test_project_create_works_when_user_alfred_dir_is_read_only(tmp_path, monkeypatch):
    """Read-only HOME (containers, service accounts): the lock degrades to the
    temp dir and a project-layer create still succeeds."""
    import os

    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    alfred = Path.home() / ".alfred"
    alfred.mkdir(parents=True, exist_ok=True)
    rules = tmp_path / "rules"
    rules.mkdir()
    monkeypatch.chdir(tmp_path)
    alfred.chmod(0o500)
    try:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["create", "sop", "--prefix", "TST", "--title", "Locked Home"],
            catch_exceptions=False,
        )
    finally:
        alfred.chmod(0o700)
    assert result.exit_code == 0, result.output
    assert (rules / "TST-0001-SOP-Locked-Home.md").exists()


def test_live_fallback_lock_owner_is_never_reclaimed(tmp_path, monkeypatch):
    """A marker whose recorded pid is alive is not reclaimed, however old."""
    import os

    from fx_alfred.commands import create_cmd

    monkeypatch.setattr(create_cmd, "fcntl", None)
    monkeypatch.setenv("AF_CREATE_LOCK_TIMEOUT", "0.2")
    monkeypatch.setenv("AF_CREATE_LOCK_STALE", "0")
    rules = tmp_path / "rules"
    rules.mkdir()
    monkeypatch.chdir(tmp_path)
    marker = create_cmd.lock_path_for(rules).with_suffix(".excl")
    marker.write_text(f"{os.getpid()} 0", encoding="utf-8")  # this process: alive
    old = 1_000_000_000
    os.utime(marker, (old, old))
    try:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["create", "sop", "--prefix", "TST", "--title", "Held"]
        )
        assert result.exit_code != 0
        assert "another af create" in result.output
        assert marker.exists(), "live owner's marker must survive"
    finally:
        marker.unlink()


def test_stale_marker_reclaim_is_atomic_between_two_waiters(tmp_path, monkeypatch):
    """Two waiters judging the same dead marker: reclaim is a rename, so only
    one wins; the loser sees the file gone and retries the create."""
    import os

    from fx_alfred.commands import create_cmd

    marker = tmp_path / "m.excl"
    marker.write_text("999999 0", encoding="utf-8")
    # Simulate the loser: the marker was already renamed away by the winner.
    real_rename = os.rename

    def racing_rename(src, dst):
        real_rename(src, str(src) + ".winner")  # the other waiter got there first
        return real_rename(src, dst)  # raises FileNotFoundError for us

    monkeypatch.setattr(os, "rename", racing_rename)
    assert create_cmd._reclaim_stale_marker(marker) is True
    assert not marker.exists()
