import { useState, useEffect, useMemo } from 'react';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip,
} from 'recharts';
import { getMonthlyMetrics, getMonthlyRun } from '../../api/client.js';
import { useChartColors } from '../../hooks/useChartColors.js';
import { monthShort, monthTick, monthRange, clock } from '../../utils/months.js';

// Which way is up. Resting heart rate is the one metric where the smaller
// number is the better month, and the arrow has to know that or it will
// congratulate you for a bad one.
const STRIP = [
  { key: 'hrvAvg',     head: 'hrv',     good: 'up' },
  { key: 'rhrAvg',     head: 'rest hr', good: 'down' },
  { key: 'vo2maxBest', head: 'vo₂',     good: 'up' },
  { key: 'sleepAvg',   head: 'sleep',   good: 'up' },
];

function Delta({ now, prev, good, colors }) {
  if (now == null || prev == null || now === prev) return null;
  const up = now > prev;
  const better = (good === 'up') === up;
  return (
    <span style={{ marginLeft: 3, fontSize: 10,
                   color: better ? colors.readyGreen : colors.readyRed }}>
      {up ? '▲' : '▼'}
    </span>
  );
}

function num(v) {
  if (v == null) return null;
  return Math.round(v * 10) / 10;
}

// Draft 1: one row per month, newest first, each number against the month
// below it. Eight months fit on a screen, which no chart of eight points does
// better.
function MonthStrip({ rows, colors }) {
  if (rows.length === 0) {
    return <div className="chart-empty">Nothing recorded yet — a saved month shows up here</div>;
  }
  const newestFirst = [...rows].reverse();
  return (
    <div style={{ overflowX: 'auto' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '82px repeat(4, minmax(46px, 1fr)) minmax(122px, 1.6fr)',
                    gap: '6px 10px', fontSize: 13, alignItems: 'center', minWidth: 400 }}>
        <span />
        {STRIP.map(c => (
          <span key={c.key} style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.head}</span>
        ))}
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>running</span>

        {newestFirst.map((r, i) => {
          const prev = newestFirst[i + 1];
          return (
            <div key={r.month} style={{ display: 'contents' }}>
              <span style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{monthShort(r.month)}</span>
              {STRIP.map(c => (
                <span key={c.key} style={{ whiteSpace: 'nowrap' }}>
                  {r[c.key] == null
                    ? <span style={{ color: 'var(--text-muted)' }}>—</span>
                    : <>{num(r[c.key])}<Delta now={r[c.key]} prev={prev?.[c.key]} good={c.good} colors={colors} /></>}
                </span>
              ))}
              <span style={{ fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                {r.totalKm == null
                  ? <span style={{ color: 'var(--text-muted)' }}>—</span>
                  : `${Math.round(r.totalKm)} km · ${r.activities} · ${clock(r.avgPaceS, true)}`}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Draft 2: volume as bars, pace as a line drawn upside down so faster is
// higher. The two together are the story — the distance went up and the pace
// came down at the same time, which neither series says on its own.
function RunningChart({ rows, colors }) {
  const data = rows.filter(r => r.totalKm != null);
  if (data.length === 0) {
    return <div className="chart-empty">No running months yet</div>;
  }
  const paces = data.map(r => r.avgPaceS).filter(v => v != null);
  const lo = Math.min(...paces), hi = Math.max(...paces);
  const pad = Math.max((hi - lo) * 0.15, 15);

  return (
    <>
      <div style={{ display: 'flex', gap: 16, fontSize: 11, color: 'var(--text-secondary)',
                    marginBottom: 6, flexWrap: 'wrap' }}>
        <span>
          <span style={{ display: 'inline-block', width: 9, height: 9, borderRadius: 2,
                         background: colors.accent, opacity: 0.55, marginRight: 5 }} />
          km per month
        </span>
        <span>
          <span style={{ display: 'inline-block', width: 14, height: 2, background: '#f59e0b',
                         verticalAlign: 'middle', marginRight: 5 }} />
          avg pace — higher is faster
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: -12 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
          <XAxis dataKey="month" tickFormatter={monthTick} tick={{ fontSize: 11, fill: colors.textMuted }}
                 axisLine={{ stroke: colors.border }} tickLine={false} interval={0} />
          <YAxis yAxisId="km" tick={{ fontSize: 11, fill: colors.textMuted }}
                 axisLine={false} tickLine={false} width={40} />
          {/* Reversed, so a faster month sits higher. A pace axis the normal
              way up reads as though getting better were falling. */}
          <YAxis yAxisId="pace" orientation="right" reversed domain={[lo - pad, hi + pad]}
                 tickFormatter={v => clock(v, true)} width={44}
                 tick={{ fontSize: 11, fill: colors.textMuted }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ background: colors.bgApp, border: `1px solid ${colors.border}`,
                            borderRadius: 8, fontSize: 12 }}
            labelFormatter={monthShort}
            formatter={(v, name) => (name === 'avgPaceS'
              ? [`${clock(v, true)} /km`, 'pace']
              : [`${Math.round(v * 10) / 10} km`, 'distance'])}
          />
          <Bar yAxisId="km" dataKey="totalKm" fill={colors.accent} fillOpacity={0.55}
               radius={[3, 3, 0, 0]} maxBarSize={44} isAnimationActive={false} />
          <Line yAxisId="pace" type="monotone" dataKey="avgPaceS" stroke="#f59e0b" strokeWidth={2}
                dot={{ r: 3, fill: '#f59e0b' }} connectNulls isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </>
  );
}

/**
 * The two history views over the monthly tables, fetched once and shared:
 * the strip reads every column, the chart reads two of them.
 *
 * `reloadKey` is anything that should send it back to the server -- a month
 * saved elsewhere in the page. It is fetched once otherwise.
 */
export default function HealthHistory({ reloadKey = 0 }) {
  const colors = useChartColors();
  const [metrics, setMetrics] = useState(null);
  const [run, setRun] = useState(null);

  useEffect(() => {
    let live = true;
    Promise.all([getMonthlyMetrics(), getMonthlyRun()]).then(([m, r]) => {
      if (!live) return;
      setMetrics(Array.isArray(m) ? m : []);
      setRun(Array.isArray(r) ? r : []);
    }).catch(() => { if (live) { setMetrics([]); setRun([]); } });
    return () => { live = false; };
  }, [reloadKey]);

  // One row per month from the first recorded to the last, the two tables
  // merged. A month present in only one of them is still a month.
  const rows = useMemo(() => {
    if (!metrics || !run) return [];
    const byMonth = new Map();
    [...metrics, ...run].forEach(r => {
      byMonth.set(r.month, { ...(byMonth.get(r.month) || { month: r.month }), ...r });
    });
    const months = [...byMonth.keys()].sort();
    if (months.length === 0) return [];
    return monthRange(months[0], months[months.length - 1])
      .map(m => byMonth.get(m) || { month: m });
  }, [metrics, run]);

  if (metrics === null) return null;

  return (
    <>
      <div className="chart-wrapper">
        <div className="chart-title-row">
          <span className="card-title">Months</span>
        </div>
        <MonthStrip rows={rows} colors={colors} />
      </div>

      <div className="chart-wrapper">
        <div className="chart-title-row">
          <span className="card-title">Running — volume and pace</span>
        </div>
        <RunningChart rows={rows} colors={colors} />
      </div>
    </>
  );
}
