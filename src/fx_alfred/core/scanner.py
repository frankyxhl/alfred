from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Protocol, runtime_checkable

from fx_alfred.core.document import Document


@runtime_checkable
class Traversable(Protocol):
    @property
    def name(self) -> str: ...
    def iterdir(self) -> list[Traversable]: ...
    def is_file(self) -> bool: ...
    def read_text(self) -> str: ...


class LayerValidationError(Exception):
    """Raised when layer validation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


def _scan_pkg_dir(traversable: Traversable) -> list[Document]:
    """Scan PKG layer using importlib.resources Traversable."""
    docs = []
    try:
        for f in traversable.iterdir():
            if not f.is_file():
                continue
            doc = Document.from_filename(
                f.name,
                directory="rules",
                source="pkg",
                base_path=None,
            )
            if doc is not None:
                docs.append(doc)
    except (NotADirectoryError, FileNotFoundError):
        pass
    return docs


def _scan_path_dir(directory: Path, source: str) -> list[Document]:
    """Scan USR/PRJ layer using Path."""
    if not directory.is_dir():
        return []
    docs = []
    for f in directory.iterdir():
        if not f.is_file():
            continue
        doc = Document.from_filename(
            f.name,
            directory=str(directory.name),
            source=source,
            base_path=directory,
        )
        if doc is not None:
            docs.append(doc)
    return docs


def _validate_layers(docs: list[Document]) -> None:
    """Validate layer invariants.

    - COR-* documents may ONLY exist in PKG layer
    - Duplicate ACID across any layers is an error
    """
    errors = []

    # Check for COR in non-PKG layers
    for doc in docs:
        if doc.prefix == "COR" and doc.source != "pkg":
            errors.append(
                f"COR document found in {doc.source.upper()} layer: {doc.filename}"
            )

    # Check for duplicate prefix+ACID combinations
    doc_keys: dict[str, list[str]] = {}
    for doc in docs:
        key = f"{doc.prefix}-{doc.acid}"
        if key not in doc_keys:
            doc_keys[key] = []
        doc_keys[key].append(f"{doc.source}:{doc.filename}")

    for key, sources in doc_keys.items():
        if len(sources) > 1:
            errors.append(f"Duplicate {key} found in: {', '.join(sources)}")

    if errors:
        raise LayerValidationError(errors)


def scan_documents(project_root: Path) -> list[Document]:
    """Scan all layers for documents.

    Layers (in order): PKG (bundled), USR (~/.alfred/), PRJ (rules/)
    """
    docs: list[Document] = []

    # Layer 1: PKG - bundled rules inside the package
    pkg_rules = resources.files("fx_alfred").joinpath("rules")
    docs.extend(_scan_pkg_dir(pkg_rules))  # type: ignore

    # Layer 2: USR - ~/.alfred/
    user_alfred = Path.home() / ".alfred"
    docs.extend(_scan_path_dir(user_alfred, source="usr"))

    # Layer 3: PRJ - rules/ in project (no .alfred/)
    rules_path = project_root / "rules"
    docs.extend(_scan_path_dir(rules_path, source="prj"))

    # Validate layer invariants
    _validate_layers(docs)

    # Sort: PKG first, then USR, then PRJ; each group sorted by ACID
    source_order = {"pkg": 0, "usr": 1, "prj": 2}
    docs.sort(key=lambda d: (source_order.get(d.source, 3), d.acid))
    return docs
