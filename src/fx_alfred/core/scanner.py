from __future__ import annotations

from pathlib import Path

from fx_alfred.core.document import Document

SCAN_DIRS = [".alfred", "docs"]


def scan_documents(project_root: Path) -> list[Document]:
    docs: list[Document] = []
    for dir_name in SCAN_DIRS:
        dir_path = project_root / dir_name
        if not dir_path.is_dir():
            continue
        for f in dir_path.iterdir():
            if not f.is_file():
                continue
            doc = Document.from_filename(f.name, directory=dir_name)
            if doc is not None:
                docs.append(doc)
    docs.sort(key=lambda d: d.acid)
    return docs
