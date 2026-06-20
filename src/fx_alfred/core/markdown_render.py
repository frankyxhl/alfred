"""Minimal, dependency-free Markdown -> HTML rendering for ``af render``.

Framework-agnostic (no Click). Covers the core Markdown the ``af render``
command documents: ATX headings, unordered/ordered lists, fenced code blocks,
inline code, links, bold/italic emphasis, and paragraphs. This is intentionally
small and zero-dependency, consistent with Alfred's lean-deps posture — not a
full CommonMark implementation.
"""

from __future__ import annotations

import html
import re

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_UL = re.compile(r"^[-*]\s+(.*)$")
_OL = re.compile(r"^\d+\.\s+(.*)$")
_FENCE = re.compile(r"^(`{3,})")  # captures the opening backtick run

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
# Underscore emphasis must be at word boundaries (no intraword: ALFRED_AGENT_TOOLS).
_ITALIC = re.compile(
    r"(?<!\*)\*([^*]+)\*(?!\*)|(?<![A-Za-z0-9_])_([^_]+)_(?![A-Za-z0-9_])"
)
_CODE = re.compile(r"`([^`]+)`")


def _is_closing_fence(stripped: str, opener: str) -> bool:
    """A closing fence is a run of >= len(opener) backticks and nothing else."""
    s = stripped.rstrip()
    return bool(s) and set(s) == {"`"} and len(s) >= len(opener)


_DEFAULT_CSS = (
    "body{max-width:48rem;margin:2rem auto;padding:0 1rem;"
    "font:16px/1.6 system-ui,sans-serif;color:#222}"
    "pre{background:#f4f4f4;padding:1rem;overflow:auto;border-radius:6px}"
    "code{background:#f4f4f4;padding:.1rem .3rem;border-radius:3px}"
    "pre code{background:none;padding:0}"
    "a{color:#0066cc}"
)


def _inline(text: str) -> str:
    """Render inline Markdown (emphasis, code, links) to HTML.

    Code spans and links are extracted to placeholders *before* escaping and
    emphasis run, so emphasis markup never leaks into code/link content and the
    link target is quote-escaped into the ``href`` attribute.
    """
    stash: list[str] = []

    def _hold(replacement: str) -> str:
        stash.append(replacement)
        return f"\x00{len(stash) - 1}\x00"

    # Code spans first: content is escaped and protected from emphasis/links.
    text = _CODE.sub(
        lambda m: _hold(f"<code>{html.escape(m.group(1), quote=False)}</code>"), text
    )
    # Links next: text is escaped; the URL is quote-escaped into href (no injection).
    text = _LINK.sub(
        lambda m: _hold(
            f'<a href="{html.escape(m.group(2), quote=True)}">'
            f"{html.escape(m.group(1), quote=False)}</a>"
        ),
        text,
    )
    # Escape the remaining text, then apply emphasis (placeholders are inert).
    out = html.escape(text, quote=False)
    out = _BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", out)
    out = _ITALIC.sub(lambda m: f"<em>{m.group(1) or m.group(2)}</em>", out)
    for idx, replacement in enumerate(stash):  # restore protected spans
        out = out.replace(f"\x00{idx}\x00", replacement)
    return out


def render_body(md: str) -> str:
    """Render Markdown source into an HTML body fragment (no document wrapper)."""
    lines = md.splitlines()
    parts: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        fence_open = _FENCE.match(line.strip())  # fenced code block (verbatim)
        if fence_open:
            opener = fence_open.group(1)
            i += 1
            code: list[str] = []
            while i < n and not _is_closing_fence(lines[i].strip(), opener):
                code.append(lines[i])
                i += 1
            i += 1  # consume closing fence
            escaped = html.escape("\n".join(code), quote=False)
            parts.append(f"<pre><code>{escaped}</code></pre>")
            continue
        heading = _HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            parts.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            i += 1
            continue
        if _UL.match(line):
            items: list[str] = []
            while i < n and (m := _UL.match(lines[i])):
                items.append(f"<li>{_inline(m.group(1))}</li>")
                i += 1
            parts.append("<ul>" + "".join(items) + "</ul>")
            continue
        if _OL.match(line):
            items = []
            while i < n and (m := _OL.match(lines[i])):
                items.append(f"<li>{_inline(m.group(1))}</li>")
                i += 1
            parts.append("<ol>" + "".join(items) + "</ol>")
            continue
        para: list[str] = []  # paragraph: gather until a blank line or block start
        while (
            i < n
            and lines[i].strip()
            and not (
                _HEADING.match(lines[i])
                or _UL.match(lines[i])
                or _OL.match(lines[i])
                or _FENCE.match(lines[i].strip())
            )
        ):
            para.append(lines[i].strip())
            i += 1
        parts.append(f"<p>{_inline(' '.join(para))}</p>")
    return "\n".join(parts)


def render_document(md: str, title: str = "Document") -> str:
    """Render Markdown source into a complete, standalone HTML document string."""
    body = render_body(md)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>{_DEFAULT_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )
