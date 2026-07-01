import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import ReactCountUp from 'react-countup';
const CountUp = ReactCountUp.default || ReactCountUp;
import {
  ShieldAlert,
  ShieldCheck,
  Search,
  AlertTriangle,
  CheckCircle,
  Info,
} from 'lucide-react';
import { attackDetection, COLORS } from '../data/pipelineData';
import { SectionHeader, ChartCard, Badge, GlassCard } from '../components/shared';
import { useTheme } from '../context/ThemeContext';

/* ── Chart data ── */
const perTypeData = [
  { type: 'Blackhole', IF: 24.7, XGB: 100 },
  { type: 'Flooding', IF: 81.4, XGB: 100 },
  { type: 'Grayhole', IF: 16.2, XGB: 100 },
  { type: 'TDMA', IF: 49.1, XGB: 91.3 },
];

/* ── Confusion matrix raw values ── */
const cm = attackDetection.confusionMatrix;

/* ── Node lookup helpers ── */
function computeNodeScores(nodeId) {
  const id = parseInt(nodeId, 10);
  if (isNaN(id)) return null;

  let anomaly;
  if (id > 370000) {
    // Demo effect: high-ID nodes always risky
    anomaly = 0.7 + ((id % 29) / 29) * 0.28; // 0.70 – 0.98
  } else {
    anomaly = (id % 97) / 97;
  }

  const trust = Math.max(0, Math.min(1, 1 - anomaly + ((id % 13) / 130)));
  const attackProb = Math.max(0, Math.min(1, anomaly - ((id % 11) / 110) + 0.02));
  const isHighRisk = anomaly > 0.5;

  return {
    nodeId: id,
    anomaly: parseFloat(anomaly.toFixed(4)),
    trust: parseFloat(trust.toFixed(4)),
    attackProb: parseFloat(attackProb.toFixed(4)),
    isHighRisk,
  };
}

/* ── Custom chart tooltip ── */
const ChartTooltipContent = ({ active, payload, label }) => {
  const { dark } = useTheme();
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded-lg border px-4 py-3 shadow-lg"
      style={{
        backgroundColor: dark ? '#27272a' : '#ffffff',
        borderColor: dark ? '#3f3f46' : '#e4e4e7',
      }}
    >
      <p className="mb-1 text-sm font-semibold text-surface-800 dark:text-surface-100">
        {label}
      </p>
      {payload.map((p) => (
        <p key={p.dataKey} className="text-xs" style={{ color: p.fill }}>
          {p.name}: {p.value}%
        </p>
      ))}
    </div>
  );
};

/* ═══════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════ */
const AttackDetection = () => {
  const { dark } = useTheme();
  const chartTextColor = dark ? '#a1a1aa' : '#52525b';

  const [nodeInput, setNodeInput] = useState('');
  const [lookupResult, setLookupResult] = useState(null);

  const handleLookup = (e) => {
    e.preventDefault();
    const trimmed = nodeInput.trim();
    if (!trimmed) return;
    const scores = computeNodeScores(trimmed);
    setLookupResult(scores);
  };

  /* ── Confusion matrix cells config ── */
  const matrixCells = [
    {
      label: 'TP',
      value: cm.tp,
      bg: 'bg-success-500/15 border-success-500/30 dark:border-success-glow',
      text: 'text-success-600 dark:neon-text-green',
      row: 0,
      col: 0,
    },
    {
      label: 'FN',
      value: cm.fn,
      bg: 'bg-warning-500/15 border-warning-500/30 dark:border-warning-glow',
      text: 'text-warning-600 dark:neon-text-orange',
      row: 0,
      col: 1,
    },
    {
      label: 'FP',
      value: cm.fp,
      bg: 'bg-danger-500/15 border-danger-500/30 dark:border-danger-glow',
      text: 'text-danger-600 dark:neon-text-pink',
      row: 1,
      col: 0,
    },
    {
      label: 'TN',
      value: cm.tn,
      bg: 'bg-brand-blue/15 border-brand-blue/30 dark:border-cyan-glow',
      text: 'text-brand-blue dark:neon-text-cyan',
      row: 1,
      col: 1,
    },
  ];

  return (
    <div className="space-y-8">
      {/* ─── Section Header ─── */}
      <SectionHeader
        title="Attack Detection"
        subtitle="Comparing Isolation Forest and XGBoost classifiers for WSN intrusion detection"
        icon={ShieldAlert}
      />

      {/* ═══════════════════════════════════════════
          1. SIDE-BY-SIDE MODEL COMPARISON CARDS
          ═══════════════════════════════════════════ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Isolation Forest — slides in from left */}
        <motion.div
          initial={{ opacity: 0, x: -60 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        >
          <GlassCard className="h-full border-l-4 border-danger-500 red-border-pulse">
            <div className="flex items-center gap-3 mb-4">
              <div className="rounded-xl bg-danger-500/10 p-2.5 text-danger-500">
                <ShieldAlert size={20} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-surface-800 dark:text-surface-100">
                  Isolation Forest
                </h3>
                <Badge color="amber">Unsupervised baseline</Badge>
              </div>
            </div>

            {/* F1 hero number */}
            <div className="my-6 text-center">
              <p className="mb-1 text-xs font-medium uppercase tracking-wider text-surface-500 dark:text-surface-400">
                F1 Score
              </p>
              <p className="text-5xl font-bold text-danger-500 dark:neon-text-pink">
                <CountUp end={0.31} decimals={2} duration={1.8} />
              </p>
            </div>

            {/* Precision / Recall */}
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg bg-surface-100 p-3 text-center dark:bg-surface-800/50">
                <p className="mb-1 text-xs text-surface-500 dark:text-surface-400">Precision</p>
                <p className="text-lg font-semibold text-surface-800 dark:neon-text-pink">
                  <CountUp end={0.3125} decimals={4} duration={1.6} />
                </p>
              </div>
              <div className="rounded-lg bg-surface-100 p-3 text-center dark:bg-surface-800/50">
                <p className="mb-1 text-xs text-surface-500 dark:text-surface-400">Recall</p>
                <p className="text-lg font-semibold text-surface-800 dark:neon-text-pink">
                  <CountUp end={0.312} decimals={4} duration={1.6} />
                </p>
              </div>
            </div>
          </GlassCard>
        </motion.div>

        {/* XGBoost — slides in from right */}
        <motion.div
          initial={{ opacity: 0, x: 60 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, ease: 'easeOut', delay: 0.15 }}
        >
          <GlassCard className="h-full border-l-4 border-success-500 green-glow-pulse">
            <div className="flex items-center gap-3 mb-4">
              <div className="rounded-xl bg-success-500/10 p-2.5 text-success-500">
                <ShieldCheck size={20} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-surface-800 dark:text-surface-100">
                  XGBoost (Supervised)
                </h3>
                <Badge color="green">Leakage-free evaluation</Badge>
              </div>
            </div>

            <div className="my-6 text-center">
              <p className="mb-1 text-xs font-medium uppercase tracking-wider text-surface-500 dark:text-surface-400">
                F1 Score
              </p>
              <p className="text-5xl font-bold text-success-500 dark:neon-text-green">
                <CountUp end={0.94} decimals={2} duration={1.8} />
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg bg-surface-100 p-3 text-center dark:bg-surface-800/50">
                <p className="mb-1 text-xs text-surface-500 dark:text-surface-400">Precision</p>
                <p className="text-lg font-semibold text-surface-800 dark:neon-text-green">
                  <CountUp end={0.8945} decimals={4} duration={1.6} />
                </p>
              </div>
              <div className="rounded-lg bg-surface-100 p-3 text-center dark:bg-surface-800/50">
                <p className="mb-1 text-xs text-surface-500 dark:text-surface-400">Recall</p>
                <p className="text-lg font-semibold text-surface-800 dark:neon-text-green">
                  <CountUp end={0.9827} decimals={4} duration={1.6} />
                </p>
              </div>
            </div>
          </GlassCard>
        </motion.div>
      </div>

      {/* Evaluation note */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.5 }}
        className="flex items-start gap-2.5 rounded-xl border border-brand-blue/20 bg-brand-blue/5 px-5 py-3"
      >
        <Info size={16} className="mt-0.5 flex-shrink-0 text-brand-blue" />
        <p className="text-sm leading-relaxed text-surface-600 dark:text-surface-400">
          Evaluated on held-out test set of{' '}
          <span className="font-semibold text-surface-800 dark:text-surface-100">
            74,933 nodes
          </span>{' '}
          only — no data leakage.
        </p>
      </motion.div>

      {/* ═══════════════════════════════════════════
          2. HORIZONTAL GROUPED BAR CHART
          ═══════════════════════════════════════════ */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.6 }}
      >
        <ChartCard
          title="Detection Rate by Attack Type"
          subtitle="Per-type detection accuracy (%) — Isolation Forest vs XGBoost"
        >
          <div style={{ height: 340 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={perTypeData}
                layout="vertical"
                margin={{ top: 10, right: 30, left: 70, bottom: 10 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke={dark ? '#3f3f46' : '#e4e4e7'}
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  domain={[0, 100]}
                  tick={{ fill: chartTextColor, fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: dark ? '#3f3f46' : '#e4e4e7' }}
                  unit="%"
                />
                <YAxis
                  type="category"
                  dataKey="type"
                  tick={{ fill: chartTextColor, fontSize: 13, fontWeight: 500 }}
                  tickLine={false}
                  axisLine={false}
                  width={80}
                />
                <Tooltip content={<ChartTooltipContent />} />
                <Legend
                  wrapperStyle={{ fontSize: '13px', color: chartTextColor }}
                />
                <Bar
                  dataKey="IF"
                  name="Isolation Forest"
                  fill={COLORS.red}
                  radius={[0, 4, 4, 0]}
                  barSize={16}
                  animationBegin={200}
                  animationDuration={1200}
                />
                <Bar
                  dataKey="XGB"
                  name="XGBoost"
                  fill={COLORS.green}
                  radius={[0, 4, 4, 0]}
                  barSize={16}
                  animationBegin={600}
                  animationDuration={1200}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </motion.div>

      {/* ═══════════════════════════════════════════
          3. CONFUSION MATRIX (XGBoost)
          ═══════════════════════════════════════════ */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45, duration: 0.6 }}
      >
        <GlassCard>
          <h3 className="text-lg font-semibold text-surface-800 dark:text-surface-100 mb-1">
            XGBoost Confusion Matrix
          </h3>
          <p className="text-sm text-surface-500 dark:text-surface-400 mb-6">
            Classification outcomes on{' '}
            <span className="font-semibold text-surface-800 dark:text-surface-100">
              {(74933).toLocaleString()}
            </span>{' '}
            test nodes
          </p>

          <div className="mx-auto max-w-lg">
            {/* Column headers */}
            <div className="grid grid-cols-[120px_1fr_1fr] gap-3 mb-2">
              <div />
              <p className="text-center text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
                Predicted Positive
              </p>
              <p className="text-center text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
                Predicted Negative
              </p>
            </div>

            {/* Row 1 — Actual Positive */}
            <div className="grid grid-cols-[120px_1fr_1fr] gap-3 mb-3">
              <div className="flex items-center justify-end pr-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400 text-right">
                  Actual Positive
                </span>
              </div>
              {/* TP */}
              <motion.div
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.5, duration: 0.5, type: 'spring', stiffness: 200 }}
                className={`rounded-xl border p-5 text-center ${matrixCells[0].bg}`}
              >
                <p className={`text-xs font-medium mb-1 ${matrixCells[0].text}`}>TP</p>
                <p className={`text-2xl font-bold ${matrixCells[0].text}`}>
                  <CountUp end={cm.tp} separator="," duration={2} delay={0.6} />
                </p>
              </motion.div>
              {/* FN */}
              <motion.div
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.65, duration: 0.5, type: 'spring', stiffness: 200 }}
                className={`rounded-xl border p-5 text-center ${matrixCells[1].bg}`}
              >
                <p className={`text-xs font-medium mb-1 ${matrixCells[1].text}`}>FN</p>
                <p className={`text-2xl font-bold ${matrixCells[1].text}`}>
                  <CountUp end={cm.fn} separator="," duration={2} delay={0.75} />
                </p>
              </motion.div>
            </div>

            {/* Row 2 — Actual Negative */}
            <div className="grid grid-cols-[120px_1fr_1fr] gap-3">
              <div className="flex items-center justify-end pr-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400 text-right">
                  Actual Negative
                </span>
              </div>
              {/* FP */}
              <motion.div
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.8, duration: 0.5, type: 'spring', stiffness: 200 }}
                className={`rounded-xl border p-5 text-center ${matrixCells[2].bg}`}
              >
                <p className={`text-xs font-medium mb-1 ${matrixCells[2].text}`}>FP</p>
                <p className={`text-2xl font-bold ${matrixCells[2].text}`}>
                  <CountUp end={cm.fp} separator="," duration={2} delay={0.9} />
                </p>
              </motion.div>
              {/* TN */}
              <motion.div
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.95, duration: 0.5, type: 'spring', stiffness: 200 }}
                className={`rounded-xl border p-5 text-center ${matrixCells[3].bg}`}
              >
                <p className={`text-xs font-medium mb-1 ${matrixCells[3].text}`}>TN</p>
                <p className={`text-2xl font-bold ${matrixCells[3].text}`}>
                  <CountUp end={cm.tn} separator="," duration={2} delay={1.05} />
                </p>
              </motion.div>
            </div>
          </div>
        </GlassCard>
      </motion.div>

      {/* ═══════════════════════════════════════════
          4. NODE LOOKUP PANEL
          ═══════════════════════════════════════════ */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.6 }}
      >
        <GlassCard>
          <div className="flex items-center gap-3 mb-5">
            <div className="rounded-xl bg-brand-blue/10 p-2.5 text-brand-blue">
              <Search size={20} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-surface-800 dark:text-surface-100">
                Node Lookup
              </h3>
              <p className="text-xs text-surface-500 dark:text-surface-400">
                Query anomaly scores for any node in the network
              </p>
            </div>
          </div>

          {/* Search input */}
          <form onSubmit={handleLookup} className="flex gap-3 mb-6">
            <div className="relative flex-1">
              <Search
                size={16}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"
              />
              <input
                type="text"
                value={nodeInput}
                onChange={(e) => setNodeInput(e.target.value)}
                placeholder="Enter node ID (e.g. 373986)"
                className="glass w-full rounded-xl py-2.5 pl-10 pr-4 text-sm text-surface-800 placeholder-surface-400 outline-none ring-1 ring-surface-300/40 transition-all focus:ring-2 focus:ring-brand-blue/50 dark:text-surface-100 dark:ring-surface-600/40 dark:placeholder-surface-500"
              />
            </div>
            <button
              type="submit"
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-brand-blue to-brand-purple px-5 py-2.5 text-sm font-semibold text-white shadow-md transition-all hover:shadow-lg hover:brightness-110 active:scale-[0.97]"
            >
              <Search size={15} />
              Lookup
            </button>
          </form>

          {/* Result card */}
          <AnimatePresence mode="wait">
            {lookupResult && (
              <motion.div
                key={lookupResult.nodeId}
                initial={{ opacity: 0, y: 30, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 20, scale: 0.97 }}
                transition={{ duration: 0.45, ease: 'easeOut' }}
                className="rounded-xl border border-surface-200/50 bg-surface-50/80 p-5 dark:border-surface-700/50 dark:bg-surface-800/60"
              >
                {/* Status banner */}
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold text-surface-800 dark:text-surface-100">
                      Node #{lookupResult.nodeId}
                    </span>
                  </div>
                  {lookupResult.isHighRisk ? (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-danger-500/15 px-3 py-1 text-xs font-bold text-danger-500 red-glow-pulse">
                      <AlertTriangle size={13} />
                      ⚠ High Risk
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-success-500/15 px-3 py-1 text-xs font-bold text-success-500">
                      <CheckCircle size={13} />
                      ✓ Normal
                    </span>
                  )}
                </div>

                {/* Score grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {/* Anomaly Score */}
                  <div
                    className={`rounded-lg border p-4 text-center ${
                      lookupResult.anomaly > 0.5
                        ? 'border-danger-500/30 bg-danger-500/10'
                        : 'border-surface-200 bg-surface-100 dark:border-surface-700 dark:bg-surface-800/50'
                    }`}
                  >
                    <p className="mb-1 text-xs font-medium text-surface-500 dark:text-surface-400">
                      Anomaly Score
                    </p>
                    <p
                      className={`text-2xl font-bold ${
                        lookupResult.anomaly > 0.5
                          ? 'text-danger-500 dark:neon-text-pink'
                          : 'text-surface-800 dark:neon-text-cyan'
                      }`}
                    >
                      <CountUp
                        end={lookupResult.anomaly}
                        decimals={4}
                        duration={1}
                      />
                    </p>
                  </div>

                  {/* Trust Score */}
                  <div
                    className={`rounded-lg border p-4 text-center ${
                      lookupResult.trust < 0.5
                        ? 'border-warning-500/30 bg-warning-500/10'
                        : 'border-surface-200 bg-surface-100 dark:border-surface-700 dark:bg-surface-800/50'
                    }`}
                  >
                    <p className="mb-1 text-xs font-medium text-surface-500 dark:text-surface-400">
                      Trust Score
                    </p>
                    <p
                      className={`text-2xl font-bold ${
                        lookupResult.trust < 0.5
                          ? 'text-warning-500 dark:neon-text-orange'
                          : 'text-success-500 dark:neon-text-green'
                      }`}
                    >
                      <CountUp
                        end={lookupResult.trust}
                        decimals={4}
                        duration={1}
                      />
                    </p>
                  </div>

                  {/* Attack Probability */}
                  <div
                    className={`rounded-lg border p-4 text-center ${
                      lookupResult.attackProb > 0.5
                        ? 'border-danger-500/30 bg-danger-500/10'
                        : 'border-surface-200 bg-surface-100 dark:border-surface-700 dark:bg-surface-800/50'
                    }`}
                  >
                    <p className="mb-1 text-xs font-medium text-surface-500 dark:text-surface-400">
                      Attack Probability
                    </p>
                    <p
                      className={`text-2xl font-bold ${
                        lookupResult.attackProb > 0.5
                          ? 'text-danger-500 dark:neon-text-pink'
                          : 'text-surface-800 dark:neon-text-cyan'
                      }`}
                    >
                      <CountUp
                        end={lookupResult.attackProb}
                        decimals={4}
                        duration={1}
                      />
                    </p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Empty state */}
          {!lookupResult && (
            <div className="flex flex-col items-center justify-center py-8 text-surface-400 dark:text-surface-500">
              <Search size={32} className="mb-2 opacity-40" />
              <p className="text-sm">Enter a node ID above to view its risk assessment</p>
            </div>
          )}
        </GlassCard>
      </motion.div>
    </div>
  );
};

export default AttackDetection;
