"""Market Data Agent - Fetches and analyzes market data from yFinance and FRED."""

import json
from datetime import datetime
from typing import Any

from strands import Agent, tool
from strands.models import BedrockModel

from backend.config import BEDROCK_MODEL_ID, AWS_REGION, MONITORED_TICKERS
from backend.services.data_fetcher import market_data_fetcher, fred_fetcher


@tool
def fetch_market_prices(tickers: str = "") -> str:
    """Fetch current market prices and volume data for monitored tickers.

    Args:
        tickers: Comma-separated list of tickers, or empty for all monitored tickers.
    """
    ticker_list = [t.strip() for t in tickers.split(",")] if tickers else None
    df = market_data_fetcher.get_current_prices(ticker_list)
    if df.empty:
        return json.dumps({"error": "No market data available", "data": []})
    return df.to_json(orient="records")


@tool
def fetch_correlation_matrix(period: str = "6mo") -> str:
    """Compute correlation matrix of returns for monitored assets.

    Args:
        period: Historical period for correlation calculation (e.g., '3mo', '6mo', '1y').
    """
    corr = market_data_fetcher.get_correlation_matrix(period=period)
    if corr.empty:
        return json.dumps({"error": "Unable to compute correlations"})
    # Return as nested dict for readability
    result = {}
    for ticker in corr.columns:
        result[ticker] = {
            other: round(float(corr.loc[ticker, other]), 3)
            for other in corr.columns
            if abs(corr.loc[ticker, other]) > 0.5 and ticker != other
        }
    return json.dumps(result)


@tool
def fetch_macro_indicators() -> str:
    """Fetch key macro indicators from FRED (VIX, credit spreads, Treasury yields, etc.)."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, fred_fetcher.get_all_indicators()).result()
        else:
            result = asyncio.run(fred_fetcher.get_all_indicators())
    except RuntimeError:
        result = asyncio.run(fred_fetcher.get_all_indicators())

    # Format for readability
    formatted = {}
    for name, data_points in result.items():
        if data_points:
            latest = data_points[0]
            previous = data_points[1] if len(data_points) > 1 else latest
            formatted[name] = {
                "current_value": latest["value"],
                "previous_value": previous["value"],
                "change": round(latest["value"] - previous["value"], 4),
                "date": latest["date"],
            }
    return json.dumps(formatted)


@tool
def detect_volume_anomalies(threshold: float = 2.0) -> str:
    """Detect tickers with abnormal trading volume.

    Args:
        threshold: Volume ratio threshold to flag as anomalous (default: 2.0x average).
    """
    df = market_data_fetcher.get_current_prices()
    if df.empty:
        return json.dumps({"anomalies": []})

    anomalies = df[df["volume_ratio"] > threshold].to_dict(orient="records")
    return json.dumps({
        "anomalies": anomalies,
        "total_monitored": len(df),
        "anomaly_count": len(anomalies),
    })


def create_market_data_agent() -> Agent:
    """Create and return the Market Data Agent."""
    model = BedrockModel(
        model_id=BEDROCK_MODEL_ID,
        region_name=AWS_REGION,
        temperature=0.1,
    )

    agent = Agent(
        model=model,
        tools=[
            fetch_market_prices,
            fetch_correlation_matrix,
            fetch_macro_indicators,
            detect_volume_anomalies,
        ],
        system_prompt="""You are a Market Data Analysis Agent specializing in capital markets surveillance.
Your role is to:
1. Fetch and analyze current market prices across equities, fixed income, commodities, FX, and crypto
2. Compute cross-asset correlation matrices to identify interconnectedness
3. Monitor macro indicators (VIX, credit spreads, yield curves) for stress signals
4. Detect volume anomalies that may indicate unusual market activity

When analyzing data, focus on:
- Cross-market correlations breaking down or spiking (regime changes)
- Unusual volume patterns across multiple asset classes simultaneously
- Macro indicator movements that suggest stress (VIX spikes, credit spread widening, yield curve inversions)
- Divergences between correlated assets that may signal dislocations

Always provide structured, quantitative analysis with specific numbers and percentages.""",
    )
    return agent
