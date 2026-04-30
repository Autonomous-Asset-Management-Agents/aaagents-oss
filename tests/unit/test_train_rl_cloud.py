import argparse
from unittest.mock import patch, MagicMock, ANY

# The module doesn't exist yet, so we expect this to fail initially.
import train_rl_cloud


@patch("train_rl_cloud.storage.Client")
@patch("train_rl_cloud.RecurrentPPO")
@patch("train_rl_cloud.init_vertex_experiment")
@patch("train_rl_cloud.log_vertex_params")
@patch("train_rl_cloud.end_vertex_experiment")
def test_train_rl_cloud_full_flow(
    mock_end_experiment,
    mock_log_params,
    mock_init_experiment,
    mock_recurrent_ppo,
    mock_storage_client,
):
    # Prepare mocked arguments
    mock_args = argparse.Namespace(
        total_timesteps=1000,
        batch_size=64,
        learning_rate=0.0003,
        data_gcs_path="gs://my-bucket/data/all_symbols_clean.pkl",
        model_dir="gs://my-bucket/models/rl",
        rl_version="rl_agent_v7",
    )

    # Setup Storage mock
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_storage_client.return_value.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    # Setup Model mock
    mock_model_instance = MagicMock()
    mock_recurrent_ppo.return_value = mock_model_instance

    # Avoid actual file I/O for DummyVecEnv by mocking OS checks if needed,
    # but in our test we will mainly test the parser and flow.
    with patch("train_rl_cloud.StockTradingEnv"), patch(
        "train_rl_cloud.DummyVecEnv"
    ), patch("train_rl_cloud.VecNormalize"):
        train_rl_cloud.train_model(mock_args)

    # Assert GCS Download
    mock_bucket.blob.assert_any_call("data/all_symbols_clean.pkl")
    mock_blob.download_to_filename.assert_called_once()

    # Assert Vertex AI Logging Setup
    mock_init_experiment.assert_called_once()
    mock_log_params.assert_called_once()
    assert "learning_rate" in mock_log_params.call_args[0][0]
    assert mock_log_params.call_args[0][0]["learning_rate"] == 0.0003

    # Assert Model Training
    mock_recurrent_ppo.assert_called_once()
    mock_model_instance.learn.assert_called_once_with(
        total_timesteps=1000, callback=ANY, progress_bar=ANY
    )
    mock_model_instance.save.assert_called_once()

    # Assert Upload back to GCS
    # Expected saving of .zip and .pkl
    assert mock_blob.upload_from_filename.call_count >= 2

    # Assert Vertex cleanup
    mock_end_experiment.assert_called_once()
