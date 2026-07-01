import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import ReactCountUp from 'react-countup';
const CountUp = ReactCountUp.default || ReactCountUp;
import Particles from '@tsparticles/react';
import { loadSlim } from '@tsparticles/slim';
import { tsParticles } from '@tsparticles/engine';
import * as d3Force from 'd3-force';
import { Network, ShieldAlert, BarChart3, Target, AlertTriangle, CheckCircle, Sliders } from 'lucide-react';
import { networkData, trustThresholdRanges, COLORS } from '../data/pipelineData';
import { KpiCard, SectionHeader, ChartCard } from '../components/shared';
import { useTheme } from '../context/ThemeContext';

/* ── GlassCard (local, since shared.jsx does not export one) ── */
function GlassCard({ children, className = '' }) {
  return (
    <div className={`glass rounded-2xl p-6 ${className}`}>
      {children}
    </div>
  );
}

/* ── Helpers ── */
const total = networkData.totalNodes;

function getFlaggedData(threshold) {
  const range = trustThresholdRanges.find(
    (r) => threshold >= r.min && threshold <= r.max,
  );
  return range || trustThresholdRanges[trustThresholdRanges.length - 1];
}

/* ── Seed-able pseudo-random for deterministic graph ── */
function seededRandom(seed) {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

/* ── Generate graph data (memoised outside component) ── */
function generateGraphData() {
  const rand = seededRandom(42);
  const nodes = Array.from({ length: 80 }, (_, i) => ({
    id: i,
    attacked: i < 7,
  }));
  const edgeSet = new Set();
  const links = [];
  while (links.length < 150) {
    const a = Math.floor(rand() * 80);
    const b = Math.floor(rand() * 80);
    if (a !== b) {
      const key = a < b ? `${a}-${b}` : `${b}-${a}`;
      if (!edgeSet.has(key)) {
        edgeSet.add(key);
        links.push({ source: a, target: b });
      }
    }
  }
  return { nodes, links };
}

/* ── Custom recharts tooltip ── */
const DonutTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const d = payload[0];
    const pct = ((d.value / total) * 100).toFixed(2);
    return (
      <div className="rounded-lg border border-surface-200/60 bg-white/95 px-4 py-3 shadow-xl backdrop-blur dark:border-surface-700/60 dark:bg-surface-800/95">
        <p className="text-sm font-semibold" style={{ color: d.payload.color }}>
          {d.name}
        </p>
        <p className="text-sm text-surface-600 dark:text-surface-300">
          {d.value.toLocaleString()} nodes ({pct}%)
        </p>
      </div>
    );
  }
  return null;
};

/* ── Animation variants ── */
const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: 'easeOut' },
  }),
};

const sectionVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.15 + i * 0.12, duration: 0.55, ease: 'easeOut' },
  }),
};

/* ═══════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════ */
const NetworkOverview = () => {
  const { dark } = useTheme();

  /* ── Particles engine ── */
  const [particlesReady, setParticlesReady] = useState(false);

  useEffect(() => {
    loadSlim(tsParticles).then(() => setParticlesReady(true));
  }, []);

  const particlesOptions = useMemo(
    () => ({
      fullScreen: { enable: false },
      fpsLimit: 60,
      particles: {
        number: { value: 50, density: { enable: true, area: 900 } },
        color: { value: '#2a78d6' },
        opacity: { value: 0.3 },
        size: { value: { min: 1, max: 3 } },
        links: {
          enable: true,
          color: '#2a78d6',
          opacity: 0.15,
          distance: 140,
          width: 1,
        },
        move: {
          enable: true,
          speed: 0.6,
          direction: 'none',
          outModes: { default: 'bounce' },
        },
      },
      detectRetina: true,
    }),
    [],
  );

  /* ── Trust threshold ── */
  const [threshold, setThreshold] = useState(0.4);
  const flagged = getFlaggedData(threshold);

  /* ── Force graph ── */
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const [graphDimensions, setGraphDimensions] = useState({ width: 800, height: 400 });
  const [nodePositions, setNodePositions] = useState([]);
  const [linkPositions, setLinkPositions] = useState([]);
  const [edgesVisible, setEdgesVisible] = useState(false);

  const graphData = useMemo(() => generateGraphData(), []);

  /* measure container */
  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setGraphDimensions({ width: rect.width, height: 400 });
      }
    };
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

  /* run simulation */
  useEffect(() => {
    const { width, height } = graphDimensions;
    if (width === 0) return;

    const nodes = graphData.nodes.map((n) => ({ ...n }));
    const links = graphData.links.map((l) => ({
      source: l.source,
      target: l.target,
    }));

    const simulation = d3Force
      .forceSimulation(nodes)
      .force(
        'link',
        d3Force
          .forceLink(links)
          .id((d) => d.id)
          .distance(55),
      )
      .force('charge', d3Force.forceManyBody().strength(-40))
      .force('center', d3Force.forceCenter(width / 2, height / 2))
      .force('collision', d3Force.forceCollide(12));

    simulation.on('tick', () => {
      setNodePositions(
        nodes.map((n) => ({
          id: n.id,
          x: Math.max(10, Math.min(width - 10, n.x)),
          y: Math.max(10, Math.min(height - 10, n.y)),
          attacked: n.attacked,
        })),
      );
      setLinkPositions(
        links.map((l) => ({
          x1: Math.max(10, Math.min(width - 10, l.source.x)),
          y1: Math.max(10, Math.min(height - 10, l.source.y)),
          x2: Math.max(10, Math.min(width - 10, l.target.x)),
          y2: Math.max(10, Math.min(height - 10, l.target.y)),
        })),
      );
    });

    /* fade edges in after simulation settles a bit */
    const edgeTimer = setTimeout(() => setEdgesVisible(true), 600);

    return () => {
      simulation.stop();
      clearTimeout(edgeTimer);
    };
  }, [graphData, graphDimensions]);

  /* ── Warning / success banners ── */
  const bannerContent = useMemo(() => {
    if (threshold < 0.3) {
      return { key: 'low', color: 'amber', icon: AlertTriangle, text: '⚠ Threshold too low — high false positive rate' };
    }
    if (threshold > 0.7) {
      return { key: 'high', color: 'amber', icon: AlertTriangle, text: '⚠ Threshold too high — attacks may go undetected' };
    }
    if (threshold >= 0.4 && threshold <= 0.5) {
      return { key: 'optimal', color: 'green', icon: CheckCircle, text: '✓ Optimal threshold range' };
    }
    return null;
  }, [threshold]);

  /* ═══════════════════════════════════════════════════
     RENDER
     ═══════════════════════════════════════════════════ */
  return (
    <div className="relative min-h-screen">
      {/* ── Particles background ── */}
      {particlesReady && (
        <Particles
          id="overview-particles"
          className="pointer-events-none absolute inset-0 z-0"
          options={particlesOptions}
        />
      )}

      {/* ── Content ── */}
      <div className="relative z-10 space-y-8">
        {/* Page title */}
        <motion.div
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="gradient-text mb-1 text-3xl font-extrabold tracking-tight lg:text-4xl">
            Network Overview
          </h1>
          <p className="text-sm text-surface-500 dark:text-surface-400">
            WSN-DS dataset summary and attack distribution across {total.toLocaleString()} sensor nodes
          </p>
        </motion.div>

        {/* ────────────────── 1. KPI Cards ────────────────── */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              title: 'Total Nodes',
              value: <CountUp end={networkData.totalNodes} separator="," duration={2} />,
              subtitle: 'Sensor node observations',
              icon: Network,
              color: 'blue',
            },
            {
              title: 'Attacked Nodes',
              value: <CountUp end={networkData.attackedNodes} separator="," duration={2} />,
              subtitle: '4 attack categories',
              icon: ShieldAlert,
              color: 'red',
            },
            {
              title: '% Attacked',
              value: (
                <>
                  <CountUp end={networkData.attackedPercent} decimals={2} duration={2} />%
                </>
              ),
              subtitle: 'Attack rate',
              icon: BarChart3,
              color: 'amber',
            },
            {
              title: 'Classifier F1',
              value: <CountUp end={networkData.classifierF1} decimals={4} duration={2} />,
              subtitle: 'XGBoost leakage-free',
              icon: Target,
              color: 'green',
            },
          ].map((kpi, i) => (
            <motion.div
              key={kpi.title}
              custom={i}
              initial="hidden"
              animate="visible"
              variants={cardVariants}
            >
              <KpiCard
                title={kpi.title}
                value={kpi.value}
                subtitle={kpi.subtitle}
                icon={kpi.icon}
                color={kpi.color}
                delay={i}
              />
            </motion.div>
          ))}
        </div>

        {/* ────────────────── 2. Donut Chart ────────────────── */}
        <motion.div
          custom={1}
          initial="hidden"
          animate="visible"
          variants={sectionVariants}
        >
          <ChartCard
            title="Attack Type Distribution"
            subtitle="Breakdown across all 374,661 sensor nodes"
          >
            <div className="grid grid-cols-1 items-center gap-6 lg:grid-cols-2">
              {/* Chart */}
              <div className="flex items-center justify-center" style={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={networkData.attackTypes}
                      cx="50%"
                      cy="50%"
                      innerRadius={70}
                      outerRadius={115}
                      paddingAngle={2}
                      dataKey="value"
                      stroke="none"
                      animationBegin={200}
                      animationDuration={1200}
                    >
                      {networkData.attackTypes.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip content={<DonutTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Legend */}
              <div className="space-y-3">
                {networkData.attackTypes.map((entry) => {
                  const pct = ((entry.value / total) * 100).toFixed(2);
                  return (
                    <div
                      key={entry.name}
                      className="flex items-center justify-between rounded-lg px-3 py-2 transition-colors hover:bg-surface-100/60 dark:hover:bg-surface-700/40"
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className="h-3 w-3 flex-shrink-0 rounded-sm"
                          style={{ backgroundColor: entry.color }}
                        />
                        <span className="text-sm font-medium text-surface-700 dark:text-surface-300">
                          {entry.name}
                        </span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-sm font-semibold text-surface-800 dark:text-surface-100">
                          {entry.value.toLocaleString()}
                        </span>
                        <span className="w-14 text-right text-xs text-surface-500 dark:text-surface-400">
                          {pct}%
                        </span>
                      </div>
                    </div>
                  );
                })}
                <div className="mt-2 flex items-center justify-between border-t border-surface-200 pt-3 dark:border-surface-700">
                  <span className="text-sm font-semibold text-surface-800 dark:text-surface-100">
                    Total
                  </span>
                  <span className="text-sm font-bold text-surface-800 dark:text-surface-100">
                    {total.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          </ChartCard>
        </motion.div>

        {/* ────────────────── 3. Force-Directed Graph ────────────────── */}
        <motion.div
          custom={2}
          initial="hidden"
          animate="visible"
          variants={sectionVariants}
        >
          <ChartCard
            title="Network Topology"
            subtitle="Sample network topology — attacked nodes highlighted"
          >
            <div ref={containerRef} className="relative w-full" style={{ height: 400 }}>
              <svg
                ref={svgRef}
                width={graphDimensions.width}
                height={graphDimensions.height}
                className="w-full"
              >
                {/* Glow filter for attacked nodes */}
                <defs>
                  <filter id="red-glow" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="4" result="blur" />
                    <feFlood floodColor="#e34948" floodOpacity="0.6" result="color" />
                    <feComposite in="color" in2="blur" operator="in" result="shadow" />
                    <feMerge>
                      <feMergeNode in="shadow" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>

                {/* Edges */}
                <g>
                  {linkPositions.map((l, i) => (
                    <line
                      key={i}
                      x1={l.x1}
                      y1={l.y1}
                      x2={l.x2}
                      y2={l.y2}
                      stroke={dark ? 'rgba(255, 255, 255, 0.35)' : 'rgba(15, 23, 42, 0.2)'}
                      strokeWidth={0.8}
                      style={{
                        opacity: edgesVisible ? 1 : 0,
                        transition: `opacity 1.2s ease ${i * 4}ms`,
                      }}
                    />
                  ))}
                </g>

                {/* Nodes */}
                <g>
                  {nodePositions.map((n) => (
                    <circle
                      key={n.id}
                      cx={n.x}
                      cy={n.y}
                      r={n.attacked ? 7 : 5}
                      fill={n.attacked ? COLORS.red : (dark ? '#ffffff' : COLORS.blue)}
                      opacity={n.attacked ? 1 : 0.9}
                      className={n.attacked ? 'node-attacked' : ''}
                      filter={n.attacked ? 'url(#red-glow)' : undefined}
                      style={
                        n.attacked
                          ? { animation: 'node-pulse 2s ease-in-out infinite' }
                          : undefined
                      }
                    />
                  ))}
                </g>
              </svg>

              {/* Legend overlay */}
              <div className="absolute bottom-3 left-3 flex items-center gap-4 rounded-lg bg-white/80 px-3 py-2 text-xs backdrop-blur dark:bg-surface-800/80">
                <span className="flex items-center gap-1.5 text-surface-800 dark:text-surface-100">
                  <span className="inline-block h-2.5 w-2.5 rounded-full border border-surface-300 dark:border-transparent" style={{ backgroundColor: dark ? '#ffffff' : COLORS.blue }} />
                  Normal (73)
                </span>
                <span className="flex items-center gap-1.5 text-surface-800 dark:text-surface-100">
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS.red }} />
                  Attacked (7)
                </span>
              </div>
            </div>
          </ChartCard>
        </motion.div>

        {/* ────────────────── 4. Trust Threshold Slider ────────────────── */}
        <motion.div
          custom={3}
          initial="hidden"
          animate="visible"
          variants={sectionVariants}
        >
          <GlassCard>
            <SectionHeader
              title="Trust Threshold Tuning"
              subtitle="Adjust the anomaly trust threshold to balance detection sensitivity"
              icon={Sliders}
            />

            <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
              {/* Slider column */}
              <div className="space-y-6">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-semibold text-surface-700 dark:text-surface-300">
                      Trust Threshold
                    </label>
                    <span className="rounded-md bg-brand-blue/10 px-3 py-1 font-mono text-lg font-bold text-brand-blue">
                      {threshold.toFixed(2)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0.10"
                    max="0.90"
                    step="0.01"
                    value={threshold}
                    onChange={(e) => setThreshold(parseFloat(e.target.value))}
                    className="h-2 w-full cursor-pointer appearance-none rounded-full bg-surface-200 accent-brand-blue dark:bg-surface-700"
                  />
                  <div className="flex justify-between text-xs text-surface-500 dark:text-surface-400">
                    <span>0.10 (lenient)</span>
                    <span>0.90 (strict)</span>
                  </div>
                </div>

                {/* Warning / success banner */}
                <AnimatePresence mode="wait">
                  {bannerContent && (
                    <motion.div
                      key={bannerContent.key}
                      initial={{ opacity: 0, height: 0, marginTop: 0 }}
                      animate={{ opacity: 1, height: 'auto', marginTop: 8 }}
                      exit={{ opacity: 0, height: 0, marginTop: 0 }}
                      transition={{ duration: 0.3 }}
                      className={`overflow-hidden rounded-lg border px-4 py-3 ${
                        bannerContent.color === 'green'
                          ? 'border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-400'
                          : 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400'
                      }`}
                    >
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <bannerContent.icon size={16} />
                        {bannerContent.text}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* KPI display column */}
              <div className="flex flex-col justify-center gap-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-xl border border-brand-red/20 bg-brand-red/5 p-4 text-center">
                    <p className="text-xs font-medium uppercase tracking-wider text-surface-500 dark:text-surface-400">
                      Flagged Nodes
                    </p>
                    <p className="mt-1 text-2xl font-bold text-brand-red">
                      <CountUp
                        key={flagged.flagged}
                        end={flagged.flagged}
                        separator=","
                        duration={0.8}
                        preserveValue
                      />
                    </p>
                  </div>
                  <div className="rounded-xl border border-brand-amber/20 bg-brand-amber/5 p-4 text-center">
                    <p className="text-xs font-medium uppercase tracking-wider text-surface-500 dark:text-surface-400">
                      % Flagged
                    </p>
                    <p className="mt-1 text-2xl font-bold text-brand-amber">
                      <CountUp
                        key={flagged.pct}
                        end={flagged.pct}
                        decimals={2}
                        duration={0.8}
                        preserveValue
                      />
                      %
                    </p>
                  </div>
                </div>
                <p className="text-center text-xs text-surface-500 dark:text-surface-400">
                  Out of {total.toLocaleString()} total nodes
                </p>
              </div>
            </div>
          </GlassCard>
        </motion.div>
      </div>

      {/* ── Inline styles for node pulse (SVG circles) ── */}
      <style>{`
        @keyframes node-pulse {
          0%, 100% { r: 7; opacity: 1; }
          50% { r: 11; opacity: 0.6; }
        }
        .node-attacked {
          animation: node-pulse 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
};

export default NetworkOverview;
