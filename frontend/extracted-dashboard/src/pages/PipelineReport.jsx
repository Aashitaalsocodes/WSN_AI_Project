import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactCountUp from 'react-countup';
const CountUp = ReactCountUp.default || ReactCountUp;
import {
  AlertTriangle,
  ShieldCheck,
  SlidersHorizontal,
  Bot,
  CheckCircle,
  FileText,
  Lightbulb,
  Play,
  Loader2,
} from 'lucide-react';
import { pipelineReport, COLORS } from '../data/pipelineData';
import { KpiCard, SectionHeader, ChartCard, GlassCard, Badge } from '../components/shared';
import { useTheme } from '../context/ThemeContext';

/* ─── animation variants ─── */
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.12 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 30, scale: 0.95 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      delay: i * 0.1,
      duration: 0.5,
      ease: 'easeOut',
    },
  }),
};

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

/* ─── status messages for pipeline simulation ─── */
const PIPELINE_STAGES = [
  'Running XGBoost classifier…',
  'Calculating trust scores…',
  'Querying LLM…',
];

export default function PipelineReport() {
  const { dark } = useTheme();

  /* ── pipeline simulation state ── */
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineComplete, setPipelineComplete] = useState(false);
  const [stageIndex, setStageIndex] = useState(0);

  /* ── dynamic report values (updated after pipeline run) ── */
  const [flaggedNodes, setFlaggedNodes] = useState(pipelineReport.flaggedNodes);
  const [avgTrust, setAvgTrust] = useState(pipelineReport.avgTrustScore);
  const [healthText, setHealthText] = useState(pipelineReport.healthReport);
  const [attackDesc, setAttackDesc] = useState(pipelineReport.attackAlert.description);

  /* cycle through pipeline stages while running */
  useEffect(() => {
    if (!pipelineRunning) return;
    const interval = setInterval(() => {
      setStageIndex((prev) => {
        if (prev < PIPELINE_STAGES.length - 1) return prev + 1;
        return prev;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [pipelineRunning]);

  function handleRunPipeline() {
    setPipelineRunning(true);
    setPipelineComplete(false);
    setStageIndex(0);

    setTimeout(() => {
      /* simulate slightly varied values */
      const newFlagged = pipelineReport.flaggedNodes + Math.floor((Math.random() - 0.5) * 400);
      const newTrust = +(pipelineReport.avgTrustScore + (Math.random() - 0.5) * 0.01).toFixed(4);

      setFlaggedNodes(newFlagged);
      setAvgTrust(newTrust);
      setHealthText(
        `Network health analysis indicates trust scores averaging ${newTrust} with ${((newFlagged / 374661) * 100).toFixed(2)}% of nodes flagged as anomalous by the supervised classifier (F1=0.94). The current trust threshold of ${pipelineReport.trustThreshold} flags nearly all suspicious nodes. Recommendation: consider raising the threshold to 0.5 to reduce false positives while maintaining security posture.`
      );
      setAttackDesc(
        `Node with high anomaly score and low trust score detected. ${newFlagged.toLocaleString()} nodes flagged in latest scan.`
      );

      setPipelineRunning(false);
      setPipelineComplete(true);
    }, 3000);
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      {/* ── Page header ── */}
      <SectionHeader
        title="LLM Pipeline Report"
        subtitle="AI‑generated network health assessment and adaptive policies"
        icon={FileText}
      />

      {/* ── KPI row ── */}
      <motion.div
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={fadeInUp}>
          <KpiCard
            title="Flagged Nodes"
            value={<CountUp key={flaggedNodes} end={flaggedNodes} separator="," duration={2} />}
            subtitle="Anomalous behavior detected"
            icon={AlertTriangle}
            color="red"
          />
        </motion.div>
        <motion.div variants={fadeInUp}>
          <KpiCard
            title="Avg Trust Score"
            value={<CountUp key={avgTrust} end={avgTrust} decimals={4} duration={2} />}
            subtitle="Network‑wide average"
            icon={ShieldCheck}
            color="green"
          />
        </motion.div>
        <motion.div variants={fadeInUp}>
          <KpiCard
            title="Trust Threshold"
            value={<CountUp end={pipelineReport.trustThreshold} decimals={2} duration={1.5} />}
            subtitle="Recommended: 0.5"
            icon={SlidersHorizontal}
            color="amber"
          />
        </motion.div>
        <motion.div variants={fadeInUp}>
          <KpiCard
            title="LLM Model"
            value={pipelineReport.llmModel}
            subtitle="Ollama local inference"
            icon={Bot}
            color="purple"
          />
        </motion.div>
      </motion.div>

      {/* ── Health Report ── */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.6 }}
        className="rounded-2xl border border-surface-200/50 bg-white/70 shadow-sm backdrop-blur-sm transition-all duration-300 hover:shadow-md dark:border-surface-700/50 dark:bg-surface-800/70 border-l-4 border-l-brand-blue overflow-hidden"
      >
        <div className="p-6">
          <div className="mb-3 flex items-center gap-2">
            <CheckCircle size={18} className="text-success-500" />
            <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
              Health Report
            </h3>
            {pipelineComplete && (
              <Badge color="green">Updated</Badge>
            )}
          </div>
          <AnimatePresence mode="wait">
            <motion.p
              key={healthText}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-sm leading-relaxed text-surface-600 dark:text-surface-300"
            >
              {healthText}
            </motion.p>
          </AnimatePresence>
        </div>
      </motion.div>

      {/* ── Attack Alert ── */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.6 }}
        className="rounded-2xl border border-surface-200/50 bg-white/70 shadow-sm backdrop-blur-sm transition-all duration-300 hover:shadow-md dark:border-surface-700/50 dark:bg-surface-800/70 border-l-4 border-l-danger-500 red-border-pulse overflow-hidden"
      >
        <div className="p-6">
          {/* header with badge */}
          <div className="mb-3 flex items-center gap-3">
            <Badge color="red">ALERT</Badge>
            <h3 className="text-sm font-semibold text-danger-600 dark:text-danger-400">
              {pipelineReport.attackAlert.title}
            </h3>
          </div>

          {/* description */}
          <AnimatePresence mode="wait">
            <motion.p
              key={attackDesc}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="mb-4 text-sm leading-relaxed text-surface-600 dark:text-surface-300"
            >
              {attackDesc}
            </motion.p>
          </AnimatePresence>

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
      </motion.div>

      {/* ── Adaptive Policy Recommendations ── */}
      <div>
        <div className="mb-4 flex items-center gap-2">
          <Lightbulb size={18} className="text-primary-500" />
          <h3 className="text-lg font-bold text-surface-900 dark:text-white">
            {pipelineReport.adaptivePolicy.length} Adaptive Policy Recommendations
          </h3>
        </div>

        <motion.div
          className="grid grid-cols-1 gap-4 lg:grid-cols-2"
          initial="hidden"
          animate="visible"
          variants={containerVariants}
        >
          {pipelineReport.adaptivePolicy.map((policy, idx) => (
            <motion.div
              key={idx}
              custom={idx}
              variants={cardVariants}
              whileHover={{ y: -4, transition: { duration: 0.2 } }}
              className="rounded-2xl border border-surface-200/50 bg-white/70 p-5 shadow-sm backdrop-blur-sm transition-all duration-300 hover:shadow-md dark:border-surface-700/50 dark:bg-surface-800/70"
            >
              <div className="mb-3 flex items-center gap-3">
                <motion.span
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-500 text-sm font-bold text-white shadow-sm"
                  whileHover={{ scale: 1.15 }}
                >
                  {idx + 1}
                </motion.span>
                <h4 className="font-bold text-surface-900 dark:text-white">
                  {policy.title}
                </h4>
              </div>
              <p className="text-sm leading-relaxed text-surface-600 dark:text-surface-300">
                {policy.desc}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* ── Run Pipeline Button ── */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7, duration: 0.6 }}
        className="rounded-2xl border border-surface-200/50 bg-white/70 p-6 shadow-sm backdrop-blur-sm dark:border-surface-700/50 dark:bg-surface-800/70"
      >
        <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start">
          <div className="flex-1">
            <h3 className="mb-1 text-sm font-semibold text-surface-900 dark:text-white">
              Pipeline Simulation
            </h3>
            <p className="text-xs text-surface-500 dark:text-surface-400">
              Re-run the AI pipeline to refresh health reports and attack alerts with updated analysis.
            </p>
          </div>

          <motion.button
            onClick={handleRunPipeline}
            disabled={pipelineRunning}
            whileHover={!pipelineRunning ? { scale: 1.04 } : {}}
            whileTap={!pipelineRunning ? { scale: 0.97 } : {}}
            className={`flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold text-white shadow-md transition-all ${
              pipelineRunning
                ? 'cursor-not-allowed bg-surface-400 dark:bg-surface-600'
                : 'bg-success-500 hover:bg-success-600 green-glow-pulse'
            }`}
          >
            {pipelineRunning ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Running…
              </>
            ) : (
              <>
                <Play size={16} />
                Simulate Pipeline Run
              </>
            )}
          </motion.button>
        </div>

        {/* pipeline progress */}
        <AnimatePresence>
          {pipelineRunning && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-5 overflow-hidden"
            >
              {/* progress bar */}
              <div className="mb-4 h-2 overflow-hidden rounded-full bg-surface-200 dark:bg-surface-700">
                <div
                  className="progress-animate h-full rounded-full bg-gradient-to-r from-primary-500 via-violet-500 to-success-500"
                />
              </div>

              {/* status messages */}
              <div className="space-y-2">
                {PIPELINE_STAGES.map((stage, i) => (
                  <motion.div
                    key={stage}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{
                      opacity: i <= stageIndex ? 1 : 0.3,
                      x: 0,
                    }}
                    transition={{ delay: i * 0.15, duration: 0.3 }}
                    className="flex items-center gap-2 text-sm"
                  >
                    {i < stageIndex ? (
                      <CheckCircle size={14} className="text-success-500" />
                    ) : i === stageIndex ? (
                      <Loader2 size={14} className="animate-spin text-primary-500" />
                    ) : (
                      <span className="inline-block h-3.5 w-3.5 rounded-full border border-surface-300 dark:border-surface-600" />
                    )}
                    <span
                      className={
                        i <= stageIndex
                          ? 'font-medium text-surface-900 dark:text-white'
                          : 'text-surface-400 dark:text-surface-500'
                      }
                    >
                      {stage}
                    </span>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* completion message */}
        <AnimatePresence>
          {pipelineComplete && !pipelineRunning && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-5 flex items-center gap-2 rounded-xl bg-success-50/60 p-3 dark:bg-success-900/10"
            >
              <CheckCircle size={16} className="text-success-500" />
              <span className="text-sm font-medium text-success-700 dark:text-success-400">
                Pipeline completed successfully — reports updated with new values.
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
