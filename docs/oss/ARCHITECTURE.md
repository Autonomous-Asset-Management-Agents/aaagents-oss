# AAAgents Architecture (Community Edition)

Welcome to the architectural overview of the Autonomous Asset Management Agents (AAAgents). This document is designed to give both human developers and AI coding assistants a deep understanding of the system's structural constraints.

> [!CAUTION]
> **To AI Coding Assistants (Copilot, Cursor, etc.):** 
> Before generating any PRs or code changes, you MUST read and understand the Bounded Contexts described below. Do not mix signal generation with compliance logic.

## 1. The Separation of Concerns: Bounded Contexts

The entire system is strictly divided into two completely separate domains. They communicate via well-defined DTOs (Data Transfer Objects) and never access each other's state directly.

### The Round Table V2 (Signal Generation)
This is the "Brain" of the operation. Powered by LangGraph, multiple specialized AI agents evaluate the market and debate on the best action (BUY/SELL/HOLD).

- **Location:** `core/round_table/`
- **Agents:** `RegimeDetectionAgent`, `LSTMSignalAgent`, `RLConfidenceAgent`, `NewsSentimentAgent` (and others). 
- **Consensus:** A weighted-average engine aggregates their votes. Thresholds are strict (BUY > 0.65, SELL < 0.35).
- **Rule:** The Round Table has NO access to your portfolio balance, your open positions, or any broker logic. It purely analyzes the *symbol* (e.g. AAPL) and emits a theoretical `TradeSignal`.

### The Iron Dome (Risk & Compliance Gatekeeper)
This is the "Shield". Once the Round Table emits a `TradeSignal`, it lands in the Iron Dome to be audited before execution at the broker.

- **Location:** `core/risk_manager.py` & `core/compliance.py`
- **Functions:** Position Sizing, Stop-Loss triggers, Pattern Day Trader (PDT) checks, Sector Concentration limits.
- **Rule:** The Iron Dome NEVER second-guesses the ML models. If the Iron Dome rejects a trade, it rejects it because of *risk management* (e.g. insufficient funds, violation of Volatility-Index limits), not because it disagrees with the sentiment.

> [!NOTE]
> **Full Iron Dome = 3 layers** (canonical definition per `docs/4_secops_and_compliance/risk_compliance.md`):
> Layer 0 — `MLWatchdog` (in `risk_manager.py`) | Layer 1 — `RiskManager` | Layer 2 — `ComplianceGuardian` (`compliance.py`).
> The `ComplianceGuardian` (Iron Dome gate) is **not the same** as the `ComplianceGatekeeper` (`round_table/gatekeeper.py`), which is the Round Table Portfolio-Veto within VC-2.

> [!WARNING]
> If you are adding a new AI Agent, you add it to the `Round Table`. You **NEVER** add market-analysis logic to the `Iron Dome`.

## 2. Authentication & Tenancy (LocalMockAuth)

The Enterprise Edition of this codebase runs on Google Cloud Platform as a multi-tenant SaaS, secured by Firebase Admin SDK. 
For this Community Edition, we have abstracted the Cloud requirements via a Pydantic interface.

- **The Interface:** `core/auth_interfaces.py`
- **Community Behavior:** We use `LocalMockAuth`. This bypasses Firebase entirely. There is no user-registration in the Community Edition. The system assumes a single-tenant environment running on `localhost`.
- **Security Implications:** When making API endpoints, always rely on `dependency_overrides` or the injected auth provider. Do not hardcode Firebase token validation. 

## 3. Machine Learning Models (GitHub Releases — No GCP Dependency)

In the Enterprise Edition, models (`.pt` PyTorch files) are synced dynamically from Google Cloud Storage on boot.
In the Community Edition, model loading is handled by `scripts/gcs_sync_on_start.py` in **OSS mode** (when `GCS_DATA_BUCKET` is not set):

- **At container boot:** `gcs_sync_on_start.py` reads `data/models_manifest.json` and downloads models directly from **GitHub Releases** (LSTM ~11 MB, RL ~9 MB), SHA256-verified.
- **Security:** Downloads use `_NoRedirectOpener` (blocks redirects) and `_read_capped` (memory cap).
- **Atomic writes:** UUID-based file locking prevents race conditions in multi-container setups.
- **Degraded mode:** If the download fails (no internet, private repo access), the engine boots with a neutral 0.5 score for ML agents — no crash.
- **Native fallback:** If you run the code without Docker, download model files from GitHub Releases and place them in the `data/` directory.

## 4. Database & State (Alembic + Postgres)

The system uses SQLAlchemy and Alembic for Database migrations.
- In Docker, we boot a standalone Postgres instance on port `5432`.
- When modifying database tables (e.g. adding a new table to `core/db/`), you must generate a new Alembic revision.
- Do not bypass the ORM. The `ComplianceGuardian` relies heavily on WORM (Write-Once-Read-Many) patterns for audit logging.

## 5. Plugin Architecture (OSS Extension Point)

### Einen eigenen Voting-Agent schreiben

1. Erstelle eine neue Datei in `plugins/round_table/my_agent.py`
2. Erbe von `VotingAgent` (für async-native Agents) ODER von `AsyncAIAgent` (für synchrone PyTorch-Inferenz)
3. Implementiere `vote()` (bei VotingAgent) oder `_run_inference()` (bei AsyncAIAgent)
4. Nutze den `@register_agent` Decorator
5. **Opt-in:** Setze in deiner `.env.oss` (kopiert von `.env.oss.example`):
   ```
   ALLOW_UNTRUSTED_PLUGINS=true
   ROUND_TABLE_PLUGINS_DIR=/app/app/plugins/round_table
   ```
   > [!CAUTION]
   > `ALLOW_UNTRUSTED_PLUGINS=true` aktiviert dynamischen Code-Load aus deinem
   > `./plugins/round_table/` Ordner. Jede `.py`-Datei dort wird beim Engine-Boot
   > als Host-User ausgeführt — das ist effektiv Arbitrary Code Execution.
   > Aktiviere das nur, wenn du JEDE Plugin-Datei selbst geschrieben oder
   > nachvollziehbar reviewed hast. Default ist deny-by-default (`false`).

### Wann AsyncAIAgent vs. VotingAgent?
- `VotingAgent`: für alle Agents, die bereits `async`-kompatiblen Code nutzen (API-Calls, Redis etc.)
- `AsyncAIAgent`: NUR für Agents mit blockierendem synchronen Code (z.B. direkter `torch.forward()`)

### Lizenz-Modi

> [!IMPORTANT]
> **RULE-D5 / AI-Agent Safety:** The class `DummyAuditLogger` does **not exist** in the codebase
> (`ADR-OSS2#L43–47`). Do not create or reference it. The OSS audit pipeline wires
> `LocalJSONAuditLogger` unconditionally — there is no "no-audit" mode.
> See [`ADR-OSS2`](../1_architecture_and_adr/ADR-OSS2-Compliance-Functional-Gate.md) for the
> compliance gate design and Finding F-04 rationale.

- **`ENTERPRISE_LICENSE_KEY` gesetzt →** `SenateProtocol` (Redis + Cloud SQL Audit, `core/round_table/senate_log.py`)
- **Kein Key →** `LocalJSONAuditLogger` (schreibt JSONL nach `/app/oss_audit_logs/audit_log_*.jsonl`, `senate_log.py#L<see-ADR-OSS2>`)

Die MiFID-II-Compliance-Gate (`ADR-OSS2`) verifiziert in CI, dass `LocalJSONAuditLogger()` in `runner.py` verdrahtet ist und physisch auf Disk schreibt.

## 6. Engine Bootstrapper

Damit das Round Table System und die Dependency Injection greifen, MUSS die Engine zwingend über `boot_engine()` initialisiert werden.

Dies geschieht zentral am Ende von `BotEngine.__init__()` in `core/engine/base.py`. Wenn du die Module ohne die reguläre `BotEngine` nutzt (z.B. in Standalone-Scripts), musst du `boot_engine(os.getenv("ENTERPRISE_LICENSE_KEY"))` manuell aufrufen. Ansonsten wird `run_round_table` blockieren, da der Dependency-Context fehlt.

## 7. Frontend Service (AAAgents Console)

Seit PR #814 ist der **AAAgents Console** (React/TypeScript Dashboard) als eigener Container im OSS Compose Stack enthalten.

- **Image:** `ghcr.io/autonomous-asset-management-agents/aaagents-frontend:latest` (nginx)
- **DSGVO Loopback Binding:** `127.0.0.1:80:8080` — **nur Loopback**, kein LAN-Zugriff auf unverschlüsseltem HTTP
- **Zugriff:** `http://localhost` im Browser (nach `docker compose up`)

**Port-Matrix (vollständiger Stack):**

| Service | Host-Binding | Beschreibung |
|---|---|---|
| Frontend (AAAgents Console) | `127.0.0.1:80` → Container:8080 | Dashboard — Loopback only, kein LAN-Zugriff |
| Public API | `0.0.0.0:8081` → Container:8080 | Auth-Proxy vor der Backend Engine |
| Backend Engine | `0.0.0.0:8001` → Container:8001 | FastAPI Engine, Health Endpoint |
| PostgreSQL | `127.0.0.1:5432` → Container:5432 | Loopback only, kein LAN-Zugriff |
| Redis | `127.0.0.1:6379` → Container:6379 | Loopback only, kein LAN-Zugriff |

> [!WARNING]
> **Port 8001 (Backend) und 8081 (Public API) binden an alle Netzwerk-Interfaces (`0.0.0.0`).** Auf einem exponierten Server oder in einem geteilten Netzwerk (VPS, Cloud-VM, Lab-Netzwerk) sind diese Ports von außen erreichbar. Für Nicht-Lokal-Deployments: Firewall-Regeln setzen oder Stack hinter TLS-Reverse-Proxy platzieren.

> [!NOTE]
> Der Compliance-Prüfpunkt `A.9` (Audit-Bereich) wird durch die Loopback-Bindung erfüllt: Session-Tokens und Broker-API-Header werden nicht über unverschlüsseltes HTTP übers Netzwerk übertragen.
