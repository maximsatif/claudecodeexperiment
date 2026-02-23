from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class GraphNode(BaseModel):
    id: str
    label: str
    sector: str
    risk_score: float  # 0-100
    status: str  # "healthy", "stressed", "critical"
    price_change_pct: float
    volume_anomaly: bool


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float  # correlation strength
    contagion_risk: float  # 0-1 probability of risk transmission


class ContagionGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    timestamp: datetime
    systemic_risk_score: float  # 0-100 aggregate score


class RiskAlert(BaseModel):
    id: str
    severity: str  # "low", "medium", "high", "critical"
    title: str
    description: str
    affected_entities: list[str]
    timestamp: datetime
    contagion_probability: float
    margin_impact_estimate: Optional[float] = None


class MarketDataPoint(BaseModel):
    ticker: str
    price: float
    change_pct: float
    volume: float
    volume_avg: float
    volume_ratio: float
    timestamp: datetime


class MacroIndicator(BaseModel):
    name: str
    value: float
    previous_value: float
    change: float
    signal: str  # "normal", "elevated", "warning", "critical"


class SentimentResult(BaseModel):
    ticker: str
    sentiment_score: float  # -1 to 1
    num_articles: int
    key_themes: list[str]
    risk_keywords_found: list[str]


class MarginImpact(BaseModel):
    portfolio_var: float  # Value at Risk
    margin_requirement: float
    margin_shortfall_probability: float
    stress_test_results: dict[str, float]  # scenario_name -> loss_estimate
    recommendations: list[str]


class RiskNarrative(BaseModel):
    summary: str
    risk_level: str  # "low", "moderate", "elevated", "high", "critical"
    key_findings: list[str]
    contagion_pathways: list[str]
    recommended_actions: list[str]
    timestamp: datetime


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    risk_data: Optional[dict] = None


class DashboardData(BaseModel):
    graph: ContagionGraph
    alerts: list[RiskAlert]
    market_data: list[MarketDataPoint]
    macro_indicators: list[MacroIndicator]
    narrative: RiskNarrative
    margin_impact: Optional[MarginImpact] = None
