"""Tests for the dependency-free Markdown -> HTML renderer (FXA af render)."""

from fx_alfred.core.markdown_render import render_body, render_document


def test_headings():
    assert "<h1>Title</h1>" in render_body("# Title")
    assert "<h3>Sub</h3>" in render_body("### Sub")


def test_unordered_list():
    assert "<ul><li>a</li><li>b</li></ul>" in render_body("- a\n- b")


def test_ordered_list():
    assert "<ol><li>a</li><li>b</li></ol>" in render_body("1. a\n2. b")


def test_fenced_code_is_escaped_verbatim():
    assert "<pre><code>&lt;x&gt; &amp; y</code></pre>" in render_body("```\n<x> & y\n```")


def test_link_and_emphasis():
    assert '<a href="https://x.com">x</a>' in render_body("[x](https://x.com)")
    assert "<strong>b</strong>" in render_body("**b**")
    assert "<em>i</em>" in render_body("*i*")
    assert "<em>u</em>" in render_body("_u_")


def test_inline_code():
    assert "<code>af render</code>" in render_body("`af render`")


def test_paragraph_escapes_html():
    assert "<p>plain &lt;text&gt; &amp;</p>" in render_body("plain <text> &")


def test_document_is_standalone():
    doc = render_document("# Hi", title="T")
    assert doc.startswith("<!DOCTYPE html>")
    assert "<title>T</title>" in doc
    assert "<h1>Hi</h1>" in doc
    assert doc.rstrip().endswith("</html>")
