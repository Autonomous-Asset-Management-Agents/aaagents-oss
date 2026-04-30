"""
TDD tests for CI gate regressions uncovered after Cluster A YAML fix.

Bug 1 — ci.yml Frontend gate treats 'cancelled' as failure:
  When no frontend files change, path-filter skips frontend jobs (result=skipped).
  The gate runs with if:always() and fails on 'cancelled'/'skipped'.
  Fix: only fail on 'failure', accept 'cancelled' and 'skipped'.
"""

import os
import re
import subprocess
import pytest
import yaml

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
WORKFLOWS_DIR = os.path.join(REPO_ROOT, ".github", "workflows")


def load_workflow(filename: str) -> dict:
    path = os.path.join(WORKFLOWS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_workflow_raw(filename: str) -> str:
    path = os.path.join(WORKFLOWS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Bug 1: ci.yml Frontend gate must not reject 'cancelled' / 'skipped'
# ---------------------------------------------------------------------------


class TestFrontendGateLogic:
    """The frontend rollup gate must only fail on actual 'failure' results."""

    def _extract_gate_script(self) -> str:
        """Pull the bash body out of the 'Check all frontend gates passed' step."""
        wf = load_workflow("ci.yml")
        frontend_job = wf["jobs"].get("frontend")
        assert frontend_job is not None, "ci.yml: missing 'frontend' rollup job"
        for step in frontend_job.get("steps", []):
            if "frontend gates" in step.get("name", "").lower():
                return step.get("run", "")
        pytest.fail("ci.yml: 'Check all frontend gates passed' step not found")

    def test_gate_does_not_fail_on_cancelled(self):
        """Gate must accept 'cancelled' — happens when path filter skips frontend jobs."""
        script = self._extract_gate_script()
        # The script must NOT contain: "$r" == "cancelled"
        assert '"cancelled"' not in script or "cancelled" not in script.replace(
            "# cancelled is ok", ""
        ), (
            "ci.yml frontend gate fails on 'cancelled' — "
            "this breaks PRs that don't touch frontend files. "
            "Remove 'cancelled' from the failure condition."
        )

    def test_gate_does_not_fail_on_skipped(self):
        """Gate must accept 'skipped' — happens when path filter outputs false."""
        script = self._extract_gate_script()
        assert '"skipped"' not in script, (
            "ci.yml frontend gate fails on 'skipped' — "
            "this breaks PRs that don't touch frontend files."
        )

    def test_gate_still_fails_on_failure(self):
        """Gate must still fail when a frontend job genuinely fails."""
        script = self._extract_gate_script()
        assert (
            '"failure"' in script
        ), "ci.yml frontend gate no longer checks for 'failure' — gate is useless."
