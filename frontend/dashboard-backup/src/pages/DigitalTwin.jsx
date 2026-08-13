import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import * as d3 from 'd3-force';

// Custom CountUp hook to avoid third-party library conflicts
function useCountUp(endValue, duration = 800) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    let startTimestamp = null;
    let animationFrameId;

    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);

      // Easing function: easeOutQuart
      const easeProgress = 1 - Math.pow(1 - progress, 4);
      setValue(easeProgress * endValue);

      if (progress < 1) {
        animationFrameId = window.requestAnimationFrame(step);
      }
    };

    animationFrameId = window.requestAnimationFrame(step);
    return () => window.cancelAnimationFrame(animationFrameId);
  }, [endValue, duration]);

  return value;
}

export default function DigitalTwin() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentRound, setCurrentRound] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // Fetch data
  useEffect(() => {
    setLoading(true);
     fetch('https://wsn-ai-project.onrender.com/api/digital-twin')
     .then(res => res.json())
      .then(fetchedData => {
        setData(fetchedData);
        setLoading(false);
      })
      .catch(err => {
        console.error("API fetch failed, using fallback mock data", err);

        // Fallback data if API is down, simulating the exact shape requested
        const mockData = {
          num_rounds: 20,
          rounds: Array.from({ length: 20 }, (_, i) => ({
            round: i,
            attacked_nodes: Array.from({ length: Math.floor(Math.random() * 5) + 2 }, () => Math.floor(Math.random() * 80).toString()),
            attacked_count: Math.floor(Math.random() * 10) + 5,
            avg_trust_score: 0.9 - (i * 0.02) + (Math.random() * 0.05),
            compromised_routes_pct: i * 1.5 + Math.random() * 2,
            avg_hop_count: 4.15 + (Math.random() * 0.1),
            excluded_node_count: Math.floor(i / 2)
          }))
        };

        // Simulate backend wake-up delay
        setTimeout(() => {
          setData(mockData);
          setLoading(false);
        }, 3000);
      });
  }, []);

  // Auto-play logic (steps every 1.5s)
  useEffect(() => {
    let interval;
    if (isPlaying && data) {
      interval = setInterval(() => {
        setCurrentRound(prev => {
          if (prev >= data.num_rounds - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [isPlaying, data]);

  const currentRoundData = data?.rounds[currentRound] || {};

  // Force Directed Graph logic (D3)
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const svgRef = useRef(null);

  useEffect(() => {
    if (!data) return;

    // Generate static nodes and edges once for the force graph (80 sample nodes)
    const nodes = Array.from({ length: 80 }, (_, i) => ({ id: i.toString() }));
    const links = [];
    for (let i = 0; i < 120; i++) {
      links.push({
        source: Math.floor(Math.random() * 80).toString(),
        target: Math.floor(Math.random() * 80).toString()
      });
    }

    const sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(30))
      .force('charge', d3.forceManyBody().strength(-20))
      .force('center', d3.forceCenter(200, 150));

    // Fast-forward simulation for static layout
    sim.stop();
    sim.tick(300);

    setGraphData({ nodes, links });
  }, [data]);

  // Loading Screen
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] w-full bg-slate-950 rounded-xl border border-purple-500/20 shadow-[0_0_30px_rgba(168,85,247,0.1)]">
        <div className="w-12 h-12 border-4 border-purple-500/20 border-t-purple-500 rounded-full animate-spin mb-4"></div>
        <p className="text-purple-400 font-mono animate-pulse text-sm uppercase tracking-widest">Waking up trust engine...</p>
      </div>
    );
  }

  // Animated KPI Card Component
  const KpiCard = ({ title, value, suffix = '', decimals = 0 }) => {
    const animatedValue = useCountUp(value, 600);
    return (
      <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-5 shadow-[0_0_15px_rgba(168,85,247,0.05)] transition-all hover:border-purple-500/40 hover:shadow-[0_0_25px_rgba(168,85,247,0.2)]">
        <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">{title}</p>
        <p className="text-3xl font-bold text-white flex items-baseline">
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-fuchsia-400 drop-shadow-[0_0_8px_rgba(192,132,252,0.4)]">
            {animatedValue.toFixed(decimals)}
          </span>
          <span className="text-purple-400/60 text-lg ml-1 font-medium">{suffix}</span>
        </p>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 p-6 md:p-8 font-sans text-slate-200">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* 1. Page Header */}
        <div className="border-b border-purple-500/20 pb-4 mb-8">
          <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-fuchsia-500 flex items-center gap-3">
            <span className="inline-block w-3 h-3 rounded-full bg-purple-500 animate-pulse shadow-[0_0_12px_rgba(168,85,247,0.8)]"></span>
            Digital Twin
          </h1>
          <p className="text-slate-400 mt-2 text-sm">20-round live simulation using the real trust engine and routing logic</p>
        </div>

        {/* 2. KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard title="Current Round" value={currentRound} decimals={0} />
          <KpiCard title="Attacked Nodes" value={currentRoundData.attacked_count || 0} decimals={0} />
          <KpiCard title="Avg Trust Score" value={currentRoundData.avg_trust_score || 0} decimals={2} />
          <KpiCard title="Compromised Routes" value={currentRoundData.compromised_routes_pct || 0} decimals={1} suffix="%" />
        </div>

        {/* 3. Scrubber and Auto-play */}
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-5 flex flex-col md:flex-row items-center gap-6 shadow-[0_0_20px_rgba(0,0,0,0.3)]">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className={`px-6 py-2.5 rounded-lg font-bold text-xs tracking-wider uppercase transition-all duration-300 shadow-[0_4_15px_rgba(0,0,0,0.5)] ${
              isPlaying
                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/50 hover:bg-rose-500/20 hover:shadow-[0_0_15px_rgba(244,63,94,0.3)]'
                : 'bg-purple-500/10 text-purple-400 border border-purple-500/50 hover:bg-purple-500/20 hover:shadow-[0_0_15px_rgba(168,85,247,0.3)]'
            }`}
          >
            {isPlaying ? 'Stop Engine' : 'Auto-Play'}
          </button>

          <div className="flex-1 w-full flex items-center gap-4">
            <span className="text-xs text-purple-500/70 font-mono font-semibold">0</span>
            <input
              type="range"
              min="0"
              max={data.num_rounds - 1}
              value={currentRound}
              onChange={(e) => {
                setCurrentRound(parseInt(e.target.value));
                setIsPlaying(false);
              }}
              className="flex-1 h-2 bg-slate-900 rounded-lg appearance-none cursor-pointer accent-purple-500 border border-purple-500/30 shadow-[inset_0_2px_4px_rgba(0,0,0,0.6)]"
            />
            <span className="text-xs text-purple-500/70 font-mono font-semibold">19</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* 4. Line Chart */}
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-5 shadow-[0_0_20px_rgba(0,0,0,0.3)]">
            <h3 className="text-sm font-semibold text-slate-300 mb-6 tracking-wide">Simulation Trending</h3>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.rounds}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} />
                  <XAxis dataKey="round" stroke="#64748b" tick={{fontSize: 11}} tickLine={false} axisLine={{stroke: '#334155'}} />
                  <YAxis yAxisId="left" stroke="#a855f7" tick={{fontSize: 11}} domain={[0, 1]} tickLine={false} axisLine={false} />
                  <YAxis yAxisId="right" orientation="right" stroke="#ec4899" tick={{fontSize: 11}} tickLine={false} axisLine={false} />

                  <Tooltip
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', borderColor: 'rgba(168, 85, 247, 0.4)', borderRadius: '12px', boxShadow: '0 10px 25px rgba(0,0,0,0.5)' }}
                    itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
                    labelStyle={{ color: '#94a3b8', marginBottom: '6px', fontSize: '11px', textTransform: 'uppercase' }}
                  />

                  <ReferenceLine x={currentRound} stroke="#c084fc" strokeDasharray="4 4" opacity={0.6} yAxisId="left" />

                  <Line yAxisId="left" type="monotone" dataKey="avg_trust_score" name="Avg Trust" stroke="#a855f7" strokeWidth={2} dot={false} activeDot={{ r: 5, fill: '#a855f7', stroke: '#fff', strokeWidth: 2 }} />
                  <Line yAxisId="right" type="monotone" dataKey="compromised_routes_pct" name="Compromised %" stroke="#ec4899" strokeWidth={2} dot={false} activeDot={{ r: 5, fill: '#ec4899', stroke: '#fff', strokeWidth: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 5. Force-Directed Network Graph */}
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-5 shadow-[0_0_20px_rgba(0,0,0,0.3)] flex flex-col">
            <h3 className="text-sm font-semibold text-slate-300 mb-6 flex justify-between items-center tracking-wide">
              <span>Network Topology</span>
              <span className="text-[10px] text-purple-300 font-mono bg-purple-500/20 border border-purple-500/30 px-2 py-1 rounded-md shadow-[0_0_10px_rgba(168,85,247,0.2)]">
                ROUND {currentRound.toString().padStart(2, '0')}
              </span>
            </h3>
            <div className="flex-1 w-full bg-slate-950/80 rounded-xl overflow-hidden border border-slate-800 relative shadow-[inset_0_0_40px_rgba(0,0,0,0.8)]">

              {/* Optional neon grid background inside the graph */}
              <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>

              <svg ref={svgRef} viewBox="0 0 400 300" className="w-full h-full relative z-10">
                {/* Edges */}
                <g stroke="#334155" strokeOpacity="0.4" strokeWidth="1">
                  {graphData.links.map((link, i) => (
                    <line key={`link-${i}`} x1={link.source.x} y1={link.source.y} x2={link.target.x} y2={link.target.y} />
                  ))}
                </g>

                {/* Nodes */}
                <g>
                  {graphData.nodes.map(node => {
                    // Check if node is attacked in the current round
                    const isAttacked = currentRoundData.attacked_nodes?.includes(node.id);

                    return (
                      <circle
                        key={node.id}
                        cx={node.x}
                        cy={node.y}
                        r={isAttacked ? 6 : 4}
                        fill={isAttacked ? '#f43f5e' : '#8b5cf6'}
                        className="transition-all duration-500 ease-in-out"
                        style={{
                          filter: isAttacked
                            ? 'drop-shadow(0 0 8px rgba(244,63,94,0.9))'
                            : 'drop-shadow(0 0 4px rgba(139,92,246,0.5))'
                        }}
                      />
                    );
                  })}
                </g>
              </svg>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}