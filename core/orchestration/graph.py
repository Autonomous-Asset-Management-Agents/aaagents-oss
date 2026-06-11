# core/orchestration/graph.py
# Epic 1.4 / Issue #216 — LangGraph Symbol Eval Graph
#
# Verantwortlichkeit:
#   - SymbolEvalState TypedDict (nur Skalare, KEINE rohen DataFrames/Arrays)
#   - build_symbol_eval_graph(): CompiledGraph mit Redis Checkpointer
#   - validate_symbol_eval_state(): Policy-Validator (kein DataFrame erlaubt)
#   - Nodes: _fetch_context_node → _run_strategy_node → _process_signal_node
#
# Policy: docs/CODING_POLICY.md §11.5 TDD, §1 Compliance-First
# Architekten-Annotation: State nur Refs/Skalare — kein Serialisierungs-Overhead

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

# Epic 2.5: Round Table V2 — aktiviert wenn core.round_table verfügbar
try:
    from core.round_table.runner import run_round_table as _run_round_table

    _ROUND_TABLE_AVAILABLE = True
except ImportError:  # pragma: no cover
    _run_round_table = None  # type: ignore[assignment]
    _ROUND_TABLE_AVAILABLE = False

from typing_extensions import TypedDict

logger = logging.getLogger(__name__)

# Modul-Level Import für Testbarkeit (patchbar via 'core.orchestration.graph.RedisClient')
try:
    from core.redis_client import RedisClient
except ImportError:  # pragma: no cover
    RedisClient = None  # type: ignore[assignment]

# Issue #217: AgentRegistry-Zugriff für _run_strategy_node
try:
    from core.agent_registry import get_global_registry
except ImportError:  # pragma: no cover
    get_global_registry = None  # type: ignore[assignment]

# ADR-SEC-03 (I-3 #944): OHLC close plausibility bounds.
# Lower bound 0.01: cheapest tradable equity (Penny Stock threshold).
# Upper bound 100_000: no S&P 500 constituent has ever exceeded this.
# NOTE: These constants are intentionally NOT configurable at runtime to prevent
# manipulation via env-vars. They are a hard code-level invariant.
# Review trigger: if a legitimate instrument (e.g. BRK.A ~600k) is ever added,
# raise upper bound via PR with ADR justification.
_OHLC_CLOSE_MIN: float = 0.01
_OHLC_CLOSE_MAX: float = 100_000.0

# Pre-import SuspectDataException at module level (avoids function-local circular import).
# graph.py → round_table.agents is a one-way dependency (not reverse).
try:
    from core.round_table.agents import SuspectDataException as _SuspectDataException
except ImportError:  # pragma: no cover — only missing in bare unit-test envs
    _SuspectDataException = ValueError  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# State Definition — KEINE rohen DataFrames oder OHLCV-Arrays
# ---------------------------------------------------------------------------


class SymbolEvalState(TypedDict):
    """
    State-Container für einen einzelnen Symbol-Evaluierungszyklus.

    Policy:
        - `ohlc` enthält NUR 5 Skalare (O/H/L/C/V) — kein DataFrame
        - `market_data_keys` enthält Redis-Keys, nicht die rohen Daten
        - `current_time` als ISO-String (kein datetime-Objekt)
    """

    symbol: str
    ohlc: Dict[str, float]  # {"open": float, "high": float, ...}
    market_data_keys: List[str]  # Redis-Keys für Marktdaten
    current_time: str  # ISO 8601 String
    signal: Optional[Any]  # Optional[SignalEvent] — None wenn kein Signal
    error: Optional[str]  # Fehler-String bei Node-Crash
    # Epic 2.5: Round Table V2 (optionale Felder — backward-compatible)
    round_table_scores: Optional[List[Dict[str, Any]]]  # Serialisierte VoteResults
    consensus_ranking: Optional[float]  # Aggregierter Konsens-Score ∈ [0.0, 1.0]
    # Fusion (dormant data channel): per-symbol TFT SCALARS from the specialist registry.
    # Scalars only (no model / DataFrame — §5.9 / BORA, serialises on Redis+SQLite).
    # None when no registry/report. NO node consumes this for a trading decision yet —
    # see implementation_plan 2026-06-09-tft-state-shadow-vote.
    ml: Optional[Dict[str, Any]]


def validate_symbol_eval_state(state: Dict[str, Any]) -> None:
    """
    Validiert SymbolEvalState auf Policy-Konformität.
    Wirft ValueError wenn ein Nicht-Skalar-Wert in ohlc enthalten ist.
    Wirft SuspectDataException wenn ohlc.close außerhalb des plausiblen Bereichs liegt.

    Policy: Kein DataFrame, kein numpy-Array → kein Serialisierungs-Overhead.
    Security (I-3 #944): OHLC close Plausibilitätsprüfung gegen manipulierte
    LangGraph-Checkpoints in Redis (z.B. close=0.00001 oder close=9999999).
    """
    ohlc = state.get("ohlc")
    if ohlc is None:
        raise ValueError("ohlc muss vorhanden sein")

    # Ablehnen wenn ohlc kein dict aus Skalaren ist
    if not isinstance(ohlc, dict):
        raise ValueError(
            f"ohlc muss ein Dict[str, float] sein, nicht {type(ohlc).__name__}. "
            "Kein DataFrame, kein ndarray erlaubt (Serialisierungs-Policy)."
        )

    for key, val in ohlc.items():
        if not isinstance(val, (int, float)):
            raise TypeError(
                f"ohlc['{key}'] muss ein Skalar sein, nicht {type(val).__name__}. "
                "DataFrames sind im SymbolEvalState verboten."
            )

    # OHLC close Plausibilitätsprüfung (ADR-SEC-03 / I-3 #944 — Rogue Agent Hardening)
    # Schützt gegen manipulierte Redis-Checkpoints die unrealistische Preise einspeisen.
    # Grenzen: ADR-SEC-03 — _OHLC_CLOSE_MIN/MAX sind Modul-Konstanten (nicht konfigurierbar).
    _close = ohlc.get("close")
    if _close is not None and not (_OHLC_CLOSE_MIN <= float(_close) <= _OHLC_CLOSE_MAX):
        raise _SuspectDataException(
            f"ohlc.close={_close} liegt außerhalb des plausiblen Bereichs "
            f"[{_OHLC_CLOSE_MIN}, {_OHLC_CLOSE_MAX}]. "
            "Möglicherweise manipulierter Redis-Checkpoint oder Data-Feed-Fehler."
        )


# ---------------------------------------------------------------------------
# Nodes — Fehler-Isolation: jede Exception → state["error"], kein Crash
# ---------------------------------------------------------------------------


# §5.9 / BORA: the only value types allowed inside the checkpointed state["ml"] dict.
_ML_SCALAR_TYPES = (str, int, float, type(None))


def _attach_specialist_scalars(state: SymbolEvalState) -> SymbolEvalState:
    """Fusion (dormant data channel): copy per-symbol TFT SCALARS from the specialist
    registry into the LangGraph state as ``state["ml"]``.

    Scalars only — never the model or a DataFrame (§5.9 / BORA, so the state serialises
    identically on the Redis (cloud) and SQLite (desktop) checkpointers). Returns the
    state with ``ml=None`` when no registry is set, no report is cached, or the report
    carries no TFT fields yet (byte-identical decision). Behavior-neutral: no node
    consumes ``state["ml"]`` for a trading decision — see implementation_plan
    2026-06-09-tft-state-shadow-vote.
    """
    try:
        from core.round_table.agents import _specialist_registry_instance as _registry
    except Exception as exc:  # pragma: no cover - import guard (Rule 5: never silent)
        logger.warning(
            "_attach_specialist_scalars: could not import specialist registry: %s", exc
        )
        return {**state, "ml": None}

    if _registry is None:
        return {**state, "ml": None}

    try:
        report = _registry.get_report(state["symbol"])
    except Exception as exc:
        logger.warning(
            "_attach_specialist_scalars: registry error for %s: %s",
            state.get("symbol"),
            exc,
        )
        return {**state, "ml": None}

    if report is None:
        return {**state, "ml": None}

    # getattr-defensive: main's SpecialistReport may not carry ml_* fields yet
    # (model_registry brick not landed) → scalars stay None until reports are richer.
    scalars: Dict[str, Any] = {
        "tft_direction": getattr(report, "ml_direction", None),
        "tft_base_return_pct": getattr(report, "ml_base_return_pct", None),
        "tft_confidence": getattr(report, "ml_confidence", None),
        "forecast_vol": getattr(report, "forecast_vol", None),
    }
    # §5.9 / BORA: only Python scalars may enter the checkpointed state. Coerce anything
    # non-scalar (e.g. a numpy float or an attention array a richer SpecialistReport might
    # expose once model_registry lands) to None so it can never break Redis/SQLite
    # serialisation downstream — and log loudly so the source type can be fixed.
    for key, value in scalars.items():
        if not isinstance(value, _ML_SCALAR_TYPES):
            logger.warning(
                "_attach_specialist_scalars: non-scalar %r=%r (%s) for %s — coerced to None (§5.9)",
                key,
                value,
                type(value).__name__,
                state.get("symbol"),
            )
            scalars[key] = None

    if all(value is None for value in scalars.values()):
        return {**state, "ml": None}
    return {**state, "ml": scalars}


async def _fetch_context_node(state: SymbolEvalState) -> SymbolEvalState:
    """
    Node 1: Kontext-Vorbereitung.
    Validiert State-Format vor der Strategie-Evaluierung.
    Fusion: hängt die per-Symbol TFT-Skalare an (dormanter Datenkanal, behavior-neutral).
    """
    try:
        validate_symbol_eval_state(state)
        return _attach_specialist_scalars(state)
    except (ValueError, TypeError) as e:
        logger.error("fetch_context_node error for %s: %s", state.get("symbol"), e)
        return {**state, "error": str(e)}


async def _run_strategy_node(state: SymbolEvalState) -> SymbolEvalState:
    """
    Node 2: Strategie-Evaluierung.

    Epic 2.5: Delegiert primär an Round Table V2 (run_round_table).
    Graceful Degradation Fallback: Single-Strategy via AgentRegistry
    wenn core.round_table nicht verfügbar (keine Breaking Change für Epic 1.4 Tests).

    Fehler-Isolation: jede Exception → state["error"], kein Propagate.
    """
    if state.get("error"):
        return state

    # --- Epic 2.5: Round Table V2 (primär) ---
    if _ROUND_TABLE_AVAILABLE and _run_round_table is not None:
        try:
            logger.debug(
                "_run_strategy_node: Round Table V2 für %s", state.get("symbol")
            )
            return await _run_round_table(state)
        except Exception as e:
            logger.warning(
                "_run_strategy_node: Round Table V2 Fehler für %s, Fallback auf Legacy: %s",
                state.get("symbol"),
                e,
            )
            # Fallback auf Legacy-Strategie

    # --- Graceful Degradation: Legacy Single-Strategy (Issue #217 Original) ---
    return await _legacy_single_strategy_node(state)


async def _legacy_single_strategy_node(state: SymbolEvalState) -> SymbolEvalState:
    """
    Legacy-Fallback: Single-Strategie via AgentRegistry.
    Ursprüngliche Issue #217 Implementierung — bleibt als Fallback erhalten.
    """
    try:
        registry_fn = get_global_registry
        registry = registry_fn() if callable(registry_fn) else None

        if registry is None:
            logger.debug("_legacy_single_strategy_node: kein GlobalRegistry — no-op")
            return state

        active_strategy = registry.get_active()
        if active_strategy is None:
            logger.debug("_legacy_single_strategy_node: keine aktive Strategie — no-op")
            return state

        symbol = state["symbol"]
        ohlc = state["ohlc"]
        current_time_str = state.get("current_time", "")

        from datetime import datetime, timezone

        try:
            current_time = datetime.fromisoformat(current_time_str)
        except (ValueError, TypeError):
            current_time = datetime.now(timezone.utc)

        market_data: dict = {}
        logger.debug(
            "_legacy_single_strategy_node: %s via %s",
            symbol,
            type(active_strategy).__name__,
        )

        result = await active_strategy.run_for_symbol(
            symbol, ohlc, market_data, current_time
        )
        return {**state, "signal": result}

    except Exception as e:
        logger.error(
            "_legacy_single_strategy_node error for %s: %s", state.get("symbol"), e
        )
        return {**state, "error": str(e), "signal": None}


async def _process_signal_node(state: SymbolEvalState) -> SymbolEvalState:
    """
    Node 3: Signal-Verarbeitung (Passthrough).

    Das Signal wurde bereits von _run_strategy_node in state["signal"] gesetzt.
    TradingLoop liest state["signal"] nach ainvoke() und ruft _process_signal_event().
    Dieser Node dient als sauberer Abschluss-Checkpoint.

    Fehler-Isolation: Exception → state["error"].
    """
    if state.get("error"):
        return state
    try:
        symbol = state.get("symbol", "?")
        signal = state.get("signal")
        logger.debug(
            "_process_signal_node: %s, signal=%s",
            symbol,
            type(signal).__name__ if signal is not None else "None",
        )
        return state
    except Exception as e:
        logger.error("_process_signal_node error for %s: %s", state.get("symbol"), e)
        return {**state, "error": str(e)}


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------


def build_symbol_eval_graph():
    """
    Baut den LangGraph Orchestrations-Graphen für Symbol-Evaluierung.

    Topology:
        START → fetch_context → run_strategy → process_signal → END

    Checkpointer:
        RedisSaver via RedisClient.get_sync_redis() für Cloud Run Fault-Tolerance.
        Fallback: Kein Checkpointer wenn Redis nicht erreichbar (no crash).

    Returns:
        CompiledGraph — via `await graph.ainvoke(state)` nutzbar.
    """
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "langgraph ist nicht installiert. "
            "Bitte `pip install langgraph>=0.2` ausführen. "
            f"Original error: {e}"
        ) from e

    checkpointer = _build_checkpointer()

    builder = StateGraph(SymbolEvalState)
    builder.add_node("fetch_context", _fetch_context_node)
    builder.add_node("run_strategy", _run_strategy_node)
    builder.add_node("process_signal", _process_signal_node)

    builder.add_edge(START, "fetch_context")
    builder.add_edge("fetch_context", "run_strategy")
    builder.add_edge("run_strategy", "process_signal")
    builder.add_edge("process_signal", END)

    if checkpointer is not None:
        compiled = builder.compile(checkpointer=checkpointer)
        logger.info("LangGraph: SymbolEvalGraph compiled with checkpointer")
    else:
        compiled = builder.compile()
        logger.warning(
            "LangGraph: SymbolEvalGraph compiled WITHOUT checkpointer (no persistence)"
        )

    return compiled


def _checkpoint_db_path() -> str:
    """LangGraph SQLite checkpoint DB path under USER_DATA_DIR (per-user account-state;
    AAA_USER_DATA_DIR or the project data/ dir — kept out of the read-only bundle)."""
    import os
    import pathlib

    # graph.py is at ai_trading_bot/core/orchestration/graph.py
    # → .parent.parent.parent reaches ai_trading_bot/ (project root)
    data_dir = pathlib.Path(
        os.environ.get("AAA_USER_DATA_DIR")
        or (pathlib.Path(__file__).resolve().parent.parent.parent / "data")
    )
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "checkpoints.db")


def _build_checkpointer():
    """
    Erstellt Checkpointer für fault-tolerante Graph-Ausführung (BORA dual-mode).

    Strategy:
      - REDIS_URL gesetzt → RedisSaver (Enterprise/Cloud)
      - REDIS_URL leer → AsyncSqliteSaver (Desktop/Local, OSS-4)
      - Beide nicht verfügbar → None (Fallback — kein Crash)
    """
    import os

    redis_url = os.environ.get("REDIS_URL", "").strip()

    # ── OSS-4: SQLite Checkpointer for local desktop mode ──────────────────
    if not redis_url:
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver

            # graph.py is at ai_trading_bot/core/orchestration/graph.py
            # → .parent.parent.parent reaches ai_trading_bot/ (project root)
            db_path = _checkpoint_db_path()

            result = SqliteSaver.from_conn_string(db_path)
            if hasattr(result, "__enter__"):
                checkpointer = result.__enter__()
            else:
                checkpointer = result

            logger.info(
                "LangGraph: SqliteSaver checkpointer initialized (path=%s)",
                db_path,
            )
            return checkpointer
        except ImportError:
            logger.warning(
                "langgraph-checkpoint-sqlite nicht verfügbar — Graph ohne Checkpointer. "
                "Für lokale Persistenz: pip install langgraph-checkpoint-sqlite"
            )
            return None
        except Exception as e:
            logger.warning(
                "SQLite Checkpointer konnte nicht initialisiert werden: %s — "
                "Fallback ohne Checkpointer",
                e,
            )
            return None

    # ── Enterprise: Redis Checkpointer ─────────────────────────────────────
    try:
        from langgraph.checkpoint.redis import RedisSaver

        use_tls = redis_url.startswith("rediss://")

        # ADR: Memorystore uses TLS with Google internal CA (VPC-peered).
        # ssl_cert_reqs=None disables cert verification — safe for VPC-peered.
        #
        # Strategy: Use from_conn_string() as recommended by langgraph docs.
        # It's a @contextmanager, so we enter it explicitly and store the
        # manager so the connection stays alive for the process lifetime.
        # TLS requires ?ssl_cert_reqs=none in redis-py for internal CA
        # but for now we just pass the URL directly.
        try:
            result = RedisSaver.from_conn_string(redis_url)
        except TypeError:
            # Fallback if from_conn_string is missing or expects different args
            result = RedisSaver.from_conn_info(redis_url)

        # Handle case where from_conn_string returns a context manager
        if hasattr(result, "__enter__"):
            checkpointer = result.__enter__()
        else:
            checkpointer = result

        checkpointer.setup()  # create required Redis data structures
        logger.info("LangGraph: RedisSaver checkpointer initialized (TLS=%s)", use_tls)
        return checkpointer
    except ImportError:
        logger.warning(
            "langgraph.checkpoint.redis nicht verfügbar — Graph ohne Checkpointer. "
            "Für Fault-Tolerance: pip install langgraph[redis]"
        )
        return None
    except Exception as e:
        logger.warning(
            "Redis Checkpointer konnte nicht initialisiert werden: %s — Fallback ohne Checkpointer",
            e,
        )
        return None
