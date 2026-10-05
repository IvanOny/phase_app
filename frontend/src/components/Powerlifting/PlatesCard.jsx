// What to put on the bar: the last top set of each barbell lift, with the
// plates it takes per side. The bench phase's Next Step card answered "what
// next"; this answers "what did I last lift, and how do I load it again".
// How a side is built -- 25s, then 35s -- lives in utils/plates.js.
import { platesPerSide } from '../../utils/plates.js';
import { planDay } from '../../utils/nextLift.js';

const LIFTS = {
  squat:    'Squat',
  bench:    'Bench press',
  deadlift: 'Deadlift',
};

// Rows in training order, today's day first: an A day reads bench, squat,
// then deadlift; a B day reads deadlift, then bench, squat. Which day it is
// comes from the same rule Quick log uses.
const ORDER = {
  A: ['bench', 'squat', 'deadlift'],
  B: ['deadlift', 'bench', 'squat'],
};

// The lift metrics as the A/B rule wants them: one entry per training day,
// newest first, naming the lifts done that day. The roles stand in for
// exercise ids, so no second fetch is needed.
function trainingDays(sessions, plMetrics) {
  const byDate = new Map();
  for (const s of sessions || []) {
    const date = String(s.sessionDate).slice(0, 10);
    for (const role of ['squat', 'bench', 'deadlift', 'pullup']) {
      if (plMetrics?.e1rm?.[role]?.[String(s.sessionId)]) {
        if (!byDate.has(date)) byDate.set(date, new Set());
        byDate.get(date).add(role);
      }
    }
  }
  return [...byDate.entries()]
    .sort((a, b) => (a[0] < b[0] ? 1 : -1))
    .map(([date, roles]) => ({ date, exerciseIds: [...roles] }));
}
const ROLE_IDS = { squat: 'squat', bench: 'bench', deadlift: 'deadlift', pullup: 'pullup' };

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
  const today = new Date().toISOString().slice(0, 10);
  const { type } = planDay(today, trainingDays(sessions, plMetrics), ROLE_IDS);
  const rows = ORDER[type]
    .map(key => ({ key, label: LIFTS[key], last: lastTopSet(key, sessions, plMetrics) }))
    .filter(r => r.last);
  if (rows.length === 0) return null;

  return (
    <div className="chart-wrapper">
      <div className="chart-title-row">
        <span className="card-title">Plates</span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
          today: day {type} · last top set · per side, lb, 45 lb bar
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
