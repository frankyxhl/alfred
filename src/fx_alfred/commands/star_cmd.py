"""af star / af unstar / af starred — bookmark documents (FXA-2274)."""

from __future__ import annotations


import click

from fx_alfred.commands._helpers import (
    SCHEMA_VERSION,
    emit_json,
    find_or_fail,
    scan_or_fail,
)
from fx_alfred.context import root_option
from fx_alfred.core.preferences import (
    PreferencesError,
    add_starred_doc,
    get_starred_docs,
    remove_starred_doc,
)


def _canonical_from_doc(doc) -> str:
    """Build a canonical PREFIX-ACID string from a Document."""
    return f"{doc.prefix}-{doc.acid}"


def _normalise_input(identifier: str) -> str:
    """Upper-case the prefix portion if present; leave ACID-only inputs alone.

    `find_document` is case-sensitive on prefix matching, so `tst-5001` would
    miss `TST-5001`. Canonicalising the prefix here lets users type either form.
    """
    s = identifier.strip()
    if "-" in s:
        prefix, acid = s.split("-", 1)
        return f"{prefix.upper()}-{acid}"
    return s


@click.command("star")
@root_option
@click.argument("identifier")
@click.pass_context
def star_cmd(ctx: click.Context, identifier: str) -> None:
    """Bookmark a document by ID (e.g., COR-1202 or 1202)."""
    docs = scan_or_fail(ctx)
    doc = find_or_fail(docs, _normalise_input(identifier))
    canonical = _canonical_from_doc(doc)
    try:
        added, _ = add_starred_doc(canonical)
    except PreferencesError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"{'starred' if added else 'already starred'}: {canonical}")


def _resolve_unstar_target(
    ctx: click.Context, identifier: str
) -> tuple[str | None, str | None]:
    """Resolve `identifier` to the canonical PREFIX-ACID to remove.

    Returns (canonical_id, error_message). Exactly one is non-None.

    Strategy (starred-first, to honour the operator's intent when an ACID
    is shared between a stale starred entry and a different live doc):

      1. Load `starred_docs` from preferences.
      2. If input is `PREFIX-ACID` form: literal-match against starred. If
         found, target = that exact canonical entry. If not, target is the
         normalised input itself — `remove_starred_doc` will report
         "not starred".
      3. If input is ACID-only: search starred entries for any ending in
         `-<ACID>`. Exactly one match → that entry. Multiple → ambiguity
         error (operator must use full PREFIX-ACID). Zero → try live
         resolution to give a friendlier "not starred: PREFIX-ACID"
         message (the doc exists but isn't starred); if live resolution
         also fails, return the raw ACID for a "not starred: 5001" report.
    """
    norm = _normalise_input(identifier)

    try:
        starred = get_starred_docs()
    except PreferencesError as exc:
        return None, str(exc)

    if "-" in norm:
        # PREFIX-ACID form: literal match against starred list.
        # No live resolution needed; if not in starred, report "not starred".
        return norm, None

    # ACID-only form
    suffix = f"-{norm}"
    matches = [s for s in starred if s.endswith(suffix)]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, (
            f"ambiguous: starred entries match ACID {norm} — "
            f"{', '.join(matches)}. Use a full PREFIX-ACID."
        )

    # Zero starred matches; try live resolution for a friendlier message.
    try:
        docs = scan_or_fail(ctx)
        doc = find_or_fail(docs, norm)
        return _canonical_from_doc(doc), None
    except click.ClickException:
        return norm, None


@click.command("unstar")
@root_option
@click.argument("identifier")
@click.pass_context
def unstar_cmd(ctx: click.Context, identifier: str) -> None:
    """Remove a document bookmark."""
    canonical, err = _resolve_unstar_target(ctx, identifier)
    if err is not None:
        raise click.ClickException(err)
    assert canonical is not None
    try:
        removed, _ = remove_starred_doc(canonical)
    except PreferencesError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"{'unstarred' if removed else 'not starred'}: {canonical}")


@click.command("starred")
@root_option
@click.option("--json", "json_output", is_flag=True, help="Output as JSON object.")
@click.pass_context
def starred_cmd(ctx: click.Context, json_output: bool) -> None:
    """List bookmarked documents."""
    try:
        starred = get_starred_docs()
    except PreferencesError as exc:
        raise click.ClickException(str(exc)) from exc

    # Compute which starred IDs no longer resolve to existing docs
    docs = scan_or_fail(ctx)
    resolvable = {f"{d.prefix}-{d.acid}" for d in docs}
    missing = sorted(s for s in starred if s not in resolvable)

    if json_output:
        emit_json(
            {
                "schema_version": SCHEMA_VERSION,
                "starred_docs": starred,
                "missing": missing,
            }
        )
        return

    for doc_id in starred:
        suffix = " (missing)" if doc_id in missing else ""
        click.echo(f"{doc_id}{suffix}")
