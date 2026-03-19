"""Search command for af CLI -- searches document contents."""

import click

from fx_alfred.commands._helpers import scan_or_fail
from fx_alfred.context import root_option
from fx_alfred.core.source import SOURCE_LABELS


@click.command("search")
@root_option
@click.argument("pattern")
@click.pass_context
def search_cmd(ctx: click.Context, pattern: str):
    """Search document contents for PATTERN (case-insensitive substring match)."""
    docs = scan_or_fail(ctx)
    pattern_lower = pattern.lower()

    matches_found = False

    for doc in docs:
        try:
            content = doc.resolve_resource().read_text()
        except Exception:
            # Skip unreadable documents silently
            continue

        lines = content.split("\n")
        matching_lines = []

        for i, line in enumerate(lines, start=1):
            if pattern_lower in line.lower():
                matching_lines.append((i, line))

        if matching_lines:
            matches_found = True
            label = SOURCE_LABELS.get(doc.source, "???")
            # Header line: PREFIX-ACID  SOURCE_LABEL  Title
            click.echo(f"{doc.prefix}-{doc.acid}  {label}  {doc.title}")

            # Show up to 3 matching lines with line numbers
            for line_num, line_content in matching_lines[:3]:
                click.echo(f"  {line_num}: {line_content}")

            # Blank line after document group
            click.echo()

    if not matches_found:
        click.echo("No matches found.")
