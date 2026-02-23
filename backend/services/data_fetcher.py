"""Data fetching service for market data, macro indicators, and news."""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
import json
import os
import httpx
import random

from backend.config import (
    MONITORED_TICKERS,
    FRED_API_KEY,
    FINNHUB_API_KEY,
    FRED_SERIES,
    RISK_KEYWORDS,
    POSITIVE_KEYWORDS,
)


class MarketDataFetcher:
    """Fetches real-time and historical market data from yFinance."""

    def __init__(self):
        self._cache: dict = {}
        self._cache_ttl = 300  # 5 minutes

    # Fallback prices for when yFinance is unreachable
    _FALLBACK_PRICES = {
        "JPM": 195.50, "BAC": 37.80, "C": 58.40, "WFC": 55.20, "GS": 410.30,
        "MS": 95.60, "DB": 15.80, "UBS": 28.90, "CS": 2.10, "HSBC": 41.50,
        "SCHW": 68.20, "USB": 42.10, "PNC": 155.30, "TFC": 36.80, "FITB": 35.40,
        "BRK-B": 365.00, "AIG": 68.50, "MET": 72.30, "PRU": 108.60,
        "SPY": 502.40, "QQQ": 432.10, "IWM": 198.50, "EFA": 77.90, "EEM": 42.30,
        "TLT": 92.80, "HYG": 76.50, "LQD": 108.20, "AGG": 99.60,
        "GLD": 190.50, "USO": 72.40, "UNG": 7.80,
        "BITO": 22.30, "UVXY": 18.60,
        "UUP": 28.40, "FXE": 104.50, "FXY": 66.70,
    }

    def get_current_prices(self, tickers: Optional[list[str]] = None) -> pd.DataFrame:
        """Get current price data for monitored tickers."""
        tickers = tickers or MONITORED_TICKERS
        try:
            data = yf.download(tickers, period="5d", progress=False, threads=True)
            if data.empty:
                return self._get_fallback_prices(tickers)

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

            if not result:
                return self._get_fallback_prices(tickers)
            return pd.DataFrame(result)
        except Exception as e:
            print(f"Error fetching market data: {e}, using fallback data")
            return self._get_fallback_prices(tickers)

    def _get_fallback_prices(self, tickers: list[str]) -> pd.DataFrame:
        """Return synthetic market data when yFinance is unreachable."""
        rng = random.Random(42)
        result = []
        for ticker in tickers:
            base_price = self._FALLBACK_PRICES.get(ticker, 100.0)
            change_pct = round(rng.gauss(0, 1.5), 2)
            vol_ratio = round(max(0.5, rng.gauss(1.0, 0.4)), 2)
            result.append({
                "ticker": ticker,
                "price": round(base_price * (1 + change_pct / 100), 2),
                "change_pct": change_pct,
                "volume": round(rng.uniform(5e6, 50e6)),
                "volume_avg": round(rng.uniform(8e6, 40e6)),
                "volume_ratio": vol_ratio,
                "timestamp": datetime.now().isoformat(),
            })
        return pd.DataFrame(result)

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
            return self._get_fallback_correlation_matrix(tickers or MONITORED_TICKERS)
        returns = prices.pct_change().dropna()
        corr = returns.corr()
        if corr.empty:
            return self._get_fallback_correlation_matrix(tickers or MONITORED_TICKERS)
        return corr

    def _get_fallback_correlation_matrix(self, tickers: list[str]) -> pd.DataFrame:
        """Generate a realistic synthetic correlation matrix when yFinance is unreachable."""
        # Sector groupings for realistic intra-sector correlations
        sector_map = {
            "Major Banks": ["JPM", "BAC", "C", "WFC", "GS", "MS", "DB", "UBS", "CS", "HSBC"],
            "Regional Banks": ["SCHW", "USB", "PNC", "TFC", "FITB"],
            "Insurance": ["BRK-B", "AIG", "MET", "PRU"],
            "Equity Index": ["SPY", "QQQ", "IWM", "EFA", "EEM"],
            "Fixed Income": ["TLT", "HYG", "LQD", "AGG"],
            "Commodities": ["GLD", "USO", "UNG"],
            "Crypto": ["BITO"],
            "Volatility": ["UVXY"],
            "FX": ["UUP", "FXE", "FXY"],
        }
        ticker_to_sector = {}
        for sector, members in sector_map.items():
            for t in members:
                ticker_to_sector[t] = sector

        n = len(tickers)
        rng = np.random.RandomState(42)
        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                si = ticker_to_sector.get(tickers[i], "Other")
                sj = ticker_to_sector.get(tickers[j], "Other")
                if si == sj:
                    c = rng.uniform(0.6, 0.9)
                elif {si, sj} & {"Major Banks", "Regional Banks"} == {si, sj}:
                    c = rng.uniform(0.5, 0.75)
                elif "Volatility" in (si, sj):
                    c = rng.uniform(-0.5, -0.2)
                elif "Fixed Income" in (si, sj) and "Equity Index" in (si, sj):
                    c = rng.uniform(-0.3, 0.1)
                else:
                    c = rng.uniform(0.1, 0.5)
                corr[i, j] = c
                corr[j, i] = c

        return pd.DataFrame(corr, index=tickers, columns=tickers)


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

    async def get_batch_sentiment_scores(
        self,
        tickers: list[str],
        days_back: int = 3,
    ) -> dict[str, float]:
        """Compute keyword-based sentiment scores for a batch of tickers.

        Returns dict mapping ticker -> sentiment_score (-1 to +1).
        Defaults to 0.0 (neutral) when news is unavailable.
        """
        scores: dict[str, float] = {}
        for ticker in tickers:
            try:
                articles = await self.get_company_news(ticker, days_back=days_back)
                if not articles:
                    scores[ticker] = 0.0
                    continue

                pos_count = 0
                neg_count = 0
                for article in articles:
                    text = f"{article.get('headline', '')} {article.get('summary', '')}".lower()
                    pos_count += sum(1 for w in POSITIVE_KEYWORDS if w in text)
                    neg_count += sum(1 for w in RISK_KEYWORDS if w in text)

                total = pos_count + neg_count
                scores[ticker] = round((pos_count - neg_count) / total, 2) if total > 0 else 0.0
            except Exception:
                scores[ticker] = 0.0
        return scores

    def _get_fallback_news(self, ticker: str) -> list[dict]:
        """Return empty news when API is unavailable."""
        return []


# Singleton instances
market_data_fetcher = MarketDataFetcher()
fred_fetcher = FREDDataFetcher()
news_fetcher = NewsFetcher()
