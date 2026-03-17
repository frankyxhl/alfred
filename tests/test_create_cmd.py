from click.testing import CliRunner
from fx_alfred.cli import cli


def test_create_sop_without_docs_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "My SOP"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (tmp_path / "docs" / "TST-2100-SOP-My-SOP.md").exists()


def test_create_rejects_lowercase_prefix(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["create", "sop", "--prefix", "tst", "--acid", "2100", "--title", "Bad"]
    )
    assert result.exit_code != 0


def test_create_rejects_invalid_acid(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["create", "sop", "--prefix", "TST", "--acid", "21", "--title", "Bad"]
    )
    assert result.exit_code != 0


def test_create_sop(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "My New SOP"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    created = tmp_path / "docs" / "TST-2100-SOP-My-New-SOP.md"
    assert created.exists()
    content = created.read_text()
    assert "SOP-2100" in content
    assert "My New SOP" in content


def test_create_refuses_duplicate(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "TST-2100-SOP-Existing.md").write_text("# existing")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "sop", "--prefix", "TST", "--acid", "2100", "--title", "Duplicate"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
