# tests/unit/test_gcs_sync_on_start.py
# TDD: Tests geschrieben VOR der Implementierung von scripts/gcs_sync_on_start.py
#
# Deckt ab:
#   - Kein GCS_DATA_BUCKET gesetzt → lokaler Betrieb, exit 0
#   - data/ wird angelegt wenn nicht vorhanden
#   - Modelle werden von gs://bucket/data/ nach DATA_DIR/ heruntergeladen
#   - GCS-Fehler blockiert NICHT den Engine-Start (exit immer 0)
#   - Leerer Bucket → exit 0

import importlib
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Pfad zum scripts/-Verzeichnis hinzufügen, damit gcs_sync_on_start importierbar ist
_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "../../scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Hilfsfunktion: Modul nach Env-Var-Änderungen neu laden (Caching umgehen)
# ---------------------------------------------------------------------------
def _load_module():
    import gcs_sync_on_start

    importlib.reload(gcs_sync_on_start)
    return gcs_sync_on_start


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGcsSyncOnStart:
    """Unit-Tests für scripts/gcs_sync_on_start.py (GCS → Container Sync)."""

    def test_no_gcs_bucket_env_returns_zero(self, monkeypatch):
        """Wenn GCS_DATA_BUCKET nicht gesetzt ist, soll main() 0 zurückgeben (lokaler Betrieb).
        Der Engine-Startup darf nicht blockiert werden.
        """
        monkeypatch.delenv("GCS_DATA_BUCKET", raising=False)
        mod = _load_module()
        result = mod.main()
        assert (
            result == 0
        ), "main() MUSS 0 zurückgeben wenn kein GCS-Bucket konfiguriert ist"

    def test_empty_gcs_bucket_string_returns_zero(self, monkeypatch):
        """GCS_DATA_BUCKET='' (leerer String) → gleiches Verhalten wie nicht gesetzt."""
        monkeypatch.setenv("GCS_DATA_BUCKET", "")
        mod = _load_module()
        result = mod.main()
        assert result == 0

    def test_creates_data_dir_if_missing(self, monkeypatch, tmp_path):
        """Das DATA_DIR-Verzeichnis wird angelegt, falls es noch nicht existiert."""
        target_dir = tmp_path / "new_data"
        assert not target_dir.exists()

        monkeypatch.setenv("GCS_DATA_BUCKET", "gs://aaa-trading-bot-models")
        monkeypatch.setenv("DATA_DIR", str(target_dir))

        mock_blob = MagicMock()
        mock_blob.name = "data/rl_agent_v5.zip"
        mock_blob.download_to_file = MagicMock()

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value.bucket.return_value.list_blobs.return_value = [
                mock_blob
            ]
            mod = _load_module()
            mod.main()

        assert target_dir.exists(), "DATA_DIR muss nach dem Sync existieren"

    def test_downloads_rl_and_lstm_models(self, monkeypatch, tmp_path):
        """RL-Modell (rl_agent_v5.zip) und LSTM-Modell (lstm_model_v2.pth) werden
        von gs://bucket/data/ nach DATA_DIR/ heruntergeladen.
        """
        data_dir = tmp_path / "data"
        monkeypatch.setenv("GCS_DATA_BUCKET", "gs://aaa-trading-bot-models")
        monkeypatch.setenv("DATA_DIR", str(data_dir))

        mock_rl = MagicMock()
        mock_rl.name = "data/rl_agent_v5.zip"
        mock_lstm = MagicMock()
        mock_lstm.name = "data/lstm_model_v2.pth"

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value.bucket.return_value.list_blobs.return_value = [
                mock_rl,
                mock_lstm,
            ]
            mod = _load_module()
            result = mod.main()

        assert result == 0
        # Verify each blob had download_to_file called exactly once.
        assert mock_rl.download_to_file.call_count == 1
        assert mock_lstm.download_to_file.call_count == 1
        # Verify the files were written to the correct paths by checking
        # that the expected output files exist on disk (created by open()).
        assert (data_dir / "rl_agent_v5.zip").exists()
        assert (data_dir / "lstm_model_v2.pth").exists()

    def test_correct_bucket_name_used(self, monkeypatch, tmp_path):
        """gs://-Präfix wird korrekt entfernt; nur der Bucket-Name wird übergeben."""
        monkeypatch.setenv("GCS_DATA_BUCKET", "gs://aaa-trading-bot-models")
        monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value.bucket.return_value.list_blobs.return_value = []
            mod = _load_module()
            mod.main()

            mock_client.return_value.bucket.assert_called_once_with(
                "aaa-trading-bot-models"
            )

    def test_gcs_connection_error_does_not_block_engine(self, monkeypatch, tmp_path):
        """Wenn GCS nicht erreichbar ist, MUSS main() trotzdem 0 zurückgeben.
        Der Engine-Start wird nie durch einen GCS-Fehler blockiert.
        """
        monkeypatch.setenv("GCS_DATA_BUCKET", "gs://aaa-trading-bot-models")
        monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value.bucket.side_effect = Exception(
                "Connection refused"
            )
            mod = _load_module()
            result = mod.main()

        assert result == 0, "GCS-Fehler darf den Engine-Start NICHT blockieren"

    def test_empty_bucket_returns_zero(self, monkeypatch, tmp_path):
        """Leerer GCS-Bucket (keine Dateien unter data/) → exit 0, kein Crash."""
        monkeypatch.setenv("GCS_DATA_BUCKET", "gs://aaa-trading-bot-models")
        monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value.bucket.return_value.list_blobs.return_value = []
            mod = _load_module()
            result = mod.main()

        assert result == 0

    def test_directory_blob_skipped(self, monkeypatch, tmp_path):
        """Ein Blob der auf '/' endet (GCS-Ordner-Marker) wird übersprungen."""
        data_dir = tmp_path / "data"
        monkeypatch.setenv("GCS_DATA_BUCKET", "gs://aaa-trading-bot-models")
        monkeypatch.setenv("DATA_DIR", str(data_dir))

        mock_dir_blob = MagicMock()
        mock_dir_blob.name = "data/"  # GCS-Ordner-Marker (endet mit /)
        mock_dir_blob.size = 0

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value.bucket.return_value.list_blobs.return_value = [
                mock_dir_blob
            ]
            mod = _load_module()
            result = mod.main()

        assert result == 0
        mock_dir_blob.download_to_file.assert_not_called()
