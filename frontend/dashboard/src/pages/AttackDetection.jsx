import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactCountUp from 'react-countup'
const CountUp = ReactCountUp.default || ReactCountUp
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

export default function AttackDetection({ data }) {
  const { models, detectionRates, confusionMatrix } = data
  const testSetSize = 74933

  const [nodeId, setNodeId] = useState('')
  const [analyzedNode, setAnalyzedNode] = useState(null)

  const handleAnalyze = (e) => {
    e.preventDefault()
    if (!nodeId.trim()) return

    const id = parseInt(nodeId, 10)
    const isAnomalous = id > 370000

    // Simulate analysis result
    const anomalyScore = isAnomalous
      ? 0.70 + Math.random() * 0.25
      : Math.random() * 0.28

    const trustScore = isAnomalous
      ? 0.10 + Math.random() * 0.22
      : 0.65 + Math.random() * 0.30

    const attackProbability = anomalyScore * 0.98

    const status = isAnomalous ? 'ANOMALOUS' : 'NORMAL'

    setAnalyzedNode({
      id,
      anomalyScore: anomalyScore.toFixed(4),
      trustScore: trustScore.toFixed(4),
      attackProbability: (attackProbability * 100).toFixed(2),
      status
    })
  }

  // Map IF and XGB data for chart correctly
  const chartData = detectionRates.map(r => ({
    name: r.attack,
    "Isolation Forest": r.isolationForest,
    "XGBoost": r.xgboost
  }))

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const cellVariants = {
    hidden: { scale: 0.3, opacity: 0 },
    show: { scale: 1, opacity: 1, transition: { type: 'spring', stiffness: 200, damping: 15 } }
  }

  return (
    <div className="main-content-inner">
      <h1 className="page-title">ATTACK DETECTION</h1>
      <p className="page-subtitle">Evaluation of machine learning models for anomaly and intrusion classification</p>

      {/* Model Cards Side-by-Side */}
      <div className="two-col-grid">
        {/* Isolation Forest Card */}
        <motion.div
          className="card"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          whileHover={{ translateY: -3 }}
        >
          <div className="flex-between mb-16">
            <h3 className="model-card-name">Isolation Forest</h3>
            <span className="badge badge-amber badge-pulse">Unsupervised baseline</span>
          </div>
          <div className="model-card-metrics">
            <div className="model-metric">
              <div className="model-metric-label">F1 Score</div>
              <div className="model-metric-value neon-text-white">0.31</div>
            </div>
            <div className="model-metric">
              <div className="model-metric-label">Precision</div>
              <div className="model-metric-value neon-text-white">0.3125</div>
            </div>
            <div className="model-metric">
              <div className="model-metric-label">Recall</div>
              <div className="model-metric-value neon-text-white">0.3120</div>
            </div>
          </div>
        </motion.div>

        {/* XGBoost Card */}
        <motion.div
          className="card"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          whileHover={{ translateY: -3 }}
        >
          <div className="flex-between mb-16">
            <h3 className="model-card-name">XGBoost</h3>
            <span className="badge badge-green badge-pulse">Leakage-free evaluation</span>
          </div>
          <div className="model-card-metrics">
            <div className="model-metric">
              <div className="model-metric-label">F1 Score</div>
              <div className="model-metric-value neon-text-white">0.94</div>
            </div>
            <div className="model-metric">
              <div className="model-metric-label">Precision</div>
              <div className="model-metric-value neon-text-white">0.8945</div>
            </div>
            <div className="model-metric">
              <div className="model-metric-label">Recall</div>
              <div className="model-metric-value neon-text-white">0.9827</div>
            </div>
          </div>
        </motion.div>
      </div>

      <p className="model-note mb-24">Evaluated on held-out test set of {testSetSize.toLocaleString()} nodes — no data leakage</p>

      {/* Charts Row */}
      <div className="two-col-grid">
        {/* Detection Rate Bar Chart */}
        <div className="dash-card">
          <h2 className="dash-card-title">DETECTION RATE BY ATTACK TYPE</h2>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 20, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2030" vertical={false} />
                <XAxis dataKey="name" axisLine={false} tickLine={false} />
                <YAxis unit="%" domain={[0, 100]} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: '#0d0d14',
                    border: '1px solid #1e2030',
                    borderRadius: '8px',
                    color: '#ffffff'
                  }}
                  itemStyle={{ color: '#ffffff' }}
                />
                <Legend iconType="circle" />
                <Bar dataKey="Isolation Forest" fill="var(--neon-red)" isAnimationActive={true} animationDuration={1200} />
                <Bar dataKey="XGBoost" fill="var(--neon-cyan)" isAnimationActive={true} animationDuration={1200} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Confusion Matrix */}
        <div className="dash-card">
          <h2 className="dash-card-title">CONFUSION MATRIX</h2>
          <motion.div 
            className="confusion-matrix"
            variants={containerVariants}
            initial="hidden"
            animate="show"
          >
            {/* TP */}
            <motion.div className="confusion-cell" variants={cellVariants} style={{ border: '1px solid rgba(0,255,136,0.8)', boxShadow: '0 0 20px rgba(0,255,136,0.35), inset 0 0 10px rgba(0,255,136,0.15)' }}>
              <div className="confusion-cell-label">True Positive (TP)</div>
              <div className="confusion-cell-value neon-text-green">
                <CountUp end={confusionMatrix.tp} separator="," duration={1.8} />
              </div>
            </motion.div>

            {/* FP */}
            <motion.div className="confusion-cell" variants={cellVariants} style={{ border: '1px solid rgba(255,0,110,0.8)', boxShadow: '0 0 20px rgba(255,0,110,0.35), inset 0 0 10px rgba(255,0,110,0.15)' }}>
              <div className="confusion-cell-label">False Positive (FP)</div>
              <div className="confusion-cell-value neon-text-pink">
                <CountUp end={confusionMatrix.fp} separator="," duration={1.8} />
              </div>
            </motion.div>

            {/* FN */}
            <motion.div className="confusion-cell" variants={cellVariants} style={{ border: '1px solid rgba(255,176,32,0.8)', boxShadow: '0 0 20px rgba(255,176,32,0.35), inset 0 0 10px rgba(255,176,32,0.15)' }}>
              <div className="confusion-cell-label">False Negative (FN)</div>
              <div className="confusion-cell-value neon-text-orange">
                <CountUp end={confusionMatrix.fn} separator="," duration={1.8} />
              </div>
            </motion.div>

            {/* TN */}
            <motion.div className="confusion-cell" variants={cellVariants} style={{ border: '1px solid rgba(0,210,255,0.8)', boxShadow: '0 0 20px rgba(0,210,255,0.35), inset 0 0 10px rgba(0,210,255,0.15)' }}>
              <div className="confusion-cell-label">True Negative (TN)</div>
              <div className="confusion-cell-value neon-text-cyan">
                <CountUp end={confusionMatrix.tn} separator="," duration={1.8} />
              </div>
            </motion.div>
          </motion.div>
        </div>
      </div>

      {/* Node Lookup Panel */}
      <div className="dash-card mt-16">
        <h2 className="dash-card-title">NODE SEARCH & ANALYTICS</h2>
        <form onSubmit={handleAnalyze} className="node-lookup">
          <div className="node-lookup-input-row">
            <input
              type="number"
              className="node-lookup-input"
              placeholder="Enter node ID (e.g. 373986)"
              value={nodeId}
              onChange={e => setNodeId(e.target.value)}
            />
            <motion.button
              type="submit"
              className="node-lookup-btn"
              whileTap={{ scale: 0.95 }}
            >
              Analyze
            </motion.button>
          </div>
        </form>

        <AnimatePresence mode="wait">
          {analyzedNode && (
            <motion.div
              key={analyzedNode.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.3 }}
              className="node-result-card card"
            >
              <div className="node-result-grid">
                <div className="node-result-item">
                  <span className="node-result-label">Anomaly Score</span>
                  <span className="node-result-value neon-text-cyan">{analyzedNode.anomalyScore}</span>
                </div>
                <div className="node-result-item">
                  <span className="node-result-label">Trust Score</span>
                  <span className="node-result-value neon-text-purple">{analyzedNode.trustScore}</span>
                </div>
                <div className="node-result-item">
                  <span className="node-result-label">Attack Probability</span>
                  <span className="node-result-value neon-text-orange">{analyzedNode.attackProbability}%</span>
                </div>
                <div className="node-result-item">
                  <span className="node-result-label">Predicted Status</span>
                  <span className={`node-result-value ${analyzedNode.status === 'ANOMALOUS' ? 'neon-text-red' : 'neon-text-green'}`}>
                    {analyzedNode.status}
                  </span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
