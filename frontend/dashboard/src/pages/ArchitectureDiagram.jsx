import React from 'react'
import { motion } from 'framer-motion'
import {
  Database,
  SlidersHorizontal,
  ShieldAlert,
  Radar,
  Route,
  RefreshCw,
  Server,
  MonitorSmartphone
} from 'lucide-react'

const stages = [
  {
    id: 'data-sources',
    title: 'Data Sources',
    color: 'cyan',
    icon: Database,
    description: 'Raw inputs feeding the pipeline.',
    items: ['WSN-DS dataset', 'IBRL sensor telemetry']
  },
  {
    id: 'preprocessing',
    title: 'Preprocessing & Feature Engineering',
    color: 'cyan',
    icon: SlidersHorizontal,
    description: 'Cleans and transforms raw data into model-ready features.',
    items: ['Missing value handling', 'Feature scaling & encoding']
  },
  {
    id: 'attack-detection',
    title: 'Attack Detection Models',
    color: 'magenta',
    icon: ShieldAlert,
    description: 'Multi-model ensemble flags anomalous node behavior.',
    items: ['Isolation Forest', 'XGBoost (F1 0.94)', 'GNN trust propagation']
  },
  {
    id: 'digital-twin',
    title: 'Digital Twin Simulation',
    color: 'purple',
    icon: Radar,
    description: 'Round-based simulated network mirrors real conditions.',
    items: ['Energy decay modeling', 'Attack replay']
  },
  {
    id: 'routing-engine',
    title: 'Trust-Aware Routing Engine',
    color: 'orange',
    icon: Route,
    description: 'Selects paths using a multi-objective cost formula.',
    items: ['Distance + energy + attack-risk weighting']
  },
  {
    id: 'feedback-loop',
    title: 'Feedback Loop',
    color: 'yellow',
    icon: RefreshCw,
    description: 'Closes the loop by recalibrating the system over time.',
    items: ['Recalibrates miss-rates', 'Tunes risk weights']
  }
]

const outputs = [
  { id: 'backend', title: 'FastAPI Backend', subtitle: 'Served via Render', icon: Server },
  { id: 'frontend', title: 'React Dashboard', subtitle: 'Served via Netlify', icon: MonitorSmartphone }
]

const colorVarMap = {
  cyan: 'var(--neon-cyan)',
  magenta: 'var(--neon-magenta)',
  purple: 'var(--neon-purple)',
  orange: 'var(--neon-orange)',
  yellow: 'var(--neon-yellow)',
  green: 'var(--neon-green)'
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.15 }
  }
}

const stageVariants = {
  hidden: { opacity: 0, x: -40 },
  show: { opacity: 1, x: 0, transition: { type: 'spring', stiffness: 180, damping: 20 } }
}

const connectorVariants = {
  hidden: { scaleY: 0, opacity: 0 },
  show: { scaleY: 1, opacity: 1, transition: { duration: 0.4, ease: 'easeOut' } }
}

const outputVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 200, damping: 18 } }
}

function StageCard({ stage, index }) {
  const Icon = stage.icon
  const accent = colorVarMap[stage.color]

  return (
    <React.Fragment>
      <motion.div
        className="dash-card"
        variants={stageVariants}
        style={{ borderLeft: `4px solid ${accent}`, display: 'flex', gap: '20px', alignItems: 'flex-start' }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            minWidth: 48,
            borderRadius: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: `color-mix(in srgb, ${accent} 18%, transparent)`,
            boxShadow: `0 0 15px ${accent}`,
            color: accent
          }}
        >
          <Icon size={24} />
        </div>
        <div style={{ flex: 1 }}>
          <div className="flex-between">
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: '0.08em',
                color: 'var(--text-muted)'
              }}
            >
              STAGE {index + 1}
            </span>
          </div>
          <h2 className="dash-card-title" style={{ marginBottom: 6 }}>
            {stage.title}
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '0 0 12px 0' }}>
            {stage.description}
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {stage.items.map((item) => (
              <span
                key={item}
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  padding: '4px 10px',
                  borderRadius: 999,
                  color: '#fff',
                  background: 'rgba(255,255,255,0.04)',
                  border: `1px solid color-mix(in srgb, ${accent} 45%, transparent)`
                }}
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      </motion.div>

      {index < stages.length - 1 && (
        <motion.div
          variants={connectorVariants}
          style={{
            width: 2,
            height: 28,
            margin: '0 0 0 44px',
            transformOrigin: 'top',
            background: `linear-gradient(180deg, ${accent}, ${colorVarMap[stages[index + 1].color]})`
          }}
        />
      )}
    </React.Fragment>
  )
}

export default function ArchitectureDiagram() {
  return (
    <div className="main-content-inner">
      <h1 className="page-title">SYSTEM ARCHITECTURE</h1>
      <p className="page-subtitle">End-to-end pipeline: from raw sensor data to trust-aware routing decisions</p>

      <motion.div
        className="mt-16"
        style={{ display: 'flex', flexDirection: 'column' }}
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        {stages.map((stage, index) => (
          <StageCard key={stage.id} stage={stage} index={index} />
        ))}
      </motion.div>

      <div className="mt-16">
        <h2 className="dash-card-title" style={{ marginBottom: 16 }}>Served Through</h2>
        <motion.div
          style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}
          variants={containerVariants}
          initial="hidden"
          animate="show"
        >
          {outputs.map((output) => {
            const Icon = output.icon
            return (
              <motion.div
                key={output.id}
                className="dash-card kpi-card-green"
                variants={outputVariants}
                style={{ display: 'flex', alignItems: 'center', gap: 16 }}
              >
                <div className="kpi-card-icon kpi-icon-green" style={{ position: 'static' }}>
                  <Icon size={20} />
                </div>
                <div>
                  <p className="dash-card-title" style={{ margin: 0 }}>{output.title}</p>
                  <p className="kpi-desc" style={{ margin: '4px 0 0 0' }}>{output.subtitle}</p>
                </div>
              </motion.div>
            )
          })}
        </motion.div>
      </div>
    </div>
  )
}
