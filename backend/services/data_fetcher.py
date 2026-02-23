"""Data fetching service for market data, macro indicators, and news."""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
import json
import os
import httpx

from backend.config import (
    MONITORED_TICKERS,
    FRED_API_KEY,
    FINNHUB_API_KEY,
    FRED_SERIES,
)


class MarketDataFetcher:
    """Fetches real-time and historical market data from yFinance."""

    def __init__(self):
        self._cache: dict = {}
        self._cache_ttl = 300  # 5 minutes

    def get_current_prices(self, tickers: Optional[list[str]] = None) -> pd.DataFrame:
        """Get current price data for monitored tickers."""
        tickers = tickers or MONITORED_TICKERS
        try:
            data = yf.download(tickers, period="5d", progress=False, threads=True)
            if data.empty:
                return pd.DataFrame()

            result = []
            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        close = data["Close"]
                        volume = data["Volume"]
                    else:
                        close = data["Close"][ticker]
                        volume = data["Volume"][ticker]

                    if close.empty or close.isna().all():
                        continue

                    current_price = float(close.iloc[-1])
                    prev_price = float(close.iloc[-2]) if len(close) > 1 else current_price
                    change_pct = ((current_price - prev_price) / prev_price) * 100

                    current_vol = float(volume.iloc[-1])
                    avg_vol = float(volume.mean())
                    vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0

                    result.append({
                        "ticker": ticker,
                        "price": current_price,
                        "change_pct": round(change_pct, 2),
                        "volume": current_vol,
                        "volume_avg": avg_vol,
                        "volume_ratio": round(vol_ratio, 2),
                        "timestamp": datetime.now().isoformat(),
                    })
                except (KeyError, IndexError):
                    continue

            return pd.DataFrame(result)
        except Exception as e:
            print(f"Error fetching market data: {e}")
            return pd.DataFrame()

    def get_historical_prices(
        self,
        tickers: Optional[list[str]] = None,
        period: str = "6mo",
    ) -> pd.DataFrame:
        """Get historical closing prices for correlation analysis."""
        tickers = tickers or MONITORED_TICKERS
        try:
            data = yf.download(tickers, period=period, progress=False, threads=True)
            if data.empty:
                return pd.DataFrame()
            return data["Close"].dropna(axis=1, how="all").ffill()
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return pd.DataFrame()

    def get_correlation_matrix(
        self,
        tickers: Optional[list[str]] = None,
        period: str = "6mo",
    ) -> pd.DataFrame:
        """Compute rolling correlation matrix from historical prices."""
        prices = self.get_historical_prices(tickers, period)
        if prices.empty:
            return pd.DataFrame()
        returns = prices.pct_change().dropna()
        return returns.corr()


class FREDDataFetcher:
    """Fetches macro indicators from FRED API."""

    def __init__(self):
        self.api_key = FRED_API_KEY
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"

    async def get_indicator(self, series_id: str, limit: int = 30) -> list[dict]:
        """Fetch a single FRED series."""
        if not self.api_key:
            return self._get_fallback_data(series_id)

        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.base_url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                observations = data.get("observations", [])
                return [
                    {"date": obs["date"], "value": float(obs["value"])}
                    for obs in observations
                    if obs["value"] != "."
                ]
        except Exception as e:
            print(f"Error fetching FRED data for {series_id}: {e}")
            return self._get_fallback_data(series_id)

    def _get_fallback_data(self, series_id: str) -> list[dict]:
        """Return synthetic fallback data when API is unavailable."""
        fallback_values = {
            "VIXCLS": 18.5,
            "BAMLC0A0CM": 1.35,
            "DGS10": 4.25,
            "DGS2": 4.50,
            "FEDFUNDS": 4.50,
            "TEDRATE": 0.25,
        }
        value = fallback_values.get(series_id, 1.0)
        return [{"date": datetime.now().strftime("%Y-%m-%d"), "value": value}]

    async def get_all_indicators(self) -> dict[str, list[dict]]:
        """Fetch all configured FRED indicators."""
        results = {}
        for name, series_id in FRED_SERIES.items():
            results[name] = await self.get_indicator(series_id)
        return results


class NewsFetcher:
    """Fetches financial news from Finnhub."""

    def __init__(self):
        self.api_key = FINNHUB_API_KEY
        self.base_url = "https://finnhub.io/api/v1"

    async def get_company_news(
        self,
        ticker: str,
        days_back: int = 7,
    ) -> list[dict]:
        """Fetch recent news for a specific company."""
        if not self.api_key:
            return self._get_fallback_news(ticker)

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/company-news",
                    params={
                        "symbol": ticker,
                        "from": start_date,
                        "to": end_date,
                        "token": self.api_key,
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                articles = resp.json()
                return articles[:20]  # Limit to 20 most recent
        except Exception as e:
            print(f"Error fetching news for {ticker}: {e}")
            return self._get_fallback_news(ticker)

    async def get_market_news(self, category: str = "general") -> list[dict]:
        """Fetch general market news."""
        if not self.api_key:
            return []

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/news",
                    params={"category": category, "token": self.api_key},
                    timeout=10,
                )
                resp.raise_for_status()
                return resp.json()[:30]
        except Exception as e:
            print(f"Error fetching market news: {e}")
            return []

    def _get_fallback_news(self, ticker: str) -> list[dict]:
        """Return empty news when API is unavailable."""
        return []


# Singleton instances
market_data_fetcher = MarketDataFetcher()
fred_fetcher = FREDDataFetcher()
news_fetcher = NewsFetcher()
