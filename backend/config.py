import os
from dotenv import load_dotenv

load_dotenv()

# AWS Bedrock Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514")

# API Keys (free tier)
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# Market Data Configuration
MONITORED_TICKERS = [
    # Major Banks (systemically important)
    "JPM", "BAC", "C", "WFC", "GS", "MS", "DB", "UBS", "CS", "HSBC",
    # Regional Banks (SVB-style risk)
    "SCHW", "USB", "PNC", "TFC", "FITB",
    # Insurance / Financial Services
    "BRK-B", "AIG", "MET", "PRU",
    # Major Indices (ETFs as proxies)
    "SPY", "QQQ", "IWM", "EFA", "EEM",
    # Bonds / Fixed Income
    "TLT", "HYG", "LQD", "AGG",
    # Commodities
    "GLD", "USO", "UNG",
    # Crypto proxies
    "BITO",
    # Volatility
    "UVXY",
    # FX proxies
    "UUP", "FXE", "FXY",
]

# FRED Series IDs for macro indicators
FRED_SERIES = {
    "VIX": "VIXCLS",
    "CREDIT_SPREAD": "BAMLC0A0CM",       # ICE BofA US Corporate Index OAS
    "TREASURY_10Y": "DGS10",
    "TREASURY_2Y": "DGS2",
    "FED_FUNDS": "FEDFUNDS",
    "TED_SPREAD": "TEDRATE",
    "MOVE_INDEX": "MOVE",                  # Bond volatility
}

# Sentiment Analysis Keywords
RISK_KEYWORDS = [
    "default", "bankruptcy", "insolvency", "margin call", "liquidity crisis",
    "bank run", "contagion", "systemic risk", "credit downgrade", "debt ceiling",
    "rate hike", "recession", "bear market", "crash", "collapse", "bailout",
    "regulatory action", "SEC investigation", "fraud", "manipulation",
    "counterparty risk", "exposure", "write-down", "impairment", "loss",
    "volatility spike", "flash crash", "circuit breaker", "trading halt",
    "stress test", "capital shortfall", "leverage", "deleveraging",
]

POSITIVE_KEYWORDS = [
    "growth", "profit", "beat", "strong", "upgrade", "bullish", "gain", "rally",
]

# Contagion Model Parameters
SIR_INFECTION_RATE = 0.3    # Beta: rate of risk propagation
SIR_RECOVERY_RATE = 0.1    # Gamma: rate of risk dissipation
CORRELATION_THRESHOLD = 0.6  # Min correlation to form graph edge
ANOMALY_ZSCORE_THRESHOLD = 2.0  # Z-score threshold for anomaly detection

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
