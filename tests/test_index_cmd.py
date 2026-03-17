from click.testing import CliRunner
from fx_alfred.cli import cli


def test_index_handles_multiple_prefixes(tmp_path, monkeypatch):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "ALF-2100-SOP-Something.md").write_text("# ALF doc")
    (rules_dir / "NRV-2200-SOP-Other.md").write_text("# NRV doc")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["index"], catch_exceptions=False)
    assert result.exit_code == 0
    alf_index = rules_dir / "ALF-0000-REF-Document-Index.md"
    nrv_index = rules_dir / "NRV-0000-REF-Document-Index.md"
    assert alf_index.exists()
    assert nrv_index.exists()
    assert "2100" in alf_index.read_text()
    assert "2200" in nrv_index.read_text()


def test_index_only_indexes_prj_layer(sample_project, monkeypatch):
    """Index command only indexes PRJ layer documents."""
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["index"], catch_exceptions=False)
    assert result.exit_code == 0
    # Check that index was created in rules/ for ALF prefix
    doc_indexes = list((sample_project / "rules").glob("*-0000-REF-*.md"))
    assert len(doc_indexes) == 1
    content = doc_indexes[0].read_text()
    assert "2201" in content
    assert "2202" in content


def test_index_empty_project(tmp_path, monkeypatch):
    """Index command handles empty project."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["index"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "No PRJ documents" in result.output


def test_index_with_root_option(tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "TST-2100-SOP-Something.md").write_text("# test")
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--root", str(tmp_path), "index"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert (rules_dir / "TST-0000-REF-Document-Index.md").exists()


def test_index_with_root_after_subcommand(tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "TST-2100-SOP-Something.md").write_text("# test")
    runner = CliRunner()
    result = runner.invoke(
        cli, ["index", "--root", str(tmp_path)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert (rules_dir / "TST-0000-REF-Document-Index.md").exists()
