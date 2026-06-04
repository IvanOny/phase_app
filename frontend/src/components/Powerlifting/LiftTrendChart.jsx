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

  // Running best per lift (starts with confirmed max if it pre-dates sessions)
  const runningBest = {
    squat:    confirmedMax.squat    || 0,
    bench:    confirmedMax.bench    || 0,
    deadlift: confirmedMax.deadlift || 0,
  };

  const points = [];

  for (const s of sorted) {
    const sid = String(s.sessionId);
    let updated = false;

    for (const lift of ['squat', 'bench', 'deadlift']) {
      const sessionData = e1rm[lift]?.[sid];
      if (sessionData?.topSetE1rmKg > runningBest[lift]) {
        runningBest[lift] = sessionData.topSetE1rmKg;
        updated = true;
      }
    }

    // Only emit a point if at least one lift has been seen
    if (runningBest.squat || runningBest.bench || runningBest.deadlift) {
      const total = runningBest.squat + runningBest.bench + runningBest.deadlift;
      points.push({
        date:     s.sessionDate,
        squat:    runningBest.squat    || null,
        bench:    runningBest.bench    || null,
        deadlift: runningBest.deadlift || null,
        total:    total || null,
        // raw session e1RMs for tooltip
        _squat:    e1rm.squat?.[sid]?.topSetE1rmKg    ?? null,
        _bench:    e1rm.bench?.[sid]?.topSetE1rmKg    ?? null,
        _deadlift: e1rm.deadlift?.[sid]?.topSetE1rmKg ?? null,
        updated,
      });
    }
  }

  return points;
}

export default function LiftTrendChart({ sessions, plMetrics }) {
  const colors = useChartColors();
  const isTouch = useIsTouchDevice();
  const [tooltip, openTooltip, chartRef] = useTooltip('chart-pl');
  const [hoveredDate, setHoveredDate] = useState(null);

  const data = buildChartData(sessions, plMetrics);
  const hasData = data.length > 0;

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
      const { cx, cy, payload } = props;
      if (!payload[lift]) return null;
      const isActive = tooltip?.data?.date === payload.date;
      const isHovered = hoveredDate === payload.date;
      const r = lift === 'total' ? 6 : 5;
      const dotR = isActive ? r + 2 : isHovered ? r + 1 : r;

      const handlers = {
        onMouseEnter() {
          setHoveredDate(payload.date);
          if (!isTouch) {
            const pos = getDotPos(cx, cy);
            if (pos) openTooltip({ ...pos, data: payload });
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
          openTooltip(tooltip?.data?.date === payload.date ? null : { ...pos, data: payload });
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
              <LineChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 0 }}
                onMouseLeave={() => { if (!isTouch) { setHoveredDate(null); openTooltip(null); } }}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                <XAxis dataKey="date" tickFormatter={formatDate}
                  tick={{ fill: colors.textMuted, fontSize: 12 }}
                  axisLine={{ stroke: colors.border }} tickLine={false} />
                <YAxis domain={['dataMin - 10', 'dataMax + 10']}
                  tick={{ fill: colors.textMuted, fontSize: 12 }}
                  axisLine={false} tickLine={false} width={44} />
                {['squat', 'bench', 'deadlift', 'total'].map(lift => (
                  <Line
                    key={lift}
                    type="monotone"
                    dataKey={lift}
                    stroke={LIFT_CONFIG[lift].color}
                    strokeWidth={lift === 'total' ? 2.5 : 1.8}
                    strokeDasharray={lift === 'total' ? '5 3' : undefined}
                    connectNulls
                    dot={makeDot(lift)()}
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
                {['squat', 'bench', 'deadlift'].map(lift => {
                  const sessionVal = tooltip.data[`_${lift}`];
                  const bestVal = tooltip.data[lift];
                  return bestVal != null ? (
                    <div key={lift} className="tooltip-row">
                      <span style={{ color: LIFT_CONFIG[lift].color, fontWeight: 600, textTransform: 'capitalize' }}>{lift}</span>
                      <strong>
                        {bestVal}
                        {sessionVal != null && sessionVal !== bestVal && (
                          <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> ({sessionVal} today)</span>
                        )}
                      </strong>
                    </div>
                  ) : null;
                })}
                {tooltip.data.total != null && (
                  <div className="tooltip-row" style={{ borderTop: '1px solid var(--border)', marginTop: 4, paddingTop: 4 }}>
                    <span style={{ color: LIFT_CONFIG.total.color, fontWeight: 600 }}>Total</span>
                    <strong>{tooltip.data.total}</strong>
                  </div>
                )}
              </div>
            )}
          </div>
          <div className="chart-legend">
            {Object.entries(LIFT_CONFIG).map(([key, cfg]) => (
              <span key={key} className="chart-legend-item">
                <svg width={16} height={10} style={{ flexShrink: 0, verticalAlign: 'middle' }}>
                  <line x1={0} y1={5} x2={16} y2={5}
                    stroke={cfg.color} strokeWidth={key === 'total' ? 2.5 : 1.8}
                    strokeDasharray={key === 'total' ? '5 3' : undefined} />
                </svg>
                {cfg.label}
              </span>
            ))}
          </div>
        </>
      ) : (
        <div className="chart-empty">No lift data yet — log squat, bench, or deadlift sets with top-set marked</div>
      )}
    </div>
  );
}
