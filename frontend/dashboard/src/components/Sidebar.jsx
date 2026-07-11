import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'
import { motion } from 'framer-motion'
import { Shield, Network, ShieldAlert, Route, Zap, FileText, Sun, Radar, RefreshCw, Share2, BarChart3 } from 'lucide-react'
const navItems = [
  { path: '/', label: 'Network Overview', icon: Network },
  { path: '/attack-detection', label: 'Attack Detection', icon: ShieldAlert },
  { path: '/routing-simulation', label: 'Routing Simulation', icon: Route },
  { path: '/energy-forecast', label: 'Energy Forecast', icon: Zap },
  { path: '/pipeline-report', label: 'Pipeline Report', icon: FileText },
  { path: '/digital-twin', label: 'Digital Twin', icon: Radar },
{ path: '/feedback-loop', label: 'Feedback Loop', icon: RefreshCw },
{ path: '/gnn-visualization', label: 'GNN Visualization', icon: Share2 },
{ path: '/evaluation-performance', label: 'Evaluation & Performance', icon: BarChart3 },
]

export default function Sidebar() {
  const location = useLocation()
  const { dark, toggle } = useTheme()

  return (
    <aside className="sidebar">
      {/* Brand section */}
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <Shield size={22} />
        </div>
        <div>
          <div className="sidebar-brand-title">WSN Security</div>
          <div className="sidebar-brand-subtitle">AI Pipeline Dashboard</div>
        </div>
      </div>

      {/* Section label */}
      <p className="sidebar-section-label">Dashboard</p>

      {/* Navigation items */}
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.path
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={isActive ? 'sidebar-nav-item active' : 'sidebar-nav-item'}
            >
              {isActive && (
                <motion.div
                  className="sidebar-nav-pill"
                  layoutId="sidebar-pill"
                  transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                />
              )}
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </nav>

      {/* Bottom section */}
      <div className="sidebar-bottom">
        <div className="sidebar-theme-toggle" onClick={toggle}>
          <Sun size={16} />
          <span>{dark ? 'Light Mode' : 'Dark Mode'}</span>
        </div>
        <div className="sidebar-status-card">
          <div className="sidebar-status-card-title">Pipeline Status</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className="sidebar-status-dot"></div>
            <span className="sidebar-status-text">All Systems Operational</span>
          </div>
        </div>
      </div>
    </aside>
  )
}
