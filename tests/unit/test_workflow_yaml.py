"""
TDD test for Cluster A fix: GitHub Actions workflow YAML indentation bugs.

These tests must FAIL before the fix and PASS after.
Each test validates that a workflow file:
  1. Parses as valid YAML without errors
  2. Has at least one job defined
  3. Every job has 'runs-on' as a direct top-level job property (not nested)
  4. No job has duplicate keys (e.g., duplicate timeout-minutes)
"""

import os
import pytest
import yaml

WORKFLOWS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", ".github", "workflows"
)

CLUSTER_A_FILES = [
    "ai-autorepair.yml",
    "deploy-public-api.yml",
    "e2e-playwright.yml",
    "e2e-smoke.yml",
    "terraform.yml",
]


def load_workflow(filename: str) -> dict:
    path = os.path.join(WORKFLOWS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def raw_lines(filename: str) -> list[str]:
    path = os.path.join(WORKFLOWS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()


class TestWorkflowYamlValid:
    """Each workflow file must parse without YAML errors."""

    @pytest.mark.parametrize("filename", CLUSTER_A_FILES)
    def test_parses_as_valid_yaml(self, filename):
        # yaml.safe_load raises yaml.YAMLError on invalid files
        wf = load_workflow(filename)
        assert wf is not None, f"{filename}: parsed to None (empty file?)"
        assert isinstance(wf, dict), f"{filename}: top-level must be a mapping"

    @pytest.mark.parametrize("filename", CLUSTER_A_FILES)
    def test_has_jobs_section(self, filename):
        wf = load_workflow(filename)
        assert "jobs" in wf, f"{filename}: missing 'jobs' key"
        assert len(wf["jobs"]) > 0, f"{filename}: 'jobs' section is empty"


class TestWorkflowJobProperties:
    """Every job must have 'runs-on' as a direct job-level property."""

    @pytest.mark.parametrize("filename", CLUSTER_A_FILES)
    def test_every_job_has_runs_on(self, filename):
        wf = load_workflow(filename)
        for job_id, job in wf["jobs"].items():
            assert isinstance(job, dict), (
                f"{filename}: job '{job_id}' is not a mapping — "
                f"YAML likely parsed it as part of a scalar (indentation bug)"
            )
            assert "runs-on" in job, (
                f"{filename}: job '{job_id}' missing 'runs-on' — "
                f"likely swallowed into an 'if:' folded scalar or at wrong indent"
            )

    @pytest.mark.parametrize("filename", CLUSTER_A_FILES)
    def test_runs_on_is_not_in_if_string(self, filename):
        wf = load_workflow(filename)
        for job_id, job in wf["jobs"].items():
            if not isinstance(job, dict):
                continue
            if_val = job.get("if", "")
            assert "runs-on" not in str(if_val), (
                f"{filename}: job '{job_id}' has 'runs-on' embedded inside the "
                f"'if:' value — indentation bug (folded scalar)"
            )


class TestWorkflowNoDuplicateKeys:
    """No workflow file may have duplicate keys at any mapping level.

    PyYAML silently takes the last value for duplicate keys, so we need
    a custom loader to catch them.
    """

    @staticmethod
    def _make_duplicate_checking_loader():
        class DuplicateKeyError(yaml.YAMLError):
            pass

        class DuplicateKeyLoader(yaml.SafeLoader):
            pass

        original_construct_mapping = DuplicateKeyLoader.construct_mapping

        def construct_mapping(loader, node, deep=False):
            loader.flatten_mapping(node)
            keys = [loader.construct_object(key_node) for key_node, _ in node.value]
            seen = set()
            for key in keys:
                if key in seen:
                    raise DuplicateKeyError(
                        f"Duplicate key found: '{key}' at line {node.start_mark.line + 1}"
                    )
                seen.add(key)
            return original_construct_mapping(loader, node, deep=deep)

        DuplicateKeyLoader.construct_mapping = construct_mapping
        return DuplicateKeyLoader

    @pytest.mark.parametrize("filename", CLUSTER_A_FILES)
    def test_no_duplicate_keys(self, filename):
        path = os.path.join(WORKFLOWS_DIR, filename)
        loader = self._make_duplicate_checking_loader()
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Should not raise
        try:
            yaml.load(content, Loader=loader)  # noqa: S506
        except yaml.YAMLError as exc:
            pytest.fail(f"{filename}: {exc}")
