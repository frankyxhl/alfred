"""Scanner regressions for activity ledger directories (FXA-2307)."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from fx_alfred.cli import cli
from fx_alfred.core.scanner import scan_documents


pytestmark = [pytest.mark.cli, pytest.mark.docs]


def test_user_log_markdown_is_not_scanned(sample_project, monkeypatch):
    log_dir = sample_project / "rules" / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "FXA-9999-SOP-Should-Not-Scan.md").write_text(
        """# FXA-9999: Should Not Scan

**Applies to:** Test
**Status:** Active
---
## Steps
1. should not appear
""",
        encoding="utf-8",
    )

    docs = scan_documents(sample_project)

    assert "FXA-9999-SOP-Should-Not-Scan.md" not in {doc.filename for doc in docs}


def test_log_markdown_is_hidden_from_list_search_status_validate(
    sample_project, monkeypatch
):
    log_dir = sample_project / "rules" / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "FXA-9998-SOP-Should-Not-Surface.md").write_text(
        """# FXA-9998: Should Not Surface

**Applies to:** Test
**Status:** Active
---
## Steps
1. should not appear
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(sample_project)
    runner = CliRunner()

    listed = runner.invoke(cli, ["list"], catch_exceptions=False)
    searched = runner.invoke(
        cli, ["search", "Should Not Surface"], catch_exceptions=False
    )
    status = runner.invoke(cli, ["status"], catch_exceptions=False)
    validated = runner.invoke(cli, ["validate"], catch_exceptions=False)

    assert listed.exit_code == 0
    assert searched.exit_code == 0
    assert status.exit_code == 0
    assert validated.exit_code in (0, 1)
    assert "FXA-9998" not in listed.output
    assert "FXA-9998" not in searched.output
    assert "FXA-9998" not in status.output
    assert "FXA-9998" not in validated.output
