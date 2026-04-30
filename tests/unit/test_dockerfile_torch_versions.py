"""
TDD tests for Dockerfile.backend torch version consistency.

Bug: Dockerfile.backend installs torch/torchvision/torchaudio without a
version pin (resolves to latest, e.g. 2.11.0+cpu), then installs
requirements.txt which pins torch==2.10.0+cpu — uv fails because the
constraint is unsatisfiable.

Fix: pin the explicit torch install step to the same versions as
requirements.txt so both steps agree.
"""

import os
import re

import pytest

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DOCKERFILE_PATH = os.path.join(REPO_ROOT, "Dockerfile.backend")
REQUIREMENTS_PATH = os.path.join(REPO_ROOT, "AI Trading Bot", "requirements.txt")


def _parse_torch_versions_from_requirements() -> dict[str, str]:
    """Return {'torch': '2.10.0+cpu', 'torchvision': '0.25.0+cpu', ...}"""
    versions: dict[str, str] = {}
    with open(REQUIREMENTS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            for pkg in ("torch", "torchaudio", "torchvision"):
                m = re.match(rf"^{pkg}==(.+)$", line)
                if m:
                    versions[pkg] = m.group(1)
    return versions


def _parse_torch_install_line_from_dockerfile() -> str:
    """Return the raw uv pip install torch ... line from Dockerfile.backend."""
    with open(DOCKERFILE_PATH, encoding="utf-8") as f:
        for line in f:
            if "uv pip install" in line and "torch" in line and "whl/cpu" in line:
                return line.strip()
    return ""


class TestDockerfileTorchVersionConsistency:
    """Dockerfile.backend must pin torch versions that match requirements.txt."""

    def test_dockerfile_pins_torch_version(self):
        """The torch install line must include an explicit version pin (==)."""
        install_line = _parse_torch_install_line_from_dockerfile()
        assert install_line, "Dockerfile.backend: torch CPU install line not found"
        assert "torch==" in install_line, (
            "Dockerfile.backend: torch install line does not pin a version. "
            "This causes uv to install the latest torch, which may conflict "
            "with the version pinned in requirements.txt.\n"
            f"Line: {install_line}"
        )

    def test_dockerfile_torch_version_matches_requirements(self):
        """torch version in Dockerfile must equal torch version in requirements.txt."""
        install_line = _parse_torch_install_line_from_dockerfile()
        req_versions = _parse_torch_versions_from_requirements()

        assert "torch" in req_versions, "requirements.txt does not pin torch"
        req_torch = req_versions["torch"]

        m = re.search(r'torch==([^\s"\']+)', install_line)
        assert m, f"Cannot find torch== pin in Dockerfile install line:\n{install_line}"
        dockerfile_torch = m.group(1)

        assert dockerfile_torch == req_torch, (
            f"Dockerfile.backend installs torch=={dockerfile_torch} but "
            f"requirements.txt pins torch=={req_torch}. "
            f"uv will fail to resolve this conflict."
        )

    def test_dockerfile_torchaudio_version_matches_requirements(self):
        """torchaudio version in Dockerfile must equal torchaudio in requirements.txt."""
        install_line = _parse_torch_install_line_from_dockerfile()
        req_versions = _parse_torch_versions_from_requirements()

        if "torchaudio" not in req_versions:
            pytest.skip("torchaudio not pinned in requirements.txt")

        req_ver = req_versions["torchaudio"]
        m = re.search(r'torchaudio==([^\s"\']+)', install_line)
        assert (
            m
        ), f"Cannot find torchaudio== pin in Dockerfile install line:\n{install_line}"
        assert (
            m.group(1) == req_ver
        ), f"Dockerfile torchaudio=={m.group(1)} != requirements.txt torchaudio=={req_ver}"

    def test_dockerfile_torchvision_version_matches_requirements(self):
        """torchvision version in Dockerfile must equal torchvision in requirements.txt."""
        install_line = _parse_torch_install_line_from_dockerfile()
        req_versions = _parse_torch_versions_from_requirements()

        if "torchvision" not in req_versions:
            pytest.skip("torchvision not pinned in requirements.txt")

        req_ver = req_versions["torchvision"]
        m = re.search(r'torchvision==([^\s"\']+)', install_line)
        assert (
            m
        ), f"Cannot find torchvision== pin in Dockerfile install line:\n{install_line}"
        assert (
            m.group(1) == req_ver
        ), f"Dockerfile torchvision=={m.group(1)} != requirements.txt torchvision=={req_ver}"
