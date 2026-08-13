import React, { useState } from 'react'
import { motion } from 'framer-motion'
import ReactCountUp from 'react-countup'
const CountUp = ReactCountUp.default || ReactCountUp

const borderClasses = {
  cyan: 'kpi-card-cyan',
  red: 'kpi-card-red',
  orange: 'kpi-card-orange',
  green: 'kpi-card-green',
  purple: 'kpi-card-purple',
  amber: 'kpi-card-amber',
  blue: 'kpi-card-blue',
}

const iconClasses = {
  cyan: 'kpi-icon-cyan',
  red: 'kpi-icon-red',
  orange: 'kpi-icon-orange',
  green: 'kpi-icon-green',
  purple: 'kpi-icon-purple',
  amber: 'kpi-icon-amber',
  blue: 'kpi-icon-blue',
}

const valueClasses = {
  cyan: 'kpi-value-cyan',
  red: 'kpi-value-red',
  orange: 'kpi-value-orange',
  green: 'kpi-value-green',
  purple: 'kpi-value-purple',
}

export default function KPICard({ label, value, decimals = 0, prefix = '', suffix = '', color = 'cyan', delay = 0, icon: Icon, description }) {
  const [settled, setSettled] = useState(false)

  return (
    <motion.div
      className={`kpi-card ${borderClasses[color] || 'kpi-card-cyan'}`}
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -3 }}
    >
      {Icon && (
        <div className={`kpi-card-icon ${iconClasses[color] || 'kpi-icon-cyan'}`}>
          <Icon size={18} />
        </div>
      )}
      <p className="kpi-label">{label}</p>
      <p className={`kpi-value ${valueClasses[color] || 'kpi-value-cyan'} ${settled ? 'kpi-breathe' : ''}`}>
        {prefix}
        <CountUp
          end={value}
          decimals={decimals}
          duration={2}
          separator=","
          delay={delay}
          onEnd={() => setSettled(true)}
        />
        {suffix}
      </p>
      {description && <p className="kpi-desc">{description}</p>}
    </motion.div>
  )
}
