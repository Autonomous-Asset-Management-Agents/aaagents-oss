/**
 * ai_trading_bot Engine API client.
 * Base URL: http://localhost:8001 (engine must be running).
 * Override with ?engine_port=8002 in the page URL if the engine started on another port.
 * In public view-only mode (e.g. aaagents.de), uses VITE_PUBLIC_API_URL when set.
 */

import { isPublicViewOnly, getPublicApiBase } from "./publicMode";
import { auth } from "./firebase";

const DEFAULT_ENGINE_PORT = 8001;

/** Default port for the read-only public API proxy when testing public build locally. */
const PUBLIC_PROXY_LOCAL_PORT = 8002;

/** Default public API URL for aaagents.de (Cloudflare Tunnel to local engine). */
const DEFAULT_PUBLIC_API_URL = "https://api.aaagents.de";

/** Resolve engine base URL: public API when in public mode; on localhost use local proxy so portfolio data loads. */
export function getApiBase(): string {
  if (typeof window === "undefined") return `http://localhost:${DEFAULT_ENGINE_PORT}`;
  if (isPublicViewOnly()) {
    const host = window.location.hostname.toLowerCase();
    const isLocal = host === "localhost" || host === "127.0.0.1";
    // On localhost (testing public build), use local proxy so current holdings etc. are shown
    if (isLocal) return `http://localhost:${PUBLIC_PROXY_LOCAL_PORT}`;
    // Use configured public API URL, or default to api.aaagents.de
    const publicUrl = getPublicApiBase();
    return publicUrl || DEFAULT_PUBLIC_API_URL;
  }
  const params = new URLSearchParams(window.location.search);
  const port = params.get("engine_port");
  if (port) return `http://localhost:${port}`;

  // Use explicit VITE_API_BASE_URL if provided (e.g. localhost:8081 build)
  const configuredUrl = import.meta.env?.VITE_API_BASE_URL;
  if (configuredUrl && typeof configuredUrl === "string" && configuredUrl.trim()) {
    return configuredUrl.trim().replace(/\/$/, "");
  }

  // Fallback for production console — use direct Cloud Run URL
  // (api.aaagents.de will be the primary once Cloudflare is configured)
  if (window.location.host === "localhost:8081") {
    const url = "https://aaa-api-public-lwkxsmb7dq-ey.a.run.app";
    console.log("[API] Production Console Mode Detected. Base URL:", url);
    return url;
  }

  // Option B: Wenn wir im Vite Dev Server laufen (import.meta.env.DEV),
  // nutzen wir IMMER den relativen Pfad ("/api"), unabhängig von der IP/Hostname.
  // Das erlaubt LAN-Zugriffe (z.B. 192.168.x.x:8082) via Vite Proxy ohne CORS-Probleme.
  // Option B: Wenn wir im Vite Dev Server laufen (import.meta.env.DEV) ODER im
  // Docker-Container (wo Nginx /api auflöst), nutzen wir IMMER den relativen Pfad ("/api").
  // Das erlaubt LAN-Zugriffe ohne CORS-Probleme und leitet den Traffic durch den Auth-Proxy.
  return "/api";
}

export const API_BASE = getApiBase();
console.log("[API] API_BASE initialized as:", API_BASE);

export interface Position {
  symbol: string;
  qty: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  total_score?: number;
  momentum_score?: number;
  conviction_score?: number;
  days_held?: number;
}

export interface PortfolioSummaryResponse {
  status: "success" | "error";
  summary?: string | null;
  message?: string;
  positions?: Position[];
  equity?: number;
  last_equity?: number;
  recent_debates?: unknown[];
  rebalance_recommendations?: unknown[];
  agent_statuses?: {
    name: string;
    agent_name: string;
    score: number;
    weight: number;
    reasoning: string;
    vetoed: boolean;
    signal: "BUY" | "SELL" | "HOLD" | string;
  }[];
  total_unrealized_pnl?: number;
}

/** News article from /recent-news */
export interface NewsArticle {
  title: string;
  ticker?: string;
  sentiment?: string;
  score?: number;
  published?: string;
  url?: string;
}

/** GET /recent-news response */
export interface RecentNewsResponse {
  status: string;
  articles: NewsArticle[];
}

export interface StrategyResponse {
  strategy: "RLAgent" | "LSTMDynamic";
}

/** Range for stock history: 1d | 1w | 1m | 1y | max */
export type StockHistoryRange = "1d" | "1w" | "1m" | "1y" | "max";

export interface StockHistoryPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface StockHistoryResponse {
  status: "success" | "error";
  symbol?: string;
  range?: string;
  data?: StockHistoryPoint[];
  message?: string;
  intraday?: boolean;
}

/** GET /stock-history?symbol=...&period=1d|1w|1m|1y|max */
export async function fetchStockHistory(
  symbol: string,
  period: StockHistoryRange = "1m"
): Promise<StockHistoryResponse> {
  try {
    const data = await fetchJson<StockHistoryResponse>(
      `/stock-history?symbol=${encodeURIComponent(symbol)}&period=${period}`
    );
    return data;
  } catch {
    return { status: "error", data: [] };
  }
}

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // Inject Firebase JWT if user is logged in
  if (auth.currentUser) {
    try {
      const token = await auth.currentUser.getIdToken();
      headers["Authorization"] = `Bearer ${token}`;
    } catch (error: unknown) {
      console.warn("Failed to get Firebase token:", error);
    }
  } else {
    // OSS Mode Fallback: LocalMockAuth strictly requires structurally valid Bearer tokens.
    // In Enterprise Mode, FirebaseAuth will cryptographically reject this dummy token (401),
    // which is gracefully handled by the UI as an "Offline" state without redirect loops.
    headers["Authorization"] = "Bearer oss-mode-bypass";
  }

  const res = await fetch(`${getApiBase()}${path}`, {
    ...options,
    headers: { ...headers, ...options?.headers },
  });
  return res.json() as Promise<T>;
}

/** GET /strategy - check if engine is running and get current strategy */
export async function fetchStrategy(): Promise<StrategyResponse | null> {
  try {
    const data = await fetchJson<StrategyResponse>("/strategy");
    return data;
  } catch {
    return null;
  }
}

/** GET /portfolio-summary - get portfolio and positions */
export async function fetchPortfolioSummary(): Promise<PortfolioSummaryResponse | null> {
  try {
    const data = await fetchJson<PortfolioSummaryResponse>("/portfolio-summary");
    return data;
  } catch {
    return null;
  }
}

/** POST /start-live */
export async function startLive(): Promise<{ status: string }> {
  return fetchJson("/start-live", { method: "POST" });
}

/** POST /stop */
export async function stop(): Promise<{ status: string }> {
  return fetchJson("/stop", { method: "POST" });
}

/** POST /panic-sell */
export async function panicSell(): Promise<{ status: string; message?: string }> {
  return fetchJson("/panic-sell", { method: "POST" });
}

/** POST /set-strategy */
export async function setStrategy(strategy: "RLAgent" | "LSTMDynamic"): Promise<{ status: string; strategy?: string; message?: string }> {
  return fetchJson("/set-strategy", {
    method: "POST",
    body: JSON.stringify({ strategy }),
  });
}

/** POST /run-simulation */
export async function runSimulation(params: {
  start_date: string;
  end_date: string;
  initial_capital: number;
  symbol_sample_mode: "full_market" | "sp500";
}): Promise<{ status: string; message?: string }> {
  return fetchJson("/run-simulation", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** POST /run-learning */
export async function runLearning(params: {
  start_date: string;
  end_date: string;
  initial_capital: number;
}): Promise<{ status: string; message?: string }> {
  return fetchJson("/run-learning", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** Benchmark equity curve point */
export interface BenchmarkEquityPoint {
  date: string;
  equity: number;
}

/** GET /benchmark-equity response */
export interface BenchmarkEquityResponse {
  points: BenchmarkEquityPoint[];
  spy_points: BenchmarkEquityPoint[];
  start_date?: string;
  end_date?: string;
  strategy?: string;
  initial_capital?: number;
  final_equity?: number;
  message?: string;
}

/** GET /benchmark-equity - portfolio vs S&P equity curves */
export async function fetchBenchmarkEquity(): Promise<BenchmarkEquityResponse> {
  try {
    return await fetchJson<BenchmarkEquityResponse>("/benchmark-equity");
  } catch {
    return { points: [], spy_points: [] };
  }
}

/** Trade from /recent-trades */
export interface RecentTrade {
  id: string;
  symbol: string;
  side: "buy" | "sell";
  qty: number;
  price: number;
  filled_at: string | null;
}

export interface RecentTradesResponse {
  status: string;
  trades: RecentTrade[];
  message?: string;
}

/** GET /recent-trades - last N filled orders from Alpaca */
export async function fetchRecentTrades(limit = 20): Promise<RecentTradesResponse> {
  try {
    return await fetchJson<RecentTradesResponse>(`/recent-trades?limit=${limit}`);
  } catch {
    return { status: "error", trades: [] };
  }
}

/** GET /recent-news - news articles for held symbols */
export async function fetchRecentNews(): Promise<RecentNewsResponse> {
  try {
    return await fetchJson<RecentNewsResponse>("/recent-news");
  } catch {
    return { status: "error", articles: [] };
  }
}

/** GET /auth/alpaca/login — DISABLED in OSS Edition (returns HTTP 400).
 * Kept for API surface compatibility. Do not call from UI components.
 * Enterprise edition uses GCP Secret Manager + Firebase OAuth instead.
 * @deprecated OSS: use ALPACA_API_KEY in .env.oss
 */
export async function getAlpacaAuthUrl(): Promise<{ auth_url?: string; error?: string }> {
  try {
    const res = await fetchJson<{ url?: string; detail?: string; error?: string }>("/auth/alpaca/login");

    // FastAPI returns HTTP errors in the 'detail' field
    if (res.detail) {
      return { error: res.detail };
    }
    if (res.error) {
      return { error: res.error };
    }
    if (!res.url) {
      return { error: "No authentication URL returned from the server." };
    }

    return { auth_url: res.url };
  } catch (error: unknown) {
    return { error: error instanceof Error ? error.message : "Failed to initiate login flow" };
  }
}

/** POST /settings/alpaca-keys — DISABLED in OSS Edition (returns HTTP 400).
 * Kept for API surface compatibility. Do not call from UI components.
 * Enterprise edition manages credentials via GCP Secret Manager.
 * @deprecated OSS: use ALPACA_API_KEY + ALPACA_SECRET_KEY in .env.oss
 */
export async function saveAlpacaKeys(api_key: string, secret_key: string): Promise<{ status: string; message?: string }> {
  try {
    return await fetchJson<{ status: string; message?: string }>("/settings/alpaca-keys", {
      method: "POST",
      body: JSON.stringify({ api_key, secret_key }),
    });
  } catch {
    return { status: "error", message: "Network error" };
  }
}

export interface RiskLimits {
  status: string;
  bot_status?: string;
  risk_limits?: {
    max_daily_drawdown_pct?: number;
    max_position_size_pct?: number;
  };
  message?: string;
}

export async function fetchRiskLimits(): Promise<RiskLimits | null> {
  try {
    return await fetchJson<RiskLimits>("/settings/risk-limits");
  } catch {
    return null;
  }
}

export async function updateRiskLimits(limits: Record<string, number>): Promise<{ status: string }> {
  try {
    return await fetchJson<{ status: string }>("/settings/risk-limits", {
      method: "POST",
      body: JSON.stringify({ risk_limits: limits }),
    });
  } catch {
    return { status: "error" };
  }
}

export async function updateBotStatus(status: "active" | "inactive"): Promise<{ status: string; bot_status?: string }> {
  try {
    return await fetchJson<{ status: string; bot_status: string }>("/bot/status", {
      method: "POST",
      body: JSON.stringify({ status }),
    });
  } catch {
    return { status: "error" };
  }
}
