"""Search command for af CLI -- searches document contents."""

import json

import click

from fx_alfred.commands._helpers import scan_or_fail
from fx_alfred.context import root_option
from fx_alfred.core.source import SOURCE_LABELS


_EPILOG = """\
Examples:

  af search TDD                    # find docs mentioning TDD
  af search "Change History"       # quote multi-word patterns
  af search workflow --root myproj # search in specific project

Shows up to 3 matching lines per document with line numbers.
"""


@click.command("search", epilog=_EPILOG)
@root_option
@click.argument("pattern")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def search_cmd(ctx: click.Context, pattern: str, output_json: bool):
    """Search document contents for PATTERN (case-insensitive substring)."""
    docs = scan_or_fail(ctx)
    pattern_lower = pattern.lower()

    matches_found = False
    results = []

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

            if output_json:
                # First matching line as snippet, truncated to 120 chars
                snippet = matching_lines[0][1].strip()[:120]
                results.append(
                    {
                        "doc_id": f"{doc.prefix}-{doc.acid}",
                        "title": doc.title,
                        "source": label,
                        "snippet": snippet,
                    }
                )
            else:
                # Header line: PREFIX-ACID  SOURCE_LABEL  Title
                click.echo(f"{doc.prefix}-{doc.acid}  {label}  {doc.title}")

                # Show up to 3 matching lines with line numbers
                for line_num, line_content in matching_lines[:3]:
                    click.echo(f"  {line_num}: {line_content}")

                # Blank line after document group
                click.echo()

    if output_json:
        result = {
            "schema_version": "1",
            "query": pattern,
            "results": results,
        }
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif not matches_found:
        click.echo("No matches found.")
