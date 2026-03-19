from pathlib import Path

import pytest
from click.testing import CliRunner

from fx_alfred.cli import cli


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


def test_create_neither_acid_nor_area_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--title", "No ACID"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "Must specify either" in result.output


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
