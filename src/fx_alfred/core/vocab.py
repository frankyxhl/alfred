"""Tag vocabulary helpers — union of CONTROLLED_TAGS and user custom_tags.

Framework-agnostic: no Click imports. The allowed_tags() helper is the
shared call site for vocab checks in validate_cmd.py and tag_cmd.py.
"""

from __future__ import annotations

from fx_alfred.core.schema import CONTROLLED_TAGS
from fx_alfred.core.preferences import load_custom_tags


def allowed_tags() -> set[str]:
    """Return the full allowed tag set: CONTROLLED_TAGS | user custom_tags.

    custom_tags come from ~/.alfred/preferences.yaml and are independent
    of --root (they are user-global, not project-scoped).
    """
    return set(CONTROLLED_TAGS) | set(load_custom_tags())
