# aaagents — BORA OSS Plug & Run CLI

[![PyPI](https://img.shields.io/pypi/v/aaagents)](https://pypi.org/project/aaagents/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](https://github.com/Autonomous-Asset-Management-Agents/Dev-Enviroment/blob/main/LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/aaagents)](https://pypi.org/project/aaagents/)

The official CLI for the **AAAgents Community Edition** — a Docker-based,
local-first AI trading platform stack (BORA: Build Once, Run Anywhere).

> **Requires:** Docker Desktop (Windows/Mac) or Docker Engine (Linux), Python ≥ 3.11

---

## Quickstart

```bash
pip install aaagents
aaagents install   # one-time setup wizard
aaagents start     # launch the stack
aaagents status    # verify all containers are healthy
```

---

## Commands

| Command | Description |
|---|---|
| `aaagents install` | Interactive setup wizard: configures `.env.oss`, pulls Docker images |
| `aaagents start` | Start all BORA containers in the background |
| `aaagents start --no-detach` | Start in foreground (stream logs) |
| `aaagents stop` | Stop all containers (volumes preserved) |
| `aaagents status` | Show container health and port bindings |
| `aaagents version` | Print CLI version |

---

## Stack Overview

After `aaagents start`, the following services are available:

| Service | URL | Description |
|---|---|---|
| **Frontend** | http://localhost | BORA Dashboard (React) |
| **Public API** | http://localhost:8081 | REST API (Firebase-auth-gated in production) |
| **Engine** | http://localhost:8001 | AI Trading Engine (internal) |
| **Postgres** | localhost:5432 | Local database (loopback only) |
| **Redis** | localhost:6379 | Cache / Round Table state (loopback only) |

---

## Configuration

`aaagents install` creates `.env.oss` from the `.env.oss.example` template.
To reconfigure, delete `.env.oss` and run `aaagents install` again, or edit it
manually.

**Required values:**
- `POSTGRES_PASSWORD` — must be set; the stack refuses to start without it.

**Optional values:**
- `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` — leave unset to boot in **offline mode** (no live broker calls).
- `ALLOW_UNTRUSTED_PLUGINS` — set `true` only if you wrote and trust every plugin in `./plugins/round_table/`. See [ADR-OSS1](https://github.com/Autonomous-Asset-Management-Agents/Dev-Enviroment/blob/main/docs/oss/ARCHITECTURE.md).

---

## Security

Report vulnerabilities privately to **security@aaagents.de**. See [SECURITY.md](https://github.com/Autonomous-Asset-Management-Agents/Dev-Enviroment/blob/main/SECURITY.md).

---

## License

Apache 2.0 — see [LICENSE](https://github.com/Autonomous-Asset-Management-Agents/Dev-Enviroment/blob/main/LICENSE).
