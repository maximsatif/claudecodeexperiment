import type { MarketDataPoint, RiskScore } from '../services/api';
import { TrendingDown, TrendingUp, AlertTriangle } from 'lucide-react';

interface Props {
  marketData: MarketDataPoint[];
  riskScore: RiskScore | null;
}

export default function RiskHeatmap({ marketData, riskScore }: Props) {
  const sortedData = [...marketData].sort((a, b) => a.change_pct - b.change_pct);

  const getChangeColor = (pct: number) => {
    if (pct < -5) return 'text-red-500 bg-red-900/30';
    if (pct < -2) return 'text-red-400 bg-red-900/20';
    if (pct < 0) return 'text-red-300 bg-red-900/10';
    if (pct > 5) return 'text-green-500 bg-green-900/30';
    if (pct > 2) return 'text-green-400 bg-green-900/20';
    if (pct > 0) return 'text-green-300 bg-green-900/10';
    return 'text-gray-400';
  };

  return (
    <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
      <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center justify-between">
        <span>Market Data & Risk Heatmap</span>
        <span className="text-xs text-gray-500">{marketData.length} assets monitored</span>
      </h3>

      {/* Sector Risk Summary */}
      {riskScore?.sector_breakdown && (
        <div className="grid grid-cols-3 gap-2 mb-3">
          {Object.entries(riskScore.sector_breakdown)
            .sort((a, b) => b[1].max - a[1].max)
            .slice(0, 6)
            .map(([sector, data]) => (
              <div key={sector} className="bg-gray-800/50 rounded p-2">
                <div className="text-xs text-gray-400 truncate">{sector}</div>
                <div className={`text-sm font-bold ${
                  data.max > 60 ? 'text-red-400' :
                  data.max > 30 ? 'text-orange-400' :
                  'text-green-400'
                }`}>
                  {data.avg.toFixed(0)}
                </div>
              </div>
            ))}
        </div>
      )}

      {/* Market Data Table */}
      <div className="max-h-[200px] overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-gray-900">
            <tr className="text-gray-500 border-b border-gray-800">
              <th className="text-left py-1 px-1">Ticker</th>
              <th className="text-right py-1 px-1">Price</th>
              <th className="text-right py-1 px-1">Change</th>
              <th className="text-right py-1 px-1">Vol Ratio</th>
              <th className="text-center py-1 px-1">Signal</th>
            </tr>
          </thead>
          <tbody>
            {sortedData.map(d => (
              <tr key={d.ticker} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="py-1 px-1 font-medium">{d.ticker}</td>
                <td className="py-1 px-1 text-right font-mono">${d.price?.toFixed(2)}</td>
                <td className={`py-1 px-1 text-right font-mono ${getChangeColor(d.change_pct)}`}>
                  <span className="inline-flex items-center gap-0.5">
                    {d.change_pct > 0 ? <TrendingUp className="w-3 h-3" /> : d.change_pct < 0 ? <TrendingDown className="w-3 h-3" /> : null}
                    {d.change_pct?.toFixed(2)}%
                  </span>
                </td>
                <td className={`py-1 px-1 text-right font-mono ${
                  d.volume_ratio > 2 ? 'text-yellow-400' : 'text-gray-400'
                }`}>
                  {d.volume_ratio?.toFixed(1)}x
                </td>
                <td className="py-1 px-1 text-center">
                  {d.volume_anomaly && (
                    <AlertTriangle className="w-3 h-3 text-yellow-400 mx-auto" />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
