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
import {
  Brain,
  Target,
  Zap,
  Cpu,
  Crown,
  ChevronRight,
  Database,
} from 'lucide-react';
import { energyData } from '../data/pipelineData';
import { KpiCard, SectionHeader, ChartCard } from '../components/shared';
import { useTheme } from '../context/ThemeContext';

/* ─── custom tooltip ─── */
function VoltageTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { node, voltage } = payload[0].payload;
  return (
    <div className="custom-tooltip">
      <p className="text-sm font-semibold text-surface-900 dark:text-white">
        Node {node}: {voltage}V
      </p>
    </div>
  );
}

/* ─── main page ─── */
export default function EnergyForecast() {
  const { dark } = useTheme();

  const avgVoltage =
    energyData.voltageForecasts.reduce((s, d) => s + d.voltage, 0) /
    energyData.voltageForecasts.length;

  const rankColors = {
    1: { bg: '#f59e0b', text: '#fff' },
    2: { bg: '#94a3b8', text: '#fff' },
    3: { bg: '#d97706', text: '#fff' },
    4: { bg: '#3b82f6', text: '#fff' },
    5: { bg: '#3b82f6', text: '#fff' },
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      {/* ── Page header ── */}
      <SectionHeader
        title="Energy Forecast & Cluster‑Head Selection"
        subtitle="LSTM voltage prediction across 57 IBRL sensor nodes"
        icon={Zap}
      />

      {/* ── KPI row ── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Model Type"
          value="LSTM"
          subtitle="Recurrent Neural Network"
          icon={Brain}
          color="blue"
          delay={0}
        />
        <KpiCard
          title="Val MSE"
          value="3.94×10⁻⁶"
          subtitle="Mean Squared Error"
          icon={Target}
          color="green"
          delay={1}
        />
        <KpiCard
          title="Avg Forecast"
          value="0.220 mJ"
          subtitle="Per‑node energy"
          icon={Zap}
          color="amber"
          delay={2}
        />
        <KpiCard
          title="Nodes Count"
          value="57"
          subtitle="IBRL sensor nodes"
          icon={Cpu}
          color="purple"
          delay={3}
        />
      </div>

      {/* ── Voltage forecast chart ── */}
      <ChartCard
        title="Voltage Forecast Across Nodes"
        subtitle="LSTM predicted voltage (V) per node — blue line with gradient fill"
      >
        <ResponsiveContainer width="100%" height={380}>
          <AreaChart
            data={energyData.voltageForecasts}
            margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="voltGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid
              strokeDasharray="3 3"
              stroke={dark ? '#3f3f46' : '#e4e4e7'}
            />

            <XAxis
              dataKey="node"
              tick={{ fill: dark ? '#a1a1aa' : '#71717a', fontSize: 11 }}
              axisLine={{ stroke: dark ? '#3f3f46' : '#e4e4e7' }}
              tickLine={false}
              label={{
                value: 'Node ID',
                position: 'insideBottomRight',
                offset: -5,
                fill: dark ? '#a1a1aa' : '#71717a',
                fontSize: 12,
              }}
            />

            <YAxis
              tick={{ fill: dark ? '#a1a1aa' : '#71717a', fontSize: 11 }}
              axisLine={{ stroke: dark ? '#3f3f46' : '#e4e4e7' }}
              tickLine={false}
              domain={['auto', 'auto']}
              label={{
                value: 'Voltage (V)',
                angle: -90,
                position: 'insideLeft',
                fill: dark ? '#a1a1aa' : '#71717a',
                fontSize: 12,
              }}
            />

            <Tooltip content={<VoltageTooltip />} />

            <ReferenceLine
              y={avgVoltage}
              stroke={dark ? '#a1a1aa' : '#71717a'}
              strokeDasharray="4 4"
              label={{
                value: `Avg ${avgVoltage.toFixed(3)}V`,
                position: 'right',
                fill: dark ? '#a1a1aa' : '#71717a',
                fontSize: 11,
              }}
            />

            <Area
              type="monotone"
              dataKey="voltage"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#voltGrad)"
              activeDot={{ r: 6, strokeWidth: 2, stroke: '#fff' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* ── Top 5 Cluster‑Head Candidates ── */}
      <ChartCard
        title="Top 5 Cluster‑Head Candidates"
        subtitle={`XGBoost classifier — F1 = ${energyData.clusterHeads.f1} · AUC = ${energyData.clusterHeads.auc}`}
      >
        <ul className="divide-y divide-surface-100 dark:divide-surface-700/50">
          {energyData.clusterHeads.top5.map((item) => {
            const rc = rankColors[item.rank];
            return (
              <li
                key={item.rank}
                className="flex items-center gap-4 py-3 transition-colors duration-200 hover:bg-surface-50 dark:hover:bg-surface-700/30 px-2 rounded-lg"
              >
                {/* rank badge */}
                <span
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                  style={{ background: rc.bg, color: rc.text }}
                >
                  #{item.rank}
                </span>

                {/* node id */}
                <span className="flex-1 font-mono text-sm font-semibold text-surface-900 dark:text-white">
                  {item.id}
                </span>

                {/* trailing icon */}
                <ChevronRight
                  size={16}
                  className="text-surface-400 dark:text-surface-500"
                />
              </li>
            );
          })}
        </ul>
      </ChartCard>

      {/* ── Footer credit ── */}
      <div className="flex items-center justify-center gap-2 pb-4 text-xs text-surface-400 dark:text-surface-500">
        <Database size={12} />
        <span>
          Data source: Intel Berkeley Research Lab (IBRL)
        </span>
      </div>
    </div>
  );
}
