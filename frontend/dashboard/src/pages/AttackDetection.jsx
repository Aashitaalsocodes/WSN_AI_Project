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
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Info,
} from 'lucide-react';
import { attackDetection } from '../data/pipelineData';
import { KpiCard, SectionHeader, ChartCard } from '../components/shared';
import { useTheme } from '../context/ThemeContext';

const perTypeData = [
  { type: 'Blackhole', IF: 24.7, XGB: 100 },
  { type: 'Flooding', IF: 81.4, XGB: 100 },
  { type: 'Grayhole', IF: 16.2, XGB: 100 },
  { type: 'TDMA', IF: 49.1, XGB: 91.3 },
];

const confusionMatrix = {
  TP: 6799,
  FP: 802,
  TN: 67212,
  FN: 120,
};

const AttackDetection = () => {
  const { dark } = useTheme();
  const chartTextColor = dark ? '#a1a1aa' : '#52525b';

  return (
    <div className="gradient-mesh space-y-8">
      {/* Section Header */}
      <SectionHeader
        title="Attack Detection"
        subtitle="Comparing Isolation Forest and XGBoost classifiers for WSN intrusion detection"
      />

      {/* Model Comparison Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Isolation Forest Card */}
        <div className="glass-card p-6 border-l-4 border-red-500">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2.5 rounded-xl bg-red-500/10 text-red-500">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">
                Isolation Forest
              </h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">Unsupervised anomaly detector</p>
            </div>
          </div>
          <div className="text-center my-6">
            <p className="text-xs uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-1">
              F1 Score
            </p>
            <p className="text-5xl font-bold text-red-500">0.3123</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-3 rounded-lg bg-zinc-100 dark:bg-zinc-800/50">
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-1">Precision</p>
              <p className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">0.3125</p>
            </div>
            <div className="text-center p-3 rounded-lg bg-zinc-100 dark:bg-zinc-800/50">
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-1">Recall</p>
              <p className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">0.3120</p>
            </div>
          </div>
        </div>

        {/* XGBoost Card */}
        <div className="glass-card p-6 border-l-4 border-green-500">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2.5 rounded-xl bg-green-500/10 text-green-500">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">
                XGBoost
              </h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">Supervised gradient boosting</p>
            </div>
          </div>
          <div className="text-center my-6">
            <p className="text-xs uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-1">
              F1 Score
            </p>
            <p className="text-5xl font-bold text-green-500">0.9365</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-3 rounded-lg bg-zinc-100 dark:bg-zinc-800/50">
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-1">Precision</p>
              <p className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">0.8945</p>
            </div>
            <div className="text-center p-3 rounded-lg bg-zinc-100 dark:bg-zinc-800/50">
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-1">Recall</p>
              <p className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">0.9827</p>
            </div>
          </div>
        </div>
      </div>

      {/* Per-Type Detection Bar Chart */}
      <ChartCard
        title="Per-Type Detection Rate"
        subtitle="Detection accuracy (%) by attack type for each classifier"
      >
        <div style={{ height: 320 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={perTypeData}
              layout="vertical"
              margin={{ top: 10, right: 30, left: 60, bottom: 10 }}
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
              <Tooltip
                contentStyle={{
                  backgroundColor: dark ? '#27272a' : '#ffffff',
                  border: `1px solid ${dark ? '#3f3f46' : '#e4e4e7'}`,
                  borderRadius: '8px',
                  fontSize: '13px',
                }}
                formatter={(value) => [`${value}%`]}
              />
              <Legend
                wrapperStyle={{ fontSize: '13px', color: chartTextColor }}
              />
              <Bar
                dataKey="IF"
                name="Isolation Forest"
                fill="#ef4444"
                radius={[4, 4, 4, 4]}
                barSize={14}
              />
              <Bar
                dataKey="XGB"
                name="XGBoost"
                fill="#22c55e"
                radius={[4, 4, 4, 4]}
                barSize={14}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      {/* Confusion Matrix */}
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-zinc-800 dark:text-zinc-100 mb-1">
          XGBoost Confusion Matrix
        </h3>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
          Classification outcomes on 74,933 test nodes
        </p>

        <div className="max-w-md mx-auto">
          {/* Column Headers */}
          <div className="grid grid-cols-3 gap-2 mb-2">
            <div />
            <div className="text-center text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
              Predicted Positive
            </div>
            <div className="text-center text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
              Predicted Negative
            </div>
          </div>

          {/* Row 1: Actual Positive */}
          <div className="grid grid-cols-3 gap-2 mb-2">
            <div className="flex items-center justify-end pr-3">
              <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                Actual Positive
              </span>
            </div>
            <div className="rounded-xl bg-green-500/15 border border-green-500/30 p-4 text-center">
              <p className="text-xs text-green-600 dark:text-green-400 font-medium mb-1">TP</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                {confusionMatrix.TP.toLocaleString()}
              </p>
            </div>
            <div className="rounded-xl bg-red-500/15 border border-red-500/30 p-4 text-center">
              <p className="text-xs text-red-600 dark:text-red-400 font-medium mb-1">FN</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                {confusionMatrix.FN.toLocaleString()}
              </p>
            </div>
          </div>

          {/* Row 2: Actual Negative */}
          <div className="grid grid-cols-3 gap-2">
            <div className="flex items-center justify-end pr-3">
              <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                Actual Negative
              </span>
            </div>
            <div className="rounded-xl bg-red-500/15 border border-red-500/30 p-4 text-center">
              <p className="text-xs text-red-600 dark:text-red-400 font-medium mb-1">FP</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                {confusionMatrix.FP.toLocaleString()}
              </p>
            </div>
            <div className="rounded-xl bg-green-500/15 border border-green-500/30 p-4 text-center">
              <p className="text-xs text-green-600 dark:text-green-400 font-medium mb-1">TN</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                {confusionMatrix.TN.toLocaleString()}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="glass-card p-5 border border-blue-500/20 bg-blue-500/5">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500 mt-0.5">
            <Info className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-zinc-800 dark:text-zinc-100 mb-1">
              Leakage-Free Evaluation
            </h4>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
              All metrics are computed on a held-out test set of{' '}
              <span className="font-semibold text-zinc-800 dark:text-zinc-100">
                {(74933).toLocaleString()} test nodes
              </span>{' '}
              using stratified splitting. No data leakage exists between training and evaluation —
              the test set was never seen during model fitting, ensuring unbiased performance
              estimates.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AttackDetection;
