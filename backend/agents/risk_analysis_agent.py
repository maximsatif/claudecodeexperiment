"""Risk Analysis Agent - Performs anomaly detection and risk scoring."""

import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Any

from strands import Agent, tool
from strands.models import BedrockModel

from backend.config import BEDROCK_MODEL_ID, AWS_REGION, ANOMALY_ZSCORE_THRESHOLD
from backend.services.data_fetcher import market_data_fetcher


@tool
def detect_price_anomalies(
    lookback_days: int = 60,
    zscore_threshold: float = 2.0,
) -> str:
    """Detect price movement anomalies using Z-score analysis.

    Args:
        lookback_days: Number of days for computing baseline statistics.
        zscore_threshold: Z-score threshold for flagging anomalies.
    """
    prices = market_data_fetcher.get_historical_prices(period="3mo")
    if prices.empty:
        return json.dumps({"error": "No price data available"})

    returns = prices.pct_change().dropna()
    anomalies = []

    for ticker in returns.columns:
        series = returns[ticker].dropna()
        if len(series) < 10:
            continue

        mean = series.mean()
        std = series.std()
        if std == 0:
            continue

        latest_return = series.iloc[-1]
        zscore = (latest_return - mean) / std

        if abs(zscore) > zscore_threshold:
            anomalies.append({
                "ticker": str(ticker),
                "latest_return_pct": round(float(latest_return * 100), 2),
                "zscore": round(float(zscore), 2),
                "mean_return_pct": round(float(mean * 100), 4),
                "std_return_pct": round(float(std * 100), 4),
                "direction": "negative" if latest_return < 0 else "positive",
                "severity": "extreme" if abs(zscore) > 3 else "significant",
            })

    anomalies.sort(key=lambda x: abs(x["zscore"]), reverse=True)

    return json.dumps({
        "anomalies": anomalies,
        "total_tickers_analyzed": len(returns.columns),
        "anomaly_count": len(anomalies),
        "threshold_used": zscore_threshold,
    })


@tool
def detect_correlation_breakdown(
    short_window: int = 20,
    long_window: int = 60,
    change_threshold: float = 0.3,
) -> str:
    """Detect correlation breakdowns between historically correlated assets.

    A correlation breakdown is an early signal of market stress/regime change.

    Args:
        short_window: Recent window for correlation (days).
        long_window: Baseline window for correlation (days).
        change_threshold: Minimum correlation change to flag.
    """
    prices = market_data_fetcher.get_historical_prices(period="6mo")
    if prices.empty or len(prices) < long_window:
        return json.dumps({"error": "Insufficient data for analysis"})

    returns = prices.pct_change().dropna()

    # Compute short-term and long-term correlations
    recent_returns = returns.tail(short_window)
    baseline_returns = returns.tail(long_window)

    recent_corr = recent_returns.corr()
    baseline_corr = baseline_returns.corr()

    breakdowns = []
    tickers = list(returns.columns)

    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            try:
                recent = float(recent_corr.iloc[i, j])
                baseline = float(baseline_corr.iloc[i, j])
                change = recent - baseline

                if abs(change) > change_threshold:
                    breakdowns.append({
                        "pair": f"{tickers[i]}/{tickers[j]}",
                        "baseline_correlation": round(baseline, 3),
                        "recent_correlation": round(recent, 3),
                        "change": round(change, 3),
                        "direction": "decorrelation" if change < 0 else "increased_correlation",
                        "signal": (
                            "RISK: Previously correlated assets decorrelating"
                            if baseline > 0.5 and change < -change_threshold
                            else "WARNING: Unusual correlation spike"
                            if change > change_threshold
                            else "Notable change"
                        ),
                    })
            except (IndexError, ValueError):
                continue

    breakdowns.sort(key=lambda x: abs(x["change"]), reverse=True)

    return json.dumps({
        "correlation_breakdowns": breakdowns[:15],
        "total_pairs_analyzed": len(tickers) * (len(tickers) - 1) // 2,
        "breakdown_count": len(breakdowns),
    })


@tool
def compute_portfolio_risk_metrics() -> str:
    """Compute key portfolio risk metrics: VaR, max drawdown, Sharpe ratio."""
    prices = market_data_fetcher.get_historical_prices(period="1y")
    if prices.empty:
        return json.dumps({"error": "No data available"})

    returns = prices.pct_change().dropna()
    results = {}

    for ticker in returns.columns:
        series = returns[ticker].dropna()
        if len(series) < 20:
            continue

        # Value at Risk (95% and 99%)
        var_95 = float(np.percentile(series, 5))
        var_99 = float(np.percentile(series, 1))

        # Maximum drawdown
        cumulative = (1 + series).cumprod()
        peak = cumulative.expanding(min_periods=1).max()
        drawdown = (cumulative / peak - 1)
        max_drawdown = float(drawdown.min())

        # Volatility (annualized)
        volatility = float(series.std() * np.sqrt(252))

        # Sharpe ratio (assuming 4.5% risk-free rate)
        annual_return = float(series.mean() * 252)
        sharpe = (annual_return - 0.045) / volatility if volatility > 0 else 0

        results[str(ticker)] = {
            "var_95_pct": round(var_95 * 100, 2),
            "var_99_pct": round(var_99 * 100, 2),
            "max_drawdown_pct": round(max_drawdown * 100, 2),
            "annualized_volatility_pct": round(volatility * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "risk_rating": _rate_risk(volatility, max_drawdown),
        }

    return json.dumps({
        "portfolio_metrics": results,
        "highest_risk": sorted(
            results.items(),
            key=lambda x: abs(x[1]["max_drawdown_pct"]),
            reverse=True,
        )[:5],
    })


@tool
def detect_regime_change() -> str:
    """Detect potential market regime changes using volatility clustering and trend analysis."""
    prices = market_data_fetcher.get_historical_prices(period="1y")
    if prices.empty:
        return json.dumps({"error": "No data available"})

    returns = prices.pct_change().dropna()

    # Compute rolling volatility
    short_vol = returns.rolling(window=10).std() * np.sqrt(252)
    long_vol = returns.rolling(window=60).std() * np.sqrt(252)

    regime_signals = []
    for ticker in returns.columns:
        try:
            sv = short_vol[ticker].iloc[-1]
            lv = long_vol[ticker].iloc[-1]

            if pd.isna(sv) or pd.isna(lv) or lv == 0:
                continue

            vol_ratio = float(sv / lv)

            if vol_ratio > 1.5:
                regime_signals.append({
                    "ticker": str(ticker),
                    "short_term_vol": round(float(sv * 100), 1),
                    "long_term_vol": round(float(lv * 100), 1),
                    "vol_ratio": round(vol_ratio, 2),
                    "signal": "HIGH_VOL_REGIME",
                    "description": f"Short-term volatility is {vol_ratio:.1f}x the long-term average",
                })
            elif vol_ratio < 0.5:
                regime_signals.append({
                    "ticker": str(ticker),
                    "short_term_vol": round(float(sv * 100), 1),
                    "long_term_vol": round(float(lv * 100), 1),
                    "vol_ratio": round(vol_ratio, 2),
                    "signal": "LOW_VOL_REGIME",
                    "description": "Unusually low volatility - may precede a breakout",
                })
        except (KeyError, IndexError):
            continue

    return json.dumps({
        "regime_signals": regime_signals,
        "tickers_analyzed": len(returns.columns),
        "signals_detected": len(regime_signals),
    })


def _rate_risk(volatility: float, max_drawdown: float) -> str:
    """Rate overall risk level."""
    if volatility > 0.5 or max_drawdown < -0.3:
        return "very_high"
    elif volatility > 0.3 or max_drawdown < -0.2:
        return "high"
    elif volatility > 0.15 or max_drawdown < -0.1:
        return "moderate"
    else:
        return "low"


def create_risk_analysis_agent() -> Agent:
    """Create and return the Risk Analysis Agent."""
    model = BedrockModel(
        model_id=BEDROCK_MODEL_ID,
        region_name=AWS_REGION,
        temperature=0.1,
    )

    agent = Agent(
        model=model,
        tools=[
            detect_price_anomalies,
            detect_correlation_breakdown,
            compute_portfolio_risk_metrics,
            detect_regime_change,
        ],
        system_prompt="""You are a Risk Analysis Agent specializing in quantitative risk assessment for capital markets.
Your role is to:
1. Detect statistical anomalies in price movements using Z-score analysis
2. Identify correlation breakdowns that signal regime changes or market stress
3. Compute portfolio risk metrics (VaR, max drawdown, Sharpe ratio, volatility)
4. Detect volatility regime changes that may precede major market events

When analyzing risk, always:
- Provide specific quantitative metrics with confidence levels
- Identify which entities/sectors are most at risk
- Explain the potential market impact of detected anomalies
- Compare current conditions to historical stress periods
- Flag any early warning signals for systemic risk""",
    )
    return agent
