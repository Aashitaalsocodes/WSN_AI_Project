import { NavLink } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  ShieldAlert,
  Route,
  Battery,
  FileText,
  Sun,
  Moon,
  Menu,
  X,
  Shield,
} from 'lucide-react';
import { useState } from 'react';

const navItems = [
  { to: '/', label: 'Network Overview', icon: LayoutDashboard },
  { to: '/attack-detection', label: 'Attack Detection', icon: ShieldAlert },
  { to: '/routing', label: 'Routing Simulation', icon: Route },
  { to: '/energy', label: 'Energy Forecast', icon: Battery },
  { to: '/report', label: 'Pipeline Report', icon: FileText },
];

export default function Sidebar() {
  const { dark, toggle } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile top bar */}
      <div className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between border-b border-surface-200 bg-white/80 px-4 py-3 backdrop-blur-xl lg:hidden dark:border-surface-700 dark:bg-[#0a0a0f]/90">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-gradient-to-br from-brand-blue to-brand-purple p-1.5">
            <Shield size={18} className="text-white" />
          </div>
          <span className="text-sm font-bold text-surface-900 dark:text-white">WSN Security</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={toggle}
            className="rounded-lg p-2 text-surface-500 transition-colors hover:bg-surface-100 dark:hover:bg-surface-800"
          >
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="rounded-lg p-2 text-surface-500 transition-colors hover:bg-surface-100 dark:hover:bg-surface-800"
          >
            {mobileOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 z-40 h-screen w-64 border-r border-surface-200/50 bg-white/80 backdrop-blur-xl transition-transform duration-300 lg:translate-x-0 dark:border-surface-700/50 dark:bg-[#0a0a0f] dark:border-l-2 dark:border-l-cyan-400/50 dark:shadow-[inset_4px_0_20px_rgba(0,255,247,0.15)] ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-surface-200/50 px-5 dark:border-surface-700/50">
          <div className="rounded-xl bg-gradient-to-br from-brand-blue to-brand-purple p-2 shadow-lg">
            <Shield size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-surface-900 dark:text-white">WSN Security</h1>
            <p className="text-[10px] font-medium text-surface-400">AI Pipeline Dashboard</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="mt-4 space-y-1 px-3">
          <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-surface-400">
            Dashboard
          </p>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'nav-active bg-brand-blue/10 text-brand-blue dark:bg-brand-blue/15 dark:text-blue-400'
                    : 'text-surface-600 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-800 dark:hover:text-white'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <motion.div
                    whileHover={{ scale: 1.25, rotate: [0, -10, 10, 0] }}
                    whileTap={{ scale: 0.9 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 10 }}
                  >
                    <item.icon size={18} />
                  </motion.div>
                  <span>{item.label}</span>
                  {isActive && (
                    <motion.div
                      layoutId="nav-indicator"
                      className="absolute left-0 top-1/2 -translate-y-1/2 h-[60%] w-[3px] rounded-r bg-gradient-to-b from-brand-blue to-brand-purple"
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Bottom section */}
        <div className="absolute bottom-0 left-0 right-0 border-t border-surface-200/50 p-4 dark:border-surface-700/50">
          <button
            onClick={toggle}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-surface-600 transition-all duration-200 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800"
          >
            {dark ? <Sun size={18} /> : <Moon size={18} />}
            {dark ? 'Light Mode' : 'Dark Mode'}
          </button>
          <div className="mt-3 rounded-xl bg-gradient-to-r from-brand-blue/10 to-brand-purple/10 p-3">
            <p className="text-[10px] font-semibold text-surface-500 dark:text-surface-400">Pipeline Status</p>
            <div className="mt-1 flex items-center gap-2">
              <span className="pulse-dot h-2 w-2 rounded-full bg-brand-green"></span>
              <span className="text-xs font-medium text-brand-green">All Systems Operational</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
