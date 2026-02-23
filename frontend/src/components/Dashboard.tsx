import { useState, useEffect, useCallback } from 'react';
import {
  fetchGraph,
  fetchRiskScore,
  fetchMarketData,
  fetchMacroIndicators,
  simulateShock,
  fetchSIRModel,
  type ContagionGraph,
  type RiskScore,
  type MarketDataPoint,
  type MacroIndicators,
  type SimulationSnapshot,
  type SIRResult,
} from '../services/api';
import ContagionGraphViz from './ContagionGraph';
import RiskHeatmap from './RiskHeatmap';
import AlertPanel from './AlertPanel';
import {
  AlertTriangle,
  TrendingDown,
  Shield,
  RefreshCw,
  Zap,
  Activity,
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area,
} from 'recharts';

export default function Dashboard() {
  const [graph, setGraph] = useState<ContagionGraph | null>(null);
  const [riskScore, setRiskScore] = useState<RiskScore | null>(null);
  const [marketData, setMarketData] = useState<MarketDataPoint[]>([]);
  const [macroIndicators, setMacroIndicators] = useState<MacroIndicators | null>(null);
  const [sirResult, setSirResult] = useState<SIRResult | null>(null);
  const [simSnapshots, setSimSnapshots] = useState<SimulationSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [shockTicker, setShockTicker] = useState('JPM');
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [graphData, risk, market, macro, sir] = await Promise.allSettled([
        fetchGraph(),
        fetchRiskScore(),
        fetchMarketData(),
        fetchMacroIndicators(),
        fetchSIRModel(),
      ]);

      if (graphData.status === 'fulfilled') setGraph(graphData.value);
      if (risk.status === 'fulfilled') setRiskScore(risk.value);
      if (market.status === 'fulfilled') setMarketData(market.value.data);
      if (macro.status === 'fulfilled') setMacroIndicators(macro.value);
      if (sir.status === 'fulfilled') setSirResult(sir.value);
    } catch (err) {
      setError('Failed to load data. Ensure the backend is running.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleSimulateShock = async () => {
    setSimulating(true);
    try {
      const result = await simulateShock(shockTicker, 0.8, 10);
      setSimSnapshots(result.snapshots);
      setGraph(result.graph);
    } catch {
      setError('Simulation failed');
    } finally {
      setSimulating(false);
    }
  };

  const riskColor = (level: string) => {
    const colors: Record<string, string> = {
      low: 'text-green-400',
      moderate: 'text-yellow-400',
      elevated: 'text-orange-400',
      high: 'text-red-400',
      critical: 'text-red-600',
    };
    return colors[level] || 'text-gray-400';
  };

  const riskBg = (level: string) => {
    const colors: Record<string, string> = {
      low: 'bg-green-900/30 border-green-800',
      moderate: 'bg-yellow-900/30 border-yellow-800',
      elevated: 'bg-orange-900/30 border-orange-800',
      high: 'bg-red-900/30 border-red-800',
      critical: 'bg-red-900/50 border-red-600 animate-pulse-red',
    };
    return colors[level] || 'bg-gray-900/30 border-gray-800';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-blue-400 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading market data and building contagion graph...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded-lg p-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-400" />
          <span className="text-red-300 text-sm">{error}</span>
        </div>
      )}

      {/* Top Row: Risk Score + Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Systemic Risk Score */}
        <div className={`rounded-xl border p-4 ${riskBg(riskScore?.risk_level || 'low')}`}>
          <div className="flex items-center gap-2 mb-2">
            <Shield className="w-5 h-5 text-blue-400" />
            <span className="text-sm text-gray-300 font-medium">Systemic Risk Score</span>
          </div>
          <div className={`text-4xl font-bold ${riskColor(riskScore?.risk_level || 'low')}`}>
            {riskScore?.systemic_risk_score?.toFixed(1) || '—'}
          </div>
          <div className={`text-sm uppercase font-semibold mt-1 ${riskColor(riskScore?.risk_level || 'low')}`}>
            {riskScore?.risk_level || 'Loading...'}
          </div>
        </div>

        {/* Entity Status */}
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
          <span className="text-sm text-gray-400">Entity Status</span>
          <div className="mt-2 space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-red-400">Critical</span>
              <span className="font-bold text-red-400">{riskScore?.critical_count || 0}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-orange-400">Stressed</span>
              <span className="font-bold text-orange-400">{riskScore?.stressed_count || 0}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-green-400">Healthy</span>
              <span className="font-bold text-green-400">{riskScore?.healthy_count || 0}</span>
            </div>
          </div>
        </div>

        {/* R0 (Financial Reproduction Number) */}
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-purple-400" />
            <span className="text-sm text-gray-400">Financial R0</span>
          </div>
          <div className={`text-3xl font-bold ${
            (sirResult?.r0 || 0) > 1 ? 'text-red-400' : 'text-green-400'
          }`}>
            {sirResult?.r0?.toFixed(2) || '—'}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {(sirResult?.r0 || 0) > 1 ? 'Contagion SPREADING' : 'Contagion contained'}
          </div>
        </div>

        {/* Shock Simulator */}
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-yellow-400" />
            <span className="text-sm text-gray-400">Shock Simulator</span>
          </div>
          <div className="flex gap-2">
            <select
              value={shockTicker}
              onChange={(e) => setShockTicker(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm flex-1"
            >
              {['JPM', 'BAC', 'C', 'GS', 'MS', 'SCHW', 'SPY', 'HYG'].map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <button
              onClick={handleSimulateShock}
              disabled={simulating}
              className="bg-red-600 hover:bg-red-700 disabled:bg-gray-700 px-3 py-1.5 rounded text-sm font-medium transition-colors"
            >
              {simulating ? 'Running...' : 'Shock'}
            </button>
          </div>
          {simSnapshots.length > 0 && (
            <div className="text-xs text-gray-500 mt-2">
              Peak: {Math.max(...simSnapshots.map(s => s.infected_count))} infected
            </div>
          )}
        </div>
      </div>

      {/* Middle Row: Contagion Graph + Market Movers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Contagion Graph */}
        <div className="lg:col-span-2 bg-gray-900/50 rounded-xl border border-gray-800 p-4">
          <h2 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-blue-400" />
            Contagion Network Graph
          </h2>
          <div className="h-[450px]">
            {graph ? (
              <ContagionGraphViz graph={graph} simSnapshots={simSnapshots} />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                No graph data available
              </div>
            )}
          </div>
        </div>

        {/* Right Panel: Alerts + Macro */}
        <div className="space-y-4">
          <AlertPanel graph={graph} marketData={marketData} />

          {/* Macro Indicators */}
          {macroIndicators && (
            <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Macro Indicators</h3>
              <div className="space-y-2">
                {Object.entries(macroIndicators.indicators).map(([name, ind]) => (
                  <div key={name} className="flex justify-between items-center text-sm">
                    <span className="text-gray-400">{name}</span>
                    <div className="flex items-center gap-2">
                      <span className="font-mono">{ind.value?.toFixed(2)}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        ind.signal === 'critical' ? 'bg-red-900 text-red-300' :
                        ind.signal === 'warning' ? 'bg-orange-900 text-orange-300' :
                        ind.signal === 'elevated' ? 'bg-yellow-900 text-yellow-300' :
                        'bg-gray-800 text-gray-400'
                      }`}>
                        {ind.signal}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Row: SIR Trajectory + Market Data */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* SIR Model Trajectory */}
        {sirResult && (
          <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">
              SIR Contagion Model Trajectory
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={sirResult.trajectory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="step" stroke="#666" fontSize={11} />
                <YAxis stroke="#666" fontSize={11} />
                <Tooltip
                  contentStyle={{ background: '#1a1a2e', border: '1px solid #333', borderRadius: 8 }}
                />
                <Area type="monotone" dataKey="susceptible" stackId="1" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} name="Susceptible" />
                <Area type="monotone" dataKey="infected" stackId="1" stroke="#ef4444" fill="#ef4444" fillOpacity={0.5} name="Infected" />
                <Area type="monotone" dataKey="recovered" stackId="1" stroke="#22c55e" fill="#22c55e" fillOpacity={0.3} name="Recovered" />
                <Area type="monotone" dataKey="dead" stackId="1" stroke="#6b7280" fill="#6b7280" fillOpacity={0.3} name="Impaired" />
              </AreaChart>
            </ResponsiveContainer>
            <div className="flex gap-4 mt-2 text-xs text-gray-500">
              <span>Peak infection: {sirResult.metrics.peak_infection_rate}%</span>
              <span>Total affected: {sirResult.metrics.total_affected_pct}%</span>
              <span>Risk: <span className={riskColor(sirResult.metrics.risk_level)}>{sirResult.metrics.risk_level}</span></span>
            </div>
          </div>
        )}

        {/* Market Data Table */}
        <RiskHeatmap marketData={marketData} riskScore={riskScore} />
      </div>

      {/* Refresh Button */}
      <div className="flex justify-center">
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh All Data
        </button>
      </div>
    </div>
  );
}
