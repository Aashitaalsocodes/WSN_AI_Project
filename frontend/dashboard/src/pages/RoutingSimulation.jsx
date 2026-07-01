import React from 'react';
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
import {
  Route,
  ShieldOff,
  ShieldCheck,
  TrendingDown,
  ArrowRight,
  Gauge,
  Network,
  Filter,
} from 'lucide-react';
import { routingData } from '../data/pipelineData';
import { KpiCard, SectionHeader, ChartCard } from '../components/shared';
import { useTheme } from '../context/ThemeContext';

const comparisonData = [
  { metric: 'Compromised %', baseline: 23, trustAware: 0 },
  { metric: 'Avg Hops', baseline: 4.21, trustAware: 4.22 },
];

const RoutingSimulation = () => {
  const { dark } = useTheme();
  const chartTextColor = dark ? '#a1a1aa' : '#52525b';

  return (
    <div className="gradient-mesh space-y-8">
      {/* Section Header */}
      <SectionHeader
        title="Routing Simulation"
        subtitle="Trust-aware routing eliminates compromised paths with negligible hop overhead"
      />

      {/* Hero Banner */}
      <div
        className="relative rounded-2xl overflow-hidden p-8 md:p-12"
        style={{
          background: dark
            ? 'linear-gradient(135deg, rgba(239,68,68,0.15) 0%, rgba(34,197,94,0.15) 100%)'
            : 'linear-gradient(135deg, rgba(239,68,68,0.1) 0%, rgba(34,197,94,0.1) 100%)',
        }}
      >
        <div className="relative z-10 text-center">
          <div className="flex items-center justify-center gap-4 mb-3">
            <ShieldOff className="w-8 h-8 text-red-500" />
            <ArrowRight className="w-6 h-6 text-zinc-400" />
            <ShieldCheck className="w-8 h-8 text-green-500" />
          </div>
          <h2 className="text-5xl md:text-6xl font-extrabold mb-3">
            <span className="text-red-500">23%</span>
            <span className="text-zinc-400 dark:text-zinc-500 mx-3">→</span>
            <span className="text-green-500">0%</span>
          </h2>
          <p className="text-lg text-zinc-600 dark:text-zinc-400 max-w-xl mx-auto">
            Eliminating compromised routes by integrating AI-driven trust scores
            into the routing decision layer
          </p>
        </div>
      </div>

      {/* Side-by-Side Comparison Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Baseline Card */}
        <div className="glass-card p-6 border-l-4 border-red-500">
          <div className="flex items-center gap-3 mb-5">
            <div className="p-2.5 rounded-xl bg-red-500/10 text-red-500">
              <ShieldOff className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">
                Baseline Routing
              </h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Standard shortest-path without trust
              </p>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 rounded-lg bg-zinc-100 dark:bg-zinc-800/50">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Total Routes</span>
              <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">200</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-red-500/10">
              <span className="text-sm text-red-600 dark:text-red-400">Compromised</span>
              <span className="text-sm font-bold text-red-600 dark:text-red-400">23%</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-zinc-100 dark:bg-zinc-800/50">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Compromised Routes</span>
              <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">46</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-zinc-100 dark:bg-zinc-800/50">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Avg Hops</span>
              <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">4.21</span>
            </div>
          </div>
        </div>

        {/* Trust-Aware Card */}
        <div className="glass-card p-6 border-l-4 border-green-500">
          <div className="flex items-center gap-3 mb-5">
            <div className="p-2.5 rounded-xl bg-green-500/10 text-green-500">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">
                Trust-Aware Routing
              </h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                AI-integrated trust-scored paths
              </p>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 rounded-lg bg-zinc-100 dark:bg-zinc-800/50">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Total Routes</span>
              <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">200</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-green-500/10">
              <span className="text-sm text-green-600 dark:text-green-400">Compromised</span>
              <span className="text-sm font-bold text-green-600 dark:text-green-400">0%</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-zinc-100 dark:bg-zinc-800/50">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Compromised Routes</span>
              <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">0</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-zinc-100 dark:bg-zinc-800/50">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Avg Hops</span>
              <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">4.22</span>
            </div>
          </div>
        </div>
      </div>

      {/* Comparison Bar Chart */}
      <ChartCard
        title="Baseline vs Trust-Aware"
        subtitle="Side-by-side metric comparison between routing approaches"
      >
        <div style={{ height: 280 }}>
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
                  borderRadius: '8px',
                  fontSize: '13px',
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: '13px', color: chartTextColor }}
              />
              <Bar
                dataKey="baseline"
                name="Baseline"
                fill="#ef4444"
                radius={[4, 4, 4, 4]}
                barSize={40}
              />
              <Bar
                dataKey="trustAware"
                name="Trust-Aware"
                fill="#22c55e"
                radius={[4, 4, 4, 4]}
                barSize={40}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      {/* Metric KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Excluded Nodes"
          value="45 (9%)"
          icon={Filter}
          color="amber"
        />
        <KpiCard
          title="Hop Overhead"
          value="+0.01"
          icon={TrendingDown}
          color="green"
        />
        <KpiCard
          title="Routes Found"
          value="200"
          icon={Route}
          color="blue"
        />
        <KpiCard
          title="Trust Threshold"
          value="0.4"
          icon={Gauge}
          color="purple"
        />
      </div>
    </div>
  );
};

export default RoutingSimulation;
