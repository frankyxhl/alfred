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
from fx_alfred.context import get_root, root_option
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

--include paths resolve relative to the export root; absolute paths are
allowed (operator-controlled — review attachments like any USR/PRJ
content before sharing).

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
) -> tuple[dict[str, _ExportDoc], list[tuple[Document, str]]]:
    """Read + parse every document exactly once (PRP behavior: single-read
    cache). Unreadable/malformed documents are skipped with a reason; the
    Document is kept alongside so relevance to the user's request can be
    judged later (codex PR #201 P2 #3)."""
    loaded: dict[str, _ExportDoc] = {}
    skipped: list[tuple[Document, str]] = []
    for doc in docs:
        doc_id = f"{doc.prefix}-{doc.acid}"
        try:
            content = doc.resolve_resource().read_text(encoding="utf-8")
            parsed = parse_metadata(content)
        # Deliberately broad: mirrors Document.tags' swallowing semantics
        # (PRP behavior 5) — OSError, MalformedDocumentError, UnicodeDecodeError
        # and Traversable failures all become skip-with-warning entries.
        except Exception as exc:
            skipped.append((doc, f"{doc_id}: {type(exc).__name__}: {exc}"))
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


def _derive_type_gate(
    type_filters: tuple[str, ...], include_all: bool
) -> frozenset[str] | None:
    """Repeatable --type: OR within the dimension (CHG-2304); explicit
    values REPLACE the default gate, --all lifts it (None = no gate)."""
    if type_filters:
        return frozenset(t.upper() for t in type_filters)
    if include_all:
        return None
    return _DEFAULT_TYPES


def _skip_is_relevant(
    doc: Document,
    requested_ids: set[str],
    type_filters: tuple[str, ...],
    prefix_filter: str | None,
    source_filters: tuple[str, ...],
    include_all: bool,
) -> bool:
    """Could this skipped (unparseable) document have matched the request?

    Judged on filename-derivable dimensions only (type/prefix/source —
    status and tags need the parse that failed, so they cannot exclude).
    Used to distinguish 'all matches were skipped' (exit 1) from a true
    no-match (UsageError exit 2) — codex PR #201 P2 #3.
    """
    doc_id = f"{doc.prefix}-{doc.acid}"
    if doc_id in requested_ids:
        return True
    type_gate = _derive_type_gate(type_filters, include_all)
    if type_gate is not None and doc.type_code not in type_gate:
        return False
    if prefix_filter is not None and doc.prefix != prefix_filter.upper():
        return False
    if source_filters and doc.source not in {s.lower() for s in source_filters}:
        return False
    return True


def _select_documents(
    loaded: dict[str, _ExportDoc],
    docs: list[Document],
    ids: tuple[str, ...],
    type_filters: tuple[str, ...],
    prefix_filter: str | None,
    source_filters: tuple[str, ...],
    tag_filter: str | None,
    status_filter: str | None,
    include_all: bool,
) -> list[_ExportDoc]:
    """Selection algebra per PRP behavior 1: (positional ∪ filtered pool),
    de-duplicated; positional IDs bypass every gate."""
    selected: dict[str, _ExportDoc] = {}

    # Positional IDs — resolved like af plan, dedupe keeping first. An ID
    # whose document failed to load is called out specifically (it already
    # has a ⚠ skipped line; this names the request that lost it — glm R1).
    for identifier in ids:
        doc = find_or_fail(docs, identifier)
        doc_id = f"{doc.prefix}-{doc.acid}"
        if doc_id not in loaded:
            click.echo(
                f"⚠ requested {doc_id} was skipped (unreadable/malformed)",
                err=True,
            )
            continue
        if doc_id not in selected:
            selected[doc_id] = loaded[doc_id]

    # Filtered pool. Explicit --type/--status override that dimension's
    # default gate; --all lifts both defaults; prefix/source/tag AND in.
    any_selection_args = bool(ids)
    type_gate = _derive_type_gate(type_filters, include_all)
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
        or bool(type_filters)
        or bool(source_filters)
        or any(f is not None for f in (prefix_filter, tag_filter, status_filter))
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
            # Repeatable --source: OR within the dimension (CHG-2304).
            if source_filters and doc.source not in {s.lower() for s in source_filters}:
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


@dataclass(frozen=True)
class _IncludedFile:
    relpath: str
    content: str


def _load_includes(
    root: Path, include_paths: tuple[str, ...]
) -> tuple[list[_IncludedFile], list[str]]:
    """Load --include files verbatim (UTF-8, relative to the export root;
    absolute paths allowed). Failures follow the document skip policy
    (CHG-2304)."""
    files: list[_IncludedFile] = []
    skipped: list[str] = []
    for raw in include_paths:
        path = Path(raw)
        if not path.is_absolute():
            path = root / path
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as exc:
            skipped.append(f"{raw}: {type(exc).__name__}: {exc}")
            continue
        files.append(_IncludedFile(relpath=raw, content=content))
    return files, skipped


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


def _file_contents_line(f: _IncludedFile) -> str:
    return f"{f.relpath}  FILE  -  -  {f.relpath}"


def _render_export(ordered: list[_ExportDoc], files: list[_IncludedFile]) -> str:
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
        *(_file_contents_line(f) for f in files),
        "",
    ]
    for entry in ordered:
        lines.append(
            f"{_RULE} {entry.doc_id} · {entry.doc.type_code} · "
            f"{entry.doc.source.upper()} · {entry.status or '-'} {_RULE}"
        )
        lines.append(entry.content.rstrip("\n"))
        lines.append("")
    for f in files:
        lines.append(f"{_RULE} FILE: {f.relpath} {_RULE}")
        lines.append(f.content.rstrip("\n"))
        lines.append("")
    return "\n".join(lines)


def _emit_summary(
    ordered: list[_ExportDoc], skipped: list[str], files: list[_IncludedFile]
) -> None:
    counts = {s: 0 for s in SOURCE_ORDER}
    words = 0
    for entry in ordered:
        counts[entry.doc.source] += 1
        words += len(entry.content.split())
    summary = f"exported {len(ordered)} documents (~{words:,} words) — " + " · ".join(
        f"{s.upper()} {counts[s]}" for s in SOURCE_ORDER
    )
    if files:
        summary += f" + {len(files)} file{'s' if len(files) != 1 else ''}"
    if skipped:
        summary += f" · skipped {len(skipped)}"
    if counts["usr"] + counts["prj"] > 0 or files:
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
@click.option(
    "--type",
    "type_filters",
    multiple=True,
    help="Filter by document type (repeatable: OR within the dimension)",
)
@click.option("--prefix", "prefix_filter", default=None, help="Filter by prefix")
@click.option(
    "--source",
    "source_filters",
    multiple=True,
    help="Filter by layer pkg/usr/prj (repeatable: e.g. --source pkg --source prj)",
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
    "--include",
    "include_paths",
    multiple=True,
    help="Attach a project file verbatim (repeatable; e.g. --include README.md)",
)
@click.option(
    "-o", "--output", "output_path", default=None, help="Write to FILE (- = stdout)"
)
@click.pass_context
def export_cmd(
    ctx: click.Context,
    ids: tuple[str, ...],
    type_filters: tuple[str, ...],
    prefix_filter: str | None,
    source_filters: tuple[str, ...],
    tag_filter: str | None,
    status_filter: str | None,
    include_all: bool,
    list_only: bool,
    include_paths: tuple[str, ...],
    output_path: str | None,
) -> None:
    """Export the runbook as one self-contained Markdown file."""
    docs = scan_or_fail(ctx)
    loaded, doc_skips = _load_corpus(docs)
    files, file_skips = _load_includes(get_root(ctx), include_paths)
    skipped = [reason for _doc, reason in doc_skips] + file_skips

    selected = _select_documents(
        loaded,
        docs,
        ids,
        type_filters,
        prefix_filter,
        source_filters,
        tag_filter,
        status_filter,
        include_all,
    )
    # Skip warnings BEFORE the empty check — a matched-but-skipped
    # positional must not silently become "no documents matched"
    # (codex PR #201 P2 #2).
    for reason in skipped:
        click.echo(f"⚠ skipped {reason}", err=True)

    if not selected:
        # Only skips that COULD have matched this request justify the
        # exit-1 failure path; an unrelated corrupt document must not
        # turn a true no-match into an export failure (codex P2 #3).
        requested_ids = {
            f"{d.prefix}-{d.acid}" for d in (find_or_fail(docs, i) for i in ids)
        }
        relevant_skips = any(
            _skip_is_relevant(
                doc,
                requested_ids,
                type_filters,
                prefix_filter,
                source_filters,
                include_all,
            )
            for doc, _reason in doc_skips
        )
        if relevant_skips:
            raise click.ClickException(
                "no exportable documents — all matches were skipped "
                "(see warnings above)"
            )
        raise click.UsageError(
            "no documents matched; try --all, different filters, or positional IDs"
        )
    ordered = _order_documents(selected)

    if list_only:
        audit = [_contents_line(e) for e in ordered] + [
            _file_contents_line(f) for f in files
        ]
        _write_output("\n".join(audit), output_path)
    else:
        _write_output(_render_export(ordered, files), output_path)
    _emit_summary(ordered, skipped, files)
