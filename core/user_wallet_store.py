import asyncpg
import logging
from typing import Optional, Dict, Any, List
import json

import config

logger = logging.getLogger(__name__)


class UserWalletStore:
    """
    Manages the `User_Wallets` table in Cloud SQL (PostgreSQL).
    Stores metadata (status, limits, broker account ID, secret manager ID reference).
    """

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if not config.DATABASE_URL:
            logger.warning(
                "DATABASE_URL not set. User Wallet features will use local mock logic."
            )
            return

        try:
            self.pool = await asyncpg.create_pool(config.DATABASE_URL)
            await self._init_schema()
            logger.info("Connected to Cloud SQL (User_Wallets)")
        except Exception as e:
            logger.error("Failed to connect to Cloud SQL: %s", e)

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def _init_schema(self):
        """Ensures the User_Wallets table exists."""
        if not self.pool:
            return

        query = """
        CREATE TABLE IF NOT EXISTS user_wallets (
            user_id VARCHAR(255) PRIMARY KEY,
            broker_account_id VARCHAR(255),
            secret_manager_id VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'inactive',  -- 'active', 'inactive', 'halted'
            risk_limits JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)

    async def upsert_wallet(
        self, user_id: str, broker_account_id: str, secret_manager_id: str
    ) -> None:
        if not self.pool:
            logger.info(
                f"[Local MOCK] Upserted wallet for {user_id}: {broker_account_id}, {secret_manager_id}"
            )
            return

        query = """
        INSERT INTO user_wallets (user_id, broker_account_id, secret_manager_id, updated_at)
        VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id) DO UPDATE
        SET broker_account_id = EXCLUDED.broker_account_id,
            secret_manager_id = EXCLUDED.secret_manager_id,
            updated_at = EXCLUDED.updated_at;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, user_id, broker_account_id, secret_manager_id)

    async def get_wallet(self, user_id: str) -> Optional[Dict[str, Any]]:
        if not self.pool:
            return None

        query = "SELECT * FROM user_wallets WHERE user_id = $1;"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            if row:
                d = dict(row)
                if isinstance(d.get("risk_limits"), str):
                    d["risk_limits"] = json.loads(d["risk_limits"])
                return d
            return None

    async def get_active_wallets(self) -> List[Dict[str, Any]]:
        if not self.pool:
            return []

        query = "SELECT * FROM user_wallets WHERE status = 'active';"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            res = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get("risk_limits"), str):
                    d["risk_limits"] = json.loads(d["risk_limits"])
                res.append(d)
            return res

    async def update_risk_limits(self, user_id: str, limits: Dict[str, Any]) -> bool:
        if not self.pool:
            logger.info("[Local MOCK] Updated risk limits for %s: %s", user_id, limits)
            return True

        query = "UPDATE user_wallets SET risk_limits = $1::jsonb, updated_at = CURRENT_TIMESTAMP WHERE user_id = $2"
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, json.dumps(limits), user_id)
            return result == "UPDATE 1"

    async def update_alpaca_keys(
        self, user_id: str, api_key: str, secret_key: str
    ) -> bool:
        """Disabled in OSS Edition. API keys must be set via .env.oss.

        This method is a no-op stub. Writing Alpaca keys to the database
        is not supported in the OSS edition; all credentials are loaded
        from environment variables (ALPACA_API_KEY, ALPACA_SECRET_KEY).

        Raises:
            NotImplementedError: Always. Instructs the caller to use .env instead.
        """
        raise NotImplementedError(
            "Storing Alpaca API keys in the database is disabled in the OSS Edition. "
            "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in your .env.oss file. "
            "See README.oss.md for setup instructions."
        )

    @staticmethod
    def get_alpaca_keys_from_env() -> dict[str, str] | None:
        """Load Alpaca credentials exclusively from environment variables.

        Returns a dict with 'api_key' and 'secret_key' if both are set,
        or None if either is missing (triggering Offline/Shadow Boot mode).
        """
        import os

        api_key = os.environ.get("ALPACA_API_KEY", "").strip()
        secret_key = os.environ.get("ALPACA_SECRET_KEY", "").strip()
        if not api_key or not secret_key:
            logger.warning(
                "ALPACA_API_KEY or ALPACA_SECRET_KEY not set in environment. "
                "System will run in Offline (Shadow Boot) mode — no orders will execute."
            )
            return None
        return {"api_key": api_key, "secret_key": secret_key}

    async def update_status(self, user_id: str, status: str) -> bool:
        if not self.pool:
            logger.info("[Local MOCK] Updated status for %s: %s", user_id, status)
            return True

        # Validation
        if status not in ["active", "inactive", "halted"]:
            raise ValueError("Invalid status")

        query = "UPDATE user_wallets SET status = $1, updated_at = CURRENT_TIMESTAMP WHERE user_id = $2"
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, status, user_id)
            return result == "UPDATE 1"


# Singleton instance
wallet_store = UserWalletStore()
