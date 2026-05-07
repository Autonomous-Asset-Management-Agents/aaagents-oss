/**
 * Dashboard view — Primary interface for the AAAgents Container. Renders the real paper portfolio
 * (DashboardView + PortfolioView + SimulationView) with full controls.
 */
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { DashboardView } from "@/components/views/DashboardView";
import { PortfolioView } from "@/components/views/PortfolioView";
import { SimulationView } from "@/components/views/SimulationView";
import { fetchPortfolioSummary } from "@/lib/api";
import "@/styles/landing-b.css";

type Tab = "dashboard" | "portfolio" | "simulation";

export default function Dashboard() {
    const navigate = useNavigate();
    const [tab, setTab] = useState<Tab>("dashboard");



    const { data: portfolioData } = useQuery({
        queryKey: ["public-portfolio-summary"],
        queryFn: fetchPortfolioSummary,
        refetchInterval: 15000,
        retry: 1,
    });

    const positions = portfolioData?.status === "success" && portfolioData.positions
        ? portfolioData.positions.map((p) => ({
            symbol: p.symbol,
            qty: p.qty,
            market_value: p.market_value,
            unrealized_pnl: p.unrealized_pnl ?? 0,
            unrealized_pnl_pct: p.unrealized_pnl_pct ?? 0,
        }))
        : [];

    return (
        <div className="landing-b-root" style={{ minHeight: "100vh", background: "#000", color: "#fff" }}>
            {/* Top bar — read-only notice */}
            <div className="lb-risk-banner" style={{ background: "#0b0b0b", color: "#9a9a9a", borderBottomColor: "#1a1a1a" }}>
                <span style={{ fontFamily: "var(--lb-mono)", fontSize: 12, letterSpacing: 2, textTransform: "uppercase" }}>
                    AAAgents Console · Engine Online
                </span>
            </div>

            <nav className="lb-nav" style={{ borderBottom: "1px solid #1a1a1a" }}>
                <div className="lb-nav-logo" style={{ color: "#fff" }}>
                    aaagents<span style={{ color: "#00c27a" }}>_</span>
                </div>
                <div className="lb-nav-right">
                    <button className="lb-nav-link" style={{ color: tab === "dashboard" ? "#00c27a" : "#9a9a9a" }} onClick={() => setTab("dashboard")}>Overview</button>
                    <button className="lb-nav-link" style={{ color: tab === "portfolio" ? "#00c27a" : "#9a9a9a" }} onClick={() => setTab("portfolio")}>Portfolio</button>
                    <button className="lb-nav-link" style={{ color: tab === "simulation" ? "#00c27a" : "#9a9a9a" }} onClick={() => setTab("simulation")}>Simulation</button>
                </div>
            </nav>

            <main style={{ minHeight: "calc(100vh - 140px)", padding: "24px var(--lb-gutter)" }}>
                {tab === "dashboard" && (
                    <DashboardView
                        equity={portfolioData?.status === "success" ? portfolioData.equity : undefined}
                        lastEquity={portfolioData?.status === "success" ? portfolioData.last_equity : undefined}
                        positions={positions}
                        isConnected={portfolioData?.status === "success"}
                    />
                )}
                {tab === "portfolio" && <PortfolioView positions={positions} />}
                {tab === "simulation" && <SimulationView />}
            </main>
        </div>
    );
}
