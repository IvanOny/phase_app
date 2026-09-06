import { useState, useEffect } from 'react';
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

// Mirrors PULLUP_BW_FACTOR in phase_app/metrics.py, which is where the e1RM is
// actually computed. Here only so the tooltip can show the weight the formula
// used rather than the number on the scale.
const PULLUP_BW_FACTOR = 0.9;

const LIFT_CONFIG = {
  squat:    { label: 'Squat',    color: '#6366f1' },
  bench:    { label: 'Bench',    color: '#0891b2' },
  deadlift: { label: 'Deadlift', color: '#10b981' },
  // Pull-up e1RM is (0.9 × bodyweight + added) × (1 + reps/30) — the bar load
  // alone is 0 on an unweighted set, so it lands on the same axis as the barbell
  // lifts rather than on the floor. The 0.9 is the arms, which hang from the bar
  // instead of being lifted; it lives in metrics.py as PULLUP_BW_FACTOR and is
  // only echoed here so the tooltip shows the sum it actually used. Not part of
  // Total: that stays S+B+D.
  pullup:   { label: 'Pull-up',  color: '#ec4899' },
  total:    { label: 'Total',    color: '#f59e0b' },
};

// Squat, bench, deadlift, pull-up, then Total — the order they are read in.
const LIFT_ORDER = ['squat', 'bench', 'deadlift', 'pullup', 'total'];

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

    const squatEntry    = e1rm.squat?.[sid]    ?? null;
    const benchEntry    = e1rm.bench?.[sid]    ?? null;
    const deadliftEntry = e1rm.deadlift?.[sid] ?? null;
    const pullupEntry   = e1rm.pullup?.[sid]   ?? null;

    const sessionSquat    = squatEntry?.topSetE1rmKg    ?? null;
    const sessionBench    = benchEntry?.topSetE1rmKg    ?? null;
    const sessionDeadlift = deadliftEntry?.topSetE1rmKg ?? null;
    const sessionPullup   = pullupEntry?.topSetE1rmKg   ?? null;
    // Two different questions. anyLiftDone drives Total, which is S+B+D and must
    // not appear on a day of pull-ups alone; anyEntry decides whether the
    // session is worth a point at all.
    const anyLiftDone     = sessionSquat != null || sessionBench != null || sessionDeadlift != null;
    const anyEntry        = anyLiftDone || sessionPullup != null;

    // Update running bests for Total
    if (sessionSquat    != null) runningBest.squat    = Math.max(runningBest.squat,    sessionSquat);
    if (sessionBench    != null) runningBest.bench    = Math.max(runningBest.bench,    sessionBench);
    if (sessionDeadlift != null) runningBest.deadlift = Math.max(runningBest.deadlift, sessionDeadlift);

    if (anyEntry) anySeen = true;

    // Only emit points once we have at least one lift recorded
    if (!anySeen) continue;

    const runningTotal = runningBest.squat + runningBest.bench + runningBest.deadlift;

    points.push({
      date:     s.sessionDate,
      // Individual lifts: only non-null on sessions where they were actually performed
      squat:    sessionSquat,
      bench:    sessionBench,
      deadlift: sessionDeadlift,
      pullup:   sessionPullup,
      // Total: running cumulative S+B+D, only shown on lift days
      total:    anyLiftDone ? (runningTotal || null) : null,
      // kept as aliases for tooltip compatibility
      _squat:    sessionSquat,
      _bench:    sessionBench,
      _deadlift: sessionDeadlift,
      _pullup:   sessionPullup,
      // top set details per lift for tooltip
      _squatSet:    squatEntry    ? { load: squatEntry.topSetLoadKg,    reps: squatEntry.topSetReps    } : null,
      _benchSet:    benchEntry    ? { load: benchEntry.topSetLoadKg,    reps: benchEntry.topSetReps    } : null,
      _deadliftSet: deadliftEntry ? { load: deadliftEntry.topSetLoadKg, reps: deadliftEntry.topSetReps } : null,
      _pullupSet:   pullupEntry   ? { load: pullupEntry.topSetLoadKg,   reps: pullupEntry.topSetReps,
                                      bodyweight: pullupEntry.bodyweightKg } : null,
    });
  }

  return points;
}

export default function LiftTrendChart({ sessions, plMetrics, showTotal = true }) {
  const colors = useChartColors();
  const isTouch = useIsTouchDevice();
  const [tooltip, openTooltip, chartRef] = useTooltip('chart-pl');
  const [hovered, setHovered] = useState(null); // { date, lift }
  // Bench alone to start with. Four lines plus Total on one axis was five
  // overlapping series and a y-range wide enough to flatten all of them; one
  // lift is the question anybody actually opens this chart with, and the rest
  // are one tap away.
  const [selected, setSelected] = useState(['bench']);

  function toggleLift(lift) {
    setSelected(prev => {
      // Never all off: an empty chart is a worse answer than the one lift
      // already on screen, so the last active pill doesn't turn itself off.
      if (prev.includes(lift)) return prev.length === 1 ? prev : prev.filter(l => l !== lift);
      // Kept in LIFT_ORDER rather than tap order, so the pills and the legend
      // don't disagree about which lift is which.
      return LIFT_ORDER.filter(l => l === lift || prev.includes(l));
    });
  }

  // Global tap-outside dismiss — same pattern as ClassificationPanel tiles
  useEffect(() => {
    if (!tooltip) return;
    function dismiss() { openTooltip(null); }
    document.addEventListener('pointerdown', dismiss, { capture: true, once: true });
    return () => document.removeEventListener('pointerdown', dismiss, { capture: true });
  }, [tooltip]);

  // A tooltip pinned to a line that has just been switched off would hang there
  // describing something invisible.
  useEffect(() => { openTooltip(null); setHovered(null); }, [selected]);

  const data = buildChartData(sessions, plMetrics);
  const hasData = data.length > 0;

  // Last index in data where each lift has a non-null value (for inline label placement)
  const lastIndexByLift = {};
  // Only what the pills have on. The y-axis reads dataMin/dataMax off the
  // series actually rendered, so hiding the rest re-scales the chart around
  // what is left — which is most of the reason to hide them.
  const liftsToShow = selected.filter(l => l !== 'total' || showTotal);
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
      const isHovered = hovered?.date === payload.date && hovered?.lift === lift;
      const r = lift === 'total' ? 6 : 5;
      const dotR = isActive ? r + 2 : isHovered ? r + 1 : r;
      const isLast = index === lastIndexByLift[lift];

      const handlers = {
        onMouseEnter() {
          setHovered({ date: payload.date, lift });
          if (!isTouch) {
            const pos = getDotPos(cx, cy);
            if (pos) openTooltip({ ...pos, data: payload, lift });
          }
        },
        onMouseLeave() {
          setHovered(null);
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
        <g style={{ cursor: 'pointer' }} onPointerDown={e => e.stopPropagation()} {...handlers}>
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
      {/* Each pill wears its own line's colour when it is on, so the chart can
          be read without counting back to a legend. */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 8, flexWrap: 'wrap' }}>
        {LIFT_ORDER.filter(l => l !== 'total' || showTotal).map(lift => {
          const cfg = LIFT_CONFIG[lift];
          const on = selected.includes(lift);
          return (
            <button
              key={lift}
              className={`filter-chip${on ? ' active' : ''}`}
              onClick={() => toggleLift(lift)}
              aria-pressed={on}
              style={{
                fontSize: 11,
                padding: '1px 8px',
                ...(on ? { color: cfg.color, borderColor: cfg.color,
                           background: 'transparent' } : null),
              }}
            >
              {cfg.label}
            </button>
          );
        })}
      </div>
      {hasData ? (
        <>
          <div
            ref={chartRef}
            style={{ position: 'relative' }}
            onMouseLeave={() => { if (!isTouch) { setHovered(null); openTooltip(null); } }}
          >
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data} margin={{ top: 8, right: 64, bottom: 24, left: 0 }}
                onMouseLeave={() => { if (!isTouch) { setHovered(null); openTooltip(null); } }}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                <XAxis dataKey="date" tickFormatter={formatDate}
                  tick={{ fill: colors.textMuted, fontSize: 12 }}
                  axisLine={{ stroke: colors.border }} tickLine={false} />
                <YAxis domain={['dataMin - 10', 'dataMax + 10']}
                  tick={{ fill: colors.textMuted, fontSize: 12 }}
                  axisLine={false} tickLine={false} width={44} />
                {liftsToShow.map(lift => (
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
                {tooltip.lift === 'total' ? (
                  <>
                    <div className="tooltip-row">
                      <span style={{ color: LIFT_CONFIG.total.color, fontWeight: 600 }}>Total</span>
                      <strong>{tooltip.data.total}</strong>
                    </div>
                    <div className="tooltip-row" style={{ opacity: 0.6 }}>
                      <span>date</span>
                      <span>{formatDate(tooltip.data.date)}</span>
                    </div>
                  </>
                ) : (
                  (() => {
                    const val = tooltip.data[tooltip.lift];
                    const topSet = tooltip.data[`_${tooltip.lift}Set`];
                    const cfg = LIFT_CONFIG[tooltip.lift];
                    if (val == null) return null;
                    return (
                      <>
                        <div className="tooltip-row">
                          <span style={{ color: cfg.color, fontWeight: 600 }}>e1RM</span>
                          <strong>{val}</strong>
                        </div>
                        {topSet && (
                          <div className="tooltip-row" style={{ opacity: 0.75 }}>
                            <span>top set</span>
                            <span>
                              {topSet.bodyweight != null
                                ? `${(topSet.bodyweight * PULLUP_BW_FACTOR).toFixed(1)}${topSet.load ? ` + ${topSet.load}` : ''} × ${topSet.reps}`
                                : `${topSet.load}×${topSet.reps}`}
                            </span>
                          </div>
                        )}
                        <div className="tooltip-row" style={{ opacity: 0.6 }}>
                          <span>date</span>
                          <span>{formatDate(tooltip.data.date)}</span>
                        </div>
                      </>
                    );
                  })()
                )}
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="chart-empty">No lift data yet — log squat, bench, deadlift or pull-up sets with top-set marked</div>
      )}
    </div>
  );
}
