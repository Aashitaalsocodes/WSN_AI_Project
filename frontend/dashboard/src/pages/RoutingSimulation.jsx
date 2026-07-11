import React, { useState } from 'react'
import { motion } from 'framer-motion'
import ReactCountUp from 'react-countup'
const CountUp = ReactCountUp.default || ReactCountUp
import { CheckCircle } from 'lucide-react'
import KPICard from '../components/KPICard'

export default function RoutingSimulation({ data }) {
  const { baseline, trustAware, metrics, sampleRoutes, costWeights } = data
  const [settled, setSettled] = useState(false)
  const [selectedRouteIdx, setSelectedRouteIdx] = useState(0)

  const selectedRoute = sampleRoutes[selectedRouteIdx]

  return (
    <div className="main-content-inner">
      <h1 className="page-title">ROUTING SIMULATION</h1>
      <p className="page-subtitle">Trust-aware secure path routing versus baseline network routing</p>

      {/* Hero Banner */}
      <div className="routing-hero">
        <div className="routing-hero-icons">
          <div className={`routing-hero-value neon-text-green ${settled ? 'breathing-glow' : ''}`}>
            23% →{' '}
            <CountUp
              start={23}
              end={0}
              duration={2}
              suffix="%"
              onEnd={() => setSettled(true)}
            />
          </div>
          {settled && (
            <motion.div
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 260, damping: 20 }}
            >
              <CheckCircle size={44} className="neon-text-green" />
            </motion.div>
          )}
        </div>
        <p className="routing-hero-subtitle">
          Compromised routes eliminated by trust-aware routing
        </p>
      </div>

      {/* Side-by-Side Comparison Cards */}
      <div className="two-col-grid">
        {/* Baseline Card */}
        <motion.div
          className="card"
          style={{ border: '1px solid rgba(255,56,96,0.2)' }}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          whileHover={{ translateY: -3 }}
        >
          <h3 className="routing-card-title neon-text-red">Baseline Routing</h3>
          <div className="routing-card-stat">
            <div className="routing-card-stat-label">Compromised routes</div>
            <div className="routing-card-stat-value neon-text-red">{baseline.compromisedPercent}%</div>
          </div>
          <div className="routing-card-stat">
            <div className="routing-card-stat-label">Routes Affected</div>
            <div className="routing-card-stat-value neon-text-white">{baseline.routesAffected} / {baseline.totalRoutes}</div>
          </div>
          <div className="routing-card-stat" style={{ marginBottom: 0 }}>
            <div className="routing-card-stat-label">Average Hops</div>
            <div className="routing-card-stat-value neon-text-white">{baseline.avgHops}</div>
          </div>
        </motion.div>

        {/* Trust-Aware Card */}
        <motion.div
          className="card"
          style={{ border: '1px solid rgba(0,255,136,0.2)' }}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          whileHover={{ translateY: -3 }}
        >
          <h3 className="routing-card-title neon-text-green">Trust-Aware Routing</h3>
          <div className="routing-card-stat">
            <div className="routing-card-stat-label">Compromised routes</div>
            <div className="routing-card-stat-value neon-text-green">
              <CountUp end={trustAware.compromisedPercent} suffix="%" duration={1.5} />
            </div>
          </div>
          <div className="routing-card-stat">
            <div className="routing-card-stat-label">Routes Affected</div>
            <div className="routing-card-stat-value neon-text-white">
              <CountUp end={trustAware.routesAffected} /> / {trustAware.totalRoutes}
            </div>
          </div>
          <div className="routing-card-stat" style={{ marginBottom: 0 }}>
            <div className="routing-card-stat-label">Average Hops</div>
            <div className="routing-card-stat-value neon-text-white">
              <CountUp end={trustAware.avgHops} decimals={2} duration={1.5} />
            </div>
          </div>
        </motion.div>
      </div>

      {/* Metric Cards Row */}
      <div className="kpi-grid">
        <KPICard label="Excluded Nodes" value={metrics.excludedNodes} color="cyan" delay={0} />
        <KPICard label="Hop Overhead" value={metrics.hopOverhead} decimals={2} prefix="+" color="cyan" delay={0.05} />
        <div className="kpi-card kpi-card-cyan">
          <p className="kpi-label">Routes Found</p>
          <p className="kpi-value kpi-value-cyan">
            {metrics.routesFound}
          </p>
        </div>
        <KPICard label="Trust Threshold" value={metrics.trustThreshold} decimals={2} color="cyan" delay={0.15} />
        <KPICard label="Network Nodes" value={metrics.networkNodes} color="cyan" delay={0.2} />
        <KPICard label="Network Edges" value={metrics.networkEdges} color="cyan" delay={0.25} />
      </div>

      {/* Route Path Visualizer */}
      <div className="dash-card mt-16">
        <h2 className="dash-card-title">ROUTE PATH VISUALIZER</h2>
        <div className="mb-16">
          <select
            className="route-select"
            value={selectedRouteIdx}
            onChange={(e) => setSelectedRouteIdx(Number(e.target.value))}
          >
            {sampleRoutes.map((route, idx) => (
              <option key={route.id} value={idx}>
                {route.label} ({route.hops} Hops)
              </option>
            ))}
          </select>
        </div>

        <div className="route-path-container">
          <div className="flex-center" style={{ gap: '8px', flexWrap: 'wrap', width: '100%' }}>
            {selectedRoute.path.map((node, i) => (
              <React.Fragment key={`${selectedRoute.id}-${node}-${i}`}>
                <motion.div
                  className="route-pill route-pill-safe"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.15, duration: 0.3 }}
                >
                  {node}
                </motion.div>
                {i < selectedRoute.path.length - 1 && (
                  <motion.span
                    className="neon-text-green route-arrow-anim"
                    style={{
                      fontSize: '18px',
                      fontWeight: 'bold',
                      animationDelay: `${i * 0.25}s`
                    }}
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    transition={{ delay: i * 0.15 + 0.08, duration: 0.2 }}
                  >
                    →
                  </motion.span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        <div className="flex-between mt-16" style={{ color: '#94a3b8', fontSize: '13px' }}>
          <div>
            Hops count:{' '}
            <span className="neon-text-cyan" style={{ fontWeight: 'bold' }}>
              {selectedRoute.hops}
            </span>
          </div>
          <div>
            Status:{' '}
            <span className="badge badge-green">
              {selectedRoute.status}
            </span>
          </div>
        </div>

        {/* Multi-Objective Cost Breakdown (Task 12) */}
        {selectedRoute.totalCost !== undefined && (
          <div className="mt-16" style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '16px' }}>
            <div className="flex-between" style={{ color: '#94a3b8', fontSize: '13px', marginBottom: '10px' }}>
              <div>
                Total Routing Cost:{' '}
                <span className="neon-text-amber" style={{ fontWeight: 'bold' }}>
                  {selectedRoute.totalCost.toFixed(4)}
                </span>
              </div>
              <div>
                Avg Trust on Path:{' '}
                <span className="neon-text-cyan" style={{ fontWeight: 'bold' }}>
                  {selectedRoute.avgTrust.toFixed(4)}
                </span>
              </div>
            </div>
            {costWeights && (
              <div style={{ color: '#64748b', fontSize: '11px' }}>
                Cost formula: ({costWeights.distance}×distance) + ({costWeights.energy}×energy) + ({costWeights.attackRisk}×attack_risk) / trust
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
