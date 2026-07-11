import React, { useState } from 'react'
import { motion } from 'framer-motion'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

export default function EvaluationPerformance({ data }) {
  const [activeTab, setActiveTab] = useState('security')

  if (!data) {
    return (
      <div className="main-content-inner">
        <div className="loading-screen" style={{ minHeight: '400px' }}>
          <div className="loading-spinner" />
          <p className="loading-text">Loading evaluation metrics...</p>
        </div>
      </div>
    )
  }

  const { security, energy, network_performance: net } = data
  const energyDataReady = typeof energy.first_node_death_round === 'number'

  // --- Security chart data ---
  const perTypeData = Object.entries(security.precision_recall_f1_by_type).map(([type, m]) => ({
    type,
    precision: +(m.precision * 100).toFixed(1),
    recall: +(m.recall * 100).toFixed(1),
    f1: +(m.f1_score * 100).toFixed(1),
  }))

  const fprData = Object.entries(security.false_positive_rate_by_type).map(([type, v]) => ({
    type,
    fpr: +(v * 100).toFixed(2),
  }))

  const mitigationData = [
    { name: 'Baseline', compromised: security.successful_attack_mitigation_rate.pct_compromised_routes_baseline },
    { name: 'Cost-Aware', compromised: security.successful_attack_mitigation_rate.pct_compromised_routes_cost_aware },
  ]
  // --- Energy chart data ---
  const energyTrend = energyDataReady
    ? energy.average_residual_energy_trend.map((v, i) => ({
        round: i,
        residualEnergy: +(v * 100).toFixed(1),
        deadNodes: energy.num_dead_nodes_trend[i],
      }))
    : []
  
  const trustTrend = energy.network_health_proxies.compromised_routes_pct_trend.map((v, i) => ({
    round: i,
    compromisedPct: v,
  }))

  // --- Network performance chart data ---
  const hopData = [
    { name: 'Baseline', hops: net.end_to_end_delay_proxy_avg_hops.baseline_avg_hops },
    { name: 'Cost-Aware', hops: net.end_to_end_delay_proxy_avg_hops.cost_aware_avg_hops },
  ]

  const kpis = [
    { label: 'Detection Accuracy', value: `${(security.attack_detection_accuracy * 100).toFixed(1)}%`, sub: 'Overall attack detection' },
    { label: 'Macro F1', value: security.macro_f1.toFixed(3), sub: 'Unweighted avg across types' },
    { label: 'Mitigation Improvement', value: `${security.successful_attack_mitigation_rate.improvement_percentage_points} pts`, sub: 'Compromised routes reduced' },
    { label: 'First Node Death', value: energyDataReady ? `Round ${energy.first_node_death_round}` : 'N/A', sub: energyDataReady ? `Half dead: round ${energy.half_node_death_round}` : 'Backend not updated yet' },
    { label: 'Avg Residual Energy', value: energyDataReady ? `${(energy.average_residual_energy * 100).toFixed(1)}%` : 'N/A', sub: 'End of simulation' },
    { label: 'Avg Trust on Path', value: net.avg_trust_on_path.toFixed(3), sub: 'Cost-aware routing' },
  ]

  return (
    <div className="main-content-inner">
      <h1 className="page-title">EVALUATION &amp; PERFORMANCE</h1>
      <p className="page-subtitle">Aggregate security, energy, and network performance metrics across the full WSN AI pipeline</p>

      {/* KPI Cards */}
      <div className="kpi-grid mb-24">
        {kpis.map((k) => (
          <div className="kpi-card" key={k.label}>
            <div className="kpi-label">{k.label}</div>
            <div className="kpi-value">{k.value}</div>
            <div className="kpi-sub">{k.sub}</div>
          </div>
        ))}
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-8 mb-16">
        {['security', 'energy', 'network'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`node-lookup-btn ${activeTab === tab ? '' : 'opacity-50'}`}
            style={{ padding: '8px 20px', fontSize: '12px' }}
          >
            {tab === 'security' ? 'Security' : tab === 'energy' ? 'Energy' : 'Network Performance'}
          </button>
        ))}
      </div>

      {/* Tab: Security */}
      {activeTab === 'security' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="dash-card mb-16">
            <h2 className="dash-card-title">PRECISION / RECALL / F1 BY ATTACK TYPE</h2>
            <p className="model-note mb-16">Multiclass classifier performance per attack type (macro F1: {security.macro_f1.toFixed(4)})</p>
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={perTypeData} margin={{ top: 20, right: 20, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2030" />
                  <XAxis dataKey="type" axisLine={false} tickLine={false} />
                  <YAxis axisLine={false} tickLine={false} domain={[0, 100]} />
                  <Tooltip contentStyle={{ background: '#0d0d14', border: '1px solid #1e2030', borderRadius: '8px', color: '#fff' }} />
                  <Legend />
                  <Line type="monotone" dataKey="precision" stroke="#00d2ff" strokeWidth={2.5} dot={false} activeDot={{ r: 5, style: { filter: 'drop-shadow(0 0 5px #00d2ff)' } }} style={{ filter: 'drop-shadow(0 0 6px rgba(0,210,255,0.6))' }} isAnimationActive={true} animationDuration={1200} animationEasing="ease-out" />
                  <Line type="monotone" dataKey="recall" stroke="#a78bfa" strokeWidth={2.5} dot={false} activeDot={{ r: 5, style: { filter: 'drop-shadow(0 0 5px #a78bfa)' } }} style={{ filter: 'drop-shadow(0 0 6px rgba(167,139,250,0.6))' }} isAnimationActive={true} animationDuration={1200} animationEasing="ease-out" />
                  <Line type="monotone" dataKey="f1" stroke="#ffb020" strokeWidth={2.5} dot={false} activeDot={{ r: 5, style: { filter: 'drop-shadow(0 0 5px #ffb020)' } }} style={{ filter: 'drop-shadow(0 0 6px rgba(255,176,32,0.6))' }} isAnimationActive={true} animationDuration={1200} animationEasing="ease-out" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid-2 mb-16" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="dash-card">
              <h2 className="dash-card-title">FALSE POSITIVE RATE BY TYPE</h2>
              <p className="model-note mb-16">Normal traffic incorrectly flagged as this attack type</p>
              <div className="chart-wrapper" style={{ height: '260px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={fprData} margin={{ top: 20, right: 20, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2030" />
                    <XAxis dataKey="type" axisLine={false} tickLine={false} />
                    <YAxis axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: '#0d0d14', border: '1px solid #1e2030', borderRadius: '8px', color: '#fff' }} formatter={(v) => `${v}%`} />
                    <Line type="monotone" dataKey="fpr" stroke="#ff3860" strokeWidth={2.5} dot={false} activeDot={{ r: 5, style: { filter: 'drop-shadow(0 0 5px #ff3860)' } }} style={{ filter: 'drop-shadow(0 0 6px rgba(255,56,96,0.6))' }} isAnimationActive={true} animationDuration={1200} animationEasing="ease-out" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="dash-card">
              <h2 className="dash-card-title">MITIGATION EFFECTIVENESS</h2>
              <p className="model-note mb-16">{security.successful_attack_mitigation_rate.note}</p>
              <div className="chart-wrapper" style={{ height: '260px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={mitigationData} margin={{ top: 20, right: 20, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2030" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} />
                    <YAxis axisLine={false} tickLine={false} domain={[0, 30]} />
                    <Tooltip contentStyle={{ background: '#0d0d14', border: '1px solid #1e2030', borderRadius: '8px', color: '#fff' }} formatter={(v) => `${v}%`} />
                    <Line type="monotone" dataKey="compromised" stroke="#00d2ff" strokeWidth={3} dot={false} activeDot={{ r: 5, style: { filter: 'drop-shadow(0 0 5px #00d2ff)' } }} style={{ filter: 'drop-shadow(0 0 6px rgba(0,210,255,0.6))' }} isAnimationActive={true} animationDuration={1200} animationEasing="ease-out" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="dash-card">
            <h2 className="dash-card-title">RECALIBRATION CONVERGENCE</h2>
            <div className="model-card-metrics mt-16">
              <div className="model-metric">
                <div className="model-metric-label">Detection Miss Rate Converged</div>
                <div className="model-metric-value neon-text-cyan">
                  {security.recalibration_convergence.detection_miss_rate_converged_count} / {security.recalibration_convergence.detection_miss_rate_total_types}
                </div>
              </div>
              <div className="model-metric">
                <div className="model-metric-label">Attack Risk Weights Converged</div>
                <div className="model-metric-value neon-text-cyan">
                  {security.recalibration_convergence.attack_risk_weights_converged_count} / {security.recalibration_convergence.attack_risk_weights_total_types}
                </div>
              </div>
              <div className="model-metric">
                <div className="model-metric-label">Attack Traffic Missed</div>
                <div className="model-metric-value neon-text-white">{(security.attack_traffic_missed_as_normal_rate * 100).toFixed(2)}%</div>
              </div>
              <div className="model-metric">
                <div className="model-metric-label">Packet Delivery (Under Attack)</div>
                <div className="model-metric-value neon-text-green">{(security.packet_delivery_ratio_under_attack * 100).toFixed(1)}%</div>
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Tab: Energy */}
      {activeTab === 'energy' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="dash-card mb-16">
            <h2 className="dash-card-title">RESIDUAL ENERGY &amp; NODE DEATHS OVER TIME</h2>
            <p className="model-note mb-16">
              FND: round {energy.first_node_death_round} | HND: round {energy.half_node_death_round} | LND: {energy.last_node_death_round ?? 'not reached (20 rounds)'}
            </p>
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={energyTrend} margin={{ top: 20, right: 20, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2030" />
                  <XAxis dataKey="round" axisLine={false} tickLine={false} label={{ value: 'Round', position: 'insideBottom', offset: -5, fill: '#888' }} />
                  <YAxis yAxisId="left" axisLine={false} tickLine={false} domain={[0, 100]} />
                  <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} domain={[0, 500]} />
                  <Tooltip contentStyle={{ background: '#0d0d14', border: '1px solid #1e2030', borderRadius: '8px', color: '#fff' }} />
                  <Legend />
                  <Line yAxisId="left" type="monotone" dataKey="residualEnergy" name="Avg Residual Energy %" stroke="#00d2ff" strokeWidth={2} dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="deadNodes" name="Dead Nodes" stroke="#ff3860" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid-2 mb-16" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="dash-card">
              <h2 className="dash-card-title">COMPROMISED ROUTES % OVER TIME</h2>
              <p className="model-note mb-16">Network health proxy — trust decline / compromise rate over 20 rounds</p>
              <div className="chart-wrapper" style={{ height: '260px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trustTrend} margin={{ top: 20, right: 20, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2030" />
                    <XAxis dataKey="round" axisLine={false} tickLine={false} />
                    <YAxis axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: '#0d0d14', border: '1px solid #1e2030', borderRadius: '8px', color: '#fff' }} formatter={(v) => `${v}%`} />
                    <Line type="monotone" dataKey="compromisedPct" stroke="#a78bfa" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="dash-card">
              <h2 className="dash-card-title">ENERGY METRICS SUMMARY</h2>
              <div className="model-card-metrics mt-16">
                <div className="model-metric">
                  <div className="model-metric-label">Total Nodes</div>
                  <div className="model-metric-value neon-text-white">{energy.total_nodes}</div>
                </div>
                <div className="model-metric">
                  <div className="model-metric-label">Energy / Packet (proxy)</div>
                  <div className="model-metric-value neon-text-cyan">{energy.energy_consumption_per_packet.toFixed(3)}</div>
                </div>
                <div className="model-metric">
                  <div className="model-metric-label">Trust Decline</div>
                  <div className="model-metric-value neon-text-red">-{energy.network_health_proxies.avg_trust_score_decline.toFixed(4)}</div>
                </div>
                <div className="model-metric">
                  <div className="model-metric-label">Network Lifetime</div>
                  <div className="model-metric-value neon-text-white">{energy.network_lifetime ?? 'Not reached'}</div>
                </div>
              </div>
              <p className="model-note mt-16">{energy.energy_consumption_per_packet_note}</p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Tab: Network Performance */}
      {activeTab === 'network' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="grid-2 mb-16" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="dash-card">
              <h2 className="dash-card-title">AVG HOP COUNT — COST-AWARE VS BASELINE</h2>
              <p className="model-note mb-16">Proxy for end-to-end delay (tradeoff: +{net.end_to_end_delay_proxy_avg_hops.hop_count_tradeoff})</p>
              <div className="chart-wrapper" style={{ height: '260px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={hopData} margin={{ top: 20, right: 20, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2030" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} />
                    <YAxis axisLine={false} tickLine={false} domain={[0, 6]} />
                    <Tooltip contentStyle={{ background: '#0d0d14', border: '1px solid #1e2030', borderRadius: '8px', color: '#fff' }} />
                    <Line type="monotone" dataKey="hops" stroke="#00d2ff" strokeWidth={3} dot={false} activeDot={{ r: 5, style: { filter: 'drop-shadow(0 0 5px #00d2ff)' } }} style={{ filter: 'drop-shadow(0 0 6px rgba(0,210,255,0.6))' }} isAnimationActive={true} animationDuration={1200} animationEasing="ease-out" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="dash-card">
              <h2 className="dash-card-title">ROUTING OVERHEAD &amp; TRUST</h2>
              <div className="model-card-metrics mt-16">
                <div className="model-metric">
                  <div className="model-metric-label">Avg Total Cost</div>
                  <div className="model-metric-value neon-text-cyan">{net.routing_overhead.avg_total_cost.toFixed(4)}</div>
                </div>
                <div className="model-metric">
                  <div className="model-metric-label">Avg Trust on Path</div>
                  <div className="model-metric-value neon-text-green">{net.avg_trust_on_path.toFixed(4)}</div>
                </div>
                <div className="model-metric">
                  <div className="model-metric-label">Throughput</div>
                  <div className="model-metric-value neon-text-white" style={{ fontSize: '12px' }}>Not available</div>
                </div>
              </div>
              <p className="model-note mt-16">{net.routing_overhead.note}</p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}