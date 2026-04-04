"""Document type schema — single source of truth for all document type rules.

This module is pure data. It must NOT import from scanner, parser, or any
other module that touches the filesystem.
"""

from enum import Enum


class DocType(str, Enum):
    SOP = "SOP"
    PRP = "PRP"
    CHG = "CHG"
    ADR = "ADR"
    REF = "REF"
    PLN = "PLN"
    INC = "INC"


class DocRole(str, Enum):
    ROUTING = "routing"
    SOP = "sop"
    INDEX = "index"
    GENERAL = "general"


# Authoritative allowed statuses per doc type.
ALLOWED_STATUSES: dict[DocType, list[str]] = {
    DocType.SOP: ["Draft", "Active", "Deprecated"],
    DocType.PRP: ["Draft", "Approved", "Rejected", "Implemented"],
    DocType.CHG: ["Proposed", "Approved", "In Progress", "Completed", "Rolled Back"],
    DocType.ADR: ["Proposed", "Accepted", "Superseded", "Deprecated"],
    DocType.REF: ["Active", "Draft", "Deprecated"],
    DocType.PLN: ["Draft", "Active", "Completed", "Cancelled"],
    DocType.INC: ["Open", "Resolved", "Monitoring"],
}

# Canonical metadata fields per doc type. List order defines rendering order.
REQUIRED_METADATA: dict[DocType, list[str]] = {
    DocType.SOP: ["Applies to", "Last updated", "Last reviewed", "Status"],
    DocType.PRP: ["Applies to", "Last updated", "Last reviewed", "Status"],
    DocType.CHG: ["Applies to", "Last updated", "Last reviewed", "Status"],
    DocType.ADR: ["Applies to", "Last updated", "Last reviewed", "Status"],
    DocType.REF: ["Applies to", "Last updated", "Last reviewed", "Status"],
    DocType.PLN: ["Applies to", "Last updated", "Last reviewed", "Status"],
    DocType.INC: ["Applies to", "Last updated", "Last reviewed", "Status"],
}

OPTIONAL_METADATA: dict[DocType, list[str]] = {dt: ["Tags"] for dt in DocType}

REQUIRED_SECTIONS: dict[DocType, list[str]] = {
    DocType.SOP: ["What Is It?", "Why", "When to Use", "When NOT to Use", "Steps"],
    DocType.PRP: [
        "What Is It?",
        "Problem",
        "Scope",
        "Proposed Solution",
        "Open Questions",
    ],
    DocType.CHG: ["What", "Why", "Impact Analysis", "Implementation Plan"],
    DocType.ADR: ["Decision", "Context", "Consequences"],
    DocType.REF: ["What Is It?"],
    DocType.PLN: ["What Is It?", "Phases"],
    DocType.INC: ["What Happened", "Impact", "Root Cause", "Resolution"],
}

# Routing document identification (supplements filename pattern in guide_cmd).
ROUTING_ROLE_METADATA_KEY = "Document role"
ROUTING_ROLE_VALUE = "routing"
