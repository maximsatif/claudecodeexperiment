"""
AWS Lambda function for the News Sentiment Bedrock Agent action group.

This Lambda handles all three tools:
  - getCompanyNews: Fetch recent news for a ticker
  - scanRiskSignals: Scan multiple tickers for risk signals
  - analyzeSentimentTrend: Analyze sentiment trend over 14 days

Environment variables required:
  - FINNHUB_API_KEY: Your Finnhub API key (free tier works)

Deployment:
  1. Create a Lambda function (Python 3.12 runtime)
  2. Set the FINNHUB_API_KEY environment variable
  3. Increase timeout to 60 seconds (default 3s is too short for API calls)
  4. Increase memory to 256 MB
  5. Attach the IAM role with bedrock:InvokeModel permission (if needed)
"""

import json
import os
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.parse import urlencode

# ─── Configuration ───────────────────────────────────────────────────────────

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

RISK_KEYWORDS = [
    "default", "bankruptcy", "insolvency", "margin call", "liquidity crisis",
    "bank run", "contagion", "systemic risk", "credit downgrade", "debt ceiling",
    "rate hike", "recession", "bear market", "crash", "collapse", "bailout",
    "regulatory action", "sec investigation", "fraud", "manipulation",
    "counterparty risk", "exposure", "write-down", "impairment", "loss",
    "volatility spike", "flash crash", "circuit breaker", "trading halt",
    "stress test", "capital shortfall", "leverage", "deleveraging",
]

POSITIVE_KEYWORDS = [
    "growth", "profit", "beat", "strong", "upgrade", "bullish", "gain", "rally",
]


# ─── Finnhub API helper ─────────────────────────────────────────────────────

def fetch_company_news(ticker: str, days_back: int = 7) -> list[dict]:
    """Fetch company news from Finnhub REST API using only stdlib."""
    if not FINNHUB_API_KEY:
        return []

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    params = urlencode({
        "symbol": ticker,
        "from": start_date,
        "to": end_date,
        "token": FINNHUB_API_KEY,
    })
    url = f"{FINNHUB_BASE_URL}/company-news?{params}"

    try:
        req = Request(url, headers={"User-Agent": "BedrockAgent/1.0"})
        with urlopen(req, timeout=10) as resp:
            articles = json.loads(resp.read().decode())
            return articles[:20]
    except Exception as e:
        print(f"Error fetching news for {ticker}: {e}")
        return []


# ─── Tool implementations ───────────────────────────────────────────────────

def get_company_news(ticker: str) -> dict:
    """Fetch recent news articles for a specific company/ticker."""
    articles = fetch_company_news(ticker, days_back=7)

    if not articles:
        return {"ticker": ticker, "articles": [], "count": 0, "risk_article_count": 0}

    formatted = []
    for article in articles[:10]:
        headline = article.get("headline", "")
        summary = article.get("summary", "")
        text = f"{headline} {summary}".lower()

        found_keywords = [kw for kw in RISK_KEYWORDS if kw in text]

        formatted.append({
            "headline": headline,
            "summary": summary[:200],
            "source": article.get("source", "unknown"),
            "datetime": article.get("datetime", 0),
            "risk_keywords": found_keywords,
            "has_risk_signal": len(found_keywords) > 0,
        })

    return {
        "ticker": ticker,
        "articles": formatted,
        "count": len(formatted),
        "risk_article_count": sum(1 for a in formatted if a["has_risk_signal"]),
    }


def scan_risk_signals(tickers: str = "JPM,BAC,C,GS,MS") -> dict:
    """Scan news for multiple tickers and identify risk signals."""
    ticker_list = [t.strip() for t in tickers.split(",")]
    results = {}

    for ticker in ticker_list[:10]:
        try:
            articles = fetch_company_news(ticker, days_back=3)

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

    return results


def analyze_sentiment_trend(ticker: str) -> dict:
    """Analyze the sentiment trend for a ticker based on recent news."""
    articles = fetch_company_news(ticker, days_back=14)

    if not articles:
        return {
            "ticker": ticker,
            "sentiment_score": 0.0,
            "sentiment": "neutral",
            "positive_signals": 0,
            "negative_signals": 0,
            "articles_analyzed": 0,
            "summary": "No recent news available",
        }

    pos_count = 0
    neg_count = 0
    for article in articles:
        text = f"{article.get('headline', '')} {article.get('summary', '')}".lower()
        pos_count += sum(1 for w in POSITIVE_KEYWORDS if w in text)
        neg_count += sum(1 for w in RISK_KEYWORDS if w in text)

    total = pos_count + neg_count
    sentiment_score = (pos_count - neg_count) / total if total > 0 else 0.0

    return {
        "ticker": ticker,
        "sentiment_score": round(sentiment_score, 2),
        "sentiment": "positive" if sentiment_score > 0.2 else "negative" if sentiment_score < -0.2 else "neutral",
        "positive_signals": pos_count,
        "negative_signals": neg_count,
        "articles_analyzed": len(articles),
    }


# ─── Lambda handler (Bedrock Agent format) ───────────────────────────────────

def lambda_handler(event, context):
    """
    AWS Bedrock Agent Lambda handler.

    Bedrock Agents invoke Lambda with a specific event structure containing:
      - actionGroup: name of the action group
      - apiPath: the path from the OpenAPI schema (e.g., /get-company-news)
      - httpMethod: POST
      - requestBody: the parameters from the agent

    The response must follow Bedrock's expected format.
    """
    print(f"Received event: {json.dumps(event)}")

    # Extract the API path and parameters
    api_path = event.get("apiPath", "")
    request_body = event.get("requestBody", {})

    # Parse parameters from the request body
    parameters = {}
    if request_body and "content" in request_body:
        body_content = request_body["content"].get("application/json", {})
        if "properties" in body_content:
            for prop in body_content["properties"]:
                parameters[prop["name"]] = prop["value"]

    # Route to the correct tool
    if api_path == "/get-company-news":
        ticker = parameters.get("ticker", "JPM")
        result = get_company_news(ticker)

    elif api_path == "/scan-risk-signals":
        tickers = parameters.get("tickers", "JPM,BAC,C,GS,MS")
        result = scan_risk_signals(tickers)

    elif api_path == "/analyze-sentiment-trend":
        ticker = parameters.get("ticker", "JPM")
        result = analyze_sentiment_trend(ticker)

    else:
        result = {"error": f"Unknown API path: {api_path}"}

    # Format response for Bedrock Agent
    response = {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "apiPath": api_path,
            "httpMethod": event.get("httpMethod", "POST"),
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(result)
                }
            }
        }
    }

    print(f"Returning response for {api_path}")
    return response
