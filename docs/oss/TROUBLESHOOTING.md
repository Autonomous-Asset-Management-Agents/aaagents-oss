# Operations & Troubleshooting Playbook

This document is for anyone running the AAAgents Community Edition locally via Docker Compose (`docker-compose.oss.yml`). If the bot fails to start, trade, or log metrics, look here first.

## 1. Container Initialization Failures

### Symptom: Backend Container Exits Immediately with "Connection Refused"
**Cause:** The typical cause is that the `backend` container is trying to run Alembic database migrations before the `postgres` container is actually ready to accept connections.
**Resolution:**
1. Check the logs: `docker-compose -f docker-compose.oss.yml logs backend`
2. If you see `psycopg2.OperationalError: FATAL: the database system is starting up`, simply wait 10 seconds and run `docker-compose -f docker-compose.oss.yml up -d backend` again.
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

## 2. LLM & Machine Learning Issues

### Symptom: "TimeoutError: Ollama Connection Refused"
**Cause:** The system is configured to use a local LLM via Ollama (`http://localhost:11434`), but Ollama is not running on your host machine or doesn't have the required model.
**Resolution:** 
1. Ensure Ollama is installed on your host OS.
2. Run `ollama serve` in a terminal.
3. Download the correct model required by the bot (default is `llama3.2`): `ollama pull llama3.2`.
4. Ensure your docker container can reach the host (`host.docker.internal` should be used instead of `localhost` in the `.env` file under `OLLAMA_BASE_URL`).

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
docker-compose -f docker-compose.oss.yml down -v
rm -rf data/db
docker-compose -f docker-compose.oss.yml up -d
```
*(Warning: The `-v` flag deletes your Postgres docker volumes. Your Alpaca brokerage state remains unaffected).*

## 5. Exposing the Dashboard Over the Internet (TLS Required)

The OSS container binds the frontend to `127.0.0.1:80` by default. This is intentional: the dashboard ships your broker API headers and session cookies; on plain HTTP over a VPS or shared network those are visible to every hop in between.

If you want to access the dashboard from another machine, **always put TLS in front** — never re-bind the container to `0.0.0.0:80` and call it a day.

### Option A — Caddy (recommended, automatic Let's Encrypt)

1. Install [Caddy](https://caddyserver.com/docs/install) on the host (one binary, no config required for basics).
2. Create `/etc/caddy/Caddyfile` with the snippet below (replace `dashboard.example.com` with a domain that resolves to your host's public IP):
   ```caddyfile
   dashboard.example.com {
       reverse_proxy 127.0.0.1:80
   }
   ```
3. `sudo systemctl reload caddy` — Caddy fetches a Let's Encrypt cert automatically and proxies HTTPS → loopback HTTP.
4. Verify: `curl -I https://dashboard.example.com` returns `200` and a valid TLS cert.

### Option B — Nginx with your own cert

```nginx
server {
    listen 443 ssl http2;
    server_name dashboard.example.com;

    ssl_certificate     /etc/ssl/certs/dashboard.crt;
    ssl_certificate_key /etc/ssl/private/dashboard.key;

    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### What NOT to do
- Do **not** edit `docker-compose.oss.yml` to bind `"80:8080"` (without `127.0.0.1:`) — that re-exposes plain HTTP to the public.
- Do **not** disable TLS for "just a quick test" — every test request leaks tokens that grant the same access as the real session.
