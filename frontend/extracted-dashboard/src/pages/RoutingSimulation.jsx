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
  ShieldOff,
  ShieldCheck,
  ArrowRight,
  TrendingDown,
  Route as RouteIcon,
  Gauge,
  Network,
  Filter,
  CheckCircle,
  GitBranch,
} from 'lucide-react';
import { routingData, COLORS } from '../data/pipelineData';
import { KpiCard, SectionHeader, ChartCard } from '../components/shared';
import { useTheme } from '../context/ThemeContext';

/* ── Static data derived from routingData ── */
const comparisonData = [
  { metric: 'Compromised Routes %', baseline: 23, trustAware: 0 },
  { metric: 'Avg Hop Count', baseline: 4.21, trustAware: 4.22 },
];

const sampleRoutes = routingData.sampleRoutes;

/* ── Animation variants ── */
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15, delayChildren: 0.1 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: 'easeOut' },
  },
};

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.5, ease: 'easeOut' },
  }),
};

/* ── Route Path Visualizer Sub-component ── */
function RoutePathVisualizer({ route }) {
  const nodes = route.path;
  const nodeCount = nodes.length;

  // Layout constants
  const paddingX = 70;
  const paddingY = 50;
  const svgWidth = Math.max(600, nodeCount * 100 + paddingX * 2);
  const svgHeight = 140;
  const startX = paddingX;
  const endX = svgWidth - paddingX;
  const centerY = svgHeight / 2 - 10;
  const spacing = nodeCount > 1 ? (endX - startX) / (nodeCount - 1) : 0;

  const nodePositions = nodes.map((id, i) => ({
    id,
    x: startX + i * spacing,
    y: centerY,
    label: String(id).slice(-4),
  }));

  // Build the polyline path string for stroke animation
  const pathD = nodePositions.map((n, i) => `${i === 0 ? 'M' : 'L'} ${n.x} ${n.y}`).join(' ');
  const totalLength = nodePositions.reduce((sum, n, i) => {
    if (i === 0) return 0;
    const prev = nodePositions[i - 1];
    return sum + Math.sqrt((n.x - prev.x) ** 2 + (n.y - prev.y) ** 2);
  }, 0);

  return (
    <div className="w-full overflow-x-auto">
      <svg
        width={svgWidth}
        height={svgHeight + 20}
        viewBox={`0 0 ${svgWidth} ${svgHeight + 20}`}
        className="mx-auto"
      >
        {/* Animated path line */}
        <motion.path
          d={pathD}
          fill="none"
          stroke={COLORS.green}
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ strokeDasharray: totalLength, strokeDashoffset: totalLength }}
          animate={{ strokeDashoffset: 0 }}
          transition={{ duration: 1.2, ease: 'easeInOut' }}
        />

        {/* Edge lines (subtle underlay) */}
        {nodePositions.map((node, i) => {
          if (i === 0) return null;
          const prev = nodePositions[i - 1];
          return (
            <motion.line
              key={`edge-${i}`}
              x1={prev.x}
              y1={prev.y}
              x2={node.x}
              y2={node.y}
              stroke={COLORS.green}
              strokeWidth={1}
              strokeOpacity={0.15}
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ delay: i * 0.12, duration: 0.4 }}
            />
          );
        })}

        {/* Nodes */}
        {nodePositions.map((node, i) => (
          <g key={`node-${node.id}`}>
            {/* Outer glow ring */}
            <motion.circle
              cx={node.x}
              cy={node.y}
              r={16}
              fill={COLORS.green}
              fillOpacity={0.08}
              stroke={COLORS.green}
              strokeWidth={1}
              strokeOpacity={0.2}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.3 + i * 0.12, duration: 0.4, ease: 'backOut' }}
            />
            {/* Main node circle */}
            <motion.circle
              cx={node.x}
              cy={node.y}
              r={10}
              fill={i === 0 ? COLORS.blue : i === nodeCount - 1 ? COLORS.green : COLORS.purple}
              stroke="rgba(255,255,255,0.3)"
              strokeWidth={1.5}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.3 + i * 0.12, duration: 0.35, type: 'spring', stiffness: 260, damping: 20 }}
            />
            {/* Node index inside circle */}
            <motion.text
              x={node.x}
              y={node.y + 1}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="white"
              fontSize={8}
              fontWeight="bold"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 + i * 0.12 }}
            >
              {i}
            </motion.text>
            {/* Truncated ID label below */}
            <motion.text
              x={node.x}
              y={node.y + 26}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#a1a1aa"
              fontSize={10}
              fontFamily="monospace"
              initial={{ opacity: 0, y: node.y + 20 }}
              animate={{ opacity: 1, y: node.y + 26 }}
              transition={{ delay: 0.6 + i * 0.12, duration: 0.3 }}
            >
              {node.label}
            </motion.text>
            {/* Arrow indicator between nodes */}
            {i < nodeCount - 1 && (
              <motion.text
                x={node.x + spacing / 2}
                y={node.y - 18}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="#71717a"
                fontSize={10}
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.6 }}
                transition={{ delay: 0.7 + i * 0.12 }}
              >
                →
              </motion.text>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}

/* ── Main Page Component ── */
const RoutingSimulation = () => {
  const { dark } = useTheme();
  const chartTextColor = dark ? '#a1a1aa' : '#52525b';
  const [countdownDone, setCountdownDone] = useState(false);
  const [selectedRouteIdx, setSelectedRouteIdx] = useState(0);

  const selectedRoute = sampleRoutes[selectedRouteIdx];

  return (
    <motion.div
      className="space-y-8"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Section Header */}
      <motion.div variants={cardVariants}>
        <SectionHeader
          title="Routing Simulation"
          subtitle="Trust-aware routing eliminates compromised paths with negligible hop overhead"
          icon={RouteIcon}
        />
      </motion.div>

      {/* ═══════════════════════════════════════════
          1. Hero Banner with Animated Countdown
         ═══════════════════════════════════════════ */}
      <motion.div
        variants={cardVariants}
        className="relative rounded-2xl overflow-hidden p-8 md:p-12"
        style={{
          background: dark
            ? 'linear-gradient(135deg, rgba(227,73,72,0.12) 0%, rgba(27,175,122,0.12) 100%)'
            : 'linear-gradient(135deg, rgba(227,73,72,0.08) 0%, rgba(27,175,122,0.08) 100%)',
        }}
      >
        {/* Decorative background elements */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div
            className="absolute -top-20 -left-20 w-60 h-60 rounded-full opacity-10"
            style={{ background: 'radial-gradient(circle, #e34948 0%, transparent 70%)' }}
          />
          <div
            className="absolute -bottom-20 -right-20 w-60 h-60 rounded-full opacity-10"
            style={{ background: 'radial-gradient(circle, #1baf7a 0%, transparent 70%)' }}
          />
        </div>

        <div className="relative z-10 text-center">
          {/* Shield icons */}
          <div className="flex items-center justify-center gap-4 mb-4">
            <motion.div
              initial={{ scale: 0, rotate: -20 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            >
              <ShieldOff className="w-8 h-8 text-danger-500" />
            </motion.div>
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
            >
              <ArrowRight className="w-6 h-6 text-surface-400" />
            </motion.div>
            <motion.div
              initial={{ scale: 0, rotate: 20 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ delay: 0.6, type: 'spring', stiffness: 200 }}
            >
              <ShieldCheck className="w-8 h-8 text-success-500" />
            </motion.div>
          </div>

          {/* Countdown number */}
          <h2 className="text-5xl md:text-7xl font-extrabold mb-3 tracking-tight">
            <span className="inline-flex items-center gap-3">
              <CountUp
                start={23}
                end={0}
                duration={3}
                suffix="%"
                delay={0.5}
                onEnd={() => setCountdownDone(true)}
              >
                {({ countUpRef }) => (
                  <span
                    ref={countUpRef}
                    className={countdownDone ? 'text-success-500 dark:neon-text-green' : 'text-danger-500 dark:neon-text-pink'}
                    style={{
                      transition: 'color 0.6s ease',
                    }}
                  />
                )}
              </CountUp>
              {/* Green checkmark appearing after countdown */}
              <AnimatePresence>
                {countdownDone && (
                  <motion.div
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0, opacity: 0 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 15 }}
                  >
                    <CheckCircle className="w-10 h-10 md:w-14 md:h-14 text-success-500 drop-shadow-lg" />
                  </motion.div>
                )}
              </AnimatePresence>
            </span>
          </h2>

          {/* Subtitle */}
          <motion.p
            className="text-lg text-surface-600 dark:neon-text-green max-w-xl mx-auto font-semibold"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8, duration: 0.5 }}
          >
            Compromised routes eliminated by trust-aware routing
          </motion.p>
        </div>
      </motion.div>

      {/* ═══════════════════════════════════════════
          2. Side-by-Side Comparison Cards
         ═══════════════════════════════════════════ */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 gap-6"
        variants={containerVariants}
      >
        {/* Baseline Card */}
        <motion.div
          variants={cardVariants}
          className="glass rounded-2xl p-6 border-l-4 border-danger-500 transition-all duration-300 hover:shadow-lg"
        >
          <div className="flex items-center gap-3 mb-5">
            <div className="p-2.5 rounded-xl bg-danger-500/10 text-danger-500">
              <ShieldOff className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-surface-800 dark:text-surface-100">
                Baseline Routing
              </h3>
              <p className="text-xs text-surface-500 dark:text-surface-400">
                Standard shortest-path without trust filtering
              </p>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 rounded-lg bg-surface-100 dark:bg-surface-800/50">
              <span className="text-sm text-surface-600 dark:text-surface-400">Total Routes</span>
              <span className="text-sm font-semibold text-surface-800 dark:text-surface-100">200</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-danger-500/10 dark:bg-danger-500/20 dark:border dark:border-danger-glow">
              <span className="text-sm text-danger-600 dark:neon-text-pink">Compromised</span>
              <span className="text-sm font-bold text-danger-600 dark:neon-text-pink">23%</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-surface-100 dark:bg-surface-800/50">
              <span className="text-sm text-surface-600 dark:text-surface-400">Affected Routes</span>
              <span className="text-sm font-semibold text-surface-800 dark:text-surface-100">46 of 200</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-surface-100 dark:bg-surface-800/50">
              <span className="text-sm text-surface-600 dark:text-surface-400">Avg Hop Count</span>
              <span className="text-sm font-semibold text-surface-800 dark:text-surface-100">4.21</span>
            </div>
          </div>
        </motion.div>

        {/* Trust-Aware Card */}
        <motion.div
          variants={cardVariants}
          className="glass rounded-2xl p-6 border-l-4 border-success-500 transition-all duration-300 hover:shadow-lg"
        >
          <div className="flex items-center gap-3 mb-5">
            <div className="p-2.5 rounded-xl bg-success-500/10 text-success-500">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-surface-800 dark:text-surface-100">
                Trust-Aware Routing
              </h3>
              <p className="text-xs text-surface-500 dark:text-surface-400">
                AI-integrated trust-scored paths
              </p>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 rounded-lg bg-surface-100 dark:bg-surface-800/50">
              <span className="text-sm text-surface-600 dark:text-surface-400">Total Routes</span>
              <span className="text-sm font-semibold text-surface-800 dark:text-surface-100">200</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-success-500/10 dark:bg-success-500/20 dark:border dark:border-success-glow">
              <span className="text-sm text-success-600 dark:neon-text-green">Compromised</span>
              <span className="text-sm font-bold text-success-600 dark:neon-text-green">0%</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-surface-100 dark:bg-surface-800/50">
              <span className="text-sm text-surface-600 dark:text-surface-400">Affected Routes</span>
              <span className="text-sm font-semibold text-surface-800 dark:text-surface-100">0 of 200</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-surface-100 dark:bg-surface-800/50">
              <span className="text-sm text-surface-600 dark:text-surface-400">Avg Hop Count</span>
              <span className="text-sm font-semibold text-surface-800 dark:text-surface-100">4.22</span>
            </div>
          </div>
        </motion.div>
      </motion.div>

      {/* ═══════════════════════════════════════════
          3. Animated Bar Chart
         ═══════════════════════════════════════════ */}
      <motion.div variants={cardVariants}>
        <ChartCard
          title="Baseline vs Trust-Aware Comparison"
          subtitle="Side-by-side metric comparison between routing approaches"
        >
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={comparisonData}
                margin={{ top: 10, right: 30, left: 20, bottom: 10 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke={dark ? '#3f3f46' : '#e4e4e7'}
                  vertical={false}
                />
                <XAxis
                  dataKey="metric"
                  tick={{ fill: chartTextColor, fontSize: 13, fontWeight: 500 }}
                  tickLine={false}
                  axisLine={{ stroke: dark ? '#3f3f46' : '#e4e4e7' }}
                />
                <YAxis
                  tick={{ fill: chartTextColor, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: dark ? '#27272a' : '#ffffff',
                    border: `1px solid ${dark ? '#3f3f46' : '#e4e4e7'}`,
                    borderRadius: '12px',
                    fontSize: '13px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                  }}
                />
                <Legend
                  wrapperStyle={{ fontSize: '13px', color: chartTextColor }}
                />
                <Bar
                  dataKey="baseline"
                  name="Baseline"
                  fill={COLORS.red}
                  radius={[6, 6, 0, 0]}
                  barSize={48}
                  animationBegin={200}
                  animationDuration={1200}
                  animationEasing="ease-out"
                />
                <Bar
                  dataKey="trustAware"
                  name="Trust-Aware"
                  fill={COLORS.green}
                  radius={[6, 6, 0, 0]}
                  barSize={48}
                  animationBegin={600}
                  animationDuration={1200}
                  animationEasing="ease-out"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </motion.div>

      {/* ═══════════════════════════════════════════
          4. Metric Cards Row (6 cards)
         ═══════════════════════════════════════════ */}
      <motion.div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
        variants={containerVariants}
      >
        <motion.div variants={cardVariants}>
          <KpiCard
            title="Excluded Nodes"
            value="45"
            subtitle="9% of topology"
            icon={Filter}
            color="amber"
            delay={0}
          />
        </motion.div>
        <motion.div variants={cardVariants}>
          <KpiCard
            title="Hop Overhead"
            value="+0.01"
            subtitle="Negligible increase"
            icon={TrendingDown}
            color="green"
            delay={1}
          />
        </motion.div>
        <motion.div variants={cardVariants}>
          <KpiCard
            title="Routes Found"
            value="200 / 200"
            subtitle="100% reachability"
            icon={RouteIcon}
            color="blue"
            delay={2}
          />
        </motion.div>
        <motion.div variants={cardVariants}>
          <KpiCard
            title="Trust Threshold"
            value="0.40"
            subtitle="Minimum trust score"
            icon={Gauge}
            color="purple"
            delay={3}
          />
        </motion.div>
        <motion.div variants={cardVariants}>
          <KpiCard
            title="Network Nodes"
            value="500"
            subtitle="Total topology nodes"
            icon={Network}
            color="blue"
            delay={4}
          />
        </motion.div>
        <motion.div variants={cardVariants}>
          <KpiCard
            title="Network Edges"
            value="7,703"
            subtitle="Total connections"
            icon={GitBranch}
            color="purple"
            delay={5}
          />
        </motion.div>
      </motion.div>

      {/* ═══════════════════════════════════════════
          5. Route Path Visualizer
         ═══════════════════════════════════════════ */}
      <motion.div variants={cardVariants}>
        <div className="glass rounded-2xl p-6 transition-all duration-300 hover:shadow-lg">
          {/* Header with Route Selector */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-brand-blue/10 p-2.5 text-brand-blue">
                <RouteIcon size={22} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-surface-800 dark:text-surface-100">
                  Route Path Visualizer
                </h3>
                <p className="text-xs text-surface-500 dark:text-surface-400">
                  Inspect trust-aware route paths through the network
                </p>
              </div>
            </div>

            {/* Route Selector Dropdown */}
            <div className="relative">
              <select
                value={selectedRouteIdx}
                onChange={(e) => setSelectedRouteIdx(Number(e.target.value))}
                className="appearance-none rounded-xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800 px-4 py-2.5 pr-10 text-sm font-medium text-surface-800 dark:text-surface-100 focus:outline-none focus:ring-2 focus:ring-brand-blue/40 transition-all cursor-pointer"
              >
                {sampleRoutes.map((route, idx) => (
                  <option key={route.id} value={idx}>
                    Route {route.id} — {route.hops} hop{route.hops !== 1 ? 's' : ''}
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-surface-400">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </div>
          </div>

          {/* Route Info Badges */}
          <div className="flex flex-wrap items-center gap-3 mb-5">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-blue/10 px-3 py-1 text-xs font-semibold text-brand-blue">
              Route #{selectedRoute.id}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-purple/10 px-3 py-1 text-xs font-semibold text-brand-purple">
              {selectedRoute.hops} Hop{selectedRoute.hops !== 1 ? 's' : ''}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-success-500/10 px-3 py-1 text-xs font-semibold text-success-600 dark:text-success-400">
              <CheckCircle className="w-3 h-3" />
              Safe ✓
            </span>
          </div>

          {/* Full path display */}
          <div className="mb-5 px-3 py-2.5 rounded-lg bg-surface-100 dark:bg-surface-800/50 overflow-x-auto">
            <p className="text-xs font-mono text-surface-500 dark:text-surface-400 whitespace-nowrap">
              {selectedRoute.path.join(' → ')}
            </p>
          </div>

          {/* Animated SVG Route Visualization */}
          <AnimatePresence mode="wait">
            <motion.div
              key={selectedRoute.id}
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.97 }}
              transition={{ duration: 0.3 }}
              className="rounded-xl bg-surface-950/5 dark:bg-surface-900/50 border border-surface-200/30 dark:border-surface-700/30 p-4"
            >
              <RoutePathVisualizer route={selectedRoute} />
            </motion.div>
          </AnimatePresence>

          {/* Legend */}
          <div className="flex flex-wrap items-center gap-5 mt-4 text-xs text-surface-500 dark:text-surface-400">
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS.blue }} />
              Source Node
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS.purple }} />
              Intermediate
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS.green }} />
              Destination
            </span>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default RoutingSimulation;
