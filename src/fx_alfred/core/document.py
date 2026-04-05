from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Protocol, runtime_checkable

from fx_alfred.core.parser import H1_PATTERN, MalformedDocumentError, parse_metadata, parse_tags

FILENAME_PATTERN = re.compile(r"^([A-Z]{3})-(\d{4})-([A-Z]{3})-(.+)\.md$")


@runtime_checkable
class Resource(Protocol):
    """Protocol for objects that support read_text()."""

    def read_text(self) -> str:
        """Read and return the content as text."""
        ...


@dataclass
class Document:
    prefix: str
    acid: str
    type_code: str
    title: str
    directory: str
    source: str = "prj"
    base_path: Path | None = None

    @classmethod
    def from_filename(
        cls,
        filename: str,
        directory: str,
        source: str = "prj",
        base_path: Path | None = None,
    ) -> Document | None:
        match = FILENAME_PATTERN.match(filename)
        if not match:
            return None
        prefix, acid, type_code, raw_title = match.groups()
        title = raw_title.replace("-", " ")
        return cls(
            prefix=prefix,
            acid=acid,
            type_code=type_code,
            title=title,
            directory=directory,
            source=source,
            base_path=base_path,
        )

    @property
    def filename(self) -> str:
        return f"{self.prefix}-{self.acid}-{self.type_code}-{self.title.replace(' ', '-')}.md"

    @property
    def tags(self) -> list[str]:
        """Parse Tags metadata field. Returns [] if absent or unreadable."""
        try:
            content = self.resolve_resource().read_text()
            # ACID=0000 index docs may have non-standard H1; substitute
            # a dummy H1 so the parser can extract metadata (same approach
            # as validate_cmd).
            if self.acid == "0000":
                lines = content.split("\n")
                if lines and not H1_PATTERN.match(lines[0]):
                    dummy_h1 = f"# {self.type_code}-{self.acid}: Index"
                    content = dummy_h1 + content[len(lines[0]) :]
            parsed = parse_metadata(content)
            tag_field = next(
                (mf for mf in parsed.metadata_fields if mf.key == "Tags"), None
            )
            return parse_tags(tag_field.value) if tag_field else []
        except (ValueError, OSError, MalformedDocumentError):
            return []

    def resolve_resource(self) -> Resource:
        """Return a resource that supports read_text().

        For PKG layer: returns Traversable from importlib.resources.
        For USR/PRJ layers: returns Path object.
        """
        if self.source == "pkg":
            return (
                resources.files("fx_alfred").joinpath("rules").joinpath(self.filename)
            )
        if self.base_path:
            return self.base_path / self.filename
        raise ValueError(
            f"Cannot resolve resource for document without base_path: {self.filename}"
        )
