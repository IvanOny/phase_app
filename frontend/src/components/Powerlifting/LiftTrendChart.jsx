import { useState } from 'react';
import { useTooltip, useIsTouchDevice } from '../../hooks/useExpandable.js';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { useChartColors } from '../../hooks/useChartColors.js';

const LIFT_CONFIG = {
  squat:    { label: 'Squat',    color: '#6366f1' },
  bench:    { label: 'Bench',    color: '#0891b2' },
  deadlift: { label: 'Deadlift', color: '#10b981' },
  total:    { label: 'Total',    color: '#f59e0b' },
};

function formatDate(dateStr) {
  if (!dateStr) return '';
  const [, mm, dd] = (dateStr.split('T')[0] || dateStr).split('-');
  return `${dd}.${mm}`;
}

/**
 * Builds per-session chart data with running cumulative best per lift.
 * sessions: array from sessionsMap
 * plMetrics: result of getSessionPlMetrics — { e1rm: { squat, bench, deadlift }, confirmedMax }
 */
function buildChartData(sessions, plMetrics) {
  if (!plMetrics) return [];

  const { e1rm = {}, confirmedMax = {} } = plMetrics;
  const sorted = [...sessions].sort((a, b) => new Date(a.sessionDate) - new Date(b.sessionDate));

  // Running best per lift — used for the Total line only
  const runningBest = {
    squat:    confirmedMax.squat    || 0,
    bench:    confirmedMax.bench    || 0,
    deadlift: confirmedMax.deadlift || 0,
  };

  const points = [];
  let anySeen = false;

  for (const s of sorted) {
    const sid = String(s.sessionId);

    const sessionSquat    = e1rm.squat?.[sid]?.topSetE1rmKg    ?? null;
    const sessionBench    = e1rm.bench?.[sid]?.topSetE1rmKg    ?? null;
    const sessionDeadlift = e1rm.deadlift?.[sid]?.topSetE1rmKg ?? null;
    const anyLiftDone     = sessionSquat != null || sessionBench != null || sessionDeadlift != null;

    // Update running bests for Total
    if (sessionSquat    != null) runningBest.squat    = Math.max(runningBest.squat,    sessionSquat);
    if (sessionBench    != null) runningBest.bench    = Math.max(runningBest.bench,    sessionBench);
    if (sessionDeadlift != null) runningBest.deadlift = Math.max(runningBest.deadlift, sessionDeadlift);

    if (anyLiftDone) anySeen = true;

    // Only emit points once we have at least one lift recorded
    if (!anySeen) continue;

    const runningTotal = runningBest.squat + runningBest.bench + runningBest.deadlift;

    points.push({
      date:     s.sessionDate,
      // Individual lifts: only non-null on sessions where they were actually performed
      squat:    sessionSquat,
      bench:    sessionBench,
      deadlift: sessionDeadlift,
      // Total: running cumulative S+B+D, only shown on lift days
      total:    anyLiftDone ? (runningTotal || null) : null,
      // kept as aliases for tooltip compatibility
      _squat:    sessionSquat,
      _bench:    sessionBench,
      _deadlift: sessionDeadlift,
    });
  }

  return points;
}

export default function LiftTrendChart({ sessions, plMetrics, showTotal = true }) {
  const colors = useChartColors();
  const isTouch = useIsTouchDevice();
  const [tooltip, openTooltip, chartRef] = useTooltip('chart-pl');
  const [hoveredDate, setHoveredDate] = useState(null);

  const data = buildChartData(sessions, plMetrics);
  const hasData = data.length > 0;

  // Last index in data where each lift has a non-null value (for inline label placement)
  const lastIndexByLift = {};
  const liftsToShow = ['squat', 'bench', 'deadlift', ...(showTotal ? ['total'] : [])];
  liftsToShow.forEach(lift => {
    for (let i = data.length - 1; i >= 0; i--) {
      if (data[i][lift] != null) { lastIndexByLift[lift] = i; break; }
    }
  });

  function getDotPos(cx, cy) {
    if (!chartRef.current) return null;
    const svgRect = chartRef.current.querySelector('svg')?.getBoundingClientRect();
    const rect = chartRef.current.getBoundingClientRect();
    if (!svgRect) return null;
    return { x: svgRect.left - rect.left + cx, y: svgRect.top - rect.top + cy };
  }

  function makeDot(lift) {
    const cfg = LIFT_CONFIG[lift];
    return function Dot(props) {
      const { cx, cy, payload, index } = props;
      // Only render a dot on days where this lift was actually performed
      const hasEntry = lift === 'total'
        ? (payload._squat != null || payload._bench != null || payload._deadlift != null)
        : payload[`_${lift}`] != null;
      if (!hasEntry) return null;
      const isActive = tooltip?.data?.date === payload.date && tooltip?.lift === lift;
      const isHovered = hoveredDate === payload.date;
      const r = lift === 'total' ? 6 : 5;
      const dotR = isActive ? r + 2 : isHovered ? r + 1 : r;
      const isLast = index === lastIndexByLift[lift];

      const handlers = {
        onMouseEnter() {
          setHoveredDate(payload.date);
          if (!isTouch) {
            const pos = getDotPos(cx, cy);
            if (pos) openTooltip({ ...pos, data: payload, lift });
          }
        },
        onMouseLeave() {
          setHoveredDate(null);
          if (!isTouch) openTooltip(null);
        },
        onClick() {
          if (!isTouch) return;
          const pos = getDotPos(cx, cy);
          if (!pos) return;
          const isSame = tooltip?.data?.date === payload.date && tooltip?.lift === lift;
          openTooltip(isSame ? null : { ...pos, data: payload, lift });
        },
      };

      return (
        <g style={{ cursor: 'pointer' }} {...handlers}>
          <circle
            cx={cx} cy={cy} r={dotR}
            fill={cfg.color}
            fillOpacity={isActive ? 1 : 0.85}
            stroke={isActive || isHovered ? cfg.color : colors.bgApp}
            strokeWidth={isActive ? 3 : 1.5}
          />
          {isLast && (
            <text
              x={cx + dotR + 4}
              y={cy + 4}
              fill={cfg.color}
              fontSize={11}
              fontWeight={600}
              style={{ pointerEvents: 'none', userSelect: 'none' }}
            >
              {cfg.label}
            </text>
          )}
        </g>
      );
    };
  }

  return (
    <div className="chart-wrapper">
      <div className="chart-title-row">
        <span className="card-title">Lift Trend — e1RM (kg)</span>
      </div>
      {hasData ? (
        <>
          <div
            ref={chartRef}
            style={{ position: 'relative' }}
            onMouseLeave={() => { if (!isTouch) { setHoveredDate(null); openTooltip(null); } }}
          >
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data} margin={{ top: 8, right: 64, bottom: 24, left: 0 }}
                onMouseLeave={() => { if (!isTouch) { setHoveredDate(null); openTooltip(null); } }}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                <XAxis dataKey="date" tickFormatter={formatDate}
                  tick={{ fill: colors.textMuted, fontSize: 12 }}
                  axisLine={{ stroke: colors.border }} tickLine={false} />
                <YAxis domain={['dataMin - 10', 'dataMax + 10']}
                  tick={{ fill: colors.textMuted, fontSize: 12 }}
                  axisLine={false} tickLine={false} width={44} />
                {['squat', 'bench', 'deadlift', ...(showTotal ? ['total'] : [])].map(lift => (
                  <Line
                    key={lift}
                    type="monotone"
                    dataKey={lift}
                    stroke={LIFT_CONFIG[lift].color}
                    strokeWidth={lift === 'total' ? 2.5 : 1.8}
                    strokeDasharray={lift === 'total' ? '5 3' : undefined}
                    connectNulls
                    dot={makeDot(lift)}
                    activeDot={false}
                  />
                ))}
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
                  zIndex: 10,
                  pointerEvents: isTouch ? 'auto' : 'none',
                  minWidth: 140,
                }}
                onClick={isTouch ? () => openTooltip(null) : undefined}
              >
                <div className="tooltip-date">{formatDate(tooltip.data.date)}</div>
                {tooltip.lift === 'total' ? (
                  <div className="tooltip-row">
                    <span style={{ color: LIFT_CONFIG.total.color, fontWeight: 600 }}>Total</span>
                    <strong>{tooltip.data.total}</strong>
                  </div>
                ) : (
                  (() => {
                    const val = tooltip.data[tooltip.lift];
                    const cfg = LIFT_CONFIG[tooltip.lift];
                    return val != null ? (
                      <div className="tooltip-row">
                        <span style={{ color: cfg.color, fontWeight: 600, textTransform: 'capitalize' }}>{cfg.label}</span>
                        <strong>{val}</strong>
                      </div>
                    ) : null;
                  })()
                )}
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="chart-empty">No lift data yet — log squat, bench, or deadlift sets with top-set marked</div>
      )}
    </div>
  );
}
