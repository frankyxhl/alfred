from __future__ import annotations

import re
from dataclasses import dataclass

FILENAME_PATTERN = re.compile(r"^([A-Z]{3})-(\d{4})-([A-Z]{3})-(.+)\.md$")


@dataclass
class Document:
    prefix: str
    acid: str
    type_code: str
    title: str
    directory: str

    @classmethod
    def from_filename(cls, filename: str, directory: str) -> Document | None:
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
        )

    @property
    def filepath(self) -> str:
        return f"{self.directory}/{self.filename}"

    @property
    def filename(self) -> str:
        return f"{self.prefix}-{self.acid}-{self.type_code}-{self.title.replace(' ', '-')}.md"
