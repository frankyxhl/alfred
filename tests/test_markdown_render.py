"""Tests for the dependency-free Markdown -> HTML renderer (FXA af render)."""

import pytest

from fx_alfred.core.markdown_render import render_body, render_document

pytestmark = pytest.mark.unit


def test_headings():
    assert "<h1>Title</h1>" in render_body("# Title")
    assert "<h3>Sub</h3>" in render_body("### Sub")


def test_unordered_list():
    assert "<ul><li>a</li><li>b</li></ul>" in render_body("- a\n- b")


def test_ordered_list():
    assert "<ol><li>a</li><li>b</li></ol>" in render_body("1. a\n2. b")


def test_fenced_code_is_escaped_verbatim():
    assert "<pre><code>&lt;x&gt; &amp; y</code></pre>" in render_body(
        "```\n<x> & y\n```"
    )


def test_link_and_emphasis():
    assert '<a href="https://x.com">x</a>' in render_body("[x](https://x.com)")
    assert "<strong>b</strong>" in render_body("**b**")
    assert "<em>i</em>" in render_body("*i*")
    assert "<em>u</em>" in render_body("_u_")


def test_inline_code():
    assert "<code>af render</code>" in render_body("`af render`")


def test_inline_code_with_markup_stays_literal():
    # underscores/asterisks inside a code span must NOT become emphasis
    assert "<code>ALFRED_AGENT_TOOLS</code>" in render_body("`ALFRED_AGENT_TOOLS`")
    assert "<code>**literal**</code>" in render_body("`**literal**`")


def test_link_target_is_quote_escaped():
    # a double quote in the URL must not break out of the href attribute
    html = render_body('[x](https://e/?q=" onmouseover="alert(1))')
    assert 'onmouseover="alert(1)"' not in html
    assert "&quot;" in html


def test_paragraph_escapes_html():
    assert "<p>plain &lt;text&gt; &amp;</p>" in render_body("plain <text> &")


def test_intraword_underscore_is_not_emphasis():
    html = render_body("ALFRED_AGENT_TOOLS and foo_bar_baz in prose")
    assert "<em>" not in html
    assert "ALFRED_AGENT_TOOLS" in html
    assert "foo_bar_baz" in html


def test_nul_in_input_does_not_corrupt_output():
    # a literal NUL placeholder sequence must not alias a real stash slot
    html = render_body("\x000\x00 and `realcode`")
    assert "<code>realcode</code>" in html
    assert "\x00" not in html


def test_code_span_inside_link_text():
    # the project's own README link style: [`code`](url) must not leak \x00
    html = render_body("See [`af render`](README.md)")
    assert '<a href="README.md"><code>af render</code></a>' in html
    assert "\x00" not in html


def test_javascript_url_is_neutralized():
    html = render_body("[x](javascript:alert(1))")
    assert "javascript:" not in html
    assert 'href="#"' in html


def test_data_url_is_neutralized():
    html = render_body("[x](data:text/html,alert(1))")
    assert "data:text/html" not in html
    assert 'href="#"' in html


def test_parens_in_url_are_preserved():
    html = render_body("[wiki](https://en.wikipedia.org/wiki/C_(programming_language))")
    assert 'href="https://en.wikipedia.org/wiki/C_(programming_language)"' in html


def test_longer_fence_keeps_inner_triple_backticks_literal():
    # a 4-backtick fence containing a literal ``` and a # line: must stay verbatim
    html = render_body("````\n```\n# not a heading\n````")
    assert "<h1>" not in html
    assert "<pre><code>" in html
    assert "# not a heading" in html
    assert "```" in html


def test_document_is_standalone():
    doc = render_document("# Hi", title="T")
    assert doc.startswith("<!DOCTYPE html>")
    assert "<title>T</title>" in doc
    assert "<h1>Hi</h1>" in doc
    assert doc.rstrip().endswith("</html>")
