from click.testing import CliRunner
from fx_alfred.cli import cli


def test_index_handles_multiple_prefixes(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ALF-2100-SOP-Something.md").write_text("# ALF doc")
    (docs_dir / "NRV-2200-SOP-Other.md").write_text("# NRV doc")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["index"], catch_exceptions=False)
    assert result.exit_code == 0
    alf_index = docs_dir / "ALF-0000-REF-Document-Index.md"
    nrv_index = docs_dir / "NRV-0000-REF-Document-Index.md"
    assert alf_index.exists()
    assert nrv_index.exists()
    assert "2100" in alf_index.read_text()
    assert "2200" in nrv_index.read_text()


def test_index_regenerates_cor_index(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["index"], catch_exceptions=False)
    assert result.exit_code == 0
    index_file = sample_project / ".alfred" / "COR-0000-REF-Document-Index.md"
    assert index_file.exists()
    content = index_file.read_text()
    assert "1000" in content
    assert "0001" in content


def test_index_regenerates_docs_index(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    runner = CliRunner()
    result = runner.invoke(cli, ["index"], catch_exceptions=False)
    assert result.exit_code == 0
    doc_indexes = list((sample_project / "docs").glob("*-0000-REF-*.md"))
    assert len(doc_indexes) == 1
    content = doc_indexes[0].read_text()
    assert "2201" in content
