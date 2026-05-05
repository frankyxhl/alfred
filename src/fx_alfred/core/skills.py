from __future__ import annotations

import re
from typing import Any

from fx_alfred.core.document import Document
from fx_alfred.core.parser import MalformedDocumentError, parse_metadata, parse_tags
from fx_alfred.core.schema import TASK_TAGS


SCHEMA_VERSION = "1"
_SKILL_TYPES = {"REF", "SOP"}
_SOURCE_PRECEDENCE = {"prj": 0, "usr": 1, "pkg": 2}


class SkillLookupError(ValueError):
    """Raised when a skill identifier cannot be resolved."""


def doc_id(doc: Document) -> str:
    return f"{doc.prefix}-{doc.acid}"


def is_skill_doc(doc: Document) -> bool:
    """Return True only for REF/SOP documents explicitly tagged as skills."""
    return doc.type_code in _SKILL_TYPES and "skill" in doc.tags


def _read_content(doc: Document) -> str:
    return doc.resolve_resource().read_text()


def _field_value(doc: Document, field: str) -> str | None:
    try:
        parsed = parse_metadata(_read_content(doc))
    except (OSError, MalformedDocumentError):
        return None
    field_map = {mf.key: mf.value for mf in parsed.metadata_fields}
    return field_map.get(field)


def task_tags(doc: Document) -> list[str]:
    raw = _field_value(doc, TASK_TAGS)
    return parse_tags(raw) if raw else []


def _body(doc: Document) -> str:
    try:
        return parse_metadata(_read_content(doc)).body
    except (OSError, MalformedDocumentError):
        return ""


def _source(doc: Document) -> dict[str, str]:
    try:
        path = str(doc.resolve_resource())
    except ValueError:
        path = doc.filename
    return {"layer": doc.source.upper(), "path": path}


def skill_metadata(doc: Document) -> dict[str, Any]:
    return {
        "id": doc_id(doc),
        "prefix": doc.prefix,
        "acid": doc.acid,
        "type_code": doc.type_code,
        "title": doc.title,
        "source": _source(doc),
        "tags": doc.tags,
        "task_tags": task_tags(doc),
    }


def _tokenize(text: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        if token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result


def _normalize(text: str) -> str:
    return " ".join(_tokenize(text))


def _slug(text: str) -> str:
    return _normalize(text).replace(" ", "-")


def _score_skill(doc: Document, task: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    tokens = _tokenize(task)

    task_tag_set = set(task_tags(doc))
    tag_set = set(doc.tags)
    title_tokens = set(_tokenize(doc.title))
    body_tokens = set(_tokenize(_body(doc)))

    for token in tokens:
        if token in task_tag_set:
            score += 4
            reasons.append(f"task_tags:{token}")
        if token in tag_set:
            score += 3
            reasons.append(f"tags:{token}")
        if token in title_tokens:
            score += 2
            reasons.append(f"title:{token}")
        if token in body_tokens:
            score += 1
            reasons.append(f"body:{token}")
    return score, reasons


def list_skills(
    docs: list[Document],
    task: str | None = None,
    layer: str = "all",
) -> list[dict[str, Any]]:
    """Return skill metadata, optionally scored against a task description."""
    layer_filter = layer.lower()
    skills = [doc for doc in docs if is_skill_doc(doc)]
    if layer_filter != "all":
        skills = [doc for doc in skills if doc.source == layer_filter]

    results: list[dict[str, Any]] = []
    for doc in skills:
        item = skill_metadata(doc)
        if task:
            score, reasons = _score_skill(doc, task)
            if score <= 0:
                continue
            item["score"] = score
            item["match_reasons"] = reasons
        else:
            item["score"] = None
            item["match_reasons"] = []
        results.append(item)

    def sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
        source_layer = item["source"]["layer"].lower()
        source_rank = _SOURCE_PRECEDENCE.get(source_layer, 99)
        if task:
            return (-int(item["score"]), source_rank, item["id"])
        return (source_rank, item["id"])

    results.sort(key=sort_key)
    return results


def read_skill(docs: list[Document], identifier: str) -> tuple[Document, str]:
    """Resolve and read one skill document."""
    skills = [doc for doc in docs if is_skill_doc(doc)]
    identifier_norm = identifier.strip()
    identifier_upper = identifier_norm.upper()
    identifier_title = _normalize(identifier_norm)
    identifier_slug = _slug(identifier_norm)

    if "-" in identifier_norm and re.match(r"^[A-Za-z]{3}-\d{4}$", identifier_norm):
        matches = [doc for doc in skills if doc_id(doc).upper() == identifier_upper]
    elif re.match(r"^\d{4}$", identifier_norm):
        matches = [doc for doc in skills if doc.acid == identifier_norm]
    else:
        matches = [
            doc
            for doc in skills
            if _normalize(doc.title) == identifier_title
            or _slug(doc.title) == identifier_slug
        ]

    if not matches:
        raise SkillLookupError(f"No skill found: {identifier}")
    if len(matches) > 1:
        options = ", ".join(doc_id(doc) for doc in matches)
        raise SkillLookupError(
            f"Ambiguous skill identifier {identifier}. Multiple matches: {options}."
        )

    doc = matches[0]
    return doc, _read_content(doc)
