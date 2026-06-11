"""af export — single-file runbook for zero-install consumption (PRP-2303).

Flattens the layer-resolved corpus (PKG + USR + PRJ) into one
self-contained plain-Markdown stream: no-CLI preamble, routing documents
first, then every selected document verbatim under full-pattern
delimiters. Behavior contracts live in PRP FXA-2303 §Specified behaviors.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import click

from fx_alfred.commands._helpers import atomic_write, find_or_fail, scan_or_fail
from fx_alfred.context import root_option
from fx_alfred.core.document import Document
from fx_alfred.core.parser import ParsedDocument, parse_metadata, parse_tags
from fx_alfred.core.routing import document_status, is_routing_document
from fx_alfred.core.source import SOURCE_ORDER

_DEFAULT_TYPES = frozenset({"SOP", "REF"})
_RULE = "═" * 23

_PREAMBLE = """\
You are reading the complete Alfred runbook inline — no installation
needed. Start with the routing document(s) immediately below: they tell
you which SOP applies to your task. Then jump to that SOP by its ID.

Every document begins at a delimiter line of the form
`{rule} <ID> · <TYPE> · <LAYER> · <STATUS> {rule}` — only lines carrying
all four fields are boundaries (a bare run of ═ inside a document is
content). Every document ID referenced in any text here (e.g. "per
COR-1402") can be located via the Contents table below.\
""".format(rule="═══")

_EPILOG = """\
Sharing risk: USR and PRJ layers may contain private material — review
before sharing (use --list to audit the exact document set first;
--source pkg exports only the public bundled COR documents).

Filter semantics: --all lifts the default type (SOP+REF) and status
(Active) gates; explicit filters AND together and also apply under
--all (e.g. `--all --status Active` = every Active document of any
type). Positional IDs bypass all filters and gates.
"""


@dataclass(frozen=True)
class _ExportDoc:
    doc: Document
    parsed: ParsedDocument
    content: str
    status: str | None
    is_routing: bool

    @property
    def doc_id(self) -> str:
        return f"{self.doc.prefix}-{self.doc.acid}"


def _load_corpus(
    docs: list[Document],
) -> tuple[dict[str, _ExportDoc], list[str]]:
    """Read + parse every document exactly once (PRP behavior: single-read
    cache). Unreadable/malformed documents are skipped with a reason."""
    loaded: dict[str, _ExportDoc] = {}
    skipped: list[str] = []
    for doc in docs:
        doc_id = f"{doc.prefix}-{doc.acid}"
        try:
            content = doc.resolve_resource().read_text(encoding="utf-8")
            parsed = parse_metadata(content)
        except Exception as exc:
            skipped.append(f"{doc_id}: {type(exc).__name__}: {exc}")
            continue
        loaded[doc_id] = _ExportDoc(
            doc=doc,
            parsed=parsed,
            content=content,
            status=document_status(parsed),
            is_routing=is_routing_document(doc, parsed),
        )
    return loaded, skipped


def _doc_tags(entry: _ExportDoc) -> list[str]:
    """Tags from the cached parse (mirrors Document.tags semantics
    without a second file read)."""
    field = next((mf for mf in entry.parsed.metadata_fields if mf.key == "Tags"), None)
    return parse_tags(field.value) if field else []


def _select_documents(
    loaded: dict[str, _ExportDoc],
    docs: list[Document],
    ids: tuple[str, ...],
    type_filter: str | None,
    prefix_filter: str | None,
    source_filter: str | None,
    tag_filter: str | None,
    status_filter: str | None,
    include_all: bool,
) -> list[_ExportDoc]:
    """Selection algebra per PRP behavior 1: (positional ∪ filtered pool),
    de-duplicated; positional IDs bypass every gate."""
    selected: dict[str, _ExportDoc] = {}

    # Positional IDs — resolved like af plan, dedupe keeping first.
    for identifier in ids:
        doc = find_or_fail(docs, identifier)
        doc_id = f"{doc.prefix}-{doc.acid}"
        if doc_id in loaded and doc_id not in selected:
            selected[doc_id] = loaded[doc_id]

    # Filtered pool. Explicit --type/--status override that dimension's
    # default gate; --all lifts both defaults; prefix/source/tag AND in.
    any_selection_args = bool(ids)
    type_gate: frozenset[str] | None
    if type_filter is not None:
        type_gate = frozenset({type_filter.upper()})
    elif include_all:
        type_gate = None
    else:
        type_gate = _DEFAULT_TYPES
    status_gate: str | None
    if status_filter is not None:
        status_gate = status_filter.lower()
    elif include_all:
        status_gate = None
    else:
        status_gate = "active"

    use_pool = (
        not any_selection_args
        or include_all
        or any(
            f is not None
            for f in (
                type_filter,
                prefix_filter,
                source_filter,
                tag_filter,
                status_filter,
            )
        )
    )
    if use_pool:
        for doc_id, entry in loaded.items():
            if doc_id in selected:
                continue
            doc = entry.doc
            if type_gate is not None and doc.type_code not in type_gate:
                continue
            if status_gate is not None and (
                entry.status is None or entry.status.lower() != status_gate
            ):
                continue
            if prefix_filter is not None and doc.prefix != prefix_filter.upper():
                continue
            if source_filter is not None and doc.source != source_filter.lower():
                continue
            if tag_filter is not None and tag_filter.lower() not in _doc_tags(entry):
                continue
            selected[doc_id] = entry
    return list(selected.values())


def _order_documents(selected: list[_ExportDoc]) -> list[_ExportDoc]:
    """Routing-first ordering per PRP behavior 2: at most one Active
    routing doc per layer (lowest ACID — guide semantics), PKG→USR→PRJ,
    then everything else in scanner order."""
    routing_block: list[_ExportDoc] = []
    for source in SOURCE_ORDER:
        candidates = sorted(
            (
                e
                for e in selected
                if e.doc.source == source and e.is_routing and e.status == "Active"
            ),
            key=lambda e: e.doc.acid,
        )
        if candidates:
            routing_block.append(candidates[0])
    routing_ids = {e.doc_id for e in routing_block}
    rest = [e for e in selected if e.doc_id not in routing_ids]
    rest.sort(key=lambda e: (SOURCE_ORDER.index(e.doc.source), e.doc.acid))
    return routing_block + rest


def _version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("fx-alfred")
    except PackageNotFoundError:
        return "unknown"


def _contents_line(entry: _ExportDoc) -> str:
    return (
        f"{entry.doc_id}  {entry.doc.type_code}  {entry.doc.source.upper()}  "
        f"{entry.status or '-'}  {entry.doc.title}"
    )


def _render_export(ordered: list[_ExportDoc]) -> str:
    counts = {s: 0 for s in SOURCE_ORDER}
    for entry in ordered:
        counts[entry.doc.source] += 1
    lines: list[str] = [
        "ALFRED RUNBOOK — SINGLE-FILE EXPORT",
        (
            f"fx-alfred {_version()} · {len(ordered)} documents ("
            + " · ".join(f"{s.upper()} {counts[s]}" for s in SOURCE_ORDER)
            + ") · layers merged, routing first · UTF-8"
        ),
        "",
        f"{_RULE} HOW TO USE THIS FILE {_RULE}",
        _PREAMBLE,
        "",
        f"{_RULE} CONTENTS {_RULE}",
        *(_contents_line(e) for e in ordered),
        "",
    ]
    for entry in ordered:
        lines.append(
            f"{_RULE} {entry.doc_id} · {entry.doc.type_code} · "
            f"{entry.doc.source.upper()} · {entry.status or '-'} {_RULE}"
        )
        lines.append(entry.content.rstrip("\n"))
        lines.append("")
    return "\n".join(lines)


def _emit_summary(ordered: list[_ExportDoc], skipped: list[str]) -> None:
    counts = {s: 0 for s in SOURCE_ORDER}
    words = 0
    for entry in ordered:
        counts[entry.doc.source] += 1
        words += len(entry.content.split())
    summary = f"exported {len(ordered)} documents (~{words:,} words) — " + " · ".join(
        f"{s.upper()} {counts[s]}" for s in SOURCE_ORDER
    )
    if skipped:
        summary += f" · skipped {len(skipped)}"
    if counts["usr"] + counts["prj"] > 0:
        summary += (
            " ⚠ includes USR/PRJ content — review for private material before sharing"
        )
    click.echo(summary, err=True)


def _write_output(text: str, output_path: str | None) -> None:
    if output_path is None or output_path == "-":
        click.echo(text)
        return
    target = Path(output_path)
    if target.is_dir():
        raise click.ClickException(f"--output target is a directory: {target}")
    atomic_write(target, text + "\n")


@click.command("export", epilog=_EPILOG)
@root_option
@click.argument("ids", nargs=-1)
@click.option("--type", "type_filter", default=None, help="Filter by document type")
@click.option("--prefix", "prefix_filter", default=None, help="Filter by prefix")
@click.option(
    "--source", "source_filter", default=None, help="Filter by layer (pkg/usr/prj)"
)
@click.option("--tag", "tag_filter", default=None, help="Filter by tag")
@click.option(
    "--status",
    "status_filter",
    default=None,
    help="Filter by Status (case-insensitive; default Active unless --all)",
)
@click.option("--all", "include_all", is_flag=True, help="Lift type/status gates")
@click.option(
    "--list",
    "list_only",
    is_flag=True,
    help="Dry run: print the export set (no document content)",
)
@click.option(
    "-o", "--output", "output_path", default=None, help="Write to FILE (- = stdout)"
)
@click.pass_context
def export_cmd(
    ctx: click.Context,
    ids: tuple[str, ...],
    type_filter: str | None,
    prefix_filter: str | None,
    source_filter: str | None,
    tag_filter: str | None,
    status_filter: str | None,
    include_all: bool,
    list_only: bool,
    output_path: str | None,
) -> None:
    """Export the runbook as one self-contained Markdown file."""
    docs = scan_or_fail(ctx)
    loaded, skipped = _load_corpus(docs)

    selected = _select_documents(
        loaded,
        docs,
        ids,
        type_filter,
        prefix_filter,
        source_filter,
        tag_filter,
        status_filter,
        include_all,
    )
    if not selected:
        raise click.UsageError(
            "no documents matched; try --all, different filters, or positional IDs"
        )
    ordered = _order_documents(selected)

    for reason in skipped:
        click.echo(f"⚠ skipped {reason}", err=True)

    if list_only:
        _write_output("\n".join(_contents_line(e) for e in ordered), output_path)
    else:
        _write_output(_render_export(ordered), output_path)
    _emit_summary(ordered, skipped)
