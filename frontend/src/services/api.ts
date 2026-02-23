import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
});

export interface GraphNode {
  id: string;
  label: string;
  sector: string;
  risk_score: number;
  status: 'healthy' | 'stressed' | 'critical';
  price_change_pct: number;
  volume_anomaly: boolean;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  contagion_risk: number;
}

export interface ContagionGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  timestamp: string;
  systemic_risk_score: number;
}

export interface RiskScore {
  systemic_risk_score: number;
  risk_level: string;
  sector_breakdown: Record<string, { avg: number; max: number }>;
  critical_count: number;
  stressed_count: number;
  healthy_count: number;
  timestamp: string;
}

export interface MacroIndicators {
  indicators: Record<string, {
    value: number;
    previous: number;
    change: number;
    date: string;
    signal: string;
  }>;
  timestamp: string;
}

export interface MarketDataPoint {
  ticker: string;
  price: number;
  change_pct: number;
  volume: number;
  volume_avg: number;
  volume_ratio: number;
  timestamp: string;
}

export interface SimulationSnapshot {
  step: number;
  states: Record<string, { state: string; risk: number }>;
  infected_count: number;
  total_risk: number;
}

export interface SIRResult {
  parameters: { beta: number; gamma: number; delta: number };
  r0: number;
  metrics: {
    peak_infection_rate: number;
    peak_step: number;
    total_affected_pct: number;
    risk_level: string;
  };
  trajectory: Array<{
    step: number;
    susceptible: number;
    infected: number;
    recovered: number;
    dead: number;
  }>;
}

export const fetchGraph = async (period = '6mo', threshold = 0.6): Promise<ContagionGraph> => {
  const { data } = await api.get(`/graph?period=${period}&threshold=${threshold}`);
  return data;
};

export const fetchRiskScore = async (): Promise<RiskScore> => {
  const { data } = await api.get('/risk-score');
  return data;
};

export const fetchMarketData = async (): Promise<{ data: MarketDataPoint[] }> => {
  const { data } = await api.get('/market-data');
  return data;
};

export const fetchMacroIndicators = async (): Promise<MacroIndicators> => {
  const { data } = await api.get('/macro-indicators');
  return data;
};

export const simulateShock = async (
  ticker: string,
  magnitude = 0.8,
  steps = 10,
): Promise<{ snapshots: SimulationSnapshot[]; graph: ContagionGraph }> => {
  const { data } = await api.post(`/graph/simulate?ticker=${ticker}&magnitude=${magnitude}&steps=${steps}`);
  return data;
};

export const fetchSIRModel = async (
  beta = 0.3,
  gamma = 0.1,
  delta = 0.05,
): Promise<SIRResult> => {
  const { data } = await api.get(`/sir-model?beta=${beta}&gamma=${gamma}&delta=${delta}`);
  return data;
};

export const sendChatMessage = async (message: string): Promise<{ response: string }> => {
  const { data } = await api.post('/chat', { message });
  return data;
};

export const runFullAnalysis = async (): Promise<any> => {
  const { data } = await api.post('/analyze');
  return data;
};
