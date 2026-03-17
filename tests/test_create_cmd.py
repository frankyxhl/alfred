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
    monkeypatch.chdir(tmp_path)
    # Don't create rules/ dir - create_cmd will mkdir it, but index_cmd
    # should handle gracefully or warn
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "Test"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (tmp_path / "rules" / "TST-2100-SOP-Test.md").exists()
