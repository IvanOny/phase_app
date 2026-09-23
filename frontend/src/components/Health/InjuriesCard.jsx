import { ReferenceArea, ReferenceLine } from 'recharts';
import { monthTick, monthRange, monthOf, thisMonth } from '../../utils/months.js';

// Severity as a colour: the one thing about an injury you want to read before
// its dates.
export const SEVERITY = {
  minor:    { label: 'minor',    color: '#d97706' },
  moderate: { label: 'moderate', color: '#ea580c' },
  severe:   { label: 'severe',   color: '#dc2626' },
};

const DAY_MS = 86400000;

function dayMs(iso) {
  return Date.parse(iso);
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function fmt(iso) {
  const [, m, d] = iso.split('-');
  return `${d}.${m}`;
}

// Days an injury limited training: start to resolution, inclusive. An open
// one counts to today, and keeps counting.
export function daysLimited(inj) {
  const end = inj.resolvedOn || todayIso();
  return Math.max(1, Math.round((dayMs(end) - dayMs(inj.startedOn)) / DAY_MS) + 1);
}

/**
 * Injuries as index ranges over a chart's own x categories.
 *
 * `indexOf(isoDate)` says which category a day falls in, or -1 if the chart
 * doesn't cover it. A span that starts before the chart and ends inside it is
 * clipped to the first category rather than dropped: the chart then opens
 * inside an injury, which is true.
 */
export function injurySpans(injuries, categories, indexOf) {
  if (!injuries?.length || !categories.length) return [];
  const last = categories.length - 1;
  const today = todayIso();
  const out = [];
  for (const inj of injuries) {
    const end = inj.resolvedOn || today;
    let i = indexOf(inj.startedOn);
    let j = indexOf(end);
    if (i === -1 && j === -1) {
      // Wholly outside, unless it wraps the entire chart.
      if (!(inj.startedOn < categories[0].from && end > categories[last].to)) continue;
      i = 0; j = last;
    }
    if (i === -1) i = 0;
    if (j === -1) j = last;
    out.push({ x1: categories[i].key, x2: categories[j].key, single: i === j,
               color: (SEVERITY[inj.severity] || SEVERITY.moderate).color, inj });
  }
  return out;
}

// Recharts reads its children by type, so these are plain elements returned
// from a function rather than a component of our own.
export function injuryMarks(spans, yAxisId) {
  const axis = yAxisId != null ? { yAxisId } : {};
  return spans.map((s, k) => (s.single ? (
    <ReferenceLine key={'inj-' + k} x={s.x1} stroke={s.color} strokeOpacity={0.25} strokeWidth={10}
                   {...axis}
                   label={{ value: s.inj.area, position: 'insideTopLeft', fontSize: 10, fill: s.color }} />
  ) : (
    <ReferenceArea key={'inj-' + k} x1={s.x1} x2={s.x2} fill={s.color} fillOpacity={0.1}
                   stroke="none" {...axis}
                   label={{ value: s.inj.area, position: 'insideTopLeft', fontSize: 10, fill: s.color }} />
  )));
}

/**
 * Every injury as a bar on a calendar, one lane each, newest on top.
 *
 * The point is the pattern rather than any single entry: how often, how
 * long, and how close together. So the axis is months, the bars are to
 * scale, and the header counts what the year cost.
 */
export default function InjuriesCard({ injuries }) {
  if (!injuries || injuries.length === 0) return null;

  const first = monthOf(injuries.reduce((a, i) => (i.startedOn < a ? i.startedOn : a), injuries[0].startedOn));
  const months = monthRange(first, thisMonth());
  const t0 = dayMs(`${months[0]}-01`);
  const t1 = dayMs(todayIso()) + DAY_MS;
  const span = t1 - t0;
  const pct = t => `${Math.max(0, Math.min(100, ((t - t0) / span) * 100))}%`;

  const year = todayIso().slice(0, 4);
  const thisYear = injuries.filter(i => i.startedOn.startsWith(year));
  const open = injuries.filter(i => !i.resolvedOn);
  const lost = thisYear.reduce((a, i) => a + daysLimited(i), 0);
  const newestFirst = [...injuries].sort((a, b) => (a.startedOn < b.startedOn ? 1 : -1));

  return (
    <div className="chart-wrapper">
      <div className="chart-title-row">
        <span className="card-title">Injuries</span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
          {thisYear.length} in {year} · {lost} days limited{open.length > 0 && ` · ${open.length} open`}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(96px, 150px) minmax(0, 1fr)',
                    columnGap: 12, rowGap: 8, alignItems: 'center', fontSize: 12 }}>
        {newestFirst.map(inj => {
          const sev = SEVERITY[inj.severity] || SEVERITY.moderate;
          const start = dayMs(inj.startedOn);
          const end = inj.resolvedOn ? dayMs(inj.resolvedOn) + DAY_MS : t1;
          return (
            <div key={inj.injuryId} style={{ display: 'contents' }}>
              <div style={{ lineHeight: 1.25, minWidth: 0 }} title={inj.note || ''}>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden',
                              textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{inj.area}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                  {fmt(inj.startedOn)}{inj.resolvedOn ? `–${fmt(inj.resolvedOn)}` : ' – open'} · {daysLimited(inj)}d
                </div>
              </div>
              <div style={{ position: 'relative', height: 14, background: 'var(--border)',
                            borderRadius: 3, opacity: 0.9 }}>
                <div style={{
                  position: 'absolute', top: 0, bottom: 0, left: pct(start),
                  width: `max(4px, calc(${pct(end)} - ${pct(start)}))`,
                  background: sev.color, borderRadius: 3,
                  // An open injury fades out toward today rather than ending
                  // cleanly, because it hasn't ended.
                  ...(inj.resolvedOn ? null : {
                    background: `linear-gradient(90deg, ${sev.color} 60%, transparent)`,
                  }),
                }} />
              </div>
            </div>
          );
        })}

        {/* The month axis under the last lane. */}
        <span />
        <div style={{ position: 'relative', height: 14, fontSize: 10, color: 'var(--text-muted)' }}>
          {months.map((m, i) => (
            // Every month gets a mark; labels thin out when there are many.
            (months.length <= 8 || i % Math.ceil(months.length / 8) === 0) && (
              <span key={m} style={{ position: 'absolute', left: pct(dayMs(`${m}-01`)),
                                     transform: 'translateX(-2px)', whiteSpace: 'nowrap' }}>
                {monthTick(m)}
              </span>
            )
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 12, fontSize: 11, color: 'var(--text-secondary)',
                    marginTop: 10, flexWrap: 'wrap' }}>
        {Object.values(SEVERITY).map(s => (
          <span key={s.label}>
            <span style={{ display: 'inline-block', width: 9, height: 9, borderRadius: 2,
                           background: s.color, marginRight: 5 }} />
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}
