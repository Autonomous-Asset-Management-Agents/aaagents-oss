# scripts/gcs_sync_on_start — TFT serving-bundle download (model-provenance Issue 3, OSS)
# Dormant unless TFT_BUNDLE_URL set; idempotent; non-blocking; allow-listed host; optional
# whole-tar SHA-256; SAFE extraction (path-traversal / symlink members rejected).

import hashlib
import io
import sys
import tarfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import gcs_sync_on_start as g  # noqa: E402

_URL = "https://github.com/org/repo/releases/download/tft-v1/tft-serving-models.tar.gz"


def _make_tar(members):
    """members: list of (arcname, bytes) → returns the .tar.gz bytes."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for arcname, data in members:
            info = tarfile.TarInfo(name=arcname)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _bundle():
    return _make_tar(
        [
            ("AAPL/checkpoint.pt", b"CK"),
            ("AAPL/training_ds.pkl", b"DS"),
            ("AAPL/metadata.json", b"{}"),
        ]
    )


def _install_download(monkeypatch, tar_bytes, spy=None):
    def _dl(url, dest, max_bytes):
        if spy is not None:
            spy(url, dest, max_bytes)
        with open(dest, "wb") as f:
            f.write(tar_bytes)
        return True

    monkeypatch.setattr(g, "_stream_download_capped", _dl)


def _root(tmp_path, monkeypatch):
    monkeypatch.setenv("TFT_MODELS_ROOT", str(tmp_path))
    monkeypatch.delenv("TFT_BUNDLE_SHA256", raising=False)
    return tmp_path


def test_dormant_without_url(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    monkeypatch.delenv("TFT_BUNDLE_URL", raising=False)
    spy = MagicMock()
    _install_download(monkeypatch, _bundle(), spy)
    g._sync_tft_bundle()
    spy.assert_not_called()  # dormant: no download attempted
    assert not (tmp_path / "AAPL").exists()


def test_happy_path_extracts(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    monkeypatch.setenv("TFT_BUNDLE_URL", _URL)
    _install_download(monkeypatch, _bundle())
    g._sync_tft_bundle()
    assert (tmp_path / "AAPL" / "checkpoint.pt").read_bytes() == b"CK"
    assert (tmp_path / "AAPL" / "training_ds.pkl").exists()
    assert not (tmp_path / ".tft_bundle.partial").exists()  # temp cleaned up


def test_idempotent_skips_when_populated(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    (tmp_path / "AAPL").mkdir()
    (tmp_path / "AAPL" / "checkpoint.pt").write_bytes(b"existing")
    monkeypatch.setenv("TFT_BUNDLE_URL", _URL)
    spy = MagicMock()
    _install_download(monkeypatch, _bundle(), spy)
    g._sync_tft_bundle()
    spy.assert_not_called()  # already provisioned → no re-download
    assert (tmp_path / "AAPL" / "checkpoint.pt").read_bytes() == b"existing"


def test_sha_mismatch_refuses_extract(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    monkeypatch.setenv("TFT_BUNDLE_URL", _URL)
    monkeypatch.setenv("TFT_BUNDLE_SHA256", "deadbeef" * 8)
    _install_download(monkeypatch, _bundle())
    g._sync_tft_bundle()
    assert not (tmp_path / "AAPL").exists()  # tampered tar never extracted


def test_sha_match_extracts(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    tar = _bundle()
    monkeypatch.setenv("TFT_BUNDLE_URL", _URL)
    monkeypatch.setenv("TFT_BUNDLE_SHA256", hashlib.sha256(tar).hexdigest())
    _install_download(monkeypatch, tar)
    g._sync_tft_bundle()
    assert (tmp_path / "AAPL" / "checkpoint.pt").exists()


def test_url_not_allowlisted_skips(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    monkeypatch.setenv("TFT_BUNDLE_URL", "http://evil.example.com/x.tar.gz")
    spy = MagicMock()
    _install_download(monkeypatch, _bundle(), spy)
    g._sync_tft_bundle()
    spy.assert_not_called()
    assert not (tmp_path / "AAPL").exists()


def test_path_traversal_member_rejected(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    monkeypatch.setenv("TFT_BUNDLE_URL", _URL)
    evil = _make_tar([("../evil.txt", b"PWNED"), ("AAPL/checkpoint.pt", b"CK")])
    _install_download(monkeypatch, evil)
    g._sync_tft_bundle()  # _safe_extract raises → caught → non-fatal
    assert not (tmp_path.parent / "evil.txt").exists()  # never escaped the root
    # the whole extraction is aborted on the bad member → AAPL not written either
    assert not (tmp_path / "AAPL" / "checkpoint.pt").exists()


def test_symlink_member_rejected(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    monkeypatch.setenv("TFT_BUNDLE_URL", _URL)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        link = tarfile.TarInfo(name="AAPL/evil_link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        tar.addfile(link)
    _install_download(monkeypatch, buf.getvalue())
    g._sync_tft_bundle()
    assert not (tmp_path / "AAPL" / "evil_link").exists()


def test_absolute_path_member_rejected(tmp_path):
    # _safe_extract_tft_tar must reject an ABSOLUTE-path member before any extraction.
    tar_path = tmp_path / "evil.tar.gz"
    tar_path.write_bytes(
        _make_tar([("/etc/pwned.txt", b"PWN"), ("AAPL/checkpoint.pt", b"CK")])
    )
    dest = tmp_path / "models"
    dest.mkdir()
    with pytest.raises(ValueError):
        g._safe_extract_tft_tar(str(tar_path), str(dest))
    assert not (dest / "AAPL" / "checkpoint.pt").exists()  # aborted → nothing extracted
