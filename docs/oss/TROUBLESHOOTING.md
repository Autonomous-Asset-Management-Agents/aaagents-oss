# Operations & Troubleshooting Playbook

This document is for anyone running the AAAgents Community Edition locally via Docker Compose (`docker-compose.oss.yml`). If the bot fails to start, trade, or log metrics, look here first.

## 1. Container Initialization Failures

### Symptom: Backend Container Exits Immediately with "Connection Refused"
**Cause:** The typical cause is that the `backend` container is trying to run Alembic database migrations before the `postgres` container is actually ready to accept connections.
**Resolution:**
1. Check the logs: `docker compose --env-file .env.oss -f docker-compose.oss.yml logs backend`
2. If you see `psycopg2.OperationalError: FATAL: the database system is starting up`, simply wait 10 seconds and run `docker compose --env-file .env.oss -f docker-compose.oss.yml up -d backend` again.
3. *Note:* The Docker-Compose file includes a `depends_on: condition: service_healthy` check, but some setups resolve this prematurely.

### Symptom: Alembic "Target database is not up to date" (Out of Sync)
**Cause:** Modifying database models and running the system without creating an alembic revision.
**Resolution:**
```bash
# Exec into the backend container
docker exec -it aaagents-backend bash
# Autogenerate the migration
alembic revision --autogenerate -m "Fix out of sync"
# Apply it
alembic upgrade head
```

## Engine running but no trades after 1 hour

If `make logs` shows the engine starting but no orders are placed, walk this checklist:

1. **Are Alpaca keys actually set?**
   ```bash
   docker compose --env-file .env.oss -f docker-compose.oss.yml exec backend printenv ALPACA_API_KEY
   ```
   If output is empty or `offline_mode`, your keys never made it into the env. Open `.env.oss` and confirm `ALPACA_API_KEY=` (no leading `#`) has your real key as the value.

2. **Did the engine boot in Shadow Mode?**
   ```bash
   make logs | grep -i "shadow\|offline_mode\|Alpaca offline"
   ```
   Hits = engine is running without a real broker connection. Fix Step 1.

3. **Did models download?**
   ```bash
   make logs | grep -i "OSS sync complete\|RL agent loaded\|RL agent file not found"
   ```
   If you see `RL agent file not found` and your release has no model assets, you're on a build without the model bundle. The engine boots but the LSTM and RL voting agents return neutral 0.5, which dilutes consensus to ~0.5 — below the BUY threshold (0.65). Wait for a release that ships a model bundle, OR build your own bundle (see [docs/oss/RELEASING_MODEL_BUNDLE.md](./RELEASING_MODEL_BUNDLE.md)).

4. **Is the market open?**
   The default trading loop sleeps 5 minutes when the market clock is closed. Check `make logs | grep "Market is CLOSED\|Sleeping for 5"`. If you want to test off-hours, set `BYPASS_MARKET_HOURS=true` in `.env.oss` (paper trading only).

5. **Did the scanner identify any candidates?**
   ```bash
   make logs | grep "Scanner identified top candidates"
   ```
   If absent, the AI market scanner returned an empty universe. Common causes (in order of likelihood): the Alpaca data feed is rate-limited or returning empty snapshots; scanner volatility/RSI thresholds are filtering everything out for the current regime; or `GEMINI_API_KEY` is unset and the non-Gemini fallback isn't finding enough candidates. The engine retries every cycle — if it never recovers, file a bug. Note: missing `POLYGON_API_KEY` is **not** the cause — `core/market_regime.py` falls through to a SPY-derived implied-volatility path (`USE_SPY_VOLATILITY_FALLBACK=True` default) using Alpaca data, so regime detection keeps working without Polygon.

## 2. LLM & Machine Learning Issues

### Symptom: "GEMINI_API_KEY not found AND Live Trading is active" or Boot Crash
**Cause:** The system relies on Google's Gemini models for sentiment analysis and reasoning. If you are attempting to boot with `PAPER_TRADING=False` (live trading with real money) and the Gemini API key is missing, the system will deterministically abort to prevent unguided live trades.
**Resolution:** 
1. Obtain a Gemini API key from Google AI Studio.
2. Edit your `.env.oss` file and add `GEMINI_API_KEY=your_key_here`.
3. Restart the backend container: `docker compose --env-file .env.oss -f docker-compose.oss.yml restart backend`.
*Note: If you only want to test the system without an LLM, ensure `PAPER_TRADING=True`. The system will boot in "Degraded Sentiment Mode" (skipping LLM-dependent agents).*

### Symptom: Docker OOM (Out Of Memory) Crash
**Cause:** Loading the PyTorch RL agents alongside data caching exceeds your Docker Desktop memory allocation limits.
**Resolution:**
1. Open Docker Desktop settings.
2. Increase the Resource limit for Memory to at least **8 GB** (12 GB recommended if also running local LLMs).

## 3. Trading & Execution Blocks

### Symptom: Bot evaluates a BUY but executes a HOLD
**Cause:** The *Iron Dome* blocked the trade. This is expected behavior!
**Resolution:**
Check the logs for `ComplianceGuardian` or `RiskManager`. Typical reasons:
- `PDT Violation Block`: You are trying to day-trade more than 3 times in 5 days with an account under $25,000.
- `VIX Threshold Exceeded`: Market volatility is too high, the bot activated the global Stop-Loss.
- `Insufficient Buying Power`: You lack the cash required for the calculated position size.

## 4. Resetting the System (Nuclear Option)
If everything breaks and you just want to start fresh (deleting all local paper-trading history and state):
```bash
docker compose --env-file .env.oss -f docker-compose.oss.yml down -v
rm -rf data/db
docker compose --env-file .env.oss -f docker-compose.oss.yml up -d
```
*(Warning: The `-v` flag deletes your Postgres docker volumes. Your Alpaca brokerage state remains unaffected).*

## 5. Exposing the Dashboard Over the Internet (SSH Tunnel Required)

The OSS container binds the frontend to `127.0.0.1:80` by default. This is intentional: the dashboard ships your broker API headers and session cookies; on plain HTTP over a VPS or shared network those are visible to every hop in between.

If you want to access the dashboard from another machine (e.g., a VPS), **do not** edit `docker-compose.oss.yml` to bind to `0.0.0.0:80`. This exposes your bot completely.

Instead, use an **SSH Tunnel**. This is the industry standard for securely accessing remote dashboards without the overhead of setting up TLS/Nginx.

### How to set up an SSH Tunnel

From your local machine (your laptop), run the following command to securely forward the dashboard and API ports over SSH:

```bash
ssh -L 8080:localhost:80 -L 8001:localhost:8001 user@vps-ip
```

*(Replace `user@vps-ip` with your actual VPS SSH login credentials).*

Once the SSH session is open, simply open your local web browser and navigate to:
`http://localhost:8080`

The traffic is encrypted via SSH, completely invisible to the public internet, and requires zero additional setup on the server.

### What NOT to do
- Do **not** edit `docker-compose.oss.yml` to bind `"80:8080"` (without `127.0.0.1:`) — that re-exposes plain HTTP to the public.
- Do **not** disable loopback bindings for "just a quick test" — every test request leaks tokens that grant the same access as the real session.

### Alternative: Public Internet Exposure via TLS (Caddy Reverse Proxy)

If you must expose the dashboard to the public internet natively (without SSH), you MUST use a reverse proxy with TLS (like Let's Encrypt). The easiest way is using Caddy.

> [!CAUTION]
> **CRITICAL WARNING: LocalMockAuth bypass!**
> The OSS Community Edition uses `LocalMockAuth` which treats **ANY Bearer token as an admin token** for local operation.
> If you expose the Engine API (`127.0.0.1:8001`) or Dashboard (`127.0.0.1:80`) to the public internet using Caddy without configuring your own authentication layer, **your entire trading bot will be exposed to attackers.**
> You MUST configure Caddy to require Basic Auth or implement your own API Gateway.

1. Keep the `docker-compose.oss.yml` bindings on `127.0.0.1:80` as they are.
2. Install Caddy on your server.
3. Edit `/etc/caddy/Caddyfile` with your public domain (add `basicauth` block):
```caddyfile
bots.your-domain.com {
    basicauth {
        # Generate with: caddy hash-password
        admin JDJhJDE0JH...
    }
    reverse_proxy 127.0.0.1:80
}
```
4. Restart Caddy. It will automatically provision TLS certs via Let's Encrypt and forward public `HTTPS:443` traffic securely to the local container.
