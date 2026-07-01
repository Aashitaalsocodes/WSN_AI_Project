import {
  AlertTriangle,
  ShieldCheck,
  SlidersHorizontal,
  Bot,
  CheckCircle,
  FileText,
  Lightbulb,
} from 'lucide-react';
import { pipelineReport } from '../data/pipelineData';
import { KpiCard, SectionHeader, ChartCard } from '../components/shared';
import { useTheme } from '../context/ThemeContext';

export default function PipelineReport() {
  const { dark } = useTheme();

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      {/* ── Page header ── */}
      <SectionHeader
        title="LLM Pipeline Report"
        subtitle="AI‑generated network health assessment and adaptive policies"
        icon={FileText}
      />

      {/* ── KPI row ── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Flagged Nodes"
          value="10.83%"
          subtitle="Anomalous behavior detected"
          icon={AlertTriangle}
          color="red"
          delay={0}
        />
        <KpiCard
          title="Avg Trust Score"
          value="0.7484"
          subtitle="Network‑wide average"
          icon={ShieldCheck}
          color="green"
          delay={1}
        />
        <KpiCard
          title="Trust Threshold"
          value="0.4 → 0.5"
          subtitle="Recommended increase"
          icon={SlidersHorizontal}
          color="amber"
          delay={2}
        />
        <KpiCard
          title="LLM Model"
          value="qwen2:1.5b"
          subtitle="Ollama local inference"
          icon={Bot}
          color="purple"
          delay={3}
        />
      </div>

      {/* ── Health Report ── */}
      <div className="rounded-2xl border border-surface-200/50 bg-white/70 shadow-sm backdrop-blur-sm transition-all duration-300 hover:shadow-md dark:border-surface-700/50 dark:bg-surface-800/70 border-l-4 border-l-success-500 overflow-hidden">
        <div className="p-6">
          <div className="mb-3 flex items-center gap-2">
            <CheckCircle size={18} className="text-success-500" />
            <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
              Health Report
            </h3>
          </div>
          <p className="text-sm leading-relaxed text-surface-600 dark:text-surface-300">
            {pipelineReport.healthReport}
          </p>
        </div>
      </div>

      {/* ── Attack Alert ── */}
      <div className="rounded-2xl border border-surface-200/50 bg-white/70 shadow-sm backdrop-blur-sm transition-all duration-300 hover:shadow-md dark:border-surface-700/50 dark:bg-surface-800/70 border-l-4 border-l-danger-500 overflow-hidden">
        <div className="p-6">
          {/* title row with pulsing dot */}
          <div className="mb-3 flex items-center gap-2">
            <span className="pulse-red inline-block h-2.5 w-2.5 rounded-full bg-danger-500" />
            <h3 className="text-sm font-semibold text-danger-600 dark:text-danger-400">
              {pipelineReport.attackAlert.title}
            </h3>
          </div>

          {/* description */}
          <p className="mb-4 text-sm leading-relaxed text-surface-600 dark:text-surface-300">
            {pipelineReport.attackAlert.description}
          </p>

          {/* action items */}
          <div className="space-y-3">
            {pipelineReport.attackAlert.actions.map((action) => (
              <div
                key={action.id}
                className="flex items-start gap-3 rounded-xl bg-danger-50/60 p-3 dark:bg-danger-900/10"
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-danger-500 text-xs font-bold text-white">
                  {action.id}
                </span>
                <p className="text-sm text-surface-700 dark:text-surface-300">
                  {action.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Adaptive Policy Recommendations ── */}
      <div>
        <div className="mb-4 flex items-center gap-2">
          <Lightbulb size={18} className="text-primary-500" />
          <h3 className="text-lg font-bold text-surface-900 dark:text-white">
            {pipelineReport.adaptivePolicy.length} Adaptive Policy
            Recommendations
          </h3>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {pipelineReport.adaptivePolicy.map((policy, idx) => (
            <div
              key={idx}
              className="rounded-2xl border border-surface-200/50 bg-white/70 p-5 shadow-sm backdrop-blur-sm transition-all duration-300 hover:shadow-md dark:border-surface-700/50 dark:bg-surface-800/70"
            >
              <div className="mb-3 flex items-center gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-500 text-sm font-bold text-white">
                  {idx + 1}
                </span>
                <h4 className="font-bold text-surface-900 dark:text-white">
                  {policy.title}
                </h4>
              </div>
              <p className="text-sm leading-relaxed text-surface-600 dark:text-surface-300">
                {policy.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
