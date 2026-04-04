#!/usr/bin/env python3
"""Build MkDocs documentation from PKG-layer COR documents.

Copies COR-*.md files from src/fx_alfred/rules/ into docs/ (flat),
generates a landing page, and updates the nav section in mkdocs.yml
grouped by document type (SOP, REF, ADR, etc.).
"""

from __future__ import annotations

import re
import shutil
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / "src" / "fx_alfred" / "rules"
DOCS_DIR = ROOT / "docs"
MKDOCS_YML = ROOT / "mkdocs.yml"

# H1 pattern: # TYPE-ACID: Title
H1_RE = re.compile(r"^#\s+(\S+)-(\d+):\s+(.+)$")


def parse_h1(path: Path) -> tuple[str, int, str] | None:
    """Extract (type, acid, title) from the first H1 line."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = H1_RE.match(line.strip())
            if m:
                return m.group(1), int(m.group(2)), m.group(3).strip()
    return None


def clean_docs_dir() -> None:
    """Remove and recreate the docs/ directory."""
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True)


def copy_cor_files() -> list[Path]:
    """Copy COR-*.md files into docs/ (flat). Return list of copied paths."""
    copied = []
    for src in sorted(RULES_DIR.glob("COR-*.md")):
        dst = DOCS_DIR / src.name
        shutil.copy2(src, dst)
        copied.append(dst)
    return copied


def create_index() -> None:
    """Create a landing page for the documentation site."""
    index = DOCS_DIR / "index.md"
    index.write_text(
        "# Alfred — Agent Runbook\n\n"
        "Workflow routing, SOP checklists, and document management "
        "for AI agents and humans.\n\n"
        "Use the **search bar** above or the **navigation sidebar** "
        "to browse COR documents.\n\n"
        "For installation and usage, see the "
        "[GitHub repository](https://github.com/frankyxhl/alfred).\n",
        encoding="utf-8",
    )


def build_nav(copied_files: list[Path]) -> list[dict]:
    """Build nav structure grouped by document type, sorted by ACID."""
    groups: dict[str, list[tuple[int, str, str]]] = defaultdict(list)

    for path in copied_files:
        parsed = parse_h1(path)
        if parsed:
            doc_type, acid, title = parsed
            label = f"{doc_type}-{acid:04d}: {title}"
            groups[doc_type].append((acid, label, path.name))

    nav: list[dict] = [{"Home": "index.md"}]
    for group_name in sorted(groups.keys()):
        entries = sorted(groups[group_name], key=lambda x: x[0])
        nav.append({group_name: [{e[1]: e[2]} for e in entries]})

    return nav


def update_mkdocs_yml(nav: list[dict]) -> None:
    """Update the nav section in mkdocs.yml using pyyaml."""
    with open(MKDOCS_YML, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config["nav"] = nav

    with open(MKDOCS_YML, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def main() -> None:
    print("Cleaning docs/ directory...")
    clean_docs_dir()

    print("Copying COR-*.md files...")
    copied = copy_cor_files()
    print(f"  Copied {len(copied)} files")

    print("Creating index page...")
    create_index()

    print("Updating nav in mkdocs.yml...")
    nav = build_nav(copied)
    update_mkdocs_yml(nav)

    print("Done.")


if __name__ == "__main__":
    main()
