import { useEffect, useRef } from 'react';
import './VisualizationPane.css';

interface VisualizationNode {
  id: string;
  type: 'agent' | 'tool';
  label: string;
  status: 'running' | 'completed' | 'failed';
  timestamp: number;
  duration?: number;
}

interface VisualizationEdge {
  from: string;
  to: string;
  label: string;
  data?: string;
}

interface TraceItem {
  id?: string;
  type?: string;
  agent_name?: string;
  status?: string;
  relative_time?: number;
  [key: string]: unknown;
}

interface VisualizationData {
  nodes: VisualizationNode[];
  edges: VisualizationEdge[];
  traces: TraceItem[];
  session_duration: number;
  total_agents: number;
  total_tools: number;
}

interface VisualizationPaneProps {
  data: VisualizationData | null;
}

export function VisualizationPane({ data }: VisualizationPaneProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!data || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // キャンバスサイズ設定
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

    // クリア
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // ノード描画
    const nodePositions = new Map<string, { x: number; y: number }>();
    const nodeWidth = 140;
    const nodeHeight = 60;
    const verticalSpacing = 100;
    const startY = 50;

    data.nodes.forEach((node, index) => {
      const x = canvas.width / 2 - nodeWidth / 2;
      const y = startY + index * (nodeHeight + verticalSpacing);
      
      nodePositions.set(node.id, { x, y });

      // ノード背景
      ctx.fillStyle = node.status === 'completed' 
        ? '#10b981' 
        : node.status === 'failed' 
        ? '#ef4444' 
        : '#3b82f6';
      ctx.fillRect(x, y, nodeWidth, nodeHeight);

      // ノードラベル
      ctx.fillStyle = '#ffffff';
      ctx.font = '14px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(node.label, x + nodeWidth / 2, y + nodeHeight / 2 - 8);

      // ステータス
      ctx.font = '11px sans-serif';
      ctx.fillText(node.status, x + nodeWidth / 2, y + nodeHeight / 2 + 10);

      // duration表示
      if (node.duration) {
        ctx.font = '10px sans-serif';
        ctx.fillText(`${node.duration.toFixed(2)}s`, x + nodeWidth / 2, y + nodeHeight / 2 + 22);
      }
    });

    // エッジ描画
    ctx.strokeStyle = '#6b7280';
    ctx.lineWidth = 2;
    data.edges.forEach((edge) => {
      const from = nodePositions.get(edge.from);
      const to = nodePositions.get(edge.to);
      
      if (from && to) {
        ctx.beginPath();
        ctx.moveTo(from.x + nodeWidth / 2, from.y + nodeHeight);
        ctx.lineTo(to.x + nodeWidth / 2, to.y);
        ctx.stroke();

        // 矢印
        const arrowSize = 8;
        ctx.fillStyle = '#6b7280';
        ctx.beginPath();
        ctx.moveTo(to.x + nodeWidth / 2, to.y);
        ctx.lineTo(to.x + nodeWidth / 2 - arrowSize, to.y - arrowSize);
        ctx.lineTo(to.x + nodeWidth / 2 + arrowSize, to.y - arrowSize);
        ctx.closePath();
        ctx.fill();
      }
    });
  }, [data]);

  if (!data) {
    return (
      <div className="visualization-pane">
        <div className="visualization-empty">
          <p>🎨 実行結果がここに可視化されます</p>
        </div>
      </div>
    );
  }

  return (
    <div className="visualization-pane">
      <div className="visualization-header">
        <h3>🔍 実行フロー</h3>
        <div className="visualization-stats">
          <span>🤖 {data.total_agents} agents</span>
          <span>🔧 {data.total_tools} tools</span>
          <span>⏱️ {data.session_duration.toFixed(2)}s</span>
        </div>
      </div>
      <canvas ref={canvasRef} className="visualization-canvas" />
      <div className="visualization-traces">
        <h4>詳細トレース</h4>
        <div className="trace-list">
          {data.traces.map((trace, index) => (
            <div key={index} className="trace-item">
              <span className="trace-time">
                {trace.relative_time?.toFixed(2)}s
              </span>
              <span className="trace-type">{trace.type}</span>
              {trace.agent_name && (
                <span className="trace-agent">{trace.agent_name}</span>
              )}
              {trace.status && (
                <span className={`trace-status ${trace.status}`}>
                  {trace.status}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
