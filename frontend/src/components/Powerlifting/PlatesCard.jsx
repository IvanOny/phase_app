// What to put on the bar: the last top set of each barbell lift, with the
// plates it takes per side. The bench phase's Next Step card answered "what
// next"; this answers "what did I last lift, and how do I load it again".
// How a side is built -- 25s, then 35s -- lives in utils/plates.js.
import { platesPerSide } from '../../utils/plates.js';

const LIFTS = [
  { key: 'squat',    label: 'Squat' },
  { key: 'bench',    label: 'Bench press' },
  { key: 'deadlift', label: 'Deadlift' },
];

function fmtDate(d) {
  const [, m, day] = String(d).slice(0, 10).split('-');
  return `${day}.${m}`;
}

// The most recent session that has a top set for this lift, across every
// phase the feed covers.
function lastTopSet(lift, sessions, plMetrics) {
  const byId = plMetrics?.e1rm?.[lift] || {};
  let best = null;
  for (const s of sessions || []) {
    const e = byId[String(s.sessionId)];
    if (!e || e.topSetLoadKg == null) continue;
    if (!best || String(s.sessionDate) > String(best.date)) {
      best = { date: s.sessionDate, e1rm: e.topSetE1rmKg, load: e.topSetLoadKg, reps: e.topSetReps };
    }
  }
  return best;
}

export default function PlatesCard({ sessions, plMetrics }) {
  const rows = LIFTS
    .map(l => ({ ...l, last: lastTopSet(l.key, sessions, plMetrics) }))
    .filter(r => r.last);
  if (rows.length === 0) return null;

  return (
    <div className="chart-wrapper">
      <div className="chart-title-row">
        <span className="card-title">Plates</span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
          last top set · per side, lb, 45 lb bar
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'auto auto auto minmax(0, 1fr)',
                    columnGap: 16, rowGap: 8, alignItems: 'baseline', fontSize: 14 }}>
        {rows.map(({ key, label, last }) => {
          const { plates } = platesPerSide(last.load);
          return (
            <div key={key} style={{ display: 'contents' }}>
              <span style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                {label}
                <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 6 }}>{fmtDate(last.date)}</span>
              </span>
              <span style={{ fontWeight: 700, fontVariantNumeric: 'tabular-nums' }} title="e1RM, kg">
                {Math.round(last.e1rm)}
              </span>
              <span style={{ fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                {/* Whole kilos, like the e1RM: a load entered as plates a
                    side converts to 52.2, but the bar holds 25+10 either way. */}
                {Math.round(last.load)}×{last.reps}
              </span>
              <span style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--text-primary)' }}>
                {plates.length ? plates.join('+') : 'empty bar'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
