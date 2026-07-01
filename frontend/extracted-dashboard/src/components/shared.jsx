import { motion } from 'framer-motion';
import ReactCountUp from 'react-countup';
const CountUp = ReactCountUp.default || ReactCountUp;

const cardVariants = {
  hidden: { opacity: 0, y: 30, scale: 0.95 },
  visible: (i) => ({
    opacity: 1, y: 0, scale: 1,
    transition: { delay: i * 0.1, duration: 0.5, ease: 'easeOut' },
  }),
};

export function KpiCard({ title, value, subtitle, icon: Icon, color = 'blue', delay = 0, countUp, countUpDecimals = 0, countUpSuffix = '', countUpPrefix = '' }) {
  const colorMap = {
    blue: 'border-brand-blue/20 text-brand-blue',
    red: 'border-brand-red/20 text-brand-red',
    green: 'border-brand-green/20 text-brand-green',
    amber: 'border-brand-amber/20 text-brand-amber',
    purple: 'border-brand-purple/20 text-brand-purple',
  };

  const neonTextMap = {
    blue: 'dark:neon-text-cyan',
    red: 'dark:neon-text-pink',
    green: 'dark:neon-text-green',
    amber: 'dark:neon-text-orange',
    purple: 'dark:neon-text-purple',
  };

  const bgMap = {
    blue: 'from-brand-blue/10 to-brand-blue/5',
    red: 'from-brand-red/10 to-brand-red/5',
    green: 'from-brand-green/10 to-brand-green/5',
    amber: 'from-brand-amber/10 to-brand-amber/5',
    purple: 'from-brand-purple/10 to-brand-purple/5',
  };

  const iconBg = {
    blue: 'bg-brand-blue/10 text-brand-blue',
    red: 'bg-brand-red/10 text-brand-red',
    green: 'bg-brand-green/10 text-brand-green',
    amber: 'bg-brand-amber/10 text-brand-amber',
    purple: 'bg-brand-purple/10 text-brand-purple',
  };

  return (
    <motion.div
      custom={delay}
      variants={cardVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true }}
      whileHover={{ scale: 1.03, transition: { duration: 0.2 } }}
      className={`glass rounded-2xl border bg-gradient-to-br ${bgMap[color]} ${colorMap[color]} p-5 transition-shadow duration-300 hover:shadow-lg cursor-default`}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-surface-500 dark:text-surface-400">
            {title}
          </p>
          <p className={`text-2xl font-bold text-surface-900 ${neonTextMap[color] || 'dark:text-white'}`}>
            {countUp !== undefined ? (
              <CountUp end={countUp} decimals={countUpDecimals} duration={2} separator="," suffix={countUpSuffix} prefix={countUpPrefix} />
            ) : value}
          </p>
          {subtitle && (
            <p className="text-xs text-surface-500 dark:text-surface-400">{subtitle}</p>
          )}
        </div>
        {Icon && (
          <div className={`rounded-xl p-2.5 ${iconBg[color]}`}>
            <Icon size={20} />
          </div>
        )}
      </div>
    </motion.div>
  );
}

export function SectionHeader({ title, subtitle, icon: Icon }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5 }}
      className="mb-6 flex items-center gap-3"
    >
      {Icon && (
        <div className="rounded-xl bg-brand-blue/10 p-2.5 text-brand-blue">
          <Icon size={22} />
        </div>
      )}
      <div>
        <h2 className="gradient-text text-xl font-bold">{title}</h2>
        {subtitle && (
          <p className="text-sm text-surface-500 dark:text-surface-400">{subtitle}</p>
        )}
      </div>
    </motion.div>
  );
}

export function ChartCard({ title, subtitle, children, className = '' }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      className={`glass rounded-2xl p-6 transition-all duration-300 hover:shadow-lg ${className}`}
    >
      {(title || subtitle) && (
        <div className="mb-4">
          {title && (
            <h3 className="text-sm font-semibold text-surface-900 dark:text-white">{title}</h3>
          )}
          {subtitle && (
            <p className="mt-0.5 text-xs text-surface-500 dark:text-surface-400">{subtitle}</p>
          )}
        </div>
      )}
      {children}
    </motion.div>
  );
}

export function Badge({ children, color = 'blue' }) {
  const colors = {
    blue: 'bg-brand-blue/15 text-brand-blue',
    red: 'bg-brand-red/15 text-brand-red',
    green: 'bg-brand-green/15 text-brand-green',
    amber: 'bg-brand-amber/15 text-brand-amber',
    purple: 'bg-brand-purple/15 text-brand-purple',
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${colors[color]}`}>
      {children}
    </span>
  );
}

export function GlassCard({ children, className = '', delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: delay * 0.1, duration: 0.5 }}
      className={`glass rounded-2xl p-6 transition-all duration-300 hover:shadow-lg ${className}`}
    >
      {children}
    </motion.div>
  );
}
