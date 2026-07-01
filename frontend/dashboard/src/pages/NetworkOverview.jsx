import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  Network,
  ShieldAlert,
  BarChart3,
  Target,
  Database,
  Info,
} from 'lucide-react';
import { networkData, attackDetection } from '../data/pipelineData';
import { KpiCard, SectionHeader, ChartCard } from '../components/shared';
import { useTheme } from '../context/ThemeContext';

const ATTACK_COLORS = {
  Grayhole: '#f59e0b',
  Blackhole: '#ef4444',
  TDMA: '#8b5cf6',
  Flooding: '#f97316',
};

const attackDistribution = [
  { name: 'Grayhole', value: 14596 },
  { name: 'Blackhole', value: 10049 },
  { name: 'TDMA', value: 6638 },
  { name: 'Flooding', value: 3312 },
];

const totalAttacked = attackDistribution.reduce((sum, d) => sum + d.value, 0);

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0];
    const pct = ((data.value / totalAttacked) * 100).toFixed(1);
    return (
      <div className="bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg shadow-lg px-4 py-3">
        <p className="font-semibold text-sm" style={{ color: data.payload.fill }}>
          {data.name}
        </p>
        <p className="text-zinc-600 dark:text-zinc-300 text-sm">
          {data.value.toLocaleString()} nodes ({pct}%)
        </p>
      </div>
    );
  }
  return null;
};

const NetworkOverview = () => {
  const { dark } = useTheme();
  const chartTextColor = dark ? '#a1a1aa' : '#52525b';

  const kpis = [
    {
      title: 'Total Nodes',
      value: (374661).toLocaleString(),
      icon: Network,
      color: 'blue',
    },
    {
      title: 'Attacked Nodes',
      value: (34595).toLocaleString(),
      icon: ShieldAlert,
      color: 'red',
    },
    {
      title: 'Attack Rate',
      value: '9.23%',
      icon: BarChart3,
      color: 'amber',
    },
    {
      title: 'Classifier F1',
      value: '0.9365',
      icon: Target,
      color: 'green',
    },
  ];

  return (
    <div className="gradient-mesh space-y-8">
      {/* Section Header */}
      <SectionHeader
        title="Network Overview"
        subtitle="WSN-DS dataset summary and attack distribution across 374,661 sensor nodes"
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <KpiCard
            key={kpi.title}
            title={kpi.title}
            value={kpi.value}
            icon={kpi.icon}
            color={kpi.color}
          />
        ))}
      </div>

      {/* Attack Distribution Chart + Legend */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Attack Type Distribution" subtitle="Breakdown of attacked nodes by attack category">
          <div className="flex items-center justify-center" style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={attackDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                  stroke="none"
                >
                  {attackDistribution.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={ATTACK_COLORS[entry.name]}
                    />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        {/* Legend Card */}
        <div className="glass-card p-6 flex flex-col justify-center">
          <h3 className="text-lg font-semibold text-zinc-800 dark:text-zinc-100 mb-4">
            Attack Breakdown
          </h3>
          <div className="space-y-4">
            {attackDistribution.map((entry) => {
              const pct = ((entry.value / totalAttacked) * 100).toFixed(1);
              return (
                <div key={entry.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span
                      className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: ATTACK_COLORS[entry.name] }}
                    />
                    <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                      {entry.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                      {entry.value.toLocaleString()}
                    </span>
                    <span className="text-xs text-zinc-500 dark:text-zinc-400 w-12 text-right">
                      {pct}%
                    </span>
                  </div>
                </div>
              );
            })}
            <div className="border-t border-zinc-200 dark:border-zinc-700 pt-3 flex items-center justify-between">
              <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                Total Attacked
              </span>
              <span className="text-sm font-bold text-zinc-800 dark:text-zinc-100">
                {totalAttacked.toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Dataset Info Card */}
      <div className="glass-card p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-blue-500/10 text-blue-500">
            <Database className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-zinc-800 dark:text-zinc-100 mb-2">
              About WSN-DS
            </h3>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed mb-4">
              The Wireless Sensor Network Dataset (WSN-DS) is constructed by merging 3 real WSN
              attack datasets — Blackhole, Grayhole, Flooding, and TDMA scheduling attacks —
              into a unified benchmark for intrusion detection research. Each record represents a
              sensor node observation with network features and a ground-truth label.
            </p>
            <div className="flex flex-wrap gap-3">
              <div className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-400">
                <Info className="w-3.5 h-3.5" />
                <span>3 real datasets merged</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-400">
                <Info className="w-3.5 h-3.5" />
                <span>{(374661).toLocaleString()} total node observations</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-400">
                <Info className="w-3.5 h-3.5" />
                <span>4 attack types + normal class</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NetworkOverview;
