# ContagionGuard

## AI-Powered Cross-Market Contagion & Margin Risk Early Warning System

**Innovate.DTCC: Industry-Powered AI Hackathon 2026 | Supported by FINOS**

---

### Project Details

ContagionGuard is a **multi-agent AI system** that monitors cross-market signals, builds dynamic contagion graphs, and predicts cascading margin impacts before they materialize. It transforms risk management from reactive firefighting to proactive early warning.

**Problem**: When SVB collapsed in March 2023, cascading margin calls hit counterparties within hours. The 2008 GFC, 2020 COVID crash, and 2023 regional bank crisis all demonstrated how interconnected financial markets amplify localized shocks into systemic crises. Current risk systems detect problems *after* contagion has spread.

**Solution**: ContagionGuard applies **epidemiological modeling** (SIR model) to financial contagion, using 6 specialized AI agents orchestrated via AWS Bedrock to provide 24-48 hour advance warning of cascading margin impacts.

### Key Innovation

- **Financial R0**: Adapts the epidemiological reproduction number (R0) to quantify whether financial contagion will spread or die out
- **Multi-Agent Architecture**: 6 specialized AI agents (Market Data, News/Sentiment, Contagion Graph, Risk Analysis, Margin Impact, Narrative Report) orchestrated via AWS Bedrock Strands SDK
- **Dynamic Contagion Graph**: Real-time network visualization showing risk propagation pathways using PageRank-based "Risk Virality Score"
- **Proactive Margin Intelligence**: Monte Carlo-based margin call probability estimation under multiple stress scenarios

### Team Information

**Team Name**: ContagionGuard

---

## Architecture

```
                     React Dashboard (Vite + TypeScript)
    ┌──────────────────────────────────────────────────────┐
    │  Contagion Graph  │  Risk Heatmap  │  AI Chat (NLP)  │
    └──────────────────────┬───────────────────────────────┘
                           │ REST API
    ┌──────────────────────┴───────────────────────────────┐
    │              FastAPI Backend (Python)                  │
    │                                                       │
    │  ┌─────────────────────────────────────────────────┐ │
    │  │    Orchestrator Agent (AWS Bedrock / Strands)     │ │
    │  │                                                   │ │
    │  │  ┌────────────┐ ┌────────────┐ ┌──────────────┐ │ │
    │  │  │ Market Data │ │  News &    │ │  Contagion   │ │ │
    │  │  │   Agent    │ │ Sentiment  │ │ Graph Agent  │ │ │
    │  │  │ (yFinance  │ │  Agent     │ │ (NetworkX +  │ │ │
    │  │  │  + FRED)   │ │ (Finnhub)  │ │  SIR Model)  │ │ │
    │  │  └────────────┘ └────────────┘ └──────────────┘ │ │
    │  │  ┌────────────┐ ┌────────────┐ ┌──────────────┐ │ │
    │  │  │    Risk    │ │   Margin   │ │  Narrative   │ │ │
    │  │  │  Analysis  │ │   Impact   │ │   Report     │ │ │
    │  │  │   Agent    │ │   Agent    │ │   Agent      │ │ │
    │  │  │ (Anomaly   │ │  (Stress   │ │  (LLM Gen)   │ │ │
    │  │  │ Detection) │ │  Testing)  │ │              │ │ │
    │  │  └────────────┘ └────────────┘ └──────────────┘ │ │
    │  └─────────────────────────────────────────────────┘ │
    └──────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI/LLM** | AWS Bedrock (Claude), Strands Agents SDK |
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **Graph Analysis** | NetworkX, SIR epidemiological model |
| **ML/Analytics** | scikit-learn, pandas, numpy |
| **Data Sources** | yFinance, FRED API, Finnhub API |
| **Frontend** | React 18, TypeScript, Vite, Recharts, Tailwind CSS |
| **Visualization** | Canvas-based force-directed contagion graph |

## Data Sources (All Public/Free)

- **yFinance**: Real-time equity, bond, FX, commodity, and crypto prices/volumes
- **FRED API**: VIX, credit spreads, Treasury yields, interbank rates, macro indicators
- **Finnhub**: Real-time financial news and company-specific sentiment
- **SEC EDGAR**: Company filings and XBRL financial data

## Setup & Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- AWS account with Bedrock access (for AI agents)

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp ../.env.example ../.env
# Edit .env with your AWS credentials and API keys

# Run the backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The dashboard will be available at `http://localhost:5173`

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AWS_REGION` | AWS region for Bedrock | Yes (for AI agents) |
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes (for AI agents) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes (for AI agents) |
| `BEDROCK_MODEL_ID` | Bedrock model ID | No (default: Claude Sonnet) |
| `FRED_API_KEY` | FRED API key | No (uses fallback data) |
| `FINNHUB_API_KEY` | Finnhub API key | No (uses fallback data) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/market-data` | Current prices for all monitored assets |
| `GET` | `/api/correlations` | Cross-asset correlation matrix |
| `GET` | `/api/macro-indicators` | FRED macro indicators (VIX, spreads, yields) |
| `GET` | `/api/graph` | Build contagion graph |
| `POST` | `/api/graph/simulate` | Simulate contagion shock |
| `GET` | `/api/sir-model` | Run SIR model simulation |
| `GET` | `/api/risk-score` | Current systemic risk score |
| `POST` | `/api/chat` | AI chat interface |
| `POST` | `/api/analyze` | Full orchestrated multi-agent analysis |
| `POST` | `/api/analyze/shock` | Shock scenario analysis |

## Demo Scenarios

Pre-built scenarios for demonstration:

1. **SVB Collapse** (`data/scenarios/svb_collapse.json`): Simulates March 2023 regional bank crisis with contagion to major banks
2. **COVID Crash** (`data/scenarios/covid_crash.json`): Simulates March 2020 pandemic-driven broad-based selloff
3. **Sample Portfolio** (`data/scenarios/sample_portfolio.json`): Diversified financial services portfolio for margin risk demo

## Business Impact

- **Cost Savings**: Early warning enables proactive margin adjustments, potentially avoiding billions in margin shortfalls during crises
- **Process Improvement**: Replaces reactive risk monitoring with autonomous AI-driven surveillance
- **Revenue Protection**: Prevents cascading counterparty failures that threaten clearing operations
- **Regulatory Alignment**: Supports FINRA 2026 requirements for cross-product surveillance and GenAI in risk management

## Using DCO to sign your commits

All commits must be signed with a DCO signature:

```
Signed-off-by: John Doe <john.doe@example.com>
```

Use `git commit -s` to add this line automatically.

## License

Copyright 2026 FINOS

Distributed under the [Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0).

SPDX-License-Identifier: [Apache-2.0](https://spdx.org/licenses/Apache-2.0)
