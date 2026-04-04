"""Tests for scripts/build_docs.py (CHG FXA-2196)."""

from pathlib import Path
from textwrap import dedent

from scripts.build_docs import (
    build_nav,
    clean_docs_dir,
    copy_cor_files,
    create_index,
    parse_h1,
    update_mkdocs_yml,
)


def _make_cor_file(directory: Path, name: str, h1: str) -> Path:
    """Create a minimal COR document."""
    path = directory / name
    path.write_text(f"# {h1}\n\n**Applies to:** All\n", encoding="utf-8")
    return path


class TestParseH1:
    def test_valid_sop(self, tmp_path: Path) -> None:
        path = _make_cor_file(tmp_path, "COR-1000-SOP-Create-SOP.md", "SOP-1000: Create SOP")
        result = parse_h1(path)
        assert result == ("SOP", 1000, "Create SOP")

    def test_valid_ref(self, tmp_path: Path) -> None:
        path = _make_cor_file(tmp_path, "COR-0001-REF-Glossary.md", "REF-0001: Glossary")
        result = parse_h1(path)
        assert result == ("REF", 1, "Glossary")

    def test_no_h1(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.md"
        path.write_text("No heading here\n", encoding="utf-8")
        assert parse_h1(path) is None

    def test_malformed_h1(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.md"
        path.write_text("# Just a title\n", encoding="utf-8")
        assert parse_h1(path) is None


class TestBuildNav:
    def test_groups_by_type(self, tmp_path: Path) -> None:
        files = [
            _make_cor_file(tmp_path, "COR-1000-SOP-A.md", "SOP-1000: Alpha"),
            _make_cor_file(tmp_path, "COR-0001-REF-B.md", "REF-0001: Beta"),
            _make_cor_file(tmp_path, "COR-1001-SOP-C.md", "SOP-1001: Charlie"),
        ]
        nav = build_nav(files)
        assert nav[0] == {"Home": "index.md"}
        # REF comes before SOP alphabetically
        assert "REF" in nav[1]
        assert "SOP" in nav[2]

    def test_sorts_by_acid(self, tmp_path: Path) -> None:
        files = [
            _make_cor_file(tmp_path, "COR-1500-SOP-B.md", "SOP-1500: Bravo"),
            _make_cor_file(tmp_path, "COR-1000-SOP-A.md", "SOP-1000: Alpha"),
        ]
        nav = build_nav(files)
        sop_group = nav[1]["SOP"]
        labels = [list(e.keys())[0] for e in sop_group]
        assert labels[0].startswith("SOP-1000")
        assert labels[1].startswith("SOP-1500")

    def test_empty_list(self) -> None:
        nav = build_nav([])
        assert nav == [{"Home": "index.md"}]


class TestCleanDocsDir:
    def test_removes_and_recreates(self, tmp_path: Path, monkeypatch: object) -> None:
        import scripts.build_docs as mod

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "stale.md").write_text("old", encoding="utf-8")

        monkeypatch.setattr(mod, "DOCS_DIR", docs)  # type: ignore[attr-defined]
        clean_docs_dir()

        assert docs.exists()
        assert list(docs.iterdir()) == []


class TestCopyCorFiles:
    def test_copies_only_cor(self, tmp_path: Path, monkeypatch: object) -> None:
        import scripts.build_docs as mod

        rules = tmp_path / "rules"
        rules.mkdir()
        _make_cor_file(rules, "COR-1000-SOP-A.md", "SOP-1000: A")
        _make_cor_file(rules, "INIT.md", "Not COR")
        _make_cor_file(rules, "FXA-2100-SOP-B.md", "SOP-2100: B")

        docs = tmp_path / "docs"
        docs.mkdir()

        monkeypatch.setattr(mod, "RULES_DIR", rules)  # type: ignore[attr-defined]
        monkeypatch.setattr(mod, "DOCS_DIR", docs)  # type: ignore[attr-defined]

        copied = copy_cor_files()
        assert len(copied) == 1
        assert copied[0].name == "COR-1000-SOP-A.md"


class TestCreateIndex:
    def test_creates_index_md(self, tmp_path: Path, monkeypatch: object) -> None:
        import scripts.build_docs as mod

        docs = tmp_path / "docs"
        docs.mkdir()
        monkeypatch.setattr(mod, "DOCS_DIR", docs)  # type: ignore[attr-defined]

        create_index()
        index = docs / "index.md"
        assert index.exists()
        assert "Alfred" in index.read_text(encoding="utf-8")


class TestUpdateMkdocsYml:
    def test_updates_nav_section(self, tmp_path: Path, monkeypatch: object) -> None:
        import scripts.build_docs as mod

        yml = tmp_path / "mkdocs.yml"
        yml.write_text(
            dedent("""\
                site_name: Test
                theme:
                  name: material
                nav:
                - Home: index.md
            """),
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "MKDOCS_YML", yml)  # type: ignore[attr-defined]

        new_nav = [{"Home": "index.md"}, {"SOP": [{"SOP-1000: Create": "COR-1000.md"}]}]
        update_mkdocs_yml(new_nav)

        content = yml.read_text(encoding="utf-8")
        assert "site_name: Test" in content
        assert "SOP-1000" in content
        assert "COR-1000.md" in content

    def test_preserves_non_nav_config(self, tmp_path: Path, monkeypatch: object) -> None:
        import scripts.build_docs as mod

        yml = tmp_path / "mkdocs.yml"
        yml.write_text(
            dedent("""\
                site_name: Test
                markdown_extensions:
                - pymdownx.superfences:
                    custom_fences:
                    - name: mermaid
                      class: mermaid
                      format: !!python/name:pymdownx.superfences.fence_code_format
                nav:
                - Home: index.md
            """),
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "MKDOCS_YML", yml)  # type: ignore[attr-defined]

        update_mkdocs_yml([{"Home": "index.md"}])

        content = yml.read_text(encoding="utf-8")
        assert "pymdownx.superfences" in content
        assert "!!python/name:" in content
