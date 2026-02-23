"""Graph building service for contagion network construction."""

import networkx as nx
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional

from backend.config import CORRELATION_THRESHOLD, SIR_INFECTION_RATE, SIR_RECOVERY_RATE
from backend.models.schemas import GraphNode, GraphEdge, ContagionGraph


# Sector mapping for monitored tickers
TICKER_SECTORS = {
    "JPM": "Major Banks", "BAC": "Major Banks", "C": "Major Banks",
    "WFC": "Major Banks", "GS": "Major Banks", "MS": "Major Banks",
    "DB": "Major Banks", "UBS": "Major Banks", "CS": "Major Banks",
    "HSBC": "Major Banks",
    "SCHW": "Regional Banks", "USB": "Regional Banks", "PNC": "Regional Banks",
    "TFC": "Regional Banks", "FITB": "Regional Banks",
    "BRK-B": "Insurance/Financial", "AIG": "Insurance/Financial",
    "MET": "Insurance/Financial", "PRU": "Insurance/Financial",
    "SPY": "Equity Index", "QQQ": "Equity Index", "IWM": "Equity Index",
    "EFA": "Equity Index", "EEM": "Equity Index",
    "TLT": "Fixed Income", "HYG": "Fixed Income", "LQD": "Fixed Income",
    "AGG": "Fixed Income",
    "GLD": "Commodities", "USO": "Commodities", "UNG": "Commodities",
    "BITO": "Crypto",
    "UVXY": "Volatility",
    "UUP": "FX", "FXE": "FX", "FXY": "FX",
}


def build_contagion_graph(
    correlation_matrix: pd.DataFrame,
    market_data: pd.DataFrame,
    threshold: float = CORRELATION_THRESHOLD,
    sentiment_data: Optional[dict[str, float]] = None,
) -> ContagionGraph:
    """Build a contagion graph from correlation matrix, market data, and sentiment."""
    G = nx.Graph()
    sentiment_data = sentiment_data or {}

    # Create lookup for market data
    market_lookup = {}
    if not market_data.empty:
        for _, row in market_data.iterrows():
            market_lookup[row["ticker"]] = row

    # Add nodes
    nodes = []
    for ticker in correlation_matrix.columns:
        md = market_lookup.get(ticker, {})
        change_pct = float(md.get("change_pct", 0)) if isinstance(md, dict) else (
            float(md["change_pct"]) if hasattr(md, "__getitem__") and "change_pct" in md.index else 0
        )
        vol_ratio = float(md.get("volume_ratio", 1)) if isinstance(md, dict) else (
            float(md["volume_ratio"]) if hasattr(md, "__getitem__") and "volume_ratio" in md.index else 1
        )

        ticker_sentiment = sentiment_data.get(ticker, 0.0)

        # Compute risk score based on price change, volume anomaly, and sentiment
        risk_score = _compute_node_risk_score(change_pct, vol_ratio, ticker_sentiment)
        status = _risk_to_status(risk_score)
        volume_anomaly = vol_ratio > 2.0

        node = GraphNode(
            id=ticker,
            label=ticker,
            sector=TICKER_SECTORS.get(ticker, "Other"),
            risk_score=risk_score,
            status=status,
            price_change_pct=change_pct,
            volume_anomaly=volume_anomaly,
            sentiment_score=ticker_sentiment,
        )
        nodes.append(node)
        G.add_node(ticker, risk_score=risk_score)

    # Add edges based on correlation threshold
    edges = []
    tickers = list(correlation_matrix.columns)
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            corr = abs(correlation_matrix.iloc[i, j])
            if corr >= threshold:
                # Contagion risk is proportional to correlation and source node risk
                source_risk = G.nodes[tickers[i]].get("risk_score", 0) / 100
                contagion_risk = min(corr * source_risk * SIR_INFECTION_RATE, 1.0)

                edge = GraphEdge(
                    source=tickers[i],
                    target=tickers[j],
                    weight=round(float(corr), 3),
                    contagion_risk=round(contagion_risk, 3),
                )
                edges.append(edge)
                G.add_edge(tickers[i], tickers[j], weight=corr)

    # Compute systemic risk using PageRank-weighted risk scores
    if G.number_of_nodes() > 0 and G.number_of_edges() > 0:
        pagerank = nx.pagerank(G, weight="weight")
        systemic_risk = sum(
            pagerank.get(n.id, 0) * n.risk_score for n in nodes
        )
        # Normalize to 0-100
        systemic_risk = min(systemic_risk * 2, 100)
    else:
        systemic_risk = 0.0

    return ContagionGraph(
        nodes=nodes,
        edges=edges,
        timestamp=datetime.now(),
        systemic_risk_score=round(systemic_risk, 1),
    )


def simulate_contagion_spread(
    graph: ContagionGraph,
    shock_node: str,
    shock_magnitude: float = 0.8,
    steps: int = 10,
) -> list[dict]:
    """Simulate SIR-based contagion spread from a shocked node.

    Returns list of snapshots showing risk propagation over time steps.
    """
    # Initialize SIR states
    states = {}
    for node in graph.nodes:
        if node.id == shock_node:
            states[node.id] = {
                "state": "infected",
                "risk": min(node.risk_score + shock_magnitude * 100, 100),
            }
        else:
            states[node.id] = {
                "state": "susceptible",
                "risk": node.risk_score,
            }

    # Build adjacency for fast lookup
    adjacency: dict[str, list[tuple[str, float]]] = {}
    for edge in graph.edges:
        adjacency.setdefault(edge.source, []).append((edge.target, edge.weight))
        adjacency.setdefault(edge.target, []).append((edge.source, edge.weight))

    snapshots = [_state_snapshot(states, 0)]

    for step in range(1, steps + 1):
        new_states = {k: dict(v) for k, v in states.items()}

        for node_id, state in states.items():
            if state["state"] == "infected":
                # Try to infect neighbors
                for neighbor, weight in adjacency.get(node_id, []):
                    if states[neighbor]["state"] == "susceptible":
                        infection_prob = weight * SIR_INFECTION_RATE * (state["risk"] / 100)
                        if np.random.random() < infection_prob:
                            new_states[neighbor]["state"] = "infected"
                            risk_increase = state["risk"] * weight * 0.5
                            new_states[neighbor]["risk"] = min(
                                new_states[neighbor]["risk"] + risk_increase, 100
                            )

                # Recovery chance
                if np.random.random() < SIR_RECOVERY_RATE:
                    new_states[node_id]["state"] = "recovered"
                    new_states[node_id]["risk"] = max(state["risk"] * 0.7, 10)

        states = new_states
        snapshots.append(_state_snapshot(states, step))

    return snapshots


def _state_snapshot(states: dict, step: int) -> dict:
    """Create a snapshot of the current SIR state."""
    return {
        "step": step,
        "states": {
            node_id: {
                "state": s["state"],
                "risk": round(s["risk"], 1),
            }
            for node_id, s in states.items()
        },
        "infected_count": sum(1 for s in states.values() if s["state"] == "infected"),
        "total_risk": round(sum(s["risk"] for s in states.values()), 1),
    }


def _compute_node_risk_score(change_pct: float, vol_ratio: float, sentiment_score: float = 0.0) -> float:
    """Compute a risk score (0-100) from price change, volume, and sentiment data."""
    # Price component: larger negative moves = higher risk
    price_risk = min(abs(change_pct) * 10, 50) if change_pct < 0 else max(0, abs(change_pct) * 3 - 5)
    # Volume component: unusual volume = higher risk
    volume_risk = min((vol_ratio - 1) * 15, 50) if vol_ratio > 1.5 else 0
    # Sentiment component: negative sentiment increases risk, positive reduces it
    if sentiment_score < 0:
        sentiment_risk = min(abs(sentiment_score) * 25, 25)
    elif sentiment_score > 0:
        sentiment_risk = -min(sentiment_score * 10, 10)
    else:
        sentiment_risk = 0
    return min(max(round(price_risk + volume_risk + sentiment_risk, 1), 0), 100)


def _risk_to_status(risk_score: float) -> str:
    """Convert risk score to status string."""
    if risk_score < 25:
        return "healthy"
    elif risk_score < 60:
        return "stressed"
    else:
        return "critical"
