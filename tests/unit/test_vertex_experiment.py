import pytest
from unittest.mock import patch, MagicMock

# Attempt to import the new helper module we are about to create for Vertex Logging
# This will fail initially (Red Phase) until we create it.
try:
    from core.vertex_experiment import (
        init_vertex_experiment,
        log_vertex_params,
        log_vertex_metrics,
        end_vertex_experiment,
    )
except ImportError:
    pass


class TestVertexExperimentLogging:
    """TDD tests for Vertex AI Experiment tracking integration."""

    @patch("core.vertex_experiment.aiplatform")
    def test_init_vertex_experiment(self, mock_aiplatform):
        """Test that init_vertex_experiment sets up the AI Platform experiment."""
        project_id = "test-project"
        location = "europe-west3"
        experiment_name = "lstm-training-run"

        run_id = init_vertex_experiment(
            project_id=project_id,
            location=location,
            experiment_name=experiment_name,
            run_prefix="test-run",
        )

        mock_aiplatform.init.assert_called_once_with(
            project=project_id, location=location, experiment=experiment_name
        )
        mock_aiplatform.start_run.assert_called_once()
        assert run_id is not None
        assert run_id.startswith("test-run-")

    @patch("core.vertex_experiment.aiplatform")
    def test_log_vertex_params(self, mock_aiplatform):
        params = {"batch_size": 64, "learning_rate": 0.001, "epochs": 50}
        log_vertex_params(params)
        mock_aiplatform.log_params.assert_called_once_with(params)

    @patch("core.vertex_experiment.aiplatform")
    def test_log_vertex_metrics(self, mock_aiplatform):
        metrics = {"train_loss": 0.05, "val_loss": 0.04, "accuracy": 0.85}
        step = 10
        log_vertex_metrics(metrics, step=step)

        # Test metric structure (often step isn't directly passed to log_metrics, we might just log step-suffixed or rely on Vertex's own step tracking if available, or just log_metrics at end of epoch)
        # Assuming our wrapper handles it simply:
        mock_aiplatform.log_metrics.assert_called_once()
        args, kwargs = mock_aiplatform.log_metrics.call_args
        assert args[0] == {"train_loss": 0.05, "val_loss": 0.04, "accuracy": 0.85}

    @patch("core.vertex_experiment.aiplatform")
    def test_end_vertex_experiment(self, mock_aiplatform):
        end_vertex_experiment()
        mock_aiplatform.end_run.assert_called_once()
