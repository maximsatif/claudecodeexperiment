"""Orchestrator Agent - Coordinates all sub-agents for comprehensive risk analysis."""

import json
from datetime import datetime
from typing import Optional

from strands import Agent, tool
from strands.models import BedrockModel

from backend.config import BEDROCK_MODEL_ID, AWS_REGION
from backend.agents.market_data_agent import create_market_data_agent
from backend.agents.news_sentiment_agent import create_news_sentiment_agent
from backend.agents.contagion_graph_agent import create_contagion_graph_agent
from backend.agents.risk_analysis_agent import create_risk_analysis_agent
from backend.agents.margin_impact_agent import create_margin_impact_agent
from backend.agents.narrative_agent import create_narrative_agent


class ContagionGuardOrchestrator:
    """Orchestrates all ContagionGuard agents for comprehensive risk analysis."""

    def __init__(self):
        self._agents: dict = {}
        self._last_analysis: Optional[dict] = None

    def _get_agent(self, name: str) -> Agent:
        """Lazy-initialize agents on demand."""
        if name not in self._agents:
            creators = {
                "market_data": create_market_data_agent,
                "news_sentiment": create_news_sentiment_agent,
                "contagion_graph": create_contagion_graph_agent,
                "risk_analysis": create_risk_analysis_agent,
                "margin_impact": create_margin_impact_agent,
                "narrative": create_narrative_agent,
            }
            if name in creators:
                self._agents[name] = creators[name]()
        return self._agents.get(name)

    async def run_full_analysis(self) -> dict:
        """Run a complete risk analysis using all agents.

        This is the main entry point for the dashboard.
        Returns a comprehensive risk assessment.
        """
        results = {}

        # Step 1: Gather market data
        market_agent = self._get_agent("market_data")
        if market_agent:
            try:
                market_response = market_agent(
                    "Analyze current market conditions. Fetch current prices for all monitored "
                    "tickers, compute the correlation matrix, check macro indicators, and "
                    "detect any volume anomalies. Provide a structured summary."
                )
                results["market_data"] = str(market_response)
            except Exception as e:
                results["market_data"] = json.dumps({"error": str(e)})

        # Step 2: Check news & sentiment
        news_agent = self._get_agent("news_sentiment")
        if news_agent:
            try:
                news_response = news_agent(
                    "Scan recent news for the top 5 major banks (JPM, BAC, C, GS, MS) "
                    "and identify any risk signals. Analyze sentiment trends and flag "
                    "any concerning patterns."
                )
                results["news_sentiment"] = str(news_response)
            except Exception as e:
                results["news_sentiment"] = json.dumps({"error": str(e)})

        # Step 3: Build contagion graph
        graph_agent = self._get_agent("contagion_graph")
        if graph_agent:
            try:
                graph_response = graph_agent(
                    "Build the contagion graph from current market data. Identify "
                    "systemically important nodes and compute the financial R0. "
                    "Report the systemic risk score and any critical findings."
                )
                results["contagion_graph"] = str(graph_response)
            except Exception as e:
                results["contagion_graph"] = json.dumps({"error": str(e)})

        # Step 4: Run risk analysis
        risk_agent = self._get_agent("risk_analysis")
        if risk_agent:
            try:
                risk_response = risk_agent(
                    "Run a comprehensive risk analysis: detect price anomalies, "
                    "check for correlation breakdowns, compute portfolio risk metrics, "
                    "and check for regime changes. Report all findings."
                )
                results["risk_analysis"] = str(risk_response)
            except Exception as e:
                results["risk_analysis"] = json.dumps({"error": str(e)})

        # Step 5: Assess margin impact
        margin_agent = self._get_agent("margin_impact")
        if margin_agent:
            try:
                margin_response = margin_agent(
                    "Assess current margin risk for the portfolio. Run stress tests "
                    "under the 'credit_crisis' and 'svb_scenario' scenarios. "
                    "Estimate margin call probability over the next 5 days."
                )
                results["margin_impact"] = str(margin_response)
            except Exception as e:
                results["margin_impact"] = json.dumps({"error": str(e)})

        # Step 6: Generate narrative report
        narrative_agent = self._get_agent("narrative")
        if narrative_agent:
            try:
                narrative_response = narrative_agent(
                    f"""Generate a comprehensive risk briefing based on the following data:

Market Data Analysis: {results.get('market_data', 'N/A')[:1000]}
News & Sentiment: {results.get('news_sentiment', 'N/A')[:1000]}
Contagion Graph: {results.get('contagion_graph', 'N/A')[:1000]}
Risk Analysis: {results.get('risk_analysis', 'N/A')[:1000]}
Margin Impact: {results.get('margin_impact', 'N/A')[:1000]}

Synthesize all findings into a structured risk briefing with:
1. Overall risk level assessment
2. Top 3-5 key findings
3. Identified contagion pathways
4. Margin impact assessment
5. Recommended actions (immediate, short-term, medium-term)"""
                )
                results["narrative"] = str(narrative_response)
            except Exception as e:
                results["narrative"] = json.dumps({"error": str(e)})

        self._last_analysis = {
            "timestamp": datetime.now().isoformat(),
            "results": results,
        }

        return self._last_analysis

    async def run_shock_simulation(self, ticker: str, magnitude: float = 0.8) -> dict:
        """Simulate a contagion shock and analyze its impact."""
        graph_agent = self._get_agent("contagion_graph")
        margin_agent = self._get_agent("margin_impact")
        narrative_agent = self._get_agent("narrative")

        results = {}

        if graph_agent:
            try:
                sim_response = graph_agent(
                    f"Simulate a contagion shock originating from {ticker} with magnitude "
                    f"{magnitude}. Analyze the propagation pattern and identify which "
                    f"entities are affected. Also compute the R0."
                )
                results["simulation"] = str(sim_response)
            except Exception as e:
                results["simulation"] = json.dumps({"error": str(e)})

        if margin_agent:
            try:
                margin_response = margin_agent(
                    f"Given a shock to {ticker}, run stress tests to estimate the margin "
                    f"impact. Use the 'credit_crisis' scenario and estimate margin call "
                    f"probability."
                )
                results["margin_impact"] = str(margin_response)
            except Exception as e:
                results["margin_impact"] = json.dumps({"error": str(e)})

        if narrative_agent:
            try:
                narrative_response = narrative_agent(
                    f"""Generate a shock scenario briefing:

Shock Source: {ticker}
Shock Magnitude: {magnitude}
Simulation Results: {results.get('simulation', 'N/A')[:1500]}
Margin Impact: {results.get('margin_impact', 'N/A')[:1500]}

Provide a clear narrative of:
1. How the shock propagates through the financial system
2. Which entities are most at risk
3. Expected margin call cascade timing
4. Recommended emergency actions"""
                )
                results["narrative"] = str(narrative_response)
            except Exception as e:
                results["narrative"] = json.dumps({"error": str(e)})

        return {
            "timestamp": datetime.now().isoformat(),
            "shock_source": ticker,
            "shock_magnitude": magnitude,
            "results": results,
        }

    async def chat(self, message: str) -> str:
        """Handle a chat message using the narrative agent with context from last analysis."""
        narrative_agent = self._get_agent("narrative")
        if not narrative_agent:
            return "Agent not available"

        context = ""
        if self._last_analysis:
            context = f"\n\nLatest analysis context (from {self._last_analysis['timestamp']}):\n"
            for key, value in self._last_analysis.get("results", {}).items():
                context += f"\n{key}: {str(value)[:500]}"

        try:
            response = narrative_agent(
                f"User question: {message}\n\n"
                f"Context from latest analysis: {context[:3000]}\n\n"
                f"Provide a clear, concise answer based on the available data. "
                f"If you don't have relevant data, say so and suggest what analysis to run."
            )
            return str(response)
        except Exception as e:
            return f"Error processing question: {str(e)}"


# Global orchestrator instance
orchestrator = ContagionGuardOrchestrator()
