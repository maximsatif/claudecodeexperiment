"""Margin Impact Agent - Estimates margin call probabilities and stress test results."""

import json
import numpy as np
from datetime import datetime
from typing import Any

from strands import Agent, tool
from strands.models import BedrockModel

from backend.config import BEDROCK_MODEL_ID, AWS_REGION
from backend.services.data_fetcher import market_data_fetcher
from backend.models.contagion import FinancialSIRModel, SIRParameters


# Sample portfolio for demonstration
DEMO_PORTFOLIO = {
    "positions": [
        {"ticker": "JPM", "shares": 10000, "avg_cost": 180.0},
        {"ticker": "BAC", "shares": 15000, "avg_cost": 35.0},
        {"ticker": "GS", "shares": 5000, "avg_cost": 400.0},
        {"ticker": "C", "shares": 12000, "avg_cost": 55.0},
        {"ticker": "MS", "shares": 8000, "avg_cost": 90.0},
        {"ticker": "SPY", "shares": 3000, "avg_cost": 480.0},
        {"ticker": "TLT", "shares": 5000, "avg_cost": 95.0},
        {"ticker": "HYG", "shares": 10000, "avg_cost": 75.0},
        {"ticker": "GLD", "shares": 2000, "avg_cost": 190.0},
    ],
    "initial_margin_pct": 0.50,   # 50% initial margin
    "maintenance_margin_pct": 0.25,  # 25% maintenance margin
}


@tool
def compute_portfolio_margin_risk() -> str:
    """Compute current margin risk for the demo portfolio, including margin call probability."""
    prices = market_data_fetcher.get_current_prices(
        [p["ticker"] for p in DEMO_PORTFOLIO["positions"]]
    )
    if prices.empty:
        return json.dumps({"error": "Unable to fetch current prices"})

    price_lookup = {row["ticker"]: row["price"] for _, row in prices.iterrows()}

    total_market_value = 0
    total_cost_basis = 0
    position_details = []

    for pos in DEMO_PORTFOLIO["positions"]:
        current_price = price_lookup.get(pos["ticker"])
        if current_price is None:
            continue

        market_value = pos["shares"] * current_price
        cost_basis = pos["shares"] * pos["avg_cost"]
        pnl = market_value - cost_basis
        pnl_pct = (pnl / cost_basis) * 100

        total_market_value += market_value
        total_cost_basis += cost_basis

        position_details.append({
            "ticker": pos["ticker"],
            "shares": pos["shares"],
            "current_price": round(current_price, 2),
            "market_value": round(market_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
        })

    # Margin calculations
    initial_margin = total_market_value * DEMO_PORTFOLIO["initial_margin_pct"]
    maintenance_margin = total_market_value * DEMO_PORTFOLIO["maintenance_margin_pct"]
    equity = total_market_value - (total_cost_basis * 0.5)  # Assuming 50% borrowed
    margin_excess = equity - maintenance_margin
    margin_utilization = (1 - equity / total_market_value) * 100 if total_market_value > 0 else 0

    # Price drop needed for margin call
    if total_market_value > 0:
        drop_for_margin_call = (margin_excess / total_market_value) * 100
    else:
        drop_for_margin_call = 0

    return json.dumps({
        "portfolio_summary": {
            "total_market_value": round(total_market_value, 2),
            "total_cost_basis": round(total_cost_basis, 2),
            "total_pnl": round(total_market_value - total_cost_basis, 2),
            "equity": round(equity, 2),
            "margin_requirement": round(maintenance_margin, 2),
            "margin_excess": round(margin_excess, 2),
            "margin_utilization_pct": round(margin_utilization, 1),
            "price_drop_for_margin_call_pct": round(drop_for_margin_call, 1),
        },
        "positions": position_details,
        "margin_call_imminent": margin_excess < total_market_value * 0.05,
    })


@tool
def run_stress_test(
    scenario: str = "moderate_selloff",
) -> str:
    """Run a stress test on the portfolio under various scenarios.

    Args:
        scenario: One of 'moderate_selloff', 'severe_crash', 'rate_shock',
                  'credit_crisis', 'svb_scenario', 'covid_crash'.
    """
    # Define stress scenarios (expected returns under each)
    scenarios = {
        "moderate_selloff": {
            "description": "10-15% equity decline, 5% credit widening",
            "shocks": {"JPM": -0.12, "BAC": -0.15, "GS": -0.10, "C": -0.14,
                       "MS": -0.11, "SPY": -0.12, "TLT": 0.05, "HYG": -0.08, "GLD": 0.03},
        },
        "severe_crash": {
            "description": "30%+ equity decline, 15% credit widening, flight to safety",
            "shocks": {"JPM": -0.30, "BAC": -0.35, "GS": -0.28, "C": -0.33,
                       "MS": -0.29, "SPY": -0.30, "TLT": 0.15, "HYG": -0.20, "GLD": 0.10},
        },
        "rate_shock": {
            "description": "Sudden 200bp rate increase, bond selloff",
            "shocks": {"JPM": -0.05, "BAC": -0.08, "GS": -0.04, "C": -0.07,
                       "MS": -0.05, "SPY": -0.08, "TLT": -0.15, "HYG": -0.12, "GLD": -0.05},
        },
        "credit_crisis": {
            "description": "Credit spreads blow out, bank contagion",
            "shocks": {"JPM": -0.20, "BAC": -0.25, "GS": -0.18, "C": -0.28,
                       "MS": -0.22, "SPY": -0.15, "TLT": 0.10, "HYG": -0.25, "GLD": 0.08},
        },
        "svb_scenario": {
            "description": "Regional bank crisis with contagion to major banks",
            "shocks": {"JPM": -0.08, "BAC": -0.15, "GS": -0.06, "C": -0.12,
                       "MS": -0.07, "SPY": -0.05, "TLT": 0.08, "HYG": -0.10, "GLD": 0.05},
        },
        "covid_crash": {
            "description": "Rapid, broad-based selloff across all asset classes",
            "shocks": {"JPM": -0.35, "BAC": -0.40, "GS": -0.30, "C": -0.38,
                       "MS": -0.32, "SPY": -0.34, "TLT": 0.12, "HYG": -0.18, "GLD": -0.03},
        },
    }

    if scenario not in scenarios:
        return json.dumps({"error": f"Unknown scenario. Available: {list(scenarios.keys())}"})

    sc = scenarios[scenario]
    prices = market_data_fetcher.get_current_prices(
        [p["ticker"] for p in DEMO_PORTFOLIO["positions"]]
    )
    if prices.empty:
        return json.dumps({"error": "Unable to fetch prices"})

    price_lookup = {row["ticker"]: row["price"] for _, row in prices.iterrows()}

    total_loss = 0
    position_impacts = []

    for pos in DEMO_PORTFOLIO["positions"]:
        current_price = price_lookup.get(pos["ticker"])
        if current_price is None:
            continue

        shock = sc["shocks"].get(pos["ticker"], -0.10)
        stressed_price = current_price * (1 + shock)
        position_loss = pos["shares"] * (stressed_price - current_price)
        total_loss += position_loss

        position_impacts.append({
            "ticker": pos["ticker"],
            "current_price": round(current_price, 2),
            "stressed_price": round(stressed_price, 2),
            "shock_pct": round(shock * 100, 1),
            "position_loss": round(position_loss, 2),
        })

    # Check if margin call would be triggered
    total_mv = sum(
        pos["shares"] * price_lookup.get(pos["ticker"], 0)
        for pos in DEMO_PORTFOLIO["positions"]
        if pos["ticker"] in price_lookup
    )
    stressed_mv = total_mv + total_loss
    stressed_equity = stressed_mv * 0.5  # Simplified
    margin_call_triggered = stressed_equity < stressed_mv * DEMO_PORTFOLIO["maintenance_margin_pct"]

    return json.dumps({
        "scenario": scenario,
        "description": sc["description"],
        "total_portfolio_loss": round(total_loss, 2),
        "total_portfolio_loss_pct": round((total_loss / total_mv) * 100, 1) if total_mv > 0 else 0,
        "margin_call_triggered": margin_call_triggered,
        "position_impacts": position_impacts,
        "stressed_portfolio_value": round(stressed_mv, 2),
        "original_portfolio_value": round(total_mv, 2),
    })


@tool
def estimate_margin_call_probability(
    time_horizon_days: int = 5,
    confidence_level: float = 0.95,
) -> str:
    """Estimate the probability of a margin call within a given time horizon.

    Uses historical volatility and Monte Carlo simulation.

    Args:
        time_horizon_days: Number of days to forecast.
        confidence_level: Confidence level for VaR calculation.
    """
    tickers = [p["ticker"] for p in DEMO_PORTFOLIO["positions"]]
    prices = market_data_fetcher.get_historical_prices(tickers, period="1y")
    current_prices_df = market_data_fetcher.get_current_prices(tickers)

    if prices.empty or current_prices_df.empty:
        return json.dumps({"error": "Insufficient data"})

    returns = prices.pct_change().dropna()
    price_lookup = {row["ticker"]: row["price"] for _, row in current_prices_df.iterrows()}

    # Monte Carlo simulation
    n_simulations = 1000
    margin_call_count = 0

    for _ in range(n_simulations):
        total_mv = 0
        for pos in DEMO_PORTFOLIO["positions"]:
            current_price = price_lookup.get(pos["ticker"])
            if current_price is None or pos["ticker"] not in returns.columns:
                continue

            ticker_returns = returns[pos["ticker"]].dropna()
            if len(ticker_returns) < 20:
                continue

            # Simulate forward returns
            mu = float(ticker_returns.mean())
            sigma = float(ticker_returns.std())
            sim_return = np.random.normal(mu * time_horizon_days, sigma * np.sqrt(time_horizon_days))
            sim_price = current_price * (1 + sim_return)
            total_mv += pos["shares"] * sim_price

        if total_mv > 0:
            sim_equity = total_mv * 0.5
            if sim_equity < total_mv * DEMO_PORTFOLIO["maintenance_margin_pct"]:
                margin_call_count += 1

    margin_call_probability = margin_call_count / n_simulations

    return json.dumps({
        "time_horizon_days": time_horizon_days,
        "margin_call_probability": round(margin_call_probability * 100, 1),
        "confidence_level": confidence_level,
        "simulations_run": n_simulations,
        "risk_assessment": (
            "CRITICAL" if margin_call_probability > 0.3
            else "HIGH" if margin_call_probability > 0.15
            else "ELEVATED" if margin_call_probability > 0.05
            else "LOW"
        ),
        "recommendation": (
            "Immediate action required: reduce positions or add collateral"
            if margin_call_probability > 0.3
            else "Consider reducing leverage or hedging exposure"
            if margin_call_probability > 0.15
            else "Monitor closely, prepare contingency plans"
            if margin_call_probability > 0.05
            else "Current margin levels appear adequate"
        ),
    })


def create_margin_impact_agent() -> Agent:
    """Create and return the Margin Impact Agent."""
    model = BedrockModel(
        model_id=BEDROCK_MODEL_ID,
        region_name=AWS_REGION,
        temperature=0.1,
    )

    agent = Agent(
        model=model,
        tools=[
            compute_portfolio_margin_risk,
            run_stress_test,
            estimate_margin_call_probability,
        ],
        system_prompt="""You are a Margin Impact Analysis Agent specializing in margin risk management for clearing and settlement.
Your role is to:
1. Assess current margin utilization and identify margin call risk
2. Run stress tests under historical and hypothetical scenarios
3. Estimate margin call probabilities using Monte Carlo simulation
4. Recommend actions to mitigate margin shortfall risk

Key concepts:
- Initial margin vs maintenance margin requirements
- Portfolio VaR (Value at Risk) under stress
- Margin call triggers and cascading effects
- Collateral optimization strategies

When reporting, include:
- Current margin utilization and buffer
- Probability of margin call within various time horizons
- Worst-case loss under each stress scenario
- Whether margin call would cascade to affect other counterparties
- Specific recommended actions (reduce positions, add collateral, hedge)""",
    )
    return agent
