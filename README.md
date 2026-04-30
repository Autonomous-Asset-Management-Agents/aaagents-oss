# AAA – Autonomous Asset Management Agents

[![Release](https://img.shields.io/github/v/release/aaagents/Dev-Enviroment?label=Release&color=blue)](https://github.com/aaagents/Dev-Enviroment/releases)
[![OSS CI](https://github.com/aaagents/Dev-Enviroment/actions/workflows/oss-ci.yml/badge.svg)](https://github.com/aaagents/Dev-Enviroment/actions/workflows/oss-ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Discussions](https://img.shields.io/github/discussions/aaagents/Dev-Enviroment)](https://github.com/aaagents/Dev-Enviroment/discussions)

An autonomous stock trading system with AI-driven decision-making, consisting of a Python backend (AI Trading Bot) and a React/TypeScript frontend (Portfolio Dashboard).

> **Legal posture:** see [DISCLAIMER.md](./DISCLAIMER.md) before running live trading.

---

## 📚 Technical Documentation Hub

> [!IMPORTANT]
> **This repository uses a Docs-as-Code architecture.**
> All architectural decisions, roadmap planning, compliance posture documented in DISCLAIMER.md (paper-trading, self-hosted personal use; no BaFin licence held), and CI/CD policies are strictly maintained inside the `docs/` directory.

👉 **[Access the full Documentation Hub here](docs/index.md)** 👈

For autonomous agents and LLMs, a machine-readable index is provided at `docs/llms.txt`.

---

## ⚡ Quick Start (Developer Onboarding)

### 🐳 Unified Dev Environment (VS Code) — Recommended ⭐

The easiest way for a consistent environment (frontend + backend) is using **VS Code DevContainers**:

1. Install the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension in VS Code.
2. Open the project and click "Reopen in Container" (bottom left or via Command Palette).
3. VS Code builds the Docker image and automatically installs all dependencies (Node.js, Python 3.12, PyTorch CPU, Pre-Commit).

This ensures all tools and libraries are correctly configured, independent of your local operating system.

### 🚀 Community Edition (1-Click Local Stack) — NEW

The fastest way to spin up the entire application (Frontend, Public API, Engine, Postgres DB, Redis) locally without needing Google Cloud connectivity or Firebase Auth.

```bash
# 1. Download the Community Baseline Models (Bypasses GCP Storage)
bash scripts/setup_oss_models.sh

# 2. Start the entire Air-Gapped Stack:
docker compose -f docker-compose.oss.yml up -d
```
> **Note on Images:** The `docker-compose.oss.yml` automatically pulls pre-built Docker images from our GitHub Container Registry (GHCR). You do not need to build them locally unless you are making code changes!

→ **BORA Control Center available at:** `http://localhost` 
(The API operates silently on port 8001 and 8081).

> **Note:** You do not need to configure API keys in the `.env` file for the OSS container. You can securely enter your Alpaca API & Secret Keys directly within the Control Center UI. The keys are encrypted and stored safely in your local PostgreSQL database.

### 🖥️ Local Development (Manual)

**Backend (in `AI Trading Bot/`):**
```bash
cd "AI Trading Bot"
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # Linux/Mac

# PyTorch CPU build first (avoids ~4 GB CUDA download)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
pip install ./pandas-ta

cp .env.example .env
# Edit .env with your keys: ALPACA_API_KEY, GEMINI_API_KEY, etc.

python main.py
```
→ Engine running at `http://localhost:8001`

**Code Quality (Pre-Commit Hooks — Mandatory!):**
Before you can commit code, you must activate the local hooks. They automatically check styles (Black, Flake8) and security (Bandit):
```bash
# Run in the project root
pip install pre-commit
pre-commit install
```

**Frontend (in the project root):**
```bash
npm install
npm run dev
```
→ Dashboard at `http://localhost:8082` · Proxied via Vite to port 8001

---

## 🖥️ GPU Development Machine Setup

For local training with GPU acceleration (e.g. LSTM / RL on a separate machine):

### Windows Base Setup
```powershell
winget install Git.Git Python.Python.3.12 OpenJS.NodeJS.LTS GitHub.cli
pip install uv pre-commit
gcloud auth login
gcloud auth application-default login
gcloud config set project aaagents-oss
```

### Install GPU PyTorch First
Check your CUDA version: `nvidia-smi`
```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

### Python Dependencies
```powershell
cd "AI Trading Bot"
python -m venv .venv && .\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt --index-strategy unsafe-best-match
uv pip install -r requirements-train.txt
```

### AI Agent Tools (Antigravity + Claude Code)
```powershell
# Claude Code CLI (Claude Pro account — browser auth on first run)
irm https://claude.ai/install.ps1 | iex

# Or via npm:
npm install -g @anthropic-ai/claude-code

# Start Claude Code in the repo root (auto-loads CLAUDE.md)
cd "C:\Users\<USER>\Documents\GitHub\Dev-Enviroment"
claude
```

> [!NOTE]
> `CLAUDE.md` in the repo root is Claude Code's project config file and is loaded automatically. It contains the two-agent workflow, critical rules, and navigation pointers.

> [!WARNING]
> The current `requirements.txt` contains `torch+cpu`. On the GPU machine **always** manually install the CUDA build first, then execute the requirements install.

---

## ☁️ Production Output (Cloud Run — Live)

The platform is deployed globally on GCP Cloud Run (`europe-west3`).

### Environments
- **Backend API (`aaa-backend`)**: `https://aaa-backend-lwkxsmb7dq-ey.a.run.app` (OIDC-protected internal layer)
- **Public Console API (`aaa-api-public`)**: `https://aaa-api-public-lwkxsmb7dq-ey.a.run.app` (Firebase Auth protected)
- **Public Website**: `https://aaagents.de` (Firebase Hosting)
- **Operative Dashboard**: `https://console.aaagents.de` (Firebase Auth required)

---

## ✅ Definition of Done (DoD) & Policies

All pull requests must pass the automated CI gates and adhere to the strict platforms compliance policies.

- **Definition of Done:** See `.github/PULL_REQUEST_TEMPLATE.md`
- **Coding Policy & Standards:** See `docs/5_engineering_and_devops/CODING_POLICY.md`
- **CI/CD Architecture:** See `docs/5_engineering_and_devops/DEVOPS-CICD.md`

### Running Local Integration Checks
```bash
cd "AI Trading Bot"
pytest tests/unit/ -v              # Fast unit tests
pytest tests/integration/ -v       # Infrastructure tests
pytest tests/integration/test_engine_boot.py -v # Platform hardening boot test
```

### 👤 Alpaca User Account Mapping (Onboarding)
For onboarding new users to the platform (1:1 Broker Mapping), please refer to the Admin Runbooks inside the documentation hub.

---

## 💬 Community & Support

Got questions, want to share a custom strategy, or need help setting up your local BORA container?
👉 **[Join our GitHub Discussions!](https://github.com/aaagents/Dev-Enviroment/discussions)**

For bugs and feature requests, please use the [Issue Tracker](https://github.com/aaagents/Dev-Enviroment/issues).
