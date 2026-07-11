import React, { useState, useEffect } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import Sidebar from './components/Sidebar'
import Ticker from './components/Ticker'
import NetworkOverview from './pages/NetworkOverview'
import AttackDetection from './pages/AttackDetection'
import RoutingSimulation from './pages/RoutingSimulation'
import EnergyForecast from './pages/EnergyForecast'
import PipelineReport from './pages/PipelineReport'
import DigitalTwin from './pages/DigitalTwin';
import FeedbackLoop from './pages/FeedbackLoop';
import GNNVisualization from './pages/GNNVisualization'
import EvaluationPerformance from './pages/EvaluationPerformance'

const pageTransition = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
  transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] }
}

export default function App() {
  const [data, setData] = useState(null)
  const location = useLocation()

 useEffect(() => {
    fetch('/api/dashboard-formatted')
      .then(res => res.json())
      .then(setData)
      .catch(err => {
        console.error('API failed, falling back to local data:', err)
        fetch('/dashboard_data.json')
          .then(res => res.json())
          .then(setData)
      })
  }, [])
  if (!data) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p className="loading-text">Initializing Security Dashboard...</p>
      </div>
    )
  }

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={pageTransition.initial}
            animate={pageTransition.animate}
            exit={pageTransition.exit}
            transition={pageTransition.transition}
            className="page-container"
          >
            <Routes location={location}>
              <Route path="/" element={<NetworkOverview data={data.networkOverview} />} />
              <Route path="/attack-detection" element={<AttackDetection data={{ ...data.attackDetection, multiclassClassification: data.multiclassClassification, gnnModelReport: data.gnnModelReport, mitigationSummary: data.mitigationSummary }} />} />
              <Route path="/routing-simulation" element={<RoutingSimulation data={data.routingSimulation} />} />
              <Route path="/energy-forecast" element={<EnergyForecast data={data.energyForecast} />} />
              <Route path="/pipeline-report" element={<PipelineReport data={data.pipelineReport} />} />
<Route path="/digital-twin" element={<DigitalTwin />} />
<Route path="/feedback-loop" element={<FeedbackLoop data={data.feedbackLoop} />} />
<Route path="/gnn-visualization" element={<GNNVisualization data={{ gnnGraph: data.gnnGraph, gnnModelReport: data.gnnModelReport }} />} />
<Route path="/evaluation-performance" element={<EvaluationPerformance data={data.evaluationMetrics} />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </main>
      <Ticker text={data.ticker} />
    </div>
  )
}
