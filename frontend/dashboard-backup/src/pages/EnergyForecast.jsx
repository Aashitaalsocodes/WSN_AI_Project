import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ReferenceDot } from 'recharts'
import KPICard from '../components/KPICard'
import ReactCountUp from 'react-countup'
const CountUp = ReactCountUp.default || ReactCountUp

export default function EnergyForecast({ data }) {
  const {
    model,
    valMSE,
    avgForecast,
    dataSource,
    sensorNodes,
    minVoltage,
    maxVoltage,
    voltageData,
    outlierNodes,
    clusterHeads,
    defaultThreshold
  } = data

  const [threshold, setThreshold] = useState(defaultThreshold)

  // Parse average forecast float for CountUp
  const avgForecastVal = parseFloat(avgForecast)

  const formatVoltage = (val) => `${val.toFixed(3)}V`

  return (
    <div className="main-content-inner">
      <h1 className="page-title">ENERGY FORECAST</h1>
      <p className="page-subtitle">LSTM time-series forecasting for sensor battery voltage and outlier cluster heads</p>

      {/* KPI Cards Row 1 */}
      <div className="kpi-grid">
        <div className="kpi-card kpi-card-red">
          <p className="kpi-label">Model</p>
          <p className="kpi-value kpi-value-red">
            {model}
          </p>
        </div>
        <div className="kpi-card kpi-card-red">
          <p className="kpi-label">Val MSE</p>
          <p className="kpi-value kpi-value-red">
            {Number(valMSE).toExponential(3)}
          </p>
        </div>
        <KPICard label="Avg Forecast" value={avgForecastVal} decimals={3} suffix=" mJ" color="red" delay={0.1} />
      </div>

      {/* KPI Cards Row 2 */}
      <div className="kpi-grid">
        <div className="kpi-card kpi-card-red">
          <p className="kpi-label">Data Source</p>
          <p className="kpi-value kpi-value-red">
            {dataSource}
          </p>
        </div>
        <KPICard label="Sensor Nodes" value={sensorNodes} color="red" delay={0.2} />
        <div className="kpi-card kpi-card-red">
          <p className="kpi-label">Min Voltage</p>
          <p className="kpi-value kpi-value-red">
            {minVoltage}
          </p>
        </div>
        <div className="kpi-card kpi-card-red">
          <p className="kpi-label">Max Voltage</p>
          <p className="kpi-value kpi-value-red">
            {maxVoltage}
          </p>
        </div>
      </div>

      {/* Energy Threshold Input */}
      <div className="dash-card flex-between mb-16" style={{ padding: '16px 24px' }}>
        <span style={{ fontSize: '14px', color: '#94a3b8' }}>Energy Threshold (V)</span>
        <div className="flex-center" style={{ gap: '12px' }}>
          <input
            type="number"
            className="energy-threshold-input"
            value={threshold}
            step="0.05"
            min="1.0"
            max="3.0"
            onChange={e => setThreshold(parseFloat(e.target.value) || 0)}
          />
        </div>
      </div>

      {/* Area Chart Container */}
      <div className="dash-card">
        <h2 className="dash-card-title">VOLTAGE FORECASTS & DETECTED OUTLIERS</h2>
        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={voltageData} margin={{ top: 20, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="redGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--neon-red)" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="var(--neon-red)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2030" vertical={false} />
              <XAxis dataKey="node" tick={{ fill: '#e2e8f0' }} axisLine={false} tickLine={false} label={{ value: 'Node ID', position: 'insideBottomRight', offset: -10, fill: '#64748b' }} />
              <YAxis domain={[1.8, 3.0]} tick={{ fill: '#e2e8f0' }} axisLine={false} tickLine={false} label={{ value: 'Voltage (V)', angle: -90, position: 'insideLeft', fill: '#64748b' }} />
              <Tooltip
                contentStyle={{
                  background: '#0d0d14',
                  border: '1px solid #1e2030',
                  borderRadius: '8px',
                  color: '#ffffff'
                }}
                itemStyle={{ color: '#ffffff' }}
              />
              <ReferenceLine y={threshold} stroke="var(--neon-red)" strokeDasharray="4 4" strokeWidth={1.5} label={{ position: 'top', value: `Threshold ${threshold}V`, fill: '#ff3860', fontSize: 11 }} />

              <Area
                type="monotone"
                dataKey="voltage"
                stroke="var(--neon-red)"
                strokeWidth={2}
                fill="url(#redGrad)"
                isAnimationActive={true}
                animationDuration={2000}
                animationBegin={500}
              />

              {/* Red Dots for Nodes below threshold */}
              {voltageData.map((d, index) => {
                if (d.voltage < threshold) {
                  return (
                    <ReferenceDot
                      key={`below-thresh-${index}`}
                      x={d.node}
                      y={d.voltage}
                      r={5}
                      fill="var(--neon-red)"
                      stroke="#0d0d14"
                      strokeWidth={1}
                    />
                  )
                }
                return null
              })}

              {/* Amber Dots for Outliers */}
              {voltageData.map((d, index) => {
                if (outlierNodes.includes(d.node)) {
                  return (
                    <ReferenceDot
                      key={`outlier-${index}`}
                      x={d.node}
                      y={d.voltage}
                      r={5.5}
                      fill="var(--neon-orange)"
                      stroke="#0d0d14"
                      strokeWidth={1}
                    />
                  )
                }
                return null
              })}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Cluster Heads Grid */}
      <div className="dash-card mt-24">
        <h2 className="dash-card-title">TOP CLUSTER HEAD SELECTIONS</h2>
        <div className="cluster-heads-list">
          {clusterHeads.map((ch, idx) => (
            <motion.div
              key={ch.id}
              className="cluster-head-item"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1, duration: 0.4 }}
            >
              <div className={`cluster-head-rank ${ch.rank === 1 ? 'cluster-head-rank-1' : 'cluster-head-rank-other'}`}>
                {ch.rank}
              </div>
              <span className="cluster-head-name">{ch.id}</span>
              {ch.selected && (
                <span className="cluster-head-tag cluster-head-tag-selected">
                  Selected
                </span>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}
