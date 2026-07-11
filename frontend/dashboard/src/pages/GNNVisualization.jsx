import React, { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const BACKEND = 'https://wsn-ai-project.onrender.com'

export default function GNNVisualization({ data }) {
  const { gnnGraph, gnnModelReport } = data
  const canvasRef = useRef(null)
  const [predictions, setPredictions] = useState(null)
  const [attentionWeights, setAttentionWeights] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState(null)
  const [graphNodes, setGraphNodes] = useState([])
  const [activeTab, setActiveTab] = useState('graph')

  useEffect(() => {
    Promise.all([
      fetch(`${BACKEND}/api/gnn-node-predictions`).then(r => r.json()),
      fetch(`${BACKEND}/api/gnn-attention-weights`).then(r => r.json()),
    ]).then(([preds, attn]) => {
      setPredictions(preds)
      setAttentionWeights(attn)

      // Sample 300 nodes for visualization
      const allNodes = Object.entries(preds)
      const attacked = allNodes.filter(([, v]) => v.gnn_predicted_malicious === 1)
      const normal = allNodes.filter(([, v]) => v.gnn_predicted_malicious === 0)

     // Sample both attacked and normal to keep the visual ratio realistic
      const sampledAttacked = attacked.sort(() => Math.random() - 0.5).slice(0, 50)
      const sampledNormal = normal.sort(() => Math.random() - 0.5).slice(0, 250)
      const sampled = [...sampledAttacked, ...sampledNormal]
      // Assign deterministic positions using node_id hash
      const positioned = sampled.map(([nodeId, rec], i) => {
       let hash = 0
for (let i = 0; i < nodeId.length; i++) {
  hash = (hash * 31 + nodeId.charCodeAt(i)) >>> 0
}
const angle = (hash % 360) * (Math.PI / 180)
const radius = 60 + (hash % 170)        
return {
          id: nodeId,
          x: 250 + radius * Math.cos(angle),
          y: 200 + radius * Math.sin(angle),
          trust: rec.gnn_trust_score,
          malicious: rec.gnn_predicted_malicious,
          inAttention: attn[nodeId] !== undefined,
        }
      })

      setGraphNodes(positioned)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const handleNodeClick = (node) => {
    setSelectedNode(node)
  }

  // Risk distribution for scatter chart
  const scatterData = predictions
    ? Object.entries(predictions).slice(0, 500).map(([nodeId, rec], i) => ({
        x: i,
        y: parseFloat((1 - rec.gnn_trust_score).toFixed(4)),
        malicious: rec.gnn_predicted_malicious,
      }))
    : []

  if (loading) {
    return (
      <div className="main-content-inner">
        <div className="loading-screen" style={{ minHeight: '400px' }}>
          <div className="loading-spinner" />
          <p className="loading-text">Loading GNN graph data... (backend may take 30–50s)</p>
        </div>
      </div>
    )
  }

  return (
    <div className="main-content-inner">
      <h1 className="page-title">GNN VISUALIZATION</h1>
      <p className="page-subtitle">GraphSAGE node-level malicious detection — leveraging neighbor context across 11,120 WSN nodes</p>

      {/* KPI Cards */}
      <div className="kpi-grid mb-24">
        <div className="kpi-card">
          <div className="kpi-label">Total Nodes</div>
          <div className="kpi-value">{gnnGraph.numNodes.toLocaleString()}</div>
          <div className="kpi-sub">Physical WSN nodes</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Graph Edges</div>
          <div className="kpi-value">{gnnGraph.numEdges.toLocaleString()}</div>
          <div className="kpi-sub">K=5 nearest neighbors</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">GNN F1 Score</div>
          <div className="kpi-value">{gnnModelReport.metrics.f1.toFixed(4)}</div>
          <div className="kpi-sub">GraphSAGE primary model</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Recall</div>
          <div className="kpi-value">{gnnModelReport.metrics.recall.toFixed(4)}</div>
          <div className="kpi-sub">Only 1 attack missed</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Attacked Nodes</div>
          <div className="kpi-value">{gnnGraph.pctAttacked}%</div>
          <div className="kpi-sub">Graph label distribution</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Attention Nodes</div>
          <div className="kpi-value">{attentionWeights ? Object.keys(attentionWeights).length : 0}</div>
          <div className="kpi-sub">Top high-risk nodes</div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-8 mb-16">
        {['graph', 'attention', 'risk'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`node-lookup-btn ${activeTab === tab ? '' : 'opacity-50'}`}
            style={{ padding: '8px 20px', fontSize: '12px' }}
          >
            {tab === 'graph' ? 'Network Graph' : tab === 'attention' ? 'Attention Weights' : 'Risk Distribution'}
          </button>
        ))}
      </div>

      {/* Tab: Network Graph */}
      {activeTab === 'graph' && (
        <div className="dash-card">
          <h2 className="dash-card-title">NETWORK TOPOLOGY — SAMPLE 300 NODES</h2>
          <p className="model-note mb-16">Red = GNN predicted malicious | Blue = normal | Cyan ring = in attention weights (high-risk)</p>
          <div style={{ position: 'relative', width: '100%', height: '420px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px', overflow: 'hidden' }}>
            <svg width="100%" height="100%" viewBox="0 0 500 400">
              {/* Edges — connect nodes to their 2 nearest neighbors */}
              {graphNodes.map((node, i) => {
                const nearest = graphNodes
                  .filter((_, j) => j !== i)
                  .sort((a, b) => Math.hypot(a.x - node.x, a.y - node.y) - Math.hypot(b.x - node.x, b.y - node.y))
                  .slice(0, 2)
                return nearest.map((n, j) => (
                  <line
                    key={`${i}-${j}`}
                    x1={node.x} y1={node.y} x2={n.x} y2={n.y}
                    stroke="rgba(100,120,180,0.15)" strokeWidth="0.5"
                  />
                ))
              })}

              {/* Nodes */}
              {graphNodes.map((node) => (
                <g key={node.id} onClick={() => handleNodeClick(node)} style={{ cursor: 'pointer' }}>
                  {node.inAttention && (
                    <circle
                      cx={node.x} cy={node.y} r={9}
                      fill="none" stroke="rgba(0,210,255,0.6)" strokeWidth="1.5"
                    />
                  )}
                  <circle
                    cx={node.x} cy={node.y}
                    r={node.malicious ? 6 : 4}
                    fill={node.malicious ? '#ff3860' : '#00d2ff'}
                    opacity={0.85}
                    style={{
                      filter: node.malicious
                        ? 'drop-shadow(0 0 6px rgba(255,56,96,0.8))'
                        : 'drop-shadow(0 0 3px rgba(0,210,255,0.5))'
                    }}
                  />
                </g>
              ))}
            </svg>

            {/* Selected node info */}
            {selectedNode && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="card"
                style={{ position: 'absolute', bottom: 12, right: 12, minWidth: 220, padding: '12px 16px' }}
              >
                <div className="model-metric-label mb-4">Selected Node</div>
                <div className="model-metric-value neon-text-cyan" style={{ fontSize: '13px' }}>{selectedNode.id}</div>
                <div className="node-result-grid mt-8" style={{ gridTemplateColumns: '1fr 1fr' }}>
                  <div className="node-result-item">
                    <span className="node-result-label">Trust</span>
                    <span className={`node-result-value ${selectedNode.trust > 0.5 ? 'neon-text-green' : 'neon-text-red'}`}>
                      {selectedNode.trust.toFixed(4)}
                    </span>
                  </div>
                  <div className="node-result-item">
                    <span className="node-result-label">Status</span>
                    <span className={`node-result-value ${selectedNode.malicious ? 'neon-text-red' : 'neon-text-green'}`}>
                      {selectedNode.malicious ? 'MALICIOUS' : 'NORMAL'}
                    </span>
                  </div>
                </div>
                {attentionWeights?.[selectedNode.id] && (
                  <div className="mt-8">
                    <div className="model-metric-label mb-4">Top Influencing Neighbors</div>
                    {attentionWeights[selectedNode.id].slice(0, 3).map((n, i) => (
                      <div key={i} className="node-result-item">
                        <span className="node-result-label">{n.neighbor}</span>
                        <span className="node-result-value neon-text-cyan">{n.attention_weight.toFixed(4)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </div>
        </div>
      )}

      {/* Tab: Attention Weights */}
      {activeTab === 'attention' && (
        <div className="dash-card">
          <h2 className="dash-card-title">TOP 200 HIGH-RISK NODES — ATTENTION WEIGHTS</h2>
          <p className="model-note mb-16">GAT attention weights showing which neighbors most influenced each high-risk node's prediction</p>
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {attentionWeights && Object.entries(attentionWeights).slice(0, 20).map(([nodeId, neighbors]) => (
              <motion.div
                key={nodeId}
                className="card mb-8"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                style={{ padding: '12px 16px' }}
              >
                <div className="flex-between mb-8">
                  <span className="model-card-name" style={{ fontSize: '13px' }}>{nodeId}</span>
                  <span className="badge badge-red">High Risk</span>
                </div>
                <div className="node-result-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                  {neighbors.slice(0, 3).map((n, i) => (
                    <div key={i} className="node-result-item">
                      <span className="node-result-label">{n.neighbor}</span>
                      <span className="node-result-value neon-text-cyan">{n.attention_weight.toFixed(4)}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
            <p className="model-note mt-8">Showing 20 of {attentionWeights ? Object.keys(attentionWeights).length : 0} high-risk nodes</p>
          </div>
        </div>
      )}

      {/* Tab: Risk Distribution */}
      {activeTab === 'risk' && (
        <div className="dash-card">
          <h2 className="dash-card-title">RISK SCORE DISTRIBUTION — SAMPLE 500 NODES</h2>
          <p className="model-note mb-16">Y-axis: risk score (1 - gnn_trust_score). Red dots = predicted malicious</p>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2030" />
                <XAxis dataKey="x" name="Node index" axisLine={false} tickLine={false} hide />
                <YAxis dataKey="y" name="Risk score" domain={[0, 1]} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#0d0d14', border: '1px solid #1e2030', borderRadius: '8px', color: '#fff' }}
                  formatter={(val) => val.toFixed(4)}
                />
                <Scatter
                  data={scatterData.filter(d => d.malicious === 0)}
                  fill="#00d2ff"
                  opacity={0.5}
                  r={3}
                />
                <Scatter
                  data={scatterData.filter(d => d.malicious === 1)}
                  fill="#ff3860"
                  opacity={0.8}
                  r={5}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Architecture Note */}
      <div className="dash-card mt-16">
        <h2 className="dash-card-title">MODEL ARCHITECTURE</h2>
        <p className="model-note">{gnnModelReport.architecture}</p>
        <p className="model-note mt-8">{gnnModelReport.ablation_note}</p>
        <div className="model-card-metrics mt-16">
          <div className="model-metric">
            <div className="model-metric-label">Features</div>
            <div className="model-metric-value neon-text-white">{gnnModelReport.num_features}</div>
          </div>
          <div className="model-metric">
            <div className="model-metric-label">Test Size</div>
            <div className="model-metric-value neon-text-white">{(gnnModelReport.test_size * 100).toFixed(0)}%</div>
          </div>
          <div className="model-metric">
            <div className="model-metric-label">Epochs</div>
            <div className="model-metric-value neon-text-white">{gnnModelReport.epochs}</div>
          </div>
          <div className="model-metric">
            <div className="model-metric-label">TN / FP / FN / TP</div>
            <div className="model-metric-value neon-text-cyan" style={{ fontSize: '14px' }}>
              {gnnModelReport.metrics.confusion_matrix[0][0]} / {gnnModelReport.metrics.confusion_matrix[0][1]} / {gnnModelReport.metrics.confusion_matrix[1][0]} / {gnnModelReport.metrics.confusion_matrix[1][1]}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}