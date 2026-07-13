import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/* ─── colour palette ─── */
const ATTACK_PALETTE = {
  Blackhole: { color: '#ff3860', glow: 'rgba(255,56,96,0.5)', bg: 'rgba(255,56,96,0.08)' },
  Grayhole:  { color: '#ffb020', glow: 'rgba(255,176,32,0.5)', bg: 'rgba(255,176,32,0.08)' },
  TDMA:      { color: '#00f3ff', glow: 'rgba(0,243,255,0.5)',  bg: 'rgba(0,243,255,0.08)' },
  Flooding:  { color: '#b026ff', glow: 'rgba(176,38,255,0.5)', bg: 'rgba(176,38,255,0.08)' },
  Normal:    { color: '#39ff14', glow: 'rgba(57,255,20,0.5)',  bg: 'rgba(57,255,20,0.08)' },
};
const fallback = { color: '#a855f7', glow: 'rgba(168,85,247,0.5)', bg: 'rgba(168,85,247,0.08)' };
const getPalette = (label) => ATTACK_PALETTE[label] || fallback;

/* ─── Particle Canvas ─── */
function ParticleField() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animId;
    let particles = [];
    const resize = () => { canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight; };
    resize();
    window.addEventListener('resize', resize);

    for (let i = 0; i < 60; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        r: Math.random() * 2 + 0.5,
        color: ['#ff00ff', '#00f3ff', '#b026ff', '#39ff14'][Math.floor(Math.random() * 4)],
      });
    }
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((p) => {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.shadowBlur = 12;
        ctx.shadowColor = p.color;
        ctx.fill();
      });
      // connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(0,243,255,${0.08 * (1 - dist / 120)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      animId = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(animId); window.removeEventListener('resize', resize); };
  }, []);
  return <canvas ref={canvasRef} className="fb-particle-canvas" />;
}

/* ─── Animated Progress Bar ─── */
function AnimatedBar({ from, to, palette, delay = 0 }) {
  const max = Math.max(from, to, 1);
  const fromPct = (from / max) * 100;
  const toPct = (to / max) * 100;
  return (
    <div className="fb-bar-track">
      <motion.div
        className="fb-bar-current"
        initial={{ width: 0 }}
        animate={{ width: `${fromPct}%` }}
        transition={{ duration: 0.8, delay: delay + 0.2, ease: 'easeOut' }}
        style={{ background: `${palette.color}40` }}
      />
      <motion.div
        className="fb-bar-recommended"
        initial={{ width: 0 }}
        animate={{ width: `${toPct}%` }}
        transition={{ duration: 1.0, delay: delay + 0.5, ease: [0.22, 1, 0.36, 1] }}
        style={{
          background: `linear-gradient(90deg, ${palette.color}, ${palette.color}cc)`,
          boxShadow: `0 0 14px ${palette.glow}, 0 0 4px ${palette.glow}`,
        }}
      />
    </div>
  );
}

/* ─── Recommendation Card Row ─── */
function RecommendationRow({ label, current, recommended, extra, index }) {
  const palette = getPalette(label);
  const up = recommended > current;
  const diff = Math.abs(recommended - current);

  return (
    <motion.div
      className="fb-rec-row"
      initial={{ opacity: 0, x: -30 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ scale: 1.015, x: 6 }}
      style={{ borderLeft: `3px solid ${palette.color}` }}
    >
      <div className="fb-rec-header">
        <div className="fb-rec-label-group">
          <motion.span
            className="fb-rec-dot"
            style={{ backgroundColor: palette.color, boxShadow: `0 0 10px ${palette.glow}` }}
            animate={{ scale: [1, 1.3, 1], opacity: [1, 0.7, 1] }}
            transition={{ repeat: Infinity, duration: 2, delay: index * 0.3 }}
          />
          <span className="fb-rec-label">{label}</span>
          {extra && <span className="fb-rec-extra">{extra}</span>}
        </div>
        <div className="fb-rec-values">
          <span className="fb-rec-current">{typeof current === 'number' ? current.toFixed(4) : current}</span>
          <motion.span
            className="fb-rec-arrow"
            animate={{ x: [0, 6, 0] }}
            transition={{ repeat: Infinity, duration: 1.5, ease: 'easeInOut' }}
          >
            →
          </motion.span>
          <span className="fb-rec-recommended" style={{ color: palette.color, textShadow: `0 0 8px ${palette.glow}` }}>
            {typeof recommended === 'number' ? recommended.toFixed(4) : recommended}
          </span>
          <span className={`fb-rec-delta ${up ? 'fb-delta-up' : 'fb-delta-down'}`}>
            {up ? '▲' : '▼'} {diff.toFixed(4)}
          </span>
        </div>
      </div>
      <AnimatedBar from={current} to={recommended} palette={palette} delay={index * 0.1} />
    </motion.div>
  );
}

/* ─── Flowing Loop Visualization ─── */
function FeedbackFlowViz() {
  const steps = [
    { icon: '🛡️', label: 'Detection', sub: 'Classify threats' },
    { icon: '🔗', label: 'Routing', sub: 'Path optimization' },
    { icon: '🧬', label: 'Digital Twin', sub: 'Simulation mirror' },
    { icon: '🔄', label: 'Feedback', sub: 'Parameter tuning' },
  ];
  return (
    <div className="fb-flow-container">
      {steps.map((step, i) => (
        <React.Fragment key={step.label}>
          <motion.div
            className="fb-flow-node"
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.8 + i * 0.15, type: 'spring', stiffness: 200 }}
            whileHover={{ scale: 1.12, y: -4 }}
          >
            <motion.div
              className="fb-flow-icon"
              animate={{ rotate: [0, 5, -5, 0] }}
              transition={{ repeat: Infinity, duration: 3, delay: i * 0.5 }}
            >
              {step.icon}
            </motion.div>
            <span className="fb-flow-label">{step.label}</span>
            <span className="fb-flow-sub">{step.sub}</span>
          </motion.div>
          {i < steps.length - 1 && (
            <motion.div
              className="fb-flow-connector"
              initial={{ opacity: 0, scaleX: 0 }}
              animate={{ opacity: 1, scaleX: 1 }}
              transition={{ duration: 0.5, delay: 1.0 + i * 0.15 }}
            >
              <motion.span
                className="fb-flow-pulse"
                animate={{ x: [0, 30, 0], opacity: [0.3, 1, 0.3] }}
                transition={{ repeat: Infinity, duration: 1.5, delay: i * 0.3 }}
              >
                ⟩⟩
              </motion.span>
            </motion.div>
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

/* ─── Hero KPI Card ─── */
function HeroKPI({ value, label, icon, color, delay }) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let start = 0;
    const end = typeof value === 'number' ? value : parseInt(value) || 0;
    if (end === 0) { setCount(value); return; }
    const duration = 1500;
    const stepTime = duration / end;
    const timer = setInterval(() => {
      start += 1;
      setCount(start);
      if (start >= end) clearInterval(timer);
    }, stepTime);
    return () => clearInterval(timer);
  }, [value]);

  return (
    <motion.div
      className="fb-hero-kpi"
      initial={{ opacity: 0, y: 30, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.6, delay, type: 'spring' }}
      whileHover={{ scale: 1.05, y: -3 }}
      style={{
        borderColor: `${color}60`,
        boxShadow: `inset 0 0 25px ${color}15, 0 0 20px ${color}25`,
      }}
    >
      <motion.div
        className="fb-hero-icon"
        animate={{ rotate: [0, 10, -10, 0] }}
        transition={{ repeat: Infinity, duration: 4, delay }}
      >
        {icon}
      </motion.div>
      <div className="fb-hero-value" style={{ color, textShadow: `0 0 20px ${color}80` }}>
        {count}
      </div>
      <div className="fb-hero-label">{label}</div>
    </motion.div>
  );
}

/* ─── MAIN PAGE ─── */
export default function FeedbackLoop({ data }) {
  if (!data) {
    return (
      <div className="fb-loading">
        <motion.div
          className="fb-loading-ring"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }}
        />
        <motion.p
          className="fb-loading-text"
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
        >
          Loading feedback signals...
        </motion.p>
      </div>
    );
  }

  const { detectionRateRecommendations, riskWeightRecommendations, totalCompromisedRouteInstances, note } = data;
  const detEntries = Object.entries(detectionRateRecommendations || {});
  const riskEntries = Object.entries(riskWeightRecommendations || {});

  return (
    <div className="fb-page" style={{ '--accent-color': '#f97316', '--accent-rgb': '249,115,22' }}>
      <ParticleField />

      {/* ─── Header ─── */}
      <motion.div
        className="fb-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
      >
        <div className="fb-header-left">
          <motion.span
            className="fb-header-dot"
            animate={{ scale: [1, 1.4, 1], opacity: [1, 0.6, 1] }}
            transition={{ repeat: Infinity, duration: 2 }}
          />
          <h1 className="page-title fb-title">Feedback Loop</h1>
        </div>
        <motion.div
          className="fb-header-badge"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4 }}
        >
          <span className="fb-badge-dot" />
          LIVE TELEMETRY
        </motion.div>
      </motion.div>

      <motion.p
        className="fb-subtitle"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      >
        Digital Twin observations feeding back into detection & routing behavior
      </motion.p>

      {/* ─── Flow Visualization ─── */}
      <FeedbackFlowViz />

      {/* ─── Hero KPIs ─── */}
      <div className="fb-hero-grid">
        <HeroKPI value={totalCompromisedRouteInstances} label="Compromised Routes" icon="⚠️" color="#ff3860" delay={0.3} />
        <HeroKPI value={detEntries.length} label="Attack Types Tracked" icon="🎯" color="#00f3ff" delay={0.45} />
        <HeroKPI value={riskEntries.length} label="Risk Weights Tuned" icon="⚖️" color="#b026ff" delay={0.6} />
      </div>

      {/* ─── Two-Column Cards ─── */}
      <div className="fb-cards-grid">
        {/* Detection Miss Rate */}
        <motion.div
          className="fb-card"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4 }}
        >
          <div className="fb-card-header">
            <div>
              <h3 className="dash-card-title">Detection Miss Rate</h3>
              <p className="fb-card-subtitle">Digital Twin's simulated detector — per attack type</p>
            </div>
            <motion.div
              className="fb-card-icon"
              animate={{ rotate: [0, 360] }}
              transition={{ repeat: Infinity, duration: 8, ease: 'linear' }}
            >
              🔍
            </motion.div>
          </div>
          <div className="fb-rec-list">
            {detEntries.map(([type, rec], i) => (
              <RecommendationRow
                key={type}
                label={type}
                current={rec.current_flat_rate}
                recommended={rec.recommended_new_rate}
                extra={`miss: ${rec.observed_miss_rate}`}
                index={i}
              />
            ))}
          </div>
        </motion.div>

        {/* Risk Weight */}
        <motion.div
          className="fb-card"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.55 }}
        >
          <div className="fb-card-header">
            <div>
              <h3 className="dash-card-title">Attack Risk Weight</h3>
              <p className="fb-card-subtitle">Routing cost formula — per attack type</p>
            </div>
            <motion.div
              className="fb-card-icon"
              animate={{ scale: [1, 1.15, 1] }}
              transition={{ repeat: Infinity, duration: 2 }}
            >
              ⚡
            </motion.div>
          </div>
          <div className="fb-rec-list">
            {riskEntries.map(([type, rec], i) => (
              <RecommendationRow
                key={type}
                label={type}
                current={rec.current_weight}
                recommended={rec.recommended_new_weight}
                extra={`${(rec.share_of_compromised_routes * 100).toFixed(1)}% share`}
                index={i}
              />
            ))}
          </div>
        </motion.div>
      </div>

      {/* ─── Note ─── */}
      <AnimatePresence>
        {note && (
          <motion.div
            className="fb-note"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.5, delay: 0.8 }}
          >
            <span className="fb-note-icon">ℹ️</span>
            <p>{note}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}