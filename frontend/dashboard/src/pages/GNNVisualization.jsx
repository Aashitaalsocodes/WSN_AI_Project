import React, { useState, useEffect, useMemo, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

// In dev, /api/* is proxied to Render by vite.config.js — avoids CORS.
// In prod (deployed on same origin), relative paths work directly.
const BACKEND = import.meta.env.DEV ? '' : 'https://wsn-ai-project.onrender.com'

// Deterministic pseudo-random for per-node variation (returns 0–1)
const srand = (seed, n) => ((seed * n + 7) % 31) / 31

export default function GNNVisualization({ data }) {
  const { gnnGraph, gnnModelReport } = data || {}
  const [predictions, setPredictions] = useState(null)
  const [attentionWeights, setAttentionWeights] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState(null)
  const [graphNodes, setGraphNodes] = useState([])
  const [activeTab, setActiveTab] = useState('graph')
  const [ripples, setRipples] = useState([])
  const [hasAnimatedIn, setHasAnimatedIn] = useState(false)

  // Trigger entrance animation completion
  useEffect(() => {
    if (!loading && graphNodes.length > 0 && !hasAnimatedIn) {
      const timer = setTimeout(() => {
        setHasAnimatedIn(true)
      }, 3500) // Allow 3.5s for initial build-in animation to finish
      return () => clearTimeout(timer)
    }
  }, [loading, graphNodes, hasAnimatedIn])

  useEffect(() => {
    if (!gnnGraph) return // skip fetching if parent data isn't ready
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
      const positioned = sampled.map(([nodeId, rec]) => {
        let hash = 0
        for (let c = 0; c < nodeId.length; c++) {
          hash = (hash * 31 + nodeId.charCodeAt(c)) >>> 0
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
  }, [gnnGraph])

  // Click handler — selects node + emits expanding sonar ripple
  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node)
    const key = `${node.id}-${Date.now()}`
    setRipples(prev => [...prev, { x: node.x, y: node.y, key }])
    setTimeout(() => setRipples(prev => prev.filter(r => r.key !== key)), 1000)
  }, [])

  // Memoize O(n²) edge computation — only recalculate when graphNodes change
  const edges = useMemo(() => {
    if (!graphNodes.length) return []
    return graphNodes.flatMap((node, i) => {
      const nearest = graphNodes
        .filter((_, j) => j !== i)
        .sort((a, b) =>
          Math.hypot(a.x - node.x, a.y - node.y) - Math.hypot(b.x - node.x, b.y - node.y)
        )
        .slice(0, 2)
      return nearest.map((n, j) => ({
        id: `edge-${i}-${j}`,
        x1: node.x, y1: node.y,
        x2: n.x, y2: n.y,
        length: Math.hypot(n.x - node.x, n.y - node.y),
      }))
    })
  }, [graphNodes])

  // Pre-compute organic drift keyframes per node — 6 irregular waypoints per axis
  const nodeDrifts = useMemo(() => {
    const m = new Map()
    graphNodes.forEach(node => {
      const seed = node.id.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
      const r = 2 + (seed % 4) // 2–5px max displacement
      m.set(node.id, {
        x: [0, r*srand(seed,7), -r*srand(seed,11), r*srand(seed,17), -r*srand(seed,23), r*srand(seed,29), 0],
        y: [0, -r*srand(seed,41), r*srand(seed,43), -r*srand(seed,47), r*srand(seed,53), -r*srand(seed,59), 0],
        dur: 5 + (seed % 5), // 5–9s cycle
      })
    })
    return m
  }, [graphNodes])

  // Risk distribution for scatter chart — random sample so malicious nodes appear
  const scatterData = predictions
    ? Object.entries(predictions)
        .sort(() => Math.random() - 0.5)
        .slice(0, 500)
        .map(([nodeId, rec], i) => ({
          x: i,
          y: parseFloat((1 - rec.gnn_trust_score).toFixed(6)),
          malicious: rec.gnn_predicted_malicious,
        }))
    : []

  // Guard: if the parent data doesn't include GNN fields yet (API cold-start / fallback data)
  if (!gnnGraph || !gnnModelReport) {
    return (
      <div className="main-content-inner">
        <div className="loading-screen" style={{ minHeight: '400px' }}>
          <div className="loading-spinner" />
          <p className="loading-text">Waiting for GNN data from backend... (the Render server may take 30–60s to wake up — please refresh)</p>
        </div>
      </div>
    )
  }

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
    <div className="main-content-inner" style={{ '--accent-color': '#00f3ff', '--accent-rgb': '0,243,255' }}>
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

      {/* ══════════════════════════════════════════════════════
          Tab: Network Graph
          Animation architecture:
          • Packets (1800 circles): SVG-native <animateMotion> — zero JS cost
          • Node glow (300 circles): SVG-native <animate> on r/opacity
          • Node drift (300 groups): framer-motion <motion.g> — batched rAF
          • Ripple (1–2 groups): framer-motion AnimatePresence
          • Background: SVG <pattern> + <animateTransform> — compositor
         ══════════════════════════════════════════════════════ */}
      {activeTab === 'graph' && (
        <div className="dash-card">
          <h2 className="dash-card-title">NETWORK TOPOLOGY — SAMPLE 300 NODES</h2>
          <p className="model-note mb-16">Red = GNN predicted malicious | Blue = normal | Cyan ring = in attention weights (high-risk)</p>
          <div style={{ position: 'relative', width: '100%', height: '420px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px', overflow: 'hidden' }}>
            <svg width="100%" height="100%" viewBox="0 0 500 400">

              {/* ═══ SVG Definitions ═══ */}
              <defs>
                {/* Comet-tail glow for lead data packets (feGaussianBlur + merge) */}
                <filter id="packetGlow" x="-100%" y="-100%" width="300%" height="300%">
                  <feGaussianBlur in="SourceGraphic" stdDeviation="2.5" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                {/* Node glow aura — blue (normal nodes, subtle) */}
                <filter id="glowBlue" x="-100%" y="-100%" width="300%" height="300%">
                  <feGaussianBlur in="SourceGraphic" stdDeviation="3" />
                </filter>
                {/* Node glow aura — red (malicious nodes, wider bloom) */}
                <filter id="glowRed" x="-100%" y="-100%" width="300%" height="300%">
                  <feGaussianBlur in="SourceGraphic" stdDeviation="5" />
                </filter>
                {/* Ambient drifting dot-grid pattern */}
                <pattern id="bgGrid" width="20" height="20" patternUnits="userSpaceOnUse">
                  <circle cx="10" cy="10" r="0.5" fill="rgba(0,210,255,0.06)" />
                  <animateTransform
                    attributeName="patternTransform" type="translate"
                    from="0 0" to="20 20" dur="30s" repeatCount="indefinite"
                  />
                </pattern>
              </defs>

              {/* ═══ Ambient Background ═══ */}
              <rect width="500" height="400" fill="url(#bgGrid)" />
              {/* Slow-drifting bokeh depth circles */}
              {[0,1,2,3,4,5,6,7].map(i => {
                const bx = 40 + ((i * 67) % 420)
                const by = 30 + ((i * 53) % 340)
                const br = 20 + ((i * 11) % 25)
                return (
                  <circle key={`bk-${i}`} cx={bx} cy={by} r={br} fill="rgba(0,210,255,0.03)">
                    <animate attributeName="opacity" values="0.02;0.05;0.02" dur={`${10 + i * 3}s`} repeatCount="indefinite" />
                    <animate attributeName="cy" values={`${by};${by - 8};${by}`} dur={`${18 + i * 4}s`} repeatCount="indefinite" />
                  </circle>
                )
              })}

              {/* ═══ Edges + Multi-Packet Comet-Trail Flow ═══
                   3 packets per edge — lead has feGaussianBlur glow,
                   trail packets stagger behind with decreasing size/opacity.
                   Speed scales with edge length for physical plausibility. */}
              {edges.map((edge, i) => {
                const dur = Math.max(1.5, Math.min(4, edge.length / 50))
                const edgeDelay = Math.min(i * 0.005, 1.5) + 0.5 // Stagger edges slightly after nodes
                return (
                  <g key={edge.id}>
                    <motion.path
                      id={edge.id}
                      d={`M ${edge.x1} ${edge.y1} L ${edge.x2} ${edge.y2}`}
                      fill="none" stroke="rgba(0,210,255,0.25)" strokeWidth="0.7"
                      initial={{ pathLength: 0, opacity: 0 }}
                      animate={{ pathLength: 1, opacity: 1 }}
                      transition={{ duration: 1.2, delay: edgeDelay, ease: 'easeInOut' }}
                    />
                    {/* Only show packets after entrance animation settles */}
                    {hasAnimatedIn && (
                      <>
                        {/* Lead packet — bright comet head */}
                        <circle r="2.5" fill="#7cf5ff" opacity="0.9" filter="url(#packetGlow)">
                          <animateMotion dur={`${dur}s`} repeatCount="indefinite">
                            <mpath href={`#${edge.id}`} />
                          </animateMotion>
                        </circle>
                        {/* Trail packet 2 — dimmer, staggered start */}
                        <circle r="1.8" fill="#7cf5ff" opacity="0.45">
                          <animateMotion dur={`${dur}s`} begin={`${(dur * 0.33).toFixed(2)}s`} repeatCount="indefinite">
                            <mpath href={`#${edge.id}`} />
                          </animateMotion>
                        </circle>
                        {/* Trail packet 3 — faint tail */}
                        <circle r="1.2" fill="#7cf5ff" opacity="0.2">
                          <animateMotion dur={`${dur}s`} begin={`${(dur * 0.66).toFixed(2)}s`} repeatCount="indefinite">
                            <mpath href={`#${edge.id}`} />
                          </animateMotion>
                        </circle>
                      </>
                    )}
                  </g>
                )
              })}

              {/* ═══ Nodes — Breathing Glow + Organic Drift ═══
                   Drift: framer-motion <motion.g> with 6-keyframe irregular paths
                   Glow + pulse: SVG-native <animate> on r/opacity (zero JS cost)
                   Red nodes pulse fast (1.2s), blue nodes breathe slowly (4s) */}
              {graphNodes.map((node, i) => {
                const drift = nodeDrifts.get(node.id) || { x: [0], y: [0], dur: 6 }
                const isMal = node.malicious
                const delay = Math.min(i * 0.015, 2) // Cap delay at 2s
                return (
                  <motion.g
                    key={node.id}
                    onClick={() => handleNodeClick(node)}
                    style={{ transformOrigin: `${node.x}px ${node.y}px`, cursor: 'pointer' }}
                    initial={{ scale: 0, opacity: 0 }}
                    animate={hasAnimatedIn 
                      ? { x: drift.x, y: drift.y, scale: 1, opacity: 1 } 
                      : { scale: 1, opacity: 1 }
                    }
                    transition={hasAnimatedIn 
                      ? { duration: drift.dur, repeat: Infinity, ease: 'easeInOut' }
                      : { delay, duration: 0.5, ease: 'easeOut', scale: { type: 'spring', bounce: 0.4 } }
                    }
                  >
                    {/* Glow aura — pulses behind the node */}
                    <circle
                      cx={node.x} cy={node.y}
                      r={isMal ? 10 : 7}
                      opacity={isMal ? 0.3 : 0.15}
                      fill={isMal ? 'rgba(255,56,96,0.2)' : 'rgba(0,210,255,0.1)'}
                      filter={isMal ? 'url(#glowRed)' : 'url(#glowBlue)'}
                    >
                      {hasAnimatedIn && (
                        <>
                          <animate attributeName="r"
                            values={isMal ? '10;15;10' : '7;9;7'}
                            dur={isMal ? '1.2s' : '4s'} repeatCount="indefinite" />
                          <animate attributeName="opacity"
                            values={isMal ? '0.3;0.7;0.3' : '0.15;0.3;0.15'}
                            dur={isMal ? '1.2s' : '4s'} repeatCount="indefinite" />
                        </>
                      )}
                    </circle>
                    {/* Attention weight ring */}
                    {node.inAttention && (
                      <circle
                        cx={node.x} cy={node.y} r={9}
                        fill="none" stroke="rgba(0,210,255,0.6)" strokeWidth="1.5"
                      />
                    )}
                    {/* Core node — breathes size + opacity */}
                    <circle
                      cx={node.x} cy={node.y}
                      r={isMal ? 5 : 3.5}
                      opacity={isMal ? 0.6 : 0.75}
                      fill={isMal ? '#ff3860' : '#00d2ff'}
                      style={{
                        filter: isMal
                          ? 'drop-shadow(0 0 6px rgba(255,56,96,0.8))'
                          : 'drop-shadow(0 0 3px rgba(0,210,255,0.5))',
                      }}
                    >
                      {hasAnimatedIn && (
                        <>
                          <animate attributeName="r"
                            values={isMal ? '5;7;5' : '3.5;4.5;3.5'}
                            dur={isMal ? '1.2s' : '4s'} repeatCount="indefinite" />
                          <animate attributeName="opacity"
                            values={isMal ? '0.6;1;0.6' : '0.75;0.9;0.75'}
                            dur={isMal ? '1.2s' : '4s'} repeatCount="indefinite" />
                        </>
                      )}
                    </circle>
                  </motion.g>
                )
              })}

              {/* ═══ Click Ripple — Expanding Sonar Ping ═══ */}
              <AnimatePresence>
                {ripples.map(ripple => (
                  <motion.g key={ripple.key} exit={{ opacity: 0 }} transition={{ duration: 0.1 }}>
                    {/* Outer ring */}
                    <motion.circle
                      cx={ripple.x} cy={ripple.y}
                      fill="none" stroke="rgba(0,210,255,0.8)" strokeWidth={2}
                      initial={{ r: 6, opacity: 1 }}
                      animate={{ r: 50, opacity: 0 }}
                      transition={{ duration: 0.8, ease: 'easeOut' }}
                    />
                    {/* Inner ring — staggered for depth */}
                    <motion.circle
                      cx={ripple.x} cy={ripple.y}
                      fill="none" stroke="rgba(0,210,255,0.4)" strokeWidth={1.5}
                      initial={{ r: 6, opacity: 0.7 }}
                      animate={{ r: 35, opacity: 0 }}
                      transition={{ duration: 0.6, delay: 0.15, ease: 'easeOut' }}
                    />
                  </motion.g>
                ))}
              </AnimatePresence>

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
                <YAxis dataKey="y" name="Risk score" domain={[0, 'auto']} axisLine={false} tickLine={false} />
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