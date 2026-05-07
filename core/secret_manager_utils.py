# core/secret_manager_utils.oss.py — OSS Stub (Fail-Closed)
#
# The OSS edition does NOT persist OAuth tokens to disk.
# All broker credentials must be supplied via environment variables (.env.oss).
#
# This stub preserves the same public API surface as the Enterprise
# OAuthSecretManager (GCP Secret Manager) so that module imports do not
# break. Any attempt to actually save or retrieve tokens raises
# NotImplementedError immediately, making misconfiguration loud and obvious.
#
# Enterprise edition: uses GCP Secret Manager (core/secret_manager_utils.py).
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OAuthSecretManager:
    """
    OSS Fail-Closed stub — OAuth token storage is disabled in this edition.

    All methods raise NotImplementedError. Broker credentials must be
    provided exclusively via environment variables (ALPACA_API_KEY,
    ALPACA_SECRET_KEY) in the .env.oss file.

    Replaces the GCP Secret Manager backend used in the Enterprise edition.
    """

    def __init__(self, project_id: Optional[str] = None):
        # project_id accepted for API compatibility; ignored in OSS.
        logger.debug(
            "OAuthSecretManager (OSS stub) initialised. "
            "OAuth token storage is disabled — use .env.oss for credentials."
        )

    def save_tokens(self, user_id: str, access_token: str, refresh_token: str) -> str:
        raise NotImplementedError(
            "OAuth token storage is disabled in the OSS Edition. "
            "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in your .env.oss file. "
            "See README.oss.md for setup instructions."
        )

    def get_tokens(self, secret_id: str) -> Optional[dict]:
        raise NotImplementedError(
            "OAuth token retrieval is disabled in the OSS Edition. "
            "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in your .env.oss file. "
            "See README.oss.md for setup instructions."
        )


# Singleton — matches the Enterprise module's export surface.
# Kept as a module-level object so existing imports don't fail at load time.
# Calls to save_tokens / get_tokens will raise NotImplementedError at runtime.
oauth_secrets = OAuthSecretManager()
