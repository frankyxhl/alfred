from __future__ import annotations

from collections.abc import Iterator
from importlib import resources
from pathlib import Path
from typing import Protocol, runtime_checkable

import sys

from fx_alfred.core.document import Document, FILENAME_PATTERN
from fx_alfred.core.projects import load_projects, resolve_subproject
from fx_alfred.core.source import source_sort_key


@runtime_checkable
class Traversable(Protocol):
    @property
    def name(self) -> str: ...
    def iterdir(self) -> Iterator[Traversable]: ...
    def is_file(self) -> bool: ...


class LayerValidationError(Exception):
    """Raised when layer validation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


class DocumentNotFoundError(Exception):
    """Raised when no document matches the given identifier."""

    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"No document found: {identifier}")


class AmbiguousDocumentError(Exception):
    """Raised when multiple documents match the given identifier."""

    def __init__(self, identifier: str, matches: list[Document]):
        self.identifier = identifier
        self.matches = matches
        options = ", ".join(f"{d.prefix}-{d.acid}" for d in matches)
        super().__init__(
            f"Ambiguous ACID {identifier}. Multiple matches: {options}. "
            "Use PREFIX-ACID to be precise."
        )


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


def _scan_path_dir(
    directory: Path,
    source: str,
    recursive: bool = False,
    exclude_subdirs: set[str] | None = None,
) -> list[Document]:
    """Scan USR/PRJ layer using Path.

    Args:
        directory: Path to scan
        source: Source label ('usr' or 'prj')
        recursive: If True, scan subdirectories recursively
        exclude_subdirs: Top-level subdirectory names to skip entirely
            (used to hide registered subproject dirs from the USR layer).
    """
    if not directory.is_dir():
        return []
    docs = []

    if recursive:
        files = directory.rglob("*.md")
    else:
        files = directory.iterdir()

    for f in files:
        if not f.is_file():
            continue
        rel_parts = f.relative_to(directory).parts
        if rel_parts and rel_parts[0] == "logs":
            continue
        if exclude_subdirs and rel_parts and rel_parts[0] in exclude_subdirs:
            continue
        if "rules" in rel_parts and "logs" in rel_parts:
            continue
        doc = Document.from_filename(
            f.name,
            directory=str(directory.name),
            source=source,
            base_path=f.parent,
        )
        if doc is not None:
            docs.append(doc)
    return docs


def _validate_layers(docs: list[Document]) -> None:
    """Validate layer invariants.

    - COR-* documents may ONLY exist in PKG layer
    - Duplicate prefix+ACID across any layers is an error
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


def scan_documents(project_root: Path, validate_layers: bool = True) -> list[Document]:
    """Scan all layers for documents.

    Layers (in order): PKG (bundled), USR (~/.alfred/), PRJ (rules/ or
    ~/.alfred/<NAME>/ when the root is registered in projects.json).

    FXA-2314: when ``~/.alfred/projects.json`` maps *project_root* to a
    subproject NAME, the PRJ layer is loaded from ``~/.alfred/<NAME>/``
    (recursive) instead of ``<project_root>/rules/`` (non-recursive).  Every
    registered subproject directory is globally excluded from the USR
    recursive scan so the same file is never classified as both USR and PRJ.
    """
    docs: list[Document] = []

    # Load projects mapping once per invocation (no module-level cache).
    mapping = load_projects()
    registered_names: set[str] = set(mapping.values())

    # Layer 1: PKG - bundled rules inside the package
    pkg_rules = resources.files("fx_alfred").joinpath("rules")
    docs.extend(_scan_pkg_dir(pkg_rules))

    # Layer 2: USR - ~/.alfred/ (recursive, excluding registered subproject dirs)
    user_alfred = Path.home() / ".alfred"
    docs.extend(
        _scan_path_dir(
            user_alfred,
            source="usr",
            recursive=True,
            exclude_subdirs=registered_names,
        )
    )

    # Layer 3: PRJ
    name = resolve_subproject(project_root, mapping)
    if name is not None:
        # Mapping wins: load ~/.alfred/<NAME>/ as PRJ (recursive).
        subproject_dir = user_alfred / name

        # Emit a shadow warning when local rules/ is populated (mapping wins
        # unconditionally, but warn so the operator is aware).
        local_rules = project_root / "rules"
        if local_rules.is_dir():
            try:
                if any(
                    f.is_file()
                    and FILENAME_PATTERN.match(f.name)
                    and not f.name.startswith("COR-")
                    for f in local_rules.iterdir()
                ):
                    print(
                        f"Warning: {local_rules} is shadowed by the projects.json "
                        f"mapping to ~/.alfred/{name}/; local rules/ docs will not "
                        "be loaded as PRJ.",
                        file=sys.stderr,
                    )
            except OSError:
                pass

        if not subproject_dir.is_dir():
            print(
                f"Warning: projects.json maps this project to {name!r} but "
                f"~/.alfred/{name}/ does not exist; PRJ layer will be empty.",
                file=sys.stderr,
            )
        else:
            docs.extend(_scan_path_dir(subproject_dir, source="prj", recursive=True))
    else:
        # Normal behavior: use <project_root>/rules/ (non-recursive)
        rules_path = project_root / "rules"
        docs.extend(_scan_path_dir(rules_path, source="prj"))

    # Validate layer invariants
    if validate_layers:
        _validate_layers(docs)

    # Sort: PKG first, then USR, then PRJ; each group sorted by ACID
    docs.sort(key=lambda d: (source_sort_key(d.source), d.acid))
    return docs


def find_document(docs: list[Document], identifier: str) -> Document:
    """Find document by PREFIX-ACID or ACID only.

    Raises:
        DocumentNotFoundError: if no match found
        AmbiguousDocumentError: if multiple matches found
    """
    if "-" in identifier:
        prefix, acid = identifier.split("-", 1)
        matches = [d for d in docs if d.prefix == prefix and d.acid == acid]
    else:
        matches = [d for d in docs if d.acid == identifier]

    if not matches:
        raise DocumentNotFoundError(identifier)
    if len(matches) > 1:
        raise AmbiguousDocumentError(identifier, matches)
    return matches[0]
