import { useMemo } from 'react';

function iso(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
const WD = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

function datesInRange(fromIso, toIso) {
  const out = [];
  const d = new Date(fromIso + 'T00:00:00');
  const end = new Date(toIso + 'T00:00:00');
  while (d <= end) { out.push(new Date(d)); d.setDate(d.getDate() + 1); }
  return out;
}

function setDrag(e, payload) {
  e.dataTransfer.setData('text/plain', JSON.stringify(payload));
  e.dataTransfer.effectAllowed = 'move';
}

export default function ScheduleCalendar({
  scope, setScope, anchor, onShift, onToday, rangeFor,
  exercises, schedule, onDropOnDay, onComplete, onRemove,
}) {
  const [from, to] = rangeFor(scope, anchor);
  const days = useMemo(() => datesInRange(from, to), [from, to]);
  const todayIso = iso(new Date());

  // occurrences + suggestions grouped by date
  const byDate = useMemo(() => {
    const m = {};
    for (const o of schedule.occurrences) (m[o.date] ||= { occ: [], sug: [] }).occ.push(o);
    for (const s of schedule.suggestions) (m[s.date] ||= { occ: [], sug: [] }).sug.push(s);
    return m;
  }, [schedule]);

  // Rail: active exercises, queue first (opportunistic — no auto date otherwise)
  const rail = useMemo(() =>
    exercises.filter(e => e.status === 'active')
      .sort((a, b) => (a.scheduleType === 'queue' ? -1 : 1) - (b.scheduleType === 'queue' ? -1 : 1)),
    [exercises]);

  const title = scope === 'week'
    ? `Week of ${new Date(from + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`
    : `${MONTHS[anchor.getMonth()]} ${anchor.getFullYear()}`;

  function allowDrop(e) { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }
  function onDrop(e, dateStr) {
    e.preventDefault();
    e.currentTarget.classList.remove('exq-day--over');
    try { onDropOnDay(JSON.parse(e.dataTransfer.getData('text/plain')), dateStr); } catch { /* ignore */ }
  }

  return (
    <div className="exq-cal">
      <aside className="exq-rail">
        <div className="exq-rail-title">Exercises</div>
        <div className="exq-rail-hint">Drag onto a day →</div>
        {rail.map(ex => (
          <div
            key={ex.id}
            className={`exq-pill exq-pill--${ex.scheduleType}`}
            draggable
            onDragStart={e => setDrag(e, { kind: 'exercise', exerciseId: ex.id })}
            title={ex.description || ex.name}
          >
            {ex.name}
            <span className="exq-pill-tag">{ex.scheduleType === 'queue' ? 'queue' : ex.scheduleType === 'acquisition' ? 'acq' : `${ex.repeatIntervalDays}d`}</span>
          </div>
        ))}
        {rail.length === 0 && <div className="exq-rail-empty">No exercises yet — add via the bot (/add).</div>}
      </aside>

      <div className="exq-cal-main">
        <div className="exq-cal-toolbar">
          <div className="exq-nav">
            <button className="exq-btn" onClick={() => onShift(-1)}>‹</button>
            <button className="exq-btn" onClick={onToday}>Today</button>
            <button className="exq-btn" onClick={() => onShift(1)}>›</button>
          </div>
          <span className="exq-cal-title">{title}</span>
          <div className="exq-scope">
            <button className={`exq-btn${scope === 'week' ? ' active' : ''}`} onClick={() => setScope('week')}>Week</button>
            <button className={`exq-btn${scope === 'month' ? ' active' : ''}`} onClick={() => setScope('month')}>Month</button>
          </div>
        </div>

        <div className="exq-weekdays">
          {WD.map(w => <div key={w} className="exq-weekday">{w}</div>)}
        </div>

        <div className={`exq-grid exq-grid--${scope}`}>
          {days.map(d => {
            const ds = iso(d);
            const cell = byDate[ds] || { occ: [], sug: [] };
            const inMonth = scope === 'week' || d.getMonth() === anchor.getMonth();
            return (
              <div
                key={ds}
                className={`exq-day${ds === todayIso ? ' exq-day--today' : ''}${inMonth ? '' : ' exq-day--muted'}`}
                onDragOver={allowDrop}
                onDragEnter={e => e.currentTarget.classList.add('exq-day--over')}
                onDragLeave={e => e.currentTarget.classList.remove('exq-day--over')}
                onDrop={e => onDrop(e, ds)}
              >
                <div className="exq-day-num">{d.getDate()}</div>
                <div className="exq-day-items">
                  {cell.occ.map(o => (
                    <div
                      key={`o${o.id}`}
                      className={`exq-chip exq-chip--${o.status}`}
                      draggable
                      onDragStart={e => setDrag(e, { kind: 'occurrence', id: o.id, exerciseId: o.exerciseId, date: o.date })}
                    >
                      <span className="exq-chip-name">{o.name}</span>
                      <span className="exq-chip-actions">
                        {o.status !== 'done' && <button className="exq-chip-btn" title="Mark done" onClick={() => onComplete(o.id)}>✓</button>}
                        <button className="exq-chip-btn" title="Remove" onClick={() => onRemove(o.id)}>✕</button>
                      </span>
                    </div>
                  ))}
                  {cell.sug.map(s => (
                    <div
                      key={`s${s.exerciseId}-${s.date}`}
                      className="exq-chip exq-chip--suggestion"
                      draggable
                      onDragStart={e => setDrag(e, { kind: 'suggestion', exerciseId: s.exerciseId, date: s.date })}
                      title="Cadence suggestion — drag to commit"
                    >
                      <span className="exq-chip-name">{s.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
