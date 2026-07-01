/* ──────────────────────────────────────────────
   All hardcoded pipeline data for the WSN AI
   Security Pipeline dashboard.
   ────────────────────────────────────────────── */

export const COLORS = {
  blue:   '#2a78d6',
  red:    '#e34948',
  green:  '#1baf7a',
  amber:  '#eda100',
  purple: '#4a3aa7',
};

/* ── Page 1 ── */
export const networkData = {
  totalNodes: 374661,
  attackedNodes: 34595,
  normalNodes: 340066,
  attackedPercent: 9.23,
  classifierF1: 0.9365,
  attackTypes: [
    { name: 'Normal',    value: 340066, color: COLORS.blue   },
    { name: 'Grayhole',  value: 14596,  color: COLORS.amber  },
    { name: 'Blackhole', value: 10049,  color: COLORS.red    },
    { name: 'TDMA',      value: 6638,   color: COLORS.purple },
    { name: 'Flooding',  value: 3312,   color: COLORS.green  },
  ],
};

export const trustThresholdRanges = [
  { min: 0.10, max: 0.34, flagged: 40593, pct: 10.83 },
  { min: 0.35, max: 0.41, flagged: 38659, pct: 10.32 },
  { min: 0.42, max: 0.70, flagged: 38111, pct: 10.17 },
  { min: 0.71, max: 0.90, flagged: 12000, pct: 3.20  },
];

/* ── Page 2 ── */
export const attackDetection = {
  isolationForest: {
    name: 'Isolation Forest',
    label: 'Unsupervised baseline',
    precision: 0.3125, recall: 0.3120, f1: 0.3123,
    perType: [
      { type: 'Blackhole', rate: 24.7 },
      { type: 'Flooding',  rate: 81.4 },
      { type: 'Grayhole',  rate: 16.2 },
      { type: 'TDMA',      rate: 49.1 },
    ],
  },
  xgboost: {
    name: 'XGBoost',
    label: 'Leakage-free evaluation',
    precision: 0.8945, recall: 0.9827, f1: 0.9365,
    testNodes: 74933,
    perType: [
      { type: 'Blackhole', rate: 100  },
      { type: 'Flooding',  rate: 100  },
      { type: 'Grayhole',  rate: 100  },
      { type: 'TDMA',      rate: 91.3 },
    ],
  },
  confusionMatrix: { tp: 6799, fp: 802, tn: 67212, fn: 120 },
};

/* ── Page 3 ── */
export const routingData = {
  baseline:  { routes: 200, compromised: 23, compromisedCount: 46, avgHops: 4.21 },
  trustAware:{ routes: 200, compromised: 0,  compromisedCount: 0,  avgHops: 4.22, excludedNodes: 45, excludedPct: 9 },
  improvement: { pctPoints: 23, hopOverhead: 0.01 },
  networkNodes: 500,
  networkEdges: 7703,
  sampleRoutes: [
    { id: 0,   path: [277317,58485,180331,28401,34701,47662,280043,138403], hops: 7, safe: true },
    { id: 6,   path: [87194,81516,354005],                                  hops: 2, safe: true },
    { id: 12,  path: [350152,16829],                                         hops: 1, safe: true },
    { id: 54,  path: [104286,24702,189600,155560,276653,74905,354785,343638,97425], hops: 8, safe: true },
    { id: 186, path: [35631,328962,219949,94036,290414,242357,29327,224231,298673,81158], hops: 9, safe: true },
  ],
};

/* ── Page 4 ── */
export const energyData = {
  model: 'LSTM',
  valMSE: 3.94e-6,
  avgForecast: 0.220,
  nodesCount: 57,
  dataSource: 'Intel IBRL (real sensors)',
  voltageForecasts: [
    {node:1,voltage:2.009},{node:2,voltage:1.968},{node:3,voltage:2.077},{node:4,voltage:2.078},
    {node:6,voltage:1.972},{node:7,voltage:2.055},{node:8,voltage:2.113},{node:9,voltage:2.151},
    {node:10,voltage:1.977},{node:11,voltage:1.974},{node:12,voltage:2.123},{node:13,voltage:2.017},
    {node:14,voltage:2.064},{node:15,voltage:2.086},{node:16,voltage:2.141},{node:17,voltage:2.052},
    {node:18,voltage:2.010},{node:19,voltage:2.038},{node:20,voltage:2.020},{node:21,voltage:2.059},
    {node:22,voltage:2.073},{node:23,voltage:1.939},{node:24,voltage:2.012},{node:25,voltage:1.956},
    {node:26,voltage:2.003},{node:27,voltage:2.022},{node:29,voltage:2.035},{node:30,voltage:2.042},
    {node:31,voltage:2.001},{node:32,voltage:2.141},{node:33,voltage:2.094},{node:34,voltage:1.989},
    {node:35,voltage:2.041},{node:36,voltage:2.011},{node:37,voltage:2.009},{node:38,voltage:2.017},
    {node:39,voltage:2.050},{node:40,voltage:2.011},{node:41,voltage:2.040},{node:42,voltage:1.998},
    {node:43,voltage:2.004},{node:44,voltage:2.056},{node:45,voltage:2.263},{node:46,voltage:1.967},
    {node:47,voltage:2.060},{node:48,voltage:2.107},{node:49,voltage:1.993},{node:50,voltage:2.545},
    {node:51,voltage:2.031},{node:52,voltage:1.938},{node:53,voltage:2.030},{node:54,voltage:1.985},
    {node:55,voltage:2.676},{node:56,voltage:2.807},{node:58,voltage:2.568},
  ],
  outlierNodes: [50, 55, 56, 58],
  clusterHeads: {
    model: 'XGBoost', f1: 0.9988, auc: 0.9999,
    top5: [
      { rank: 1, id: 'node_313045' },
      { rank: 2, id: 'node_313043' },
      { rank: 3, id: 'node_313023' },
      { rank: 4, id: 'node_313009' },
      { rank: 5, id: 'node_314090' },
    ],
  },
};

/* ── Page 5 ── */
export const pipelineReport = {
  llmModel: 'qwen2:1.5b',
  flaggedNodes: 40593,
  avgTrustScore: 0.7484,
  trustThreshold: 0.40,
  healthReport:
    'Network health analysis indicates trust scores averaging 0.7484 with 10.83% of nodes flagged as anomalous by the supervised classifier (F1=0.94). The current trust threshold of 0.4 flags nearly all suspicious nodes. Recommendation: consider raising the threshold to 0.5 to reduce false positives while maintaining security posture.',
  attackAlert: {
    title: 'Active Threat Detected',
    description: 'Node with high anomaly score and low trust score detected.',
    actions: [
      { id: 1, text: 'Investigate flagged nodes immediately' },
      { id: 2, text: 'Monitor additional nodes and maintain proactive security posture' },
    ],
  },
  adaptivePolicy: [
    { title: 'Routing Changes', desc: 'Prioritize nodes with lower trust scores to reduce attack impact' },
    { title: 'Trust Thresholds', desc: 'Raise detection threshold from 0.4 to 0.5–0.6 to reduce false positives' },
    { title: 'Duty Cycling', desc: 'Rotate high-energy nodes out periodically to reduce consumption' },
    { title: 'Anomaly Detection', desc: 'Enhance algorithms with historical training data and ML techniques' },
    { title: 'Performance Monitoring', desc: 'Add continuous tracking of energy and anomaly rates' },
    { title: 'Regular Updates', desc: 'Update routing policies and thresholds to reflect new threat conditions' },
  ],
};

export const tickerText =
  '🔴 Node 373986 flagged — anomaly score 0.91 ● Trust score 0.31 — below threshold ● XGBoost classifier active — F1 0.9365 ● 10.83% nodes anomalous ● 0% compromised routes after trust-aware routing ● LSTM energy forecast MSE 3.94×10⁻⁶ ● Cluster head node_313045 selected ● 374,661 nodes monitored ●';
