import { useState, useEffect, useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip,
} from 'recharts';
import { getMonthlyMetrics } from '../../api/client.js';
import { useChartColors } from '../../hooks/useChartColors.js';
import { monthOf, monthTick, monthShort, monthRange, thisMonth } from '../../utils/months.js';

// Everything the Health tab records, in the order it is entered there, plus
// bodyweight, which is entered by date and averaged into its month.
const METRICS = [
  { key: 'hrvBest',    label: 'HRV best',     unit: 'ms',  color: '#10b981' },
  { key: 'hrvAvg',     label: 'HRV avg',      unit: 'ms',  color: '#0891b2' },
  { key: 'rhrBest',    label: 'Rest HR best', unit: 'bpm', color: '#ec4899' },
  { key: 'rhrAvg',     label: 'Rest HR avg',  unit: 'bpm', color: '#f43f5e' },
  { key: 'vo2maxBest', label: 'VO₂ max', unit: '',    color: '#6366f1' },
  { key: 'sleepAvg',   label: 'Sleep',        unit: '',    color: '#f59e0b' },
  { key: 'bw',         label: 'Bodyweight',   unit: 'kg',  color: '#78716c' },
];
const BY_KEY = Object.fromEntries(METRICS.map(m => [m.key, m]));

const SPANS = [
  { key: '6',   label: '6m',  months: 6 },
  { key: '12',  label: '1y',  months: 12 },
  { key: 'all', label: 'all', months: null },
];

function avg(xs) {
  return xs.length ? Math.round((xs.reduce((a, b) => a + b, 0) / xs.length) * 10) / 10 : null;
}

/**
 * The body, month by month: every metric the Health tab holds, on one axis
 * whose every step is a month.
 *
 * Milliseconds, beats, kilograms and a sleep score share no scale, so each
 * line gets its own y-axis, hidden, fitted to its own range. What the chart
 * compares is therefore shape, not height: whether HRV sagged in the month
 * bodyweight climbed. The numbers on the left are drawn only when a single
 * metric is on, because that is the only time they mean one thing.
 *
 * Gaps are drawn as gaps. A month with nothing entered still gets its tick,
 * so the axis is a calendar and not a list of the months that had data.
 */
export default function HealthBandChart({ plMetrics }) {
  const colors = useChartColors();
  const [selected, setSelected] = useState(['hrvAvg', 'bw']);
  const [spanKey, setSpanKey] = useState('12');
  const [monthly, setMonthly] = useState(null);

  useEffect(() => {
    let live = true;
    getMonthlyMetrics().then(r => { if (live) setMonthly(Array.isArray(r) ? r : []); })
                       .catch(() => { if (live) setMonthly([]); });
    return () => { live = false; };
  }, []);

  function toggle(key) {
    setSelected(prev => (prev.includes(key)
      // Never all off -- an empty plot answers less than the one line on it.
      ? (prev.length === 1 ? prev : prev.filter(k => k !== key))
      : METRICS.filter(m => m.key === key || prev.includes(m.key)).map(m => m.key)));
  }

  const rows = useMemo(() => {
    if (!monthly) return [];

    // Bodyweight is per date; the month takes the mean of its readings.
    const bwMonths = new Map();
    for (const b of (plMetrics?.bodyweightLog || [])) {
      const kg = Number(b.weightKg);
      if (!Number.isFinite(kg)) continue;
      const m = monthOf(b.loggedDate);
      if (!bwMonths.has(m)) bwMonths.set(m, []);
      bwMonths.get(m).push(kg);
    }

    const byMonth = new Map(monthly.map(r => [r.month, r]));
    const known = [...byMonth.keys(), ...bwMonths.keys()].sort();
    if (known.length === 0) return [];

    const last = known[known.length - 1];
    const newest = thisMonth() > last ? thisMonth() : last;
    const span = SPANS.find(s => s.key === spanKey)?.months ?? null;
    const all = monthRange(known[0], newest);
    const shown = span ? all.slice(-span) : all;

    return shown.map(m => {
      const r = byMonth.get(m) || {};
      const row = { month: m, bw: avg(bwMonths.get(m) || []) };
      METRICS.forEach(mm => { if (mm.key !== 'bw') row[mm.key] = r[mm.key] ?? null; });
      return row;
    });
  }, [plMetrics, monthly, spanKey]);

  if (monthly === null) return null;

  const withData = selected.filter(k => rows.some(r => r[k] != null));
  const missing = selected.filter(k => !withData.includes(k));
  const axisTick = { fontSize: 11, fill: colors.textMuted };
  const single = selected.length === 1;

  return (
    <div className="chart-wrapper">
      <div className="chart-title-row">
        <span className="card-title">Body, month by month</span>
        {!single && (
          <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
            each line on its own scale
          </span>
        )}
      </div>

      <div style={{ display: 'flex', gap: 4, marginBottom: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        {METRICS.map(m => {
          const on = selected.includes(m.key);
          return (
            <button key={m.key} className={`filter-chip${on ? ' active' : ''}`}
                    onClick={() => toggle(m.key)} aria-pressed={on}
                    style={{ fontSize: 11, padding: '1px 8px',
                             ...(on ? { color: m.color, borderColor: m.color,
                                        background: 'transparent' } : null) }}>
              {m.label}
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

      {withData.length === 0 ? (
        <div className="chart-empty">
          {rows.length === 0
            ? 'Nothing recorded yet — save a month in the Health tab'
            : 'No month holds this one yet'}
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: single ? -10 : -28 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
            <XAxis dataKey="month" tickFormatter={monthTick} tick={axisTick} interval={0}
                   axisLine={{ stroke: colors.border }} tickLine={false} />
            {/* One axis per line, each fitted to its own range. Only the
                single-metric case draws its numbers. */}
            {withData.map((k, i) => (
              <YAxis key={k} yAxisId={k} domain={['auto', 'auto']} width={single ? 44 : 0}
                     tick={single ? axisTick : false} axisLine={false} tickLine={false}
                     hide={!single && i > 0} />
            ))}
            <Tooltip
              contentStyle={{ background: colors.bgApp, border: `1px solid ${colors.border}`,
                              borderRadius: 8, fontSize: 12 }}
              labelFormatter={monthShort}
              formatter={(v, name) => {
                const m = BY_KEY[name];
                return [m && m.unit ? `${v} ${m.unit}` : `${v}`, m ? m.label : name];
              }}
            />
            {withData.map(k => (
              <Line key={k} yAxisId={k} type="monotone" dataKey={k} stroke={BY_KEY[k].color}
                    strokeWidth={k === 'bw' ? 1.5 : 2} strokeDasharray={k === 'bw' ? '4 3' : undefined}
                    dot={{ r: 2.5, fill: BY_KEY[k].color }} connectNulls isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}

      {withData.length > 0 && (
        <div style={{ display: 'flex', gap: 14, fontSize: 11, color: 'var(--text-secondary)',
                      marginTop: 4, flexWrap: 'wrap' }}>
          {withData.map(k => (
            <span key={k}>
              <span style={{ display: 'inline-block', width: 14, height: 2,
                             background: BY_KEY[k].color, verticalAlign: 'middle', marginRight: 5 }} />
              {BY_KEY[k].label}{BY_KEY[k].unit && ` (${BY_KEY[k].unit})`}
            </span>
          ))}
          {missing.length > 0 && (
            <span style={{ color: 'var(--text-muted)' }}>
              {missing.map(k => BY_KEY[k].label).join(', ')} — no month holds it yet
            </span>
          )}
        </div>
      )}
    </div>
  );
}
