from pathlib import Path

import pytest


pytestmark = pytest.mark.docs


def test_coverage_report_precision_is_two_decimal_places():
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    report_lines = []
    in_report_section = False
    for line in pyproject_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_report_section = stripped == "[tool.coverage.report]"
        elif in_report_section:
            report_lines.append(stripped)

    assert "precision = 2" in report_lines, (
        "pyproject.toml must set [tool.coverage.report] precision to integer 2"
    )
