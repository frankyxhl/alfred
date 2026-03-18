from typing import Literal

Source = Literal["pkg", "usr", "prj"]

SOURCE_LABELS: dict[str, str] = {"pkg": "PKG", "usr": "USR", "prj": "PRJ"}

SOURCE_ORDER: tuple[Source, ...] = ("pkg", "usr", "prj")

_SOURCE_INDEX: dict[str, int] = {s: i for i, s in enumerate(SOURCE_ORDER)}


def source_sort_key(source: str) -> int:
    """Return the sort index for a source string."""
    return _SOURCE_INDEX.get(source, len(SOURCE_ORDER))
