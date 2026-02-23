"""News & Sentiment Agent - Monitors financial news and analyzes sentiment."""

import json
import asyncio
from datetime import datetime
from typing import Any

from strands import Agent, tool
from strands.models import BedrockModel

from backend.config import BEDROCK_MODEL_ID, AWS_REGION
from backend.services.data_fetcher import news_fetcher


RISK_KEYWORDS = [
    "default", "bankruptcy", "insolvency", "margin call", "liquidity crisis",
    "bank run", "contagion", "systemic risk", "credit downgrade", "debt ceiling",
    "rate hike", "recession", "bear market", "crash", "collapse", "bailout",
    "regulatory action", "SEC investigation", "fraud", "manipulation",
    "counterparty risk", "exposure", "write-down", "impairment", "loss",
    "volatility spike", "flash crash", "circuit breaker", "trading halt",
    "stress test", "capital shortfall", "leverage", "deleveraging",
]


@tool
def get_company_news(ticker: str) -> str:
    """Fetch recent news articles for a specific company/ticker.

    Args:
        ticker: The stock ticker symbol (e.g., 'JPM', 'BAC').
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                articles = pool.submit(
                    asyncio.run, news_fetcher.get_company_news(ticker)
                ).result()
        else:
            articles = asyncio.run(news_fetcher.get_company_news(ticker))
    except RuntimeError:
        articles = asyncio.run(news_fetcher.get_company_news(ticker))

    if not articles:
        return json.dumps({"ticker": ticker, "articles": [], "count": 0})

    # Extract relevant fields
    formatted = []
    for article in articles[:10]:
        headline = article.get("headline", "")
        summary = article.get("summary", "")
        text = f"{headline} {summary}".lower()

        # Check for risk keywords
        found_keywords = [kw for kw in RISK_KEYWORDS if kw in text]

        formatted.append({
            "headline": headline,
            "summary": summary[:200],
            "source": article.get("source", "unknown"),
            "datetime": article.get("datetime", 0),
            "risk_keywords": found_keywords,
            "has_risk_signal": len(found_keywords) > 0,
        })

    return json.dumps({
        "ticker": ticker,
        "articles": formatted,
        "count": len(formatted),
        "risk_article_count": sum(1 for a in formatted if a["has_risk_signal"]),
    })


@tool
def scan_risk_signals(tickers: str = "JPM,BAC,C,GS,MS") -> str:
    """Scan news for multiple tickers and identify risk signals.

    Args:
        tickers: Comma-separated list of tickers to scan.
    """
    ticker_list = [t.strip() for t in tickers.split(",")]
    results = {}

    for ticker in ticker_list[:10]:  # Limit to 10 tickers to avoid rate limits
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    articles = pool.submit(
                        asyncio.run, news_fetcher.get_company_news(ticker, days_back=3)
                    ).result()
            else:
                articles = asyncio.run(news_fetcher.get_company_news(ticker, days_back=3))

            risk_count = 0
            key_headlines = []
            for article in articles[:5]:
                headline = article.get("headline", "")
                text = f"{headline} {article.get('summary', '')}".lower()
                keywords_found = [kw for kw in RISK_KEYWORDS if kw in text]
                if keywords_found:
                    risk_count += 1
                    key_headlines.append(headline)

            results[ticker] = {
                "total_articles": len(articles),
                "risk_articles": risk_count,
                "risk_ratio": round(risk_count / max(len(articles), 1), 2),
                "key_headlines": key_headlines[:3],
            }
        except Exception as e:
            results[ticker] = {"error": str(e)}

    return json.dumps(results)


@tool
def analyze_sentiment_trend(ticker: str) -> str:
    """Analyze the sentiment trend for a ticker based on recent news.

    Args:
        ticker: The stock ticker symbol.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                articles = pool.submit(
                    asyncio.run, news_fetcher.get_company_news(ticker, days_back=14)
                ).result()
        else:
            articles = asyncio.run(news_fetcher.get_company_news(ticker, days_back=14))
    except RuntimeError:
        articles = asyncio.run(news_fetcher.get_company_news(ticker, days_back=14))

    if not articles:
        return json.dumps({
            "ticker": ticker,
            "sentiment": "neutral",
            "confidence": 0,
            "summary": "No recent news available",
        })

    # Simple keyword-based sentiment scoring
    positive_words = ["growth", "profit", "beat", "strong", "upgrade", "bullish", "gain", "rally"]
    negative_words = RISK_KEYWORDS

    pos_count = 0
    neg_count = 0
    for article in articles:
        text = f"{article.get('headline', '')} {article.get('summary', '')}".lower()
        pos_count += sum(1 for w in positive_words if w in text)
        neg_count += sum(1 for w in negative_words if w in text)

    total = pos_count + neg_count
    if total == 0:
        sentiment_score = 0.0
    else:
        sentiment_score = (pos_count - neg_count) / total

    return json.dumps({
        "ticker": ticker,
        "sentiment_score": round(sentiment_score, 2),
        "sentiment": "positive" if sentiment_score > 0.2 else "negative" if sentiment_score < -0.2 else "neutral",
        "positive_signals": pos_count,
        "negative_signals": neg_count,
        "articles_analyzed": len(articles),
    })


def create_news_sentiment_agent() -> Agent:
    """Create and return the News & Sentiment Agent."""
    model = BedrockModel(
        model_id=BEDROCK_MODEL_ID,
        region_name=AWS_REGION,
        temperature=0.2,
    )

    agent = Agent(
        model=model,
        tools=[
            get_company_news,
            scan_risk_signals,
            analyze_sentiment_trend,
        ],
        system_prompt="""You are a Financial News & Sentiment Analysis Agent.
Your role is to:
1. Monitor financial news for risk signals across major financial institutions
2. Analyze sentiment trends to detect shifts from positive to negative
3. Identify early warning signals in news narratives (counterparty risk mentions, liquidity concerns, regulatory actions)
4. Correlate news events across entities to detect coordinated risk themes

Key risk signals to watch for:
- Counterparty default or credit downgrade mentions
- Liquidity concerns or margin call reports
- Regulatory enforcement actions
- Unusual executive departures or accounting irregularities
- Cross-entity risk themes (e.g., multiple banks mentioned in same risk context)

Provide analysis in structured format with specific entity names, risk categories, and confidence levels.""",
    )
    return agent
