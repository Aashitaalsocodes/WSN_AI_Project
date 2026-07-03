import React, { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import * as d3 from 'd3'
import KPICard from '../components/KPICard'
import { Network, ShieldAlert, BarChart3, Target } from 'lucide-react'
import ReactCountUp from 'react-countup'
const CountUp = ReactCountUp.default || ReactCountUp

export default function NetworkOverview({ data }) {
  const svgRef = useRef(null)
  const [threshold, setThreshold] = useState(0.40)

  useEffect(() => {
    if (!svgRef.current) return
    const svgElement = svgRef.current
    const width = svgElement.clientWidth || 500
    const height = svgElement.clientHeight || 300

    const nodes = Array.from({ length: 80 }).map((_, i) => ({
      id: i,
      status: i >= 73 ? 'attacked' : 'normal',
      radius: i >= 73 ? 7 : 5,
    }))

    const links = []
    for (let i = 0; i < 150; i++) {
      const source = Math.floor(Math.random() * 80)
      let target = Math.floor(Math.random() * 80)
      if (source !== target) links.push({ source, target })
    }

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(30))
      .force('charge', d3.forceManyBody().strength(-25))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(d => d.radius + 2))

    const svg = d3.select(svgElement)
    svg.selectAll('*').remove()

    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', 'var(--neon-cyan)')
      .attr('stroke-opacity', 0.8)
      .attr('stroke-width', 2)
      .style('filter', 'drop-shadow(0 0 4px var(--neon-cyan))')

    const node = svg.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', d => d.radius)
      .attr('fill', d => d.status === 'attacked' ? '#ff3860' : '#e2e8f0')
      .style('filter', d => d.status === 'attacked' 
        ? 'drop-shadow(0 0 6px #ff3860)' 
        : 'drop-shadow(0 0 2px rgba(226,232,240,0.3))'
      )
      .style('animation', d => d.status === 'attacked' ? 'pulse-node-red 2s infinite' : 'none')

    simulation.on('tick', () => {
      link
        .attr('x1', d => Math.max(10, Math.min(width - 10, d.source.x)))
        .attr('y1', d => Math.max(10, Math.min(height - 10, d.source.y)))
        .attr('x2', d => Math.max(10, Math.min(width - 10, d.target.x)))
        .attr('y2', d => Math.max(10, Math.min(height - 10, d.target.y)))
      node
        .attr('cx', d => { d.x = Math.max(10, Math.min(width - 10, d.x || width / 2)); return d.x })
        .attr('cy', d => { d.y = Math.max(10, Math.min(height - 10, d.y || height / 2)); return d.y })
    })

    const handleResize = () => {
      if (!svgElement) return
      const w = svgElement.clientWidth
      const h = svgElement.clientHeight
      simulation.force('center', d3.forceCenter(w / 2, h / 2))
      simulation.alpha(0.3).restart()
    }
    window.addEventListener('resize', handleResize)
    return () => { simulation.stop(); window.removeEventListener('resize', handleResize) }
  }, [])

  const getThresholdData = (val) => {
    if (val <= 0.34) return data.trustThresholds[0]
    if (val <= 0.41) return data.trustThresholds[1]
    if (val <= 0.70) return data.trustThresholds[2]
    return data.trustThresholds[3]
  }
  const thresholdData = getThresholdData(threshold)

  const total = data.nodeDistribution.reduce((sum, d) => sum + d.value, 0)

  const RADIAN = Math.PI / 180
  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5
    const x = cx + radius * Math.cos(-midAngle * RADIAN)
    const y = cy + radius * Math.sin(-midAngle * RADIAN)
    return (
      <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize="10px" fontWeight="bold">
        {percent > 0.05 ? `${(percent * 100).toFixed(0)}%` : ''}
      </text>
    )
  }

  return (
    <div className="main-content-inner">
      <h1 className="page-title">Network Overview</h1>
      <p className="page-subtitle">WSN-DS dataset summary and attack distribution across 3,74,661 sensor nodes</p>

      <div className="kpi-grid">
        <KPICard label="Total Nodes" value={data.totalNodes} color="cyan" delay={0} icon={Network} description="Active sensor nodes" />
        <KPICard label="Attacked Nodes" value={data.attackedNodes} color="red" delay={0.1} icon={ShieldAlert} description="Detected intrusions" />
        <KPICard label="% Attacked" value={data.percentAttacked} decimals={2} suffix="%" color="orange" delay={0.2} icon={BarChart3} description="Attack ratio" />
        <KPICard label="Classifier F1" value={data.classifierF1} decimals={4} color="green" delay={0.3} icon={Target} description="XGBoost score" />
      </div>

      <div className="two-col-grid">
        <motion.div className="dash-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }}>
          <h2 className="dash-card-title">Attack Type Distribution</h2>
          <div className="donut-chart-container">
            <div style={{ width: '220px', height: 220, flexShrink: 0 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.nodeDistribution}
                    cx="50%" cy="50%"
                    innerRadius={60} outerRadius={100}
                    paddingAngle={3} dataKey="value"
                    isAnimationActive={true}
                    animationBegin={500} animationDuration={1200}
                    labelLine={false}
                    label={renderCustomizedLabel}
                  >
                    {data.nodeDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color === '#ff3860' ? 'var(--neon-red)' : (entry.color === '#ffb020' ? 'var(--neon-orange)' : 'var(--neon-purple)')} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#0d0d14', border: '1px solid #1e2030', borderRadius: '8px', color: '#ffffff' }}
                    itemStyle={{ color: '#ffffff' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="donut-legend">
              {data.nodeDistribution.map((item, idx) => (
                <div key={idx} className="donut-legend-item">
                  <span className="donut-legend-dot" style={{ backgroundColor: item.color }} />
                  <span>{item.name}</span>
                  <span className="donut-legend-value">
                    {item.value.toLocaleString()}
                    <span className="donut-legend-percent"> ({((item.value / total) * 100).toFixed(1)}%)</span>
                  </span>
                </div>
              ))}
              <div className="donut-total-row">
                <span>Total</span>
                <span className="donut-legend-value">{total.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </motion.div>

        <motion.div className="dash-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.3 }}>
          <h2 className="dash-card-title">Network Topology</h2>
          <div className="force-graph-container breathing-glow" style={{ height: 350 }}>
            <svg ref={svgRef} style={{ width: '100%', height: '100%' }} />
          </div>
          <div className="force-graph-legend">
            <div className="force-graph-legend-item">
              <span className="force-graph-legend-dot" style={{ background: '#e2e8f0' }} />
              <span>Normal (73)</span>
            </div>
            <div className="force-graph-legend-item">
              <span className="force-graph-legend-dot" style={{ background: '#ff3860' }} />
              <span>Attacked (7)</span>
            </div>
          </div>
        </motion.div>
      </div>

      <motion.div className="dash-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.4 }}>
        <h2 className="dash-card-title">Trust Threshold Tuning</h2>
        <div className="trust-slider-container">
          <div className="trust-slider-row">
            <div style={{ flex: 1 }}>
              <input
                type="range" min="0.10" max="0.90" step="0.01"
                value={threshold}
                onChange={e => setThreshold(parseFloat(e.target.value))}
                className="trust-slider-input"
              />
              <div className="trust-slider-labels">
                <span>0.10 (lenient)</span>
                <span>0.90 (strict)</span>
              </div>
            </div>
            <div className="trust-slider-value">{threshold.toFixed(2)}</div>
          </div>

          <div className="trust-slider-info">
            <div className="trust-slider-stat" style={{ border: '1px solid rgba(255,56,96,0.2)' }}>
              <span className="trust-slider-stat-label">Flagged Nodes</span>
              <span className="trust-slider-stat-value trust-slider-stat-value-red">
                <CountUp end={thresholdData.flagged} separator="," duration={0.4} preserveValue />
              </span>
            </div>
            <div className="trust-slider-stat" style={{ border: '1px solid rgba(255,176,32,0.2)' }}>
              <span className="trust-slider-stat-label">% Flagged</span>
              <span className="trust-slider-stat-value trust-slider-stat-value-orange">
                <CountUp end={thresholdData.percent} decimals={2} suffix="%" duration={0.4} preserveValue />
              </span>
            </div>
          </div>

          <div style={{ minHeight: '50px' }}>
            {threshold < 0.30 && (
              <div className="banner-warning banner-red">
                <span>⚠</span> Threshold too low — high false positive rate
              </div>
            )}
            {threshold > 0.70 && (
              <div className="banner-warning banner-red">
                <span>⚠</span> Threshold too high — attacks may go undetected
              </div>
            )}
            {threshold >= 0.40 && threshold <= 0.50 && (
              <div className="banner-warning banner-green">
                <span>✓</span> Optimal threshold range
              </div>
            )}
          </div>

          <p className="trust-slider-caption">Out of 3,74,661 total nodes</p>
        </div>
      </motion.div>
    </div>
  )
}
