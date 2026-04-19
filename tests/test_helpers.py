from pathlib import Path
from unittest.mock import patch

import click
import pytest

from fx_alfred.commands._helpers import find_or_fail, scan_or_fail
from fx_alfred.core.document import Document
from fx_alfred.core.scanner import LayerValidationError


def test_scan_or_fail_returns_documents(sample_project):
    """scan_or_fail returns a non-empty list of Documents for a valid project."""
    ctx = click.Context(click.Command("test"), obj={"root": sample_project})
    docs = scan_or_fail(ctx)
    assert isinstance(docs, list)
    assert len(docs) > 0


def test_scan_or_fail_raises_click_exception_on_validation_error(tmp_path):
    """scan_or_fail converts LayerValidationError to ClickException."""
    ctx = click.Context(click.Command("test"), obj={"root": tmp_path})
    with patch(
        "fx_alfred.commands._helpers.scan_documents",
        side_effect=LayerValidationError(["bad layer"]),
    ):
        with pytest.raises(click.ClickException, match="bad layer"):
            scan_or_fail(ctx)


def test_find_or_fail_returns_document(sample_project):
    """find_or_fail returns the matching Document for a valid identifier."""
    ctx = click.Context(click.Command("test"), obj={"root": sample_project})
    docs = scan_or_fail(ctx)
    doc = find_or_fail(docs, "ALF-2201")
    assert doc.acid == "2201"


def test_find_or_fail_raises_on_not_found(sample_project):
    """find_or_fail raises ClickException when document is not found."""
    ctx = click.Context(click.Command("test"), obj={"root": sample_project})
    docs = scan_or_fail(ctx)
    with pytest.raises(click.ClickException, match="No document found"):
        find_or_fail(docs, "XXX-9999")


def test_find_or_fail_raises_on_ambiguous():
    """find_or_fail raises ClickException when identifier is ambiguous."""
    doc1 = Document(
        prefix="AAA",
        acid="1000",
        type_code="SOP",
        title="A",
        source="pkg",
        directory="rules",
        base_path=None,
    )
    doc2 = Document(
        prefix="BBB",
        acid="1000",
        type_code="SOP",
        title="B",
        source="prj",
        directory="rules",
        base_path=None,
    )
    with pytest.raises(click.ClickException, match="Ambiguous"):
        find_or_fail([doc1, doc2], "1000")


# ── Extracted helper tests (FXA-2157) ─────────────────────────────────────


def test_render_section_content_importable():
    """render_section_content can be imported from _helpers."""
    from fx_alfred.commands._helpers import render_section_content

    assert callable(render_section_content)


def test_validate_spec_status_importable():
    """validate_spec_status can be imported from _helpers."""
    from fx_alfred.commands._helpers import validate_spec_status

    assert callable(validate_spec_status)


def test_render_section_content_list():
    """render_section_content renders a list as markdown bullets."""
    from fx_alfred.commands._helpers import render_section_content

    result = render_section_content(["one", "two"])
    assert result == "- one\n- two"


def test_render_section_content_string():
    """render_section_content passes through a string."""
    from fx_alfred.commands._helpers import render_section_content

    assert render_section_content("hello") == "hello"


def test_render_section_content_other():
    """render_section_content converts non-str/list to str."""
    from fx_alfred.commands._helpers import render_section_content

    assert render_section_content(42) == "42"


def test_validate_spec_status_valid():
    """validate_spec_status accepts a valid status without raising."""
    from fx_alfred.commands._helpers import validate_spec_status
    from fx_alfred.core.schema import DocType

    # Should not raise
    validate_spec_status(DocType.SOP, "Active")


def test_validate_spec_status_invalid():
    """validate_spec_status raises ClickException for invalid status."""
    from fx_alfred.commands._helpers import validate_spec_status
    from fx_alfred.core.schema import DocType

    with pytest.raises(click.ClickException, match="not allowed"):
        validate_spec_status(DocType.SOP, "Nonexistent")


# ── atomic_write tests ───────────────────────────────────────────────────


def test_atomic_write_success(tmp_path):
    """atomic_write writes content and file matches expected content."""
    from fx_alfred.commands._helpers import atomic_write

    file_path = tmp_path / "test.md"
    content = "# Test Document\n\nHello, world!\n"

    atomic_write(file_path, content)

    assert file_path.exists()
    assert file_path.read_text() == content


def test_atomic_write_cleanup_on_failure(tmp_path):
    """atomic_write removes temp file when os.replace raises OSError."""
    from unittest.mock import patch

    from fx_alfred.commands._helpers import atomic_write

    file_path = tmp_path / "test.md"
    content = "test content"

    # Track temp files created
    temp_files = []

    original_mkstemp = __import__("tempfile").mkstemp

    def track_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files.append(path)
        return fd, path

    with (
        patch("tempfile.mkstemp", side_effect=track_mkstemp),
        patch("os.replace", side_effect=OSError("replace failed")),
    ):
        with pytest.raises(OSError, match="replace failed"):
            atomic_write(file_path, content)

    # Verify temp file was cleaned up
    for temp_path in temp_files:
        assert not Path(temp_path).exists(), f"Temp file {temp_path} should be removed"


def test_atomic_write_double_failure_preserves_original_error(tmp_path):
    """When both os.replace and os.unlink raise, the original replace error propagates.

    The inner `except OSError: pass` arm at _helpers.py:86-87 swallows a failing
    cleanup (os.unlink) so the ORIGINAL exception from os.replace is what reaches
    the caller — not the unlink failure. Breaking this would silently change
    which error an operator sees, masking the real cause of an atomic-write failure.
    Closes coverage gap at _helpers.py:86-87.
    """
    from unittest.mock import patch

    from fx_alfred.commands._helpers import atomic_write

    file_path = tmp_path / "test.md"
    content = "test content"

    with (
        patch("os.replace", side_effect=OSError("replace failed")),
        patch("os.unlink", side_effect=OSError("unlink failed")) as mock_unlink,
    ):
        # Must match "replace failed" — the original error wins, not "unlink failed".
        with pytest.raises(OSError, match="replace failed"):
            atomic_write(file_path, content)

    # Cleanup was attempted exactly once — proves the inner try/except arm ran.
    mock_unlink.assert_called_once()


def test_atomic_write_preserves_existing(tmp_path):
    """atomic_write preserves existing file content when os.replace fails."""
    from unittest.mock import patch

    from fx_alfred.commands._helpers import atomic_write

    file_path = tmp_path / "test.md"
    original_content = "# Original\n\nOriginal content.\n"
    file_path.write_text(original_content)

    new_content = "# New\n\nNew content.\n"

    with patch("os.replace", side_effect=OSError("replace failed")):
        with pytest.raises(OSError, match="replace failed"):
            atomic_write(file_path, new_content)

    # Original file should be unchanged
    assert file_path.read_text() == original_content


# ── invoke_index_update tests (FXA-2166) ───────────────────────────────────


def test_invoke_index_update_importable():
    """invoke_index_update can be imported from _helpers."""
    from fx_alfred.commands._helpers import invoke_index_update

    assert callable(invoke_index_update)


def test_invoke_index_update_success():
    """invoke_index_update calls ctx.invoke with index_cmd on success."""
    from unittest.mock import MagicMock, patch

    from fx_alfred.commands._helpers import invoke_index_update

    ctx = MagicMock(spec=click.Context)
    mock_index_cmd = MagicMock()

    with patch.dict(
        "sys.modules",
        {"fx_alfred.commands.index_cmd": MagicMock(index_cmd=mock_index_cmd)},
    ):
        # Simulate successful import by patching the import inside the function
        with patch(
            "fx_alfred.commands._helpers.importlib.import_module",
            return_value=MagicMock(index_cmd=mock_index_cmd),
        ):
            invoke_index_update(ctx)

    ctx.invoke.assert_called_once_with(mock_index_cmd)


def test_invoke_index_update_failure_emits_warning():
    """invoke_index_update emits warning to stderr when ctx.invoke raises."""
    from unittest.mock import MagicMock, patch

    from fx_alfred.commands._helpers import invoke_index_update

    ctx = MagicMock(spec=click.Context)
    ctx.invoke.side_effect = RuntimeError("index failed")

    with patch("click.echo") as mock_echo:
        invoke_index_update(ctx)

    mock_echo.assert_called_once()
    args, kwargs = mock_echo.call_args
    assert "Warning" in args[0]
    assert "Failed to update index" in args[0]
    assert kwargs.get("err") is True
