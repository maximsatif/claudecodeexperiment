"""Contagion Graph Agent - Builds and analyzes the financial contagion network."""

import json
import numpy as np
from datetime import datetime
from typing import Any

from strands import Agent, tool
from strands.models import BedrockModel

from backend.config import BEDROCK_MODEL_ID, AWS_REGION, CORRELATION_THRESHOLD
from backend.services.data_fetcher import market_data_fetcher
from backend.services.graph_builder import (
    build_contagion_graph,
    simulate_contagion_spread,
)
from backend.models.contagion import FinancialSIRModel, SIRParameters


@tool
def build_graph(correlation_period: str = "6mo", threshold: float = 0.6) -> str:
    """Build the contagion graph from current market data and correlations.

    Args:
        correlation_period: Period for correlation calculation (e.g., '3mo', '6mo', '1y').
        threshold: Minimum correlation to create an edge between nodes.
    """
    corr_matrix = market_data_fetcher.get_correlation_matrix(period=correlation_period)
    market_data = market_data_fetcher.get_current_prices()

    if corr_matrix.empty:
        return json.dumps({"error": "Unable to build graph - no correlation data"})

    graph = build_contagion_graph(corr_matrix, market_data, threshold=threshold)

    return json.dumps({
        "nodes_count": len(graph.nodes),
        "edges_count": len(graph.edges),
        "systemic_risk_score": graph.systemic_risk_score,
        "critical_nodes": [
            {"id": n.id, "risk_score": n.risk_score, "sector": n.sector}
            for n in graph.nodes if n.status == "critical"
        ],
        "stressed_nodes": [
            {"id": n.id, "risk_score": n.risk_score, "sector": n.sector}
            for n in graph.nodes if n.status == "stressed"
        ],
        "most_connected": _get_most_connected(graph),
        "sector_risk_summary": _sector_risk_summary(graph),
    })


@tool
def simulate_shock(
    shock_ticker: str,
    shock_magnitude: float = 0.8,
    simulation_steps: int = 10,
) -> str:
    """Simulate a contagion shock originating from a specific entity.

    Args:
        shock_ticker: The ticker of the entity experiencing the initial shock.
        shock_magnitude: Severity of the initial shock (0-1, where 1 is catastrophic).
        simulation_steps: Number of time steps to simulate.
    """
    corr_matrix = market_data_fetcher.get_correlation_matrix(period="3mo")
    market_data = market_data_fetcher.get_current_prices()

    if corr_matrix.empty:
        return json.dumps({"error": "Unable to simulate - no data available"})

    graph = build_contagion_graph(corr_matrix, market_data)
    snapshots = simulate_contagion_spread(
        graph, shock_ticker, shock_magnitude, simulation_steps
    )

    # Analyze propagation
    initial_infected = 1
    final_snapshot = snapshots[-1]
    peak_infected = max(s["infected_count"] for s in snapshots)
    peak_step = next(
        s["step"] for s in snapshots if s["infected_count"] == peak_infected
    )

    affected_entities = [
        node_id for node_id, state in final_snapshot["states"].items()
        if state["state"] in ("infected", "recovered")
    ]

    return json.dumps({
        "shock_source": shock_ticker,
        "shock_magnitude": shock_magnitude,
        "simulation_steps": len(snapshots),
        "peak_infected_count": peak_infected,
        "peak_step": peak_step,
        "total_affected": len(affected_entities),
        "affected_entities": affected_entities,
        "final_total_risk": final_snapshot["total_risk"],
        "propagation_snapshots": snapshots[:5],  # First 5 steps for detail
        "contagion_severity": _classify_severity(peak_infected, len(graph.nodes)),
    })


@tool
def compute_r0(
    beta: float = 0.3,
    gamma: float = 0.1,
    delta: float = 0.05,
) -> str:
    """Compute the financial R0 (basic reproduction number) for contagion.

    Args:
        beta: Risk propagation rate (0-1).
        gamma: Risk recovery rate (0-1).
        delta: Permanent damage rate (0-1).
    """
    model = FinancialSIRModel(SIRParameters(beta=beta, gamma=gamma, delta=delta))
    r0 = model.compute_r0()

    trajectory = model.simulate(initial_infected=0.01, steps=100)
    metrics = model.compute_contagion_risk_metrics(trajectory)

    return json.dumps({
        "r0": r0,
        "interpretation": (
            f"R0 = {r0:.2f}. "
            + ("Contagion will SPREAD exponentially. " if r0 > 1 else "Contagion will die out naturally. ")
            + f"Peak infection rate: {metrics['peak_infection_rate']}%. "
            + f"Total affected: {metrics['total_affected_pct']}%. "
            + f"Risk level: {metrics['risk_level']}."
        ),
        "metrics": metrics,
    })


@tool
def identify_systemically_important_nodes() -> str:
    """Identify the most systemically important nodes in the contagion graph
    using PageRank and betweenness centrality."""
    import networkx as nx

    corr_matrix = market_data_fetcher.get_correlation_matrix(period="6mo")
    if corr_matrix.empty:
        return json.dumps({"error": "No data available"})

    # Build NetworkX graph
    G = nx.Graph()
    tickers = list(corr_matrix.columns)
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            corr = abs(corr_matrix.iloc[i, j])
            if corr >= CORRELATION_THRESHOLD:
                G.add_edge(tickers[i], tickers[j], weight=corr)

    if G.number_of_nodes() == 0:
        return json.dumps({"error": "No significant correlations found"})

    # Compute centrality metrics
    pagerank = nx.pagerank(G, weight="weight")
    betweenness = nx.betweenness_centrality(G, weight="weight")
    degree = dict(G.degree(weight="weight"))

    # Combine into importance score
    importance = {}
    for node in G.nodes():
        importance[node] = {
            "pagerank": round(pagerank.get(node, 0), 4),
            "betweenness": round(betweenness.get(node, 0), 4),
            "weighted_degree": round(degree.get(node, 0), 4),
            "importance_score": round(
                pagerank.get(node, 0) * 0.4
                + betweenness.get(node, 0) * 0.3
                + (degree.get(node, 0) / max(degree.values())) * 0.3,
                4,
            ),
        }

    # Sort by importance
    sorted_nodes = sorted(
        importance.items(), key=lambda x: x[1]["importance_score"], reverse=True
    )

    return json.dumps({
        "systemically_important_nodes": [
            {"ticker": node, **metrics} for node, metrics in sorted_nodes[:10]
        ],
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "graph_density": round(nx.density(G), 4),
    })


def _get_most_connected(graph) -> list[dict]:
    """Get the most connected nodes in the graph."""
    connection_count: dict[str, int] = {}
    for edge in graph.edges:
        connection_count[edge.source] = connection_count.get(edge.source, 0) + 1
        connection_count[edge.target] = connection_count.get(edge.target, 0) + 1

    sorted_nodes = sorted(connection_count.items(), key=lambda x: x[1], reverse=True)
    return [{"ticker": t, "connections": c} for t, c in sorted_nodes[:5]]


def _sector_risk_summary(graph) -> dict[str, dict]:
    """Summarize risk by sector."""
    sector_risks: dict[str, list[float]] = {}
    for node in graph.nodes:
        sector_risks.setdefault(node.sector, []).append(node.risk_score)

    return {
        sector: {
            "avg_risk": round(np.mean(risks), 1),
            "max_risk": round(max(risks), 1),
            "count": len(risks),
        }
        for sector, risks in sector_risks.items()
    }


def _classify_severity(peak_infected: int, total_nodes: int) -> str:
    """Classify contagion severity."""
    ratio = peak_infected / max(total_nodes, 1)
    if ratio > 0.5:
        return "catastrophic"
    elif ratio > 0.3:
        return "severe"
    elif ratio > 0.15:
        return "moderate"
    else:
        return "contained"


def create_contagion_graph_agent() -> Agent:
    """Create and return the Contagion Graph Agent."""
    model = BedrockModel(
        model_id=BEDROCK_MODEL_ID,
        region_name=AWS_REGION,
        temperature=0.1,
    )

    agent = Agent(
        model=model,
        tools=[
            build_graph,
            simulate_shock,
            compute_r0,
            identify_systemically_important_nodes,
        ],
        system_prompt="""You are a Financial Contagion Graph Agent specializing in systemic risk analysis.
Your role is to:
1. Build and analyze contagion networks showing how risk propagates between financial entities
2. Simulate shock scenarios to predict cascading failures
3. Compute the financial R0 (reproduction number) to assess whether contagion will spread or die out
4. Identify systemically important nodes (too-big-to-fail entities)

Key concepts you apply:
- SIR epidemiological model adapted for financial contagion
- PageRank and betweenness centrality for systemic importance
- Correlation-based network construction
- Shock propagation simulation

When reporting, always include:
- The R0 number and its interpretation
- Which entities are most systemically important
- Expected propagation path of a shock
- Time-to-peak infection and total affected entities
- Risk classification (contained, moderate, severe, catastrophic)""",
    )
    return agent
