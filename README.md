# BORA OSS — Build Once, Run Anywhere

[![OSS CI](https://github.com/Autonomous-Asset-Management-Agents/aaagents-oss/actions/workflows/oss-ci.yml/badge.svg)](https://github.com/Autonomous-Asset-Management-Agents/aaagents-oss/actions/workflows/oss-ci.yml)
[![Release](https://img.shields.io/github/v/release/Autonomous-Asset-Management-Agents/aaagents-oss?label=Release&color=blue)](https://github.com/Autonomous-Asset-Management-Agents/aaagents-oss/releases)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Discussions](https://img.shields.io/github/discussions/Autonomous-Asset-Management-Agents/aaagents-oss)](https://github.com/Autonomous-Asset-Management-Agents/aaagents-oss/discussions)

**An autonomous AI trading platform you can run entirely on your own machine.** No cloud subscription, no API keys required to start — just Docker.

> **Legal posture:** This is a research and educational project. Paper-trading by default. No BaFin licence held. See [SECURITY.md](./SECURITY.md) before running with real funds.

---

## ⚡ Quick Start — 3 Commands

```bash
# Option A — via aaagents CLI (recommended)
pip install aaagents
aaagents install   # interactive setup wizard
aaagents start     # spins up the full BORA stack

# Option B — via Docker Compose directly
cp .env.oss.example .env.oss
docker compose -f docker-compose.oss.yml up -d
```

🌐 **Dashboard available at:** `http://localhost` after startup.

> **No build required.** Pre-built images are pulled automatically from GHCR:
> ```
> ghcr.io/autonomous-asset-management-agents/bora-backend:latest
> ghcr.io/autonomous-asset-management-agents/bora-public-api:latest
> ghcr.io/autonomous-asset-management-agents/bora-frontend:latest
> ```

---

## 🧠 What is BORA?

BORA is the **Community Edition** of the AAAgents autonomous trading platform. It ships with:

| Feature | Description |
|---|---|
| **Round Table V2** | 9-agent LangGraph consensus framework (LSTM, RL, News, Market Regime, Compliance…) |
| **Iron Dome** | MiFID II-inspired risk management: VIX kill-switch, position limits, wash-trade detection |
| **Plugin Architecture** | Add custom strategy agents via `StockSpecialistRegistry` — no core changes needed |
| **BORA Control Center** | React/TypeScript dashboard — live portfolio view, agent votes, kill-switch |
| **Local-First** | PostgreSQL + Redis, fully containerized — no GCP, no Firebase required |

---

## 📚 Documentation

| Document | Description |
|---|---|
| [Architecture](./docs/oss/ARCHITECTURE.md) | System design, plugin architecture, separation of concerns |
| [Troubleshooting](./docs/oss/TROUBLESHOOTING.md) | Common Docker, network, and startup issues |
| [Contributing](./CONTRIBUTING.md) | How to add features, open issues, write plugins |
| [Security](./SECURITY.md) | Responsible disclosure policy |

For AI agents and LLMs: use `CLAUDE.md` (loaded automatically by Claude Code) as your entry point.

---

## 🔌 Plugin Tutorial (Add Your Own Strategy)

BORA's agent system is fully extensible. A minimal plugin:

```python
# plugins/my_strategy.py
from core.round_table.base_agent import BaseVotingAgent

class MyStrategyAgent(BaseVotingAgent):
    name = "MyStrategy"
    default_weight = 10.0

    async def analyze(self, symbol: str, context: dict) -> float:
        # Return a score between 0.0 (strong sell) and 1.0 (strong buy)
        return 0.6
```

Mount the plugin and register it in `.env.oss`:
```env
ROUND_TABLE_PLUGINS_DIR=/app/plugins
ALLOW_UNTRUSTED_PLUGINS=true
```

See [docs/oss/ARCHITECTURE.md](./docs/oss/ARCHITECTURE.md) for the full Plugin API.

---

## 🛠️ Development Setup

```bash
# Backend (in repo root)
python -m venv venv
source venv/bin/activate          # Linux/Mac
# .\venv\Scripts\activate         # Windows

pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# Run tests
pytest tests/unit/ -v
```

**Code quality (mandatory before PRs):**
```bash
black .
flake8 .
```

---

## 🤝 Community

- 💬 [GitHub Discussions](https://github.com/Autonomous-Asset-Management-Agents/aaagents-oss/discussions) — questions, ideas, show & tell
- 🐛 [Issues](https://github.com/Autonomous-Asset-Management-Agents/aaagents-oss/issues) — bug reports
- 📖 [Contributing Guide](./CONTRIBUTING.md) — how to submit PRs

---

## 📄 License

Apache 2.0 — see [LICENSE](./LICENSE).
Model weights are licensed separately under CC-BY-4.0 — see [LICENSE-MODELS](./LICENSE-MODELS).

---

*Maintained by the AAAgents Community | [BORA OSS v0.1.0-beta](https://github.com/Autonomous-Asset-Management-Agents/aaagents-oss/releases/tag/v0.1.0-beta)*
