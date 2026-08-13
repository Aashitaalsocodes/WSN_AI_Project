export function KpiCard({ title, value, subtitle, icon: Icon, color = 'blue', delay = 0 }) {
  const colorMap = {
    blue: 'from-primary-500/15 to-primary-600/5 border-primary-500/20 text-primary-600 dark:text-primary-400',
    red: 'from-danger-500/15 to-danger-600/5 border-danger-500/20 text-danger-600 dark:text-danger-400',
    green: 'from-success-500/15 to-success-600/5 border-success-500/20 text-success-600 dark:text-success-400',
    amber: 'from-warning-500/15 to-warning-600/5 border-warning-500/20 text-warning-600 dark:text-warning-400',
    purple: 'from-violet-500/15 to-violet-600/5 border-violet-500/20 text-violet-600 dark:text-violet-400',
  };

  const iconBg = {
    blue: 'bg-primary-500/10 text-primary-500',
    red: 'bg-danger-500/10 text-danger-500',
    green: 'bg-success-500/10 text-success-500',
    amber: 'bg-warning-500/10 text-warning-500',
    purple: 'bg-violet-500/10 text-violet-500',
  };

  return (
    <div
      className={`animate-fade-in-up animate-delay-${delay} rounded-2xl border bg-gradient-to-br ${colorMap[color]} p-5 transition-all duration-300 hover:scale-[1.02] hover:shadow-lg`}
      style={{ animationDelay: `${delay * 100}ms` }}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-surface-500 dark:text-surface-400">
            {title}
          </p>
          <p className="count-up text-2xl font-bold text-surface-900 dark:text-white">{value}</p>
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
    </div>
  );
}

export function SectionHeader({ title, subtitle, icon: Icon }) {
  return (
    <div className="mb-6 flex items-center gap-3">
      {Icon && (
        <div className="rounded-xl bg-primary-500/10 p-2.5 text-primary-500">
          <Icon size={22} />
        </div>
      )}
      <div>
        <h2 className="text-xl font-bold text-surface-900 dark:text-white">{title}</h2>
        {subtitle && (
          <p className="text-sm text-surface-500 dark:text-surface-400">{subtitle}</p>
        )}
      </div>
    </div>
  );
}

export function ChartCard({ title, subtitle, children, className = '' }) {
  return (
    <div
      className={`rounded-2xl border border-surface-200/50 bg-white/70 p-6 shadow-sm backdrop-blur-sm transition-all duration-300 hover:shadow-md dark:border-surface-700/50 dark:bg-surface-800/70 ${className}`}
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
    </div>
  );
}

export function Badge({ children, color = 'blue' }) {
  const colors = {
    blue: 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400',
    red: 'bg-danger-100 text-danger-700 dark:bg-danger-900/30 dark:text-danger-400',
    green: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400',
    amber: 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400',
    purple: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${colors[color]}`}>
      {children}
    </span>
  );
}
