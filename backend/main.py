"""ContagionGuard - FastAPI Backend

AI-Powered Cross-Market Contagion & Margin Risk Early Warning System
Built for the DTCC 2026 Industry-Powered AI Hackathon
"""

import json
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.config import API_HOST, API_PORT, CORS_ORIGINS, MONITORED_TICKERS
from backend.models.schemas import (
    ChatRequest,
    ChatResponse,
    ContagionGraph,
    DashboardData,
    RiskNarrative,
)
from backend.services.data_fetcher import market_data_fetcher, fred_fetcher, news_fetcher
from backend.services.graph_builder import build_contagion_graph, simulate_contagion_spread
from backend.models.contagion import FinancialSIRModel, SIRParameters


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("ContagionGuard API starting up...")
    yield
    print("ContagionGuard API shutting down...")


app = FastAPI(
    title="ContagionGuard API",
    description=(
        "AI-Powered Cross-Market Contagion & Margin Risk Early Warning System. "
        "Uses multi-agent AI to monitor cross-market signals, build dynamic "
        "contagion graphs, and predict cascading margin impacts."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────────────────────────────
# Health & Info
# ────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "ContagionGuard",
        "tagline": "AI-Powered Cross-Market Contagion & Margin Risk Early Warning System",
        "version": "1.0.0",
        "hackathon": "DTCC 2026 Industry-Powered AI Hackathon",
        "status": "operational",
    }


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ────────────────────────────────────────────
# Market Data Endpoints
# ────────────────────────────────────────────

@app.get("/api/market-data")
async def get_market_data():
    """Get current market data for all monitored tickers."""
    df = market_data_fetcher.get_current_prices()
    if df.empty:
        raise HTTPException(status_code=503, detail="Market data unavailable")
    return {"data": json.loads(df.to_json(orient="records")), "timestamp": datetime.now().isoformat()}


@app.get("/api/market-data/{ticker}")
async def get_ticker_data(ticker: str):
    """Get market data for a specific ticker."""
    df = market_data_fetcher.get_current_prices([ticker.upper()])
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")
    return {"data": json.loads(df.to_json(orient="records"))[0]}


@app.get("/api/correlations")
async def get_correlations(period: str = "6mo"):
    """Get cross-asset correlation matrix."""
    corr = market_data_fetcher.get_correlation_matrix(period=period)
    if corr.empty:
        raise HTTPException(status_code=503, detail="Correlation data unavailable")
    return {
        "correlations": json.loads(corr.to_json()),
        "tickers": list(corr.columns),
        "period": period,
    }


# ────────────────────────────────────────────
# Macro Indicators
# ────────────────────────────────────────────

@app.get("/api/macro-indicators")
async def get_macro_indicators():
    """Get key macro indicators (VIX, credit spreads, yields, etc.)."""
    indicators = await fred_fetcher.get_all_indicators()
    formatted = {}
    for name, data_points in indicators.items():
        if data_points:
            latest = data_points[0]
            previous = data_points[1] if len(data_points) > 1 else latest
            change = latest["value"] - previous["value"]
            formatted[name] = {
                "value": latest["value"],
                "previous": previous["value"],
                "change": round(change, 4),
                "date": latest["date"],
                "signal": _classify_macro_signal(name, latest["value"], change),
            }
    return {"indicators": formatted, "timestamp": datetime.now().isoformat()}


# ────────────────────────────────────────────
# Contagion Graph
# ────────────────────────────────────────────

@app.get("/api/graph")
async def get_contagion_graph(period: str = "6mo", threshold: float = 0.6):
    """Build and return the contagion graph with sentiment-enhanced risk scores."""
    corr = market_data_fetcher.get_correlation_matrix(period=period)
    market_data = market_data_fetcher.get_current_prices()

    if corr.empty:
        raise HTTPException(status_code=503, detail="Unable to build graph")

    sentiment_data = await news_fetcher.get_batch_sentiment_scores(MONITORED_TICKERS)
    graph = build_contagion_graph(corr, market_data, threshold=threshold, sentiment_data=sentiment_data)
    return graph.model_dump()


@app.post("/api/graph/simulate")
async def simulate_shock(ticker: str, magnitude: float = 0.8, steps: int = 10):
    """Simulate a contagion shock from a specific entity."""
    corr = market_data_fetcher.get_correlation_matrix(period="3mo")
    market_data = market_data_fetcher.get_current_prices()

    if corr.empty:
        raise HTTPException(status_code=503, detail="Unable to simulate")

    sentiment_data = await news_fetcher.get_batch_sentiment_scores(MONITORED_TICKERS)
    graph = build_contagion_graph(corr, market_data, sentiment_data=sentiment_data)

    # Validate ticker exists in graph
    node_ids = [n.id for n in graph.nodes]
    if ticker.upper() not in node_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Ticker {ticker} not in graph. Available: {node_ids[:10]}",
        )

    snapshots = simulate_contagion_spread(graph, ticker.upper(), magnitude, steps)
    return {
        "shock_source": ticker.upper(),
        "magnitude": magnitude,
        "snapshots": snapshots,
        "graph": graph.model_dump(),
    }


# ────────────────────────────────────────────
# SIR Model
# ────────────────────────────────────────────

@app.get("/api/sir-model")
async def get_sir_simulation(
    beta: float = 0.3,
    gamma: float = 0.1,
    delta: float = 0.05,
    initial_infected: float = 0.01,
    steps: int = 100,
):
    """Run SIR contagion model simulation."""
    model = FinancialSIRModel(SIRParameters(beta=beta, gamma=gamma, delta=delta))
    trajectory = model.simulate(initial_infected=initial_infected, steps=steps)
    metrics = model.compute_contagion_risk_metrics(trajectory)

    return {
        "parameters": {"beta": beta, "gamma": gamma, "delta": delta},
        "r0": model.compute_r0(),
        "metrics": metrics,
        "trajectory": [
            {
                "step": i,
                "susceptible": round(s.susceptible, 4),
                "infected": round(s.infected, 4),
                "recovered": round(s.recovered, 4),
                "dead": round(s.dead, 4),
            }
            for i, s in enumerate(trajectory)
        ],
    }


# ────────────────────────────────────────────
# Risk Analysis
# ────────────────────────────────────────────

@app.get("/api/risk-score")
async def get_risk_score():
    """Get the current systemic risk score and breakdown."""
    corr = market_data_fetcher.get_correlation_matrix(period="3mo")
    market_data = market_data_fetcher.get_current_prices()

    if corr.empty or market_data.empty:
        return {"systemic_risk_score": 0, "status": "data_unavailable"}

    sentiment_data = await news_fetcher.get_batch_sentiment_scores(MONITORED_TICKERS)
    graph = build_contagion_graph(corr, market_data, sentiment_data=sentiment_data)

    # Breakdown by sector
    sector_risk = {}
    for node in graph.nodes:
        sector_risk.setdefault(node.sector, []).append(node.risk_score)

    sector_summary = {
        sector: {"avg": round(sum(scores) / len(scores), 1), "max": round(max(scores), 1)}
        for sector, scores in sector_risk.items()
    }

    return {
        "systemic_risk_score": graph.systemic_risk_score,
        "risk_level": _score_to_level(graph.systemic_risk_score),
        "sector_breakdown": sector_summary,
        "critical_count": sum(1 for n in graph.nodes if n.status == "critical"),
        "stressed_count": sum(1 for n in graph.nodes if n.status == "stressed"),
        "healthy_count": sum(1 for n in graph.nodes if n.status == "healthy"),
        "timestamp": datetime.now().isoformat(),
    }


# ────────────────────────────────────────────
# AI Chat (Agentic)
# ────────────────────────────────────────────

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Chat with the ContagionGuard AI agent."""
    try:
        from backend.agents.orchestrator import orchestrator
        response = await orchestrator.chat(request.message)
        return ChatResponse(response=response)
    except Exception as e:
        return ChatResponse(
            response=f"I encountered an issue processing your question: {str(e)}. "
            f"Please try rephrasing or ask about specific market data, risk scores, "
            f"or contagion analysis."
        )


# ────────────────────────────────────────────
# Full Analysis (Orchestrated)
# ────────────────────────────────────────────

@app.post("/api/analyze")
async def run_full_analysis():
    """Run a full orchestrated analysis using all agents."""
    try:
        from backend.agents.orchestrator import orchestrator
        results = await orchestrator.run_full_analysis()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/analyze/shock")
async def run_shock_analysis(ticker: str, magnitude: float = 0.8):
    """Run a shock simulation and analysis."""
    try:
        from backend.agents.orchestrator import orchestrator
        results = await orchestrator.run_shock_simulation(ticker.upper(), magnitude)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shock analysis failed: {str(e)}")


# ────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────

def _score_to_level(score: float) -> str:
    if score >= 75:
        return "critical"
    elif score >= 50:
        return "high"
    elif score >= 30:
        return "elevated"
    elif score >= 15:
        return "moderate"
    else:
        return "low"


def _classify_macro_signal(name: str, value: float, change: float) -> str:
    """Classify macro indicator signal based on name and value."""
    if name == "VIX":
        if value > 30:
            return "critical"
        elif value > 20:
            return "warning"
        elif value > 15:
            return "elevated"
        return "normal"
    elif name == "CREDIT_SPREAD":
        if value > 5:
            return "critical"
        elif value > 3:
            return "warning"
        elif value > 2:
            return "elevated"
        return "normal"
    elif name in ("TREASURY_10Y", "TREASURY_2Y"):
        if abs(change) > 0.2:
            return "warning"
        elif abs(change) > 0.1:
            return "elevated"
        return "normal"
    return "normal"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
