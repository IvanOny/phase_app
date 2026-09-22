import { useState, useEffect, useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip,
} from 'recharts';
import { getMonthlyMetrics } from '../../api/client.js';
import { useChartColors } from '../../hooks/useChartColors.js';
import { buildChartData } from './LiftTrendChart.jsx';
import { monthOf, monthTick, monthShort, monthRange, thisMonth } from '../../utils/months.js';

const LIFTS = {
  squat:    { label: 'Squat',    color: '#6366f1' },
  bench:    { label: 'Bench',    color: '#0891b2' },
  deadlift: { label: 'Deadlift', color: '#10b981' },
  pullup:   { label: 'Pull-up',  color: '#ec4899' },
};
const LIFT_ORDER = ['squat', 'bench', 'deadlift', 'pullup'];

const HRV_COLOR = '#10b981';

const SPANS = [
  { key: '6',   label: '6m',  months: 6 },
  { key: '12',  label: '1y',  months: 12 },
  { key: 'all', label: 'all', months: null },
];

function avg(xs) {
  return xs.length ? Math.round((xs.reduce((a, b) => a + b, 0) / xs.length) * 10) / 10 : null;
}

/**
 * The lift and the body underneath it, on one axis whose every step is a
 * month.
 *
 * A month is the coarsest unit the health numbers come in — one row each for
 * HRV, resting heart rate and the rest — so it is the unit both halves have
 * to be drawn in. The lift is averaged per month to meet them: a month with
 * four bench sessions contributes one point, the mean of the four. That is a
 * blunter line than the trend chart's, and deliberately so; the question here
 * is not "how is the bench moving" but "does it move with anything else".
 *
 * Two charts rather than two axes on one. Kilograms, milliseconds and
 * kilograms-of-you share no scale, and stacked on one plot the smaller range
 * flattens to a straight line. They share a `syncId`, so the crosshair in one
 * is the crosshair in the other, and the months line up because both are
 * given the same rows — including the empty ones.
 */
export default function HealthBandChart({ sessions, plMetrics }) {
  const colors = useChartColors();
  const [lift, setLift] = useState('bench');
  const [spanKey, setSpanKey] = useState('12');
  const [monthly, setMonthly] = useState(null);

  useEffect(() => {
    let live = true;
    getMonthlyMetrics().then(r => { if (live) setMonthly(Array.isArray(r) ? r : []); })
                       .catch(() => { if (live) setMonthly([]); });
    return () => { live = false; };
  }, []);

  const rows = useMemo(() => {
    if (!monthly) return [];

    // Per month: the average e1RM of that month's sessions, per lift.
    const liftMonths = new Map();
    for (const p of buildChartData(sessions || [], plMetrics)) {
      const m = monthOf(p.date);
      const bag = liftMonths.get(m) || {};
      LIFT_ORDER.forEach(l => {
        const v = p[`_${l}`];
        if (v != null) (bag[l] = bag[l] || []).push(v);
      });
      liftMonths.set(m, bag);
    }

    // Bodyweight is per date; the month takes the mean of its readings.
    const bwMonths = new Map();
    for (const b of (plMetrics?.bodyweightLog || [])) {
      const kg = Number(b.weightKg);
      if (!Number.isFinite(kg)) continue;
      const m = monthOf(b.loggedDate);
      if (!bwMonths.has(m)) bwMonths.set(m, []);
      bwMonths.get(m).push(kg);
    }

    const hrv = new Map((monthly || []).map(r => [r.month, r.hrvAvg]));

    const known = [...liftMonths.keys(), ...bwMonths.keys(), ...hrv.keys()].sort();
    if (known.length === 0) return [];
    const last = thisMonth();
    const span = SPANS.find(s => s.key === spanKey)?.months ?? null;
    const first = span
      ? monthRange(known[0], last).slice(-span)[0]
      : known[0];

    return monthRange(first < known[0] ? known[0] : first, last).map(m => {
      const bag = liftMonths.get(m) || {};
      const row = { month: m, hrv: hrv.get(m) ?? null, bw: avg(bwMonths.get(m) || []) };
      LIFT_ORDER.forEach(l => { row[l] = avg(bag[l] || []); });
      return row;
    });
  }, [sessions, plMetrics, monthly, spanKey]);

  if (monthly === null) return null;

  const hasLift = rows.some(r => r[lift] != null);
  const hasHrv = rows.some(r => r.hrv != null);
  const hasBw = rows.some(r => r.bw != null);
  const cfg = LIFTS[lift];

  const axis = { fontSize: 11, fill: colors.textMuted };
  const tooltipStyle = {
    background: colors.bgApp, border: `1px solid ${colors.border}`, borderRadius: 8, fontSize: 12,
  };
  const label = (v) => monthShort(v);

  return (
    <div className="chart-wrapper">
      <div className="chart-title-row">
        <span className="card-title">Lift and body, month by month</span>
      </div>

      <div style={{ display: 'flex', gap: 4, marginBottom: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        {LIFT_ORDER.map(l => {
          const on = l === lift;
          return (
            <button key={l} className={`filter-chip${on ? ' active' : ''}`}
                    onClick={() => setLift(l)} aria-pressed={on}
                    style={{ fontSize: 11, padding: '1px 8px',
                             ...(on ? { color: LIFTS[l].color, borderColor: LIFTS[l].color,
                                        background: 'transparent' } : null) }}>
              {LIFTS[l].label}
            </button>
          );
        })}
        <div style={{ display: 'flex', gap: 4, marginLeft: 'auto' }} role="group" aria-label="Months shown">
          {SPANS.map(s => (
            <button key={s.key} className={`filter-chip${s.key === spanKey ? ' active' : ''}`}
                    onClick={() => setSpanKey(s.key)} aria-pressed={s.key === spanKey}
                    style={{ fontSize: 11, padding: '1px 8px' }}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {rows.length === 0 || (!hasLift && !hasHrv && !hasBw) ? (
        <div className="chart-empty">Nothing to line up yet — this needs a month of sessions and a saved month of recovery</div>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={rows} syncId="health-months" margin={{ top: 6, right: 8, bottom: 0, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
              {/* The months are drawn once, under the band below; up here the
                  axis is present only to keep the two plots the same width. */}
              <XAxis dataKey="month" tick={false} axisLine={false} height={1} />
              <YAxis domain={['dataMin - 5', 'dataMax + 5']} tick={axis} axisLine={false}
                     tickLine={false} width={44} />
              {/* An empty right-hand axis of the same width as the band's
                  bodyweight axis. Without it the upper plot would be forty
                  pixels wider than the lower one and the months underneath
                  would sit off the points they belong to. */}
              <YAxis yAxisId="spacer" orientation="right" width={40} tick={false}
                     axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} labelFormatter={label}
                       formatter={v => [`${v} kg`, cfg.label]} />
              <Line type="monotone" dataKey={lift} stroke={cfg.color} strokeWidth={2}
                    dot={{ r: 3, fill: cfg.color }} connectNulls isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>

          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={rows} syncId="health-months" margin={{ top: 4, right: 8, bottom: 4, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
              {/* interval={0}: every month gets its tick, so the axis is a
                  calendar and not a list of the months that had data. */}
              <XAxis dataKey="month" tickFormatter={monthTick} tick={axis} interval={0}
                     axisLine={{ stroke: colors.border }} tickLine={false} />
              <YAxis yAxisId="hrv" domain={['dataMin - 4', 'dataMax + 4']} tick={axis}
                     axisLine={false} tickLine={false} width={44} />
              <YAxis yAxisId="bw" orientation="right" domain={['dataMin - 2', 'dataMax + 2']}
                     tick={axis} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={tooltipStyle} labelFormatter={label}
                       formatter={(v, name) => (name === 'hrv' ? [`${v} ms`, 'hrv avg'] : [`${v} kg`, 'bodyweight'])} />
              <Line yAxisId="hrv" type="monotone" dataKey="hrv" stroke={HRV_COLOR} strokeWidth={1.5}
                    dot={{ r: 2.5, fill: HRV_COLOR }} connectNulls isAnimationActive={false} />
              <Line yAxisId="bw" type="monotone" dataKey="bw" stroke={colors.textMuted} strokeWidth={1.5}
                    strokeDasharray="4 3" dot={false} connectNulls isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>

          <div style={{ display: 'flex', gap: 16, fontSize: 11, color: 'var(--text-secondary)',
                        marginTop: 2, flexWrap: 'wrap' }}>
            <span>
              <span style={{ display: 'inline-block', width: 14, height: 2, background: HRV_COLOR,
                             verticalAlign: 'middle', marginRight: 5 }} />
              hrv average{!hasHrv && ' — no month saved yet'}
            </span>
            <span>
              <span style={{ display: 'inline-block', width: 14, height: 0,
                             borderTop: `2px dashed ${colors.textMuted}`,
                             verticalAlign: 'middle', marginRight: 5 }} />
              bodyweight{!hasBw && ' — nothing logged yet'}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
