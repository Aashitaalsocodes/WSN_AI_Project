import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactCountUp from 'react-countup'
const CountUp = ReactCountUp.default || ReactCountUp
import { GitBranch, Sliders, Battery, Scan, Activity, RefreshCw } from 'lucide-react'
import KPICard from '../components/KPICard'

const iconMap = {
  route: GitBranch,
  sliders: Sliders,
  battery: Battery,
  scan: Scan,
  activity: Activity,
  refresh: RefreshCw,
}

export default function PipelineReport({ data }) {
  const {
    flaggedNodes,
    avgTrustScore,
    trustThreshold,
    llmModel,
    healthReport,
    attackAlert,
    adaptivePolicies,
    simulationSteps
  } = data

  const [simulating, setSimulating] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [progress, setProgress] = useState(0)

  // Simulation display data state (refreshed after simulation completes)
  const [displayData, setDisplayData] = useState({
    flaggedNodes,
    avgTrustScore
  })

  const triggerSimulation = () => {
    if (simulating) return
    setSimulating(true)
    setProgress(0)
    setCurrentStep(0)

    const totalSteps = simulationSteps.length
    const durationPerStep = 375 // 3000ms / 8 steps

    let step = 0
    const interval = setInterval(() => {
      step++
      if (step < totalSteps) {
        setCurrentStep(step)
        setProgress((step / (totalSteps - 1)) * 100)
      } else {
        clearInterval(interval)
        setProgress(100)
        setTimeout(() => {
          setSimulating(false)
          setProgress(0)
          setCurrentStep(0)
          
          // Randomize values slightly (+/- 5%) and trigger animated countup
          setDisplayData({
            flaggedNodes: flaggedNodes + Math.floor((Math.random() - 0.5) * 2000),
            avgTrustScore: parseFloat((avgTrustScore + (Math.random() - 0.5) * 0.05).toFixed(4))
          })
        }, 800)
      }
    }, durationPerStep)
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.08 }
    }
  }

  const cardVariants = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 200, damping: 18 } }
  }

  return (
    <div className="main-content-inner" style={{ '--accent-color': '#7c3aed', '--accent-rgb': '124,58,237' }}>
      <h1 className="page-title">PIPELINE REPORT</h1>
      <p className="page-subtitle">Security health reports, adaptive policies, and pipeline simulation</p>

      {/* KPI Cards Row */}
      <div className="kpi-grid">
        <KPICard label="Flagged Nodes" value={displayData.flaggedNodes} color="red" delay={0} />
        <KPICard label="Avg Trust Score" value={displayData.avgTrustScore} decimals={4} color="green" delay={0.1} />
        <KPICard label="Trust Threshold" value={trustThreshold} decimals={2} color="red" delay={0.2} />
        <div className="kpi-card kpi-card-purple">
          <p className="kpi-label">LLM Model</p>
          <p className="kpi-value kpi-value-purple">
            {llmModel}
          </p>
        </div>
      </div>

      {/* Health Report and Alert Row */}
      <div className="two-col-grid">
        {/* Health Report Card */}
        <div className="card" style={{ borderLeft: '4px solid #ff3860' }}>
          <h2 className="dash-card-title">NETWORK HEALTH ANALYSIS</h2>
          <p className="health-report-text">
            {healthReport}
          </p>
        </div>

        {/* Attack Alert Card */}
        <div 
          className="card alert-card-pulse" 
          style={{ 
            border: '1px solid rgba(255, 56, 96, 0.45)', 
            borderLeft: '4px solid #ff3860'
          }}
        >
          <div className="alert-badge">
            ALERT
          </div>
          <h3 style={{ color: '#ffffff', fontSize: '15px', fontWeight: 'bold', margin: '0 0 16px 0' }}>
            {attackAlert.title}
          </h3>
          <div className="alert-actions">
            {attackAlert.actions.map((action, i) => (
              <div key={i} className="alert-action">
                <span className="alert-action-icon">▶</span>
                {action}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Adaptive Policies Title */}
      <h2 className="dash-card-title mt-24 mb-16">ADAPTIVE SECURITY POLICIES</h2>
      
      {/* 6 Adaptive Policy Cards Grid */}
      <motion.div 
        className="policy-grid"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        {adaptivePolicies.map((policy, idx) => {
          const IconComponent = iconMap[policy.icon] || Sliders
          return (
            <motion.div
              key={idx}
              className="policy-card"
              variants={cardVariants}
            >
              <div className="flex-center mb-16" style={{ gap: '12px' }}>
                <div className="policy-card-number">
                  <IconComponent size={18} />
                </div>
                <h3 className="policy-card-title">{policy.title}</h3>
              </div>
              <p className="policy-card-desc">{policy.description}</p>
            </motion.div>
          )
        })}
      </motion.div>

      {/* Simulation Controls Card */}
      <div className="dash-card mt-24" style={{ padding: '36px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <motion.button
          onClick={triggerSimulation}
          disabled={simulating}
          className="simulate-btn"
          whileTap={{ scale: 0.95 }}
        >
          {simulating ? 'Simulating Pipeline...' : '▶ Simulate Pipeline'}
        </motion.button>

        <AnimatePresence>
          {simulating && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              style={{ width: '100%', maxWidth: '400px', marginTop: '24px', textAlign: 'center' }}
            >
              <div className="simulate-progress-bar">
                <div className="simulate-progress-fill" style={{ width: `${progress}%` }} />
              </div>
              <p className="simulate-status">
                {simulationSteps[currentStep]}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
