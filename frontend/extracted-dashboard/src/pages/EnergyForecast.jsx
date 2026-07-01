import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import ReactCountUp from 'react-countup';
const CountUp = ReactCountUp.default || ReactCountUp;
import {
  Brain,
  Target,
  Zap,
  Cpu,
  Crown,
  ChevronRight,
  Database,
  AlertTriangle,
  Search,
} from 'lucide-react';
import { energyData, COLORS } from '../data/pipelineData';
import { KpiCard, SectionHeader, ChartCard, GlassCard, Badge } from '../components/shared';
import { useTheme } from '../context/ThemeContext';

/* ─── animation variants ─── */
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -30 },
  visible: { opacity: 1, x: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } },
};

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.5, ease: 'easeOut' },
  }),
};

/* ─── derived constants ─── */
const voltages = energyData.voltageForecasts.map((d) => d.voltage);
const minVoltage = Math.min(...voltages);
const maxVoltage = Math.max(...voltages);
const avgVoltage =
  energyData.voltageForecasts.reduce((s, d) => s + d.voltage, 0) /
  energyData.voltageForecasts.length;

/* ─── custom tooltip ─── */
function VoltageTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { node, voltage } = payload[0].payload;
  const isOutlier = energyData.outlierNodes.includes(node);
  return (
    <div className="rounded-lg border border-surface-200 bg-white px-4 py-3 shadow-lg dark:border-surface-700 dark:bg-surface-800">
      <p className="text-sm font-semibold text-surface-900 dark:text-white">
        Node {node}: {voltage}V
      </p>
      {isOutlier && (
        <p className="mt-1 flex items-center gap-1 text-xs font-medium text-warning-600 dark:text-warning-400">
          <AlertTriangle size={12} />
          Above normal range
        </p>
      )}
    </div>
  );
}

/* ─── custom dot renderer ─── */
function CustomDot(props) {
  const { cx, cy, payload, thresholdV, belowThresholdNodes } = props;
  const isOutlier = energyData.outlierNodes.includes(payload.node);
  const isBelowThreshold = belowThresholdNodes?.has(payload.node);

  let fill = COLORS.blue;
  let r = 4;
  let stroke = '#fff';

  if (isBelowThreshold) {
    fill = COLORS.red;
    r = 6;
    stroke = COLORS.red;
  } else if (isOutlier) {
    fill = COLORS.amber;
    r = 6;
    stroke = COLORS.amber;
  }

  return (
    <circle
      cx={cx}
      cy={cy}
      r={r}
      fill={fill}
      stroke={stroke}
      strokeWidth={2}
      opacity={0.9}
    />
  );
}

/* ─── main page ─── */
export default function EnergyForecast() {
  const { dark } = useTheme();
  const [threshold, setThreshold] = useState(1.95);

  /* compute nodes below threshold */
  const belowThreshold = useMemo(() => {
    return energyData.voltageForecasts.filter((d) => d.voltage < threshold);
  }, [threshold]);

  const belowThresholdNodes = useMemo(() => {
    return new Set(belowThreshold.map((d) => d.node));
  }, [belowThreshold]);

  const rankColors = {
    1: { bg: '#f59e0b', text: '#fff' },
    2: { bg: '#94a3b8', text: '#fff' },
    3: { bg: '#d97706', text: '#fff' },
    4: { bg: COLORS.blue, text: '#fff' },
    5: { bg: COLORS.blue, text: '#fff' },
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      {/* ── Page header ── */}
      <SectionHeader
        title="Energy Forecast & Cluster‑Head Selection"
        subtitle="LSTM voltage prediction across 57 IBRL sensor nodes"
        icon={Zap}
      />

      {/* ── KPI row — 6 cards ── */}
      <motion.div
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={itemVariants}>
          <KpiCard
            title="Model"
            value="LSTM"
            subtitle="Recurrent Neural Network"
            icon={Brain}
            color="blue"
          />
        </motion.div>
        <motion.div variants={itemVariants}>
          <KpiCard
            title="Validation MSE"
            value="3.94×10⁻⁶"
            subtitle="Mean Squared Error"
            icon={Target}
            color="green"
          />
        </motion.div>
        <motion.div variants={itemVariants}>
          <KpiCard
            title="Avg Forecast"
            value={
              <span>
                <CountUp end={0.22} decimals={3} duration={2} /> mJ
              </span>
            }
            subtitle="Per‑node energy"
            icon={Zap}
            color="amber"
          />
        </motion.div>
        <motion.div variants={itemVariants}>
          <KpiCard
            title="Data Source"
            value="Intel IBRL"
            subtitle="Real sensor data"
            icon={Database}
            color="purple"
          />
        </motion.div>
        <motion.div variants={itemVariants}>
          <KpiCard
            title="Nodes Forecast"
            value={<CountUp end={57} duration={2} />}
            subtitle="Sensor nodes"
            icon={Cpu}
            color="blue"
          />
        </motion.div>
        <motion.div variants={itemVariants}>
          <KpiCard
            title="Voltage Range"
            value={`${minVoltage.toFixed(3)}V`}
            subtitle={`Min ${minVoltage.toFixed(3)}V | Max ${maxVoltage.toFixed(3)}V`}
            icon={Zap}
            color="green"
          />
        </motion.div>
      </motion.div>

      {/* ── Voltage forecast chart ── */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.6 }}
      >
        <ChartCard
          title="Voltage Forecast Across Nodes"
          subtitle="LSTM predicted voltage (V) per node — outlier nodes highlighted in amber, flagged nodes in red"
        >
          <div className="mb-3 flex flex-wrap items-center gap-4 text-xs text-surface-500 dark:text-surface-400">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS.blue }} />
              Normal
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS.amber }} />
              Outlier (above normal)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS.red }} />
              Below threshold
            </span>
          </div>

          <ResponsiveContainer width="100%" height={380}>
            <AreaChart
              data={energyData.voltageForecasts}
              margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="voltGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={COLORS.blue} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={COLORS.blue} stopOpacity={0.0} />
                </linearGradient>
                <filter id="neonGlowBlue" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              <CartesianGrid
                strokeDasharray="3 3"
                stroke={dark ? '#3f3f46' : '#e4e4e7'}
              />

              <XAxis
                dataKey="node"
                tick={{ fill: dark ? '#ffffff' : '#71717a', fontSize: 11 }}
                axisLine={{ stroke: dark ? '#ffffff' : '#e4e4e7', strokeOpacity: dark ? 0.3 : 1 }}
                tickLine={false}
                label={{
                  value: 'Node ID',
                  position: 'insideBottomRight',
                  offset: -5,
                  fill: dark ? '#ffffff' : '#71717a',
                  fontSize: 12,
                }}
              />

              <YAxis
                tick={{ fill: dark ? '#ffffff' : '#71717a', fontSize: 11 }}
                axisLine={{ stroke: dark ? '#ffffff' : '#e4e4e7', strokeOpacity: dark ? 0.3 : 1 }}
                tickLine={false}
                domain={[1.85, 2.95]}
                label={{
                  value: 'Voltage (V)',
                  angle: -90,
                  position: 'insideLeft',
                  fill: dark ? '#ffffff' : '#71717a',
                  fontSize: 12,
                }}
              />

              <Tooltip content={<VoltageTooltip />} />

              {/* threshold reference line */}
              <ReferenceLine
                y={threshold}
                stroke={COLORS.red}
                strokeDasharray="6 3"
                strokeWidth={1.5}
                label={{
                  value: `Threshold ${threshold}V`,
                  position: 'right',
                  fill: COLORS.red,
                  fontSize: 11,
                }}
              />

              {/* average reference line */}
              <ReferenceLine
                y={avgVoltage}
                stroke={dark ? '#a1a1aa' : '#71717a'}
                strokeDasharray="4 4"
                label={{
                  value: `Avg ${avgVoltage.toFixed(3)}V`,
                  position: 'left',
                  fill: dark ? '#a1a1aa' : '#71717a',
                  fontSize: 11,
                }}
              />

              <Area
                type="monotone"
                dataKey="voltage"
                stroke={COLORS.blue}
                strokeWidth={dark ? 3 : 2}
                fill="url(#voltGrad)"
                style={dark ? { filter: 'url(#neonGlowBlue)' } : {}}
                dot={(dotProps) => (
                  <CustomDot
                    key={dotProps.payload.node}
                    {...dotProps}
                    thresholdV={threshold}
                    belowThresholdNodes={belowThresholdNodes}
                  />
                )}
                activeDot={{ r: 7, strokeWidth: 2, stroke: '#fff', style: dark ? { filter: 'url(#neonGlowBlue)' } : {} }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </motion.div>

      {/* ── Energy Threshold Input ── */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.6 }}
      >
        <ChartCard
          title="Energy Threshold Analysis"
          subtitle="Flag nodes below a custom voltage threshold"
        >
          <div className="flex flex-col gap-5 sm:flex-row sm:items-end">
            <div className="flex-1">
              <label
                htmlFor="voltageThreshold"
                className="mb-2 flex items-center gap-2 text-sm font-medium text-surface-700 dark:text-surface-300"
              >
                <Search size={14} />
                Flag nodes below voltage threshold (V)
              </label>
              <input
                id="voltageThreshold"
                type="number"
                step="0.01"
                min="1.80"
                max="3.00"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value) || 1.95)}
                className="w-full rounded-xl border border-surface-300 bg-white px-4 py-2.5 text-sm font-mono text-surface-900 shadow-sm transition-all focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-surface-600 dark:bg-surface-800 dark:text-white sm:w-48"
              />
            </div>

            <div className="flex items-center gap-3">
              <span className="rounded-xl bg-danger-500/10 px-4 py-2.5 text-sm font-bold text-danger-600 dark:text-danger-400">
                <CountUp key={belowThreshold.length} end={belowThreshold.length} duration={0.8} /> nodes flagged
              </span>
            </div>
          </div>

          {/* below-threshold results */}
          <AnimatePresence mode="wait">
            {belowThreshold.length > 0 && (
              <motion.div
                key={`results-${threshold}`}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="mt-5 overflow-hidden"
              >
                <div className="rounded-xl border border-danger-200/50 bg-danger-50/50 p-4 dark:border-danger-800/30 dark:bg-danger-900/10">
                  <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-danger-700 dark:text-danger-400">
                    <AlertTriangle size={14} />
                    Nodes below {threshold}V threshold
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {belowThreshold.map((d, i) => (
                      <motion.span
                        key={d.node}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: i * 0.04 }}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-danger-100 px-3 py-1.5 text-xs font-semibold text-danger-700 dark:bg-danger-900/30 dark:text-danger-400"
                      >
                        <span className="font-mono">Node {d.node}</span>
                        <span className="text-danger-500">({d.voltage}V)</span>
                      </motion.span>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </ChartCard>
      </motion.div>

      {/* ── Top 5 Cluster‑Head Candidates ── */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.6 }}
      >
        <ChartCard
          title="Top 5 Cluster‑Head Candidates"
          subtitle={`XGBoost classifier — F1 = ${energyData.clusterHeads.f1} · AUC = ${energyData.clusterHeads.auc}`}
        >
          <div className="mb-4 flex items-center gap-2">
            <Crown size={16} className="text-warning-500" />
            <span className="text-xs font-medium text-surface-500 dark:text-surface-400">
              Ranked by cluster‑head election probability
            </span>
          </div>

          <motion.ul
            className="divide-y divide-surface-100 dark:divide-surface-700/50"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {energyData.clusterHeads.top5.map((item) => {
              const rc = rankColors[item.rank];
              const isSelected = item.rank === 1;
              return (
                <motion.li
                  key={item.rank}
                  variants={itemVariants}
                  className="flex items-center gap-4 rounded-lg px-3 py-3.5 transition-colors duration-200 hover:bg-surface-50 dark:hover:bg-surface-700/30"
                >
                  {/* rank badge */}
                  <motion.span
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold shadow-sm"
                    style={{ background: rc.bg, color: rc.text }}
                    whileHover={{ scale: 1.15 }}
                  >
                    #{item.rank}
                  </motion.span>

                  {/* node id */}
                  <span className="flex-1 font-mono text-sm font-semibold text-surface-900 dark:text-white">
                    {item.id}
                  </span>

                  {/* status tag */}
                  {isSelected ? (
                    <Badge color="green">Selected</Badge>
                  ) : (
                    <Badge color="blue">Candidate</Badge>
                  )}

                  {/* trailing icon */}
                  <ChevronRight
                    size={16}
                    className="text-surface-400 dark:text-surface-500"
                  />
                </motion.li>
              );
            })}
          </motion.ul>
        </ChartCard>
      </motion.div>

      {/* ── Footer credit ── */}
      <motion.div
        className="flex items-center justify-center gap-2 pb-4 text-xs text-surface-400 dark:text-surface-500"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
      >
        <Database size={12} />
        <span>Data source: Intel Berkeley Research Lab (IBRL)</span>
      </motion.div>
    </div>
  );
}
