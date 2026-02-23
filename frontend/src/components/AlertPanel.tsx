import type { ContagionGraph, MarketDataPoint } from '../services/api';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';

interface Props {
  graph: ContagionGraph | null;
  marketData: MarketDataPoint[];
}

interface Alert {
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
}

export default function AlertPanel({ graph, marketData }: Props) {
  const alerts: Alert[] = [];

  // Generate alerts from graph data
  if (graph) {
    // Systemic risk alert
    if (graph.systemic_risk_score > 50) {
      alerts.push({
        severity: 'critical',
        title: 'Elevated Systemic Risk',
        description: `Systemic risk score at ${graph.systemic_risk_score.toFixed(1)} - contagion risk is elevated across the network.`,
      });
    }

    // Critical nodes alert
    const criticalNodes = graph.nodes.filter(n => n.status === 'critical');
    if (criticalNodes.length > 0) {
      alerts.push({
        severity: 'high',
        title: `${criticalNodes.length} Entities in Critical State`,
        description: `Critical: ${criticalNodes.map(n => n.id).join(', ')}. Immediate margin review recommended.`,
      });
    }

    // Volume anomaly alert
    const volumeAnomalies = graph.nodes.filter(n => n.volume_anomaly);
    if (volumeAnomalies.length > 3) {
      alerts.push({
        severity: 'medium',
        title: 'Widespread Volume Anomalies',
        description: `${volumeAnomalies.length} entities showing abnormal volume: ${volumeAnomalies.slice(0, 5).map(n => n.id).join(', ')}`,
      });
    }

    // Correlation-based alerts
    const highContagionEdges = graph.edges.filter(e => e.contagion_risk > 0.5);
    if (highContagionEdges.length > 5) {
      alerts.push({
        severity: 'high',
        title: 'High Contagion Risk Corridors',
        description: `${highContagionEdges.length} entity pairs show >50% contagion transmission probability.`,
      });
    }
  }

  // Market data alerts
  const bigMovers = marketData.filter(d => Math.abs(d.change_pct) > 5);
  if (bigMovers.length > 0) {
    alerts.push({
      severity: 'high',
      title: 'Significant Price Movements',
      description: `${bigMovers.length} assets moved >5%: ${bigMovers.map(d => `${d.ticker} (${d.change_pct > 0 ? '+' : ''}${d.change_pct.toFixed(1)}%)`).join(', ')}`,
    });
  }

  // Add info alert if everything looks normal
  if (alerts.length === 0) {
    alerts.push({
      severity: 'low',
      title: 'Markets Normal',
      description: 'No significant risk signals detected. All monitored entities within normal parameters.',
    });
  }

  // Sort by severity
  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
  alerts.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

  const severityIcon = (s: string) => {
    switch (s) {
      case 'critical': return <AlertTriangle className="w-4 h-4 text-red-500" />;
      case 'high': return <AlertCircle className="w-4 h-4 text-orange-400" />;
      case 'medium': return <AlertCircle className="w-4 h-4 text-yellow-400" />;
      default: return <Info className="w-4 h-4 text-blue-400" />;
    }
  };

  const severityBg = (s: string) => {
    switch (s) {
      case 'critical': return 'border-l-red-500 bg-red-900/10';
      case 'high': return 'border-l-orange-400 bg-orange-900/10';
      case 'medium': return 'border-l-yellow-400 bg-yellow-900/10';
      default: return 'border-l-blue-400 bg-blue-900/10';
    }
  };

  return (
    <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
      <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center justify-between">
        <span>Risk Alerts</span>
        <span className={`text-xs px-2 py-0.5 rounded-full ${
          alerts.some(a => a.severity === 'critical')
            ? 'bg-red-900 text-red-300'
            : alerts.some(a => a.severity === 'high')
            ? 'bg-orange-900 text-orange-300'
            : 'bg-green-900 text-green-300'
        }`}>
          {alerts.length} alert{alerts.length !== 1 ? 's' : ''}
        </span>
      </h3>
      <div className="space-y-2 max-h-[300px] overflow-y-auto">
        {alerts.map((alert, i) => (
          <div key={i} className={`border-l-2 rounded-r-lg p-2 ${severityBg(alert.severity)}`}>
            <div className="flex items-center gap-2">
              {severityIcon(alert.severity)}
              <span className="text-xs font-semibold text-gray-200">{alert.title}</span>
            </div>
            <p className="text-xs text-gray-400 mt-1 ml-6">{alert.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
