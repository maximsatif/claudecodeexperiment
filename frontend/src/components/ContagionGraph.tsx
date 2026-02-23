import { useRef, useEffect, useMemo } from 'react';
import type { ContagionGraph, SimulationSnapshot } from '../services/api';

interface Props {
  graph: ContagionGraph;
  simSnapshots?: SimulationSnapshot[];
}

const SECTOR_COLORS: Record<string, string> = {
  'Major Banks': '#3b82f6',
  'Regional Banks': '#8b5cf6',
  'Insurance/Financial': '#06b6d4',
  'Equity Index': '#22c55e',
  'Fixed Income': '#eab308',
  'Commodities': '#f97316',
  'Crypto': '#ec4899',
  'Volatility': '#ef4444',
  'FX': '#14b8a6',
  'Other': '#6b7280',
};

const STATUS_COLORS: Record<string, string> = {
  healthy: '#22c55e',
  stressed: '#f97316',
  critical: '#ef4444',
};

export default function ContagionGraphViz({ graph, simSnapshots }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrame = useRef<number>(0);

  // Compute node positions using force-directed layout (simplified)
  const layout = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    const sectorGroups: Record<string, string[]> = {};

    graph.nodes.forEach(node => {
      sectorGroups[node.sector] = sectorGroups[node.sector] || [];
      sectorGroups[node.sector].push(node.id);
    });

    const sectors = Object.keys(sectorGroups);
    const centerX = 400;
    const centerY = 225;

    sectors.forEach((sector, si) => {
      const angle = (si / sectors.length) * 2 * Math.PI - Math.PI / 2;
      const radius = 140;
      const cx = centerX + Math.cos(angle) * radius;
      const cy = centerY + Math.sin(angle) * radius;

      const nodes = sectorGroups[sector];
      nodes.forEach((nodeId, ni) => {
        const subAngle = angle + ((ni - nodes.length / 2) * 0.3);
        const subRadius = 30 + ni * 15;
        positions[nodeId] = {
          x: cx + Math.cos(subAngle) * subRadius,
          y: cy + Math.sin(subAngle) * subRadius,
        };
      });
    });

    return positions;
  }, [graph]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      // Draw edges
      graph.edges.forEach(edge => {
        const src = layout[edge.source];
        const tgt = layout[edge.target];
        if (!src || !tgt) return;

        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);
        ctx.strokeStyle = `rgba(100, 116, 139, ${Math.min(edge.weight * 0.5, 0.4)})`;
        ctx.lineWidth = edge.weight * 2;
        ctx.stroke();

        // Draw contagion risk as red glow on high-risk edges
        if (edge.contagion_risk > 0.3) {
          ctx.beginPath();
          ctx.moveTo(src.x, src.y);
          ctx.lineTo(tgt.x, tgt.y);
          ctx.strokeStyle = `rgba(239, 68, 68, ${edge.contagion_risk * 0.3})`;
          ctx.lineWidth = edge.contagion_risk * 4;
          ctx.stroke();
        }
      });

      // Draw nodes
      graph.nodes.forEach(node => {
        const pos = layout[node.id];
        if (!pos) return;

        const baseColor = SECTOR_COLORS[node.sector] || '#6b7280';
        const statusColor = STATUS_COLORS[node.status] || '#22c55e';
        const radius = 8 + node.risk_score / 10;

        // Glow for critical/stressed nodes
        if (node.status === 'critical') {
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, radius + 8, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(239, 68, 68, 0.15)';
          ctx.fill();
        } else if (node.status === 'stressed') {
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, radius + 5, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(249, 115, 22, 0.1)';
          ctx.fill();
        }

        // Node circle
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = baseColor;
        ctx.fill();
        ctx.strokeStyle = statusColor;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Node label
        ctx.fillStyle = '#e2e8f0';
        ctx.font = '10px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(node.id, pos.x, pos.y + radius + 12);

        // Risk score badge
        if (node.risk_score > 30) {
          ctx.fillStyle = statusColor;
          ctx.font = 'bold 8px system-ui, sans-serif';
          ctx.fillText(node.risk_score.toFixed(0), pos.x, pos.y + 3);
        }
      });

      // Draw legend
      const legendX = 10;
      let legendY = 15;
      ctx.font = 'bold 10px system-ui, sans-serif';
      ctx.fillStyle = '#94a3b8';
      ctx.textAlign = 'left';
      ctx.fillText('Sectors:', legendX, legendY);
      legendY += 14;

      Object.entries(SECTOR_COLORS).forEach(([sector, color]) => {
        if (graph.nodes.some(n => n.sector === sector)) {
          ctx.beginPath();
          ctx.arc(legendX + 5, legendY - 3, 4, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.fill();
          ctx.fillStyle = '#94a3b8';
          ctx.font = '9px system-ui, sans-serif';
          ctx.fillText(sector, legendX + 14, legendY);
          legendY += 14;
        }
      });
    };

    draw();

    return () => cancelAnimationFrame(animFrame.current);
  }, [graph, layout, simSnapshots]);

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={450}
      className="w-full h-full"
      style={{ maxHeight: '450px' }}
    />
  );
}
