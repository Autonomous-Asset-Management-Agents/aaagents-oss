import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Play, Square, AlertTriangle, Activity, CheckCircle, XCircle, Loader2, Save, RefreshCw, ShieldAlert, Power, Clock } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import {
  startLive, stop, panicSell,
  fetchStrategy, fetchRiskLimits, updateRiskLimits, updateBotStatus,
  fetchRecentTrades, RecentTrade, RiskLimits
} from "@/lib/api";
import { BrokerConnectionWidget } from "@/components/BrokerConnectionWidget";

const INITIAL_CAPITAL = 100000;

interface PositionData {
  symbol: string;
  qty: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

interface DashboardViewProps {
  equity?: number;
  lastEquity?: number;
  positions?: PositionData[];
  isConnected?: boolean;
}

const fmt = (v: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(v);

const AGENTS = [
  { name: "LSTM",   signal: "BUY"  },
  { name: "RL-PPO", signal: "BUY"  },
  { name: "GEMINI", signal: "HOLD" },
  { name: "RISK",   signal: "BUY"  },
  { name: "MACRO",  signal: "HOLD" },
  { name: "NEWS",   signal: "BUY"  },
  { name: "VIX",    signal: "SELL" },
  { name: "FLOW",   signal: "BUY"  },
  { name: "META",   signal: "HOLD" },
];

const inputSt: React.CSSProperties = {
  width: "120px", padding: "6px 10px",
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 8, color: "rgba(255,255,255,0.85)",
  fontSize: 13, fontFamily: "JetBrains Mono, monospace", outline: "none",
};

export const DashboardView = ({ equity, lastEquity, positions = [], isConnected = false }: DashboardViewProps) => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  /* ── Strategy ── */
  const { data: strategyData, isLoading: isStrategyChecking } = useQuery({
    queryKey: ["strategy"],
    queryFn: fetchStrategy,
    refetchInterval: 5000,
  });
  const strategy = "RLAgent";
  const running = !!strategyData;
  const [isLoading, setIsLoading] = useState(false);

  /* ── Risk limits ── */
  const [riskData, setRiskData] = useState<RiskLimits | null>(null);
  const [riskLoading, setRiskLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [maxDrawdown, setMaxDrawdown] = useState("5");
  const [maxPosition, setMaxPosition] = useState("20");

  useEffect(() => {
    let mounted = true;
    fetchRiskLimits().then((res) => {
      if (!mounted) return;
      if (res?.status === "success") {
        setRiskData(res);
        if (res.risk_limits?.max_daily_drawdown_pct) setMaxDrawdown(res.risk_limits.max_daily_drawdown_pct.toString());
        if (res.risk_limits?.max_position_size_pct)  setMaxPosition(res.risk_limits.max_position_size_pct.toString());
      }
      setRiskLoading(false);
    });
    return () => { mounted = false; };
  }, []);

  /* ── Recent trades ── */
  const [trades, setTrades] = useState<RecentTrade[]>([]);
  const [tradesLoading, setTradesLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      const data = await fetchRecentTrades(20);
      if (!mounted) return;
      setTrades(data.trades || []);
      setTradesLoading(false);
    };
    load();
    const iv = setInterval(load, 15000);
    return () => { mounted = false; clearInterval(iv); };
  }, []);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["strategy"] });

  const handleStartLive = async () => {
    setIsLoading(true);
    try {
      const data = await startLive();
      if (data.status === "success") { setRunning(true); invalidate(); toast({ title: "Live trading started" }); }
    } catch { toast({ title: "Engine not reachable", variant: "destructive" }); }
    setIsLoading(false);
  };

  const handleStop = async () => {
    setIsLoading(true);
    try {
      const data = await stop();
      if (data.status === "success") { setRunning(false); invalidate(); toast({ title: "Trading stopped" }); }
    } catch { toast({ title: "Engine not reachable", variant: "destructive" }); }
    setIsLoading(false);
  };

  const handlePanicSell = async () => {
    setIsLoading(true);
    try {
      const data = await panicSell();
      toast({
        title: data.status === "success" ? "All positions sold" : "Error",
        description: data.message,
        variant: data.status === "success" ? "default" : "destructive",
      });
      if (data.status === "success") invalidate();
    } catch { toast({ title: "Engine not reachable", variant: "destructive" }); }
    setIsLoading(false);
  };

  const handleToggleBot = async () => {
    if (!riskData) return;
    const newStatus = riskData.bot_status === "active" ? "inactive" : "active";
    setRiskData({ ...riskData, bot_status: newStatus });
    const res = await updateBotStatus(newStatus);
    if (res.status === "error") setRiskData({ ...riskData, bot_status: riskData.bot_status });
  };

  const handleSaveLimits = async () => {
    setSaving(true);
    await updateRiskLimits({
      max_daily_drawdown_pct: parseFloat(maxDrawdown),
      max_position_size_pct: parseFloat(maxPosition),
    });
    setSaving(false);
  };

  /* ── Computed ── */
  const totalPnL       = equity != null ? equity - INITIAL_CAPITAL : null;
  const totalReturnPct = equity != null ? ((equity - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100 : null;
  const dailyReturnPct = equity != null && lastEquity != null && lastEquity > 0
    ? ((equity - lastEquity) / lastEquity) * 100 : null;
  const isEngineConnected = strategyData != null;

  /* ── Stat cards data ── */
  const stats = [
    { label: "Total Value",  value: equity     != null ? fmt(equity)     : "—", note: null,              col: null },
    { label: "Total P&L",    value: totalPnL   != null ? (totalPnL   >= 0 ? "+" : "") + fmt(totalPnL)   : "—",
      note: totalReturnPct != null ? (totalReturnPct >= 0 ? "+" : "") + totalReturnPct.toFixed(2) + "%" : null,
      col: totalPnL },
    { label: "Positions",    value: String(positions.length), note: isConnected ? "connected" : "offline", col: null },
    { label: "Daily",        value: dailyReturnPct != null ? (dailyReturnPct >= 0 ? "+" : "") + dailyReturnPct.toFixed(2) + "%" : "—",
      note: null, col: dailyReturnPct },
  ];

  const showRisk = riskData && riskData.status !== "error" && !riskLoading;

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="min-h-screen pt-16 pb-12 px-6"
      style={{ maxWidth: 980, margin: "0 auto" }}
    >
      {/* Header */}
      <div className="pt-10 pb-6">
        <div className="dash-overline">Dashboard</div>
        <h1 className="dash-title">Portfolio Overview</h1>
      </div>

      {/* Broker CTA (only when not connected) */}
      {!isConnected && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <BrokerConnectionWidget isConnected={isConnected} />
        </motion.div>
      )}

      {/* ── ENGINE CONTROLS ── */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="mb-5">
        <div className="surface-card p-5">
          {/* Header row */}
          <div className="flex items-center justify-between mb-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", paddingBottom: 14 }}>
            <div className="flex items-center gap-2">
              <ShieldAlert style={{ width: 16, height: 16, color: "rgba(255,255,255,0.55)" }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.85)", letterSpacing: "-0.01em" }}>Trading Engine</span>
            </div>
            <div className="flex items-center gap-4">
              {/* Connection status */}
              <div className="flex items-center gap-1.5">
                {isStrategyChecking
                  ? <Loader2 style={{ width: 11, height: 11, color: "rgba(255,255,255,0.3)" }} className="animate-spin" />
                  : isEngineConnected
                    ? <CheckCircle style={{ width: 11, height: 11, color: "#30d158" }} />
                    : <XCircle    style={{ width: 11, height: 11, color: "#ff453a" }} />
                }
                <span style={{ fontSize: 11, color: isEngineConnected ? "#30d158" : "#ff453a", fontWeight: 500 }}>
                  {isStrategyChecking ? "Checking" : isEngineConnected ? "Connected" : "Offline"}
                </span>
              </div>
              {/* Bot toggle */}
              {showRisk && (
                <div className="flex items-center gap-2">
                  <span style={{ fontSize: 11, color: "rgba(255,255,255,0.3)", fontWeight: 500 }}>Engine</span>
                  <button
                    className={"aa-toggle" + (riskData!.bot_status === "active" ? " on" : "")}
                    onClick={handleToggleBot}
                    aria-label="Toggle bot"
                  />
                  <span style={{ fontSize: 11, fontWeight: 700, color: riskData!.bot_status === "active" ? "#30d158" : "rgba(255,255,255,0.3)" }}>
                    {riskData!.bot_status === "active" ? "ACTIVE" : "PAUSED"}
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Left: strategy + controls */}
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 10 }}>Controls</div>
              <div className="flex gap-2 flex-wrap">
                {/* Start */}
                <button onClick={handleStartLive} disabled={isLoading || running} className="flex items-center gap-1.5" style={{
                  padding: "7px 14px", borderRadius: 8, fontSize: 12, fontWeight: 600,
                  background: isLoading || running ? "rgba(255,255,255,0.04)" : "rgba(48,209,88,0.1)",
                  border: "1px solid " + (isLoading || running ? "rgba(255,255,255,0.05)" : "rgba(48,209,88,0.3)"),
                  color: isLoading || running ? "rgba(255,255,255,0.3)" : "#30d158",
                  cursor: isLoading || running ? "not-allowed" : "pointer", transition: "all 0.2s",
                }}>
                  <Play style={{ width: 12, height: 12 }} /> Start Live
                </button>
                {/* Stop */}
                <button onClick={handleStop} disabled={isLoading || !running} className="flex items-center gap-1.5" style={{
                  padding: "7px 14px", borderRadius: 8, fontSize: 12, fontWeight: 600,
                  background: "transparent", border: "1px solid rgba(255,255,255,0.08)",
                  color: isLoading || !running ? "rgba(255,255,255,0.3)" : "rgba(255,255,255,0.85)",
                  cursor: isLoading || !running ? "not-allowed" : "pointer", transition: "all 0.2s",
                }}>
                  <Square style={{ width: 12, height: 12 }} /> Stop
                </button>
                {/* Panic */}
                <button onClick={handlePanicSell} disabled={isLoading} className="flex items-center gap-1.5" style={{
                  padding: "7px 14px", borderRadius: 8, fontSize: 12, fontWeight: 600,
                  background: "rgba(255,69,58,0.08)", border: "1px solid rgba(255,69,58,0.25)",
                  color: "#ff453a", cursor: isLoading ? "not-allowed" : "pointer", transition: "all 0.2s",
                }}>
                  <AlertTriangle style={{ width: 12, height: 12 }} /> Panic Sell
                </button>
              </div>
              {/* Status line */}
              <div className="flex items-center gap-2 mt-4">
                <Activity style={{ width: 13, height: 13, color: running ? "#30d158" : "rgba(255,255,255,0.3)" }} />
                <span style={{ fontSize: 12, color: running ? "#30d158" : "rgba(255,255,255,0.3)", fontFamily: "JetBrains Mono, monospace" }}>
                  {running ? "Live Trading Active" : "Stopped"} · {strategy}
                </span>
              </div>
            </div>

            {/* Right: risk limits or engine offline msg */}
            {showRisk ? (
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 10 }}>Risk Limits</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 500, color: "rgba(255,255,255,0.55)", display: "block", marginBottom: 4 }}>Max Daily Drawdown (%)</label>
                    <input type="number" value={maxDrawdown} onChange={(e) => setMaxDrawdown(e.target.value)} min="1" max="50" style={inputSt} />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 500, color: "rgba(255,255,255,0.55)", display: "block", marginBottom: 4 }}>Max Position Size (%)</label>
                    <input type="number" value={maxPosition} onChange={(e) => setMaxPosition(e.target.value)} min="1" max="100" style={inputSt} />
                  </div>
                  <button onClick={handleSaveLimits} disabled={saving} className="flex items-center gap-1.5" style={{
                    padding: "6px 14px", borderRadius: 8, fontSize: 12, fontWeight: 600, width: "fit-content",
                    background: "rgba(212,168,83,0.08)", border: "1px solid rgba(212,168,83,0.2)",
                    color: "#d4a853", cursor: saving ? "not-allowed" : "pointer", transition: "all 0.2s",
                  }}>
                    {saving ? <RefreshCw style={{ width: 12, height: 12 }} className="animate-spin" /> : <Save style={{ width: 12, height: 12 }} />}
                    Save
                  </button>
                </div>
              </div>
            ) : !isEngineConnected && !isStrategyChecking ? (
              <div style={{ background: "rgba(255,255,255,0.03)", borderRadius: 10, padding: 16, border: "1px solid rgba(255,255,255,0.05)" }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.55)", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                  <Power style={{ width: 12, height: 12 }} /> Engine offline
                </div>
                <p style={{ fontSize: 12, color: "rgba(255,255,255,0.55)", lineHeight: 1.6, margin: 0 }}>
                  The trading engine isn't reachable right now. Please contact support if this persists.
                </p>
              </div>
            ) : null}
          </div>
        </div>
      </motion.div>

      {/* ── STAT CARDS ── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
        className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 mb-5"
      >
        {stats.map((c, i) => (
          <div key={i} className="surface-card p-5">
            <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.16)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>
              {c.label}
            </div>
            <div className="stat-value" style={{ color: c.col != null ? (c.col >= 0 ? "#30d158" : "#ff453a") : "rgba(255,255,255,0.85)" }}>
              {c.value}
            </div>
            {c.note && <div style={{ fontSize: 11, color: "rgba(48,209,88,0.8)", fontWeight: 500, marginTop: 3 }}>{c.note}</div>}
          </div>
        ))}
      </motion.div>

      {/* ── POSITIONS + AGENTS ── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
        style={{ display: "grid", gridTemplateColumns: positions.length > 0 ? "1.3fr 1fr" : "1fr", gap: 10, marginBottom: 20 }}
      >
        {/* Positions */}
        <div className="surface-card p-5">
          <div className="flex justify-between items-center mb-4">
            <span style={{ fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.85)", letterSpacing: "-0.01em" }}>Open Positions</span>
            <span style={{ fontSize: 11, color: "#d4a853", fontWeight: 500 }}>{positions.length} open</span>
          </div>
          {positions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Sym</th>
                    <th style={{ textAlign: "right" }}>Qty</th>
                    <th style={{ textAlign: "right" }}>Value</th>
                    <th style={{ textAlign: "right" }}>P&amp;L</th>
                    <th style={{ textAlign: "right" }}>%</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((p) => (
                    <tr key={p.symbol}>
                      <td className="mono">{p.symbol}</td>
                      <td style={{ textAlign: "right", color: "rgba(255,255,255,0.3)", fontSize: 13 }}>{p.qty.toFixed(2)}</td>
                      <td style={{ textAlign: "right", fontSize: 13 }}>{fmt(p.market_value)}</td>
                      <td className={p.unrealized_pnl >= 0 ? "up" : "dn"} style={{ textAlign: "right" }}>
                        {p.unrealized_pnl >= 0 ? "+" : ""}{fmt(p.unrealized_pnl)}
                      </td>
                      <td className={p.unrealized_pnl_pct >= 0 ? "up" : "dn"} style={{ textAlign: "right" }}>
                        {p.unrealized_pnl_pct >= 0 ? "+" : ""}{p.unrealized_pnl_pct.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ fontSize: 13, color: "rgba(255,255,255,0.3)", textAlign: "center", padding: "24px 0" }}>No open positions</p>
          )}
        </div>

        {/* Agents */}
        <div className="surface-card p-5">
          <div className="flex justify-between items-center mb-4">
            <span style={{ fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.85)", letterSpacing: "-0.01em" }}>Agent Status</span>
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.3)", fontWeight: 500 }}>9 agents</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>
            {AGENTS.map((ag, i) => {
              const active = isEngineConnected && i % 3 !== 1;
              return (
                <div key={ag.name} className="agent-card">
                  <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, fontWeight: 600, marginBottom: 3, color: "rgba(255,255,255,0.85)" }}>{ag.name}</div>
                  <div style={{ fontSize: 10, fontWeight: 500, color: active ? "#30d158" : "rgba(255,255,255,0.3)" }}>{active ? "● Active" : "○ Idle"}</div>
                  <div style={{ fontSize: 10, color: "rgba(255,255,255,0.16)", fontWeight: 500, marginTop: 1 }}>{ag.signal}</div>
                </div>
              );
            })}
          </div>
        </div>
      </motion.div>

      {/* ── LATEST TRADES ── */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
        <div className="surface-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Clock style={{ width: 14, height: 14, color: "rgba(255,255,255,0.55)" }} />
            <span style={{ fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.85)", letterSpacing: "-0.01em" }}>Latest Trades</span>
          </div>
          {tradesLoading ? (
            <p style={{ fontSize: 12, color: "rgba(255,255,255,0.3)" }}>Loading…</p>
          ) : trades.length > 0 ? (
            <div className="data-table" style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {["Time", "Action", "Symbol", "Qty", "Price"].map((h) => (
                      <th key={h} style={{ textAlign: "left", fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "0.06em", paddingBottom: 8, paddingRight: 16 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t) => (
                    <tr key={t.id} style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                      <td style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: "rgba(255,255,255,0.35)", paddingTop: 7, paddingBottom: 7, paddingRight: 16, whiteSpace: "nowrap" }}>
                        {t.filled_at ? new Date(t.filled_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}
                      </td>
                      <td style={{ paddingRight: 16, paddingTop: 7, paddingBottom: 7 }}>
                        <span style={{ fontSize: 10, fontFamily: "JetBrains Mono, monospace", fontWeight: 700, color: t.side === "buy" ? "#30d158" : "#ff453a", background: t.side === "buy" ? "rgba(48,209,88,0.1)" : "rgba(255,69,58,0.1)", padding: "2px 7px", borderRadius: 4 }}>
                          {t.side.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace", fontWeight: 600, color: "rgba(255,255,255,0.85)", paddingRight: 16, paddingTop: 7, paddingBottom: 7 }}>{t.symbol}</td>
                      <td style={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: "rgba(255,255,255,0.55)", paddingRight: 16, paddingTop: 7, paddingBottom: 7 }}>{t.qty}</td>
                      <td style={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: "rgba(255,255,255,0.85)", paddingTop: 7, paddingBottom: 7 }}>${t.price.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ fontSize: 12, color: "rgba(255,255,255,0.3)" }}>No trades yet.</p>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
};
