import { useRef, useState } from 'react';
import { useTooltip } from '../../hooks/useExpandable.js';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts';
import { useChartColors } from '../../hooks/useChartColors.js';

// Reps buckets: ≤2 (heavy/intense) → 3 → 4 → ≥5 (volume)
const REPS_BUCKETS = [
  { maxReps: 2, r: 9,  color: '#6366f1', opacity: 0.90 }, // indigo  — very heavy
  { maxReps: 3, r: 11, color: '#0891b2', opacity: 0.90 }, // cyan    — heavy
  { maxReps: 4, r: 13, color: '#10b981', opacity: 0.90 }, // emerald — moderate
  { maxReps: Infinity, r: 15, color: '#f59e0b', opacity: 0.90 }, // amber — volume
];

function formatDate(dateStr) {
  if (!dateStr) return '';
  const [, mm, dd] = dateStr.split('T')[0].split('-');
  return `${dd}.${mm}`;
}


export default function E1rmChart({ sessions, metricsMap }) {
  const colors = useChartColors();
  const [tooltip, openTooltip, chartRef] = useTooltip('chart-e1rm');
  const [hoveredDate, setHoveredDate] = useState(null);

  function repsBucket(reps) {
    if (reps == null) return { r: 5, color: colors.textMuted, opacity: 0.4 };
    return REPS_BUCKETS.find(b => reps <= b.maxReps);
  }

  function ReadinessDot(props) {
    const { cx, cy, payload } = props;
    const { r, color, opacity } = repsBucket(payload.topSetReps);
    const isActive = tooltip?.data.date === payload.date;
    const isHovered = hoveredDate === payload.date;
    const hasAny = tooltip != null;
    return (
      <circle
        cx={cx}
        cy={cy}
        r={isActive ? r + 2 : isHovered ? r + 1 : r}
        fill={color}
        fillOpacity={isActive ? 1 : hasAny ? opacity * 0.4 : opacity}
        stroke={isActive || isHovered ? color : colors.bgApp}
        strokeWidth={isActive ? 3 : isHovered ? 2 : 1.5}
        strokeOpacity={isActive ? 0.4 : isHovered ? 0.6 : 1}
        style={{ cursor: 'pointer' }}
        onMouseEnter={() => setHoveredDate(payload.date)}
        onMouseLeave={() => setHoveredDate(null)}
        onClick={() => {
          if (!chartRef.current) return;
          const rect = chartRef.current.getBoundingClientRect();
          const svgRect = chartRef.current.querySelector('svg')?.getBoundingClientRect();
          if (!svgRect) return;
          const x = svgRect.left - rect.left + cx;
          const y = svgRect.top - rect.top + cy;
          openTooltip(tooltip?.data.date === payload.date ? null : { x, y, data: payload });
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
                onClick={() => openTooltip(null)}
              >
                <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>e1RM</div>
                <div style={{ fontWeight: 600 }}>{tooltip.data.e1rmKg}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 4 }}>top set</div>
                <div style={{ fontWeight: 600 }}>{tooltip.data.topSetLoadKg}×{tooltip.data.topSetReps}</div>
              </div>
            )}
          </div>
          <div className="chart-legend">
            {REPS_BUCKETS.map((b, i) => (
              <span key={i} className="chart-legend-item">
                <svg width="10" height="10" style={{ flexShrink: 0 }}>
                  <circle cx="5" cy="5" r="5" fill={b.color} />
                </svg>
                {b.maxReps === Infinity ? '5+ reps' : `${i === 0 ? '1–' : ''}${b.maxReps} rep${b.maxReps > 1 ? 's' : ''}`}
              </span>
            ))}
          </div>
        </>
      ) : (
        <div className="chart-empty">No strength data for this phase</div>
      )}
    </div>
  );
}
