import { useState, useRef, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts';
import { useChartColors } from '../../hooks/useChartColors.js';

// 10-color gradient: red (1) → orange → amber → yellow → lime → green (10), base is 7
const READINESS_COLORS = [
  '#ef4444', // 1 — red
  '#f97316', // 2 — orange
  '#f59e0b', // 3 — amber
  '#eab308', // 4 — yellow
  '#0891b2', // 5 — cyan (darkest)
  '#0d9488', // 6 — teal
  '#10b981', // 7 — emerald (base)
  '#22c55e', // 8 — green
  '#4ade80', // 9 — light green
  '#a3e635', // 10 — lime (lightest)
];

function formatDate(dateStr) {
  if (!dateStr) return '';
  const [, mm, dd] = dateStr.split('T')[0].split('-');
  return `${dd}.${mm}`;
}


export default function E1rmChart({ sessions, metricsMap }) {
  const colors = useChartColors();
  const [showInfo, setShowInfo] = useState(false);
  const [tooltip, setTooltip] = useState(null); // { x, y, data }
  const chartRef = useRef(null);
  const infoRef = useRef(null);

  useEffect(() => {
    function handle(e) {
      if (infoRef.current && !infoRef.current.contains(e.target)) setShowInfo(false);
    }
    if (showInfo) document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [showInfo]);

  function readinessColor(r) {
    if (r == null) return colors.readyNone;
    const idx = Math.round(Math.max(1, Math.min(10, r))) - 1;
    return READINESS_COLORS[idx];
  }

  function readinessDotProps(val) {
    if (val == null) return { r: 5, opacity: 0.5 };
    const dist = Math.abs(Math.round(Math.max(1, Math.min(10, val))) - 7);
    return {
      r: 5 + dist * 4,
      opacity: Math.min(1.0, 0.65 + dist * 0.12),
    };
  }

  function ReadinessDot(props) {
    const { cx, cy, payload } = props;
    const val = payload.eliteHrvReadiness;
    const fill = readinessColor(val);
    const { r, opacity } = readinessDotProps(val);
    return (
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill={fill}
        fillOpacity={opacity}
        stroke={colors.bgApp}
        strokeWidth={1.5}
        style={{ cursor: 'pointer' }}
        onClick={() => {
          if (!chartRef.current) return;
          const rect = chartRef.current.getBoundingClientRect();
          const svgRect = chartRef.current.querySelector('svg')?.getBoundingClientRect();
          if (!svgRect) return;
          const x = svgRect.left - rect.left + cx;
          const y = svgRect.top - rect.top + cy;
          setTooltip(prev => prev?.data.date === payload.date ? null : { x, y, data: payload });
        }}
      />
    );
  }

  const data = sessions
    .map(s => {
      const m = metricsMap[s.sessionId];
      if (!m) return null;
      return {
        date: s.sessionDate,
        e1rmKg: m.topSetE1rmKg,
        topSetLoadKg: m.topSetLoadKg,
        topSetReps: m.topSetReps,
        eliteHrvReadiness: s.eliteHrvReadiness,
      };
    })
    .filter(Boolean)
    .sort((a, b) => new Date(a.date) - new Date(b.date));

  const hasData = data.length > 0;

  return (
    <div className="chart-wrapper">
      <div className="chart-title-row">
        <span className="card-title">e1RM (kg)</span>
        <div className="info-btn-wrap" ref={infoRef}>
          <button className="info-btn" onClick={() => setShowInfo(v => !v)} aria-label="What is e1RM?">?</button>
          {showInfo && (
            <div className="info-popover">
              <p><strong>Estimated 1-rep max</strong> — a weekly strength snapshot without the risk of true max testing. Each heavy session your top set is used to project peak strength.</p>
              <p className="info-example">Example: 87.5 kg × 5 reps → e1RM <strong>100 kg</strong></p>
            </div>
          )}
        </div>
      </div>
      {hasData ? (
        <>
          <div ref={chartRef} style={{ position: 'relative' }}>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 0 }} tabIndex={-1}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatDate}
                  tick={{ fill: colors.textMuted, fontSize: 12 }}
                  axisLine={{ stroke: colors.border }}
                  tickLine={false}
                />
                <YAxis
                  domain={['dataMin - 5', 'dataMax + 5']}
                  tickFormatter={v => `${v}`}
                  tick={{ fill: colors.textMuted, fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                  width={40}
                />
                <Line
                  type="monotone"
                  dataKey="e1rmKg"
                  stroke={colors.accent}
                  strokeWidth={2}
                  dot={<ReadinessDot />}
                  activeDot={false}
                />
              </LineChart>
            </ResponsiveContainer>
            {tooltip && (
              <div
                className="chart-tooltip"
                style={{
                  position: 'absolute',
                  left: tooltip.x,
                  top: tooltip.y,
                  transform: 'translate(-50%, -110%)',
                  width: 'fit-content',
                  minWidth: 0,
                  cursor: 'pointer',
                  zIndex: 10,
                }}
                onClick={() => setTooltip(null)}
              >
                <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>e1RM</div>
                <div style={{ fontWeight: 600 }}>{tooltip.data.e1rmKg} kg</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 4 }}>top set</div>
                <div style={{ fontWeight: 600 }}>{tooltip.data.topSetLoadKg}×{tooltip.data.topSetReps}</div>
                {tooltip.data.eliteHrvReadiness != null && (
                  <>
                    <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 4 }}>readiness</div>
                    <div style={{ fontWeight: 600, color: readinessColor(tooltip.data.eliteHrvReadiness) }}>{tooltip.data.eliteHrvReadiness}</div>
                  </>
                )}
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="chart-empty">No strength data for this phase</div>
      )}
    </div>
  );
}
