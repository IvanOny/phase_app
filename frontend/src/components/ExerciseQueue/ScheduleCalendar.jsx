import { useMemo, useRef, useState, useEffect } from 'react';

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

export default function ScheduleCalendar({
  scope, setScope, anchor, onShift, onToday, rangeFor,
  exercises, schedule, onDropOnDay, onComplete, onRemove,
}) {
  const [from, to] = rangeFor(scope, anchor);
  const days = useMemo(() => datesInRange(from, to), [from, to]);
  const todayIso = iso(new Date());

  // ── pointer-based drag (mouse + touch) ──
  const dragState = useRef({ payload: null, hoverDate: null });
  const [dragging, setDragging] = useState(false);
  const [ghost, setGhost] = useState(null);        // { name, x, y }
  const [hoverDate, setHoverDate] = useState(null);

  useEffect(() => {
    if (!dragging) return;
    function move(e) {
      const x = e.clientX, y = e.clientY;
      const el = document.elementFromPoint(x, y);
      const day = el && el.closest('[data-date]');
      const hd = day ? day.getAttribute('data-date') : null;
      dragState.current.hoverDate = hd;
      setHoverDate(hd);
      setGhost(g => (g ? { ...g, x, y } : g));
    }
    function up() {
      const { payload, hoverDate: hd } = dragState.current;
      if (payload && hd) onDropOnDay(payload, hd);
      setDragging(false);
    }
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
    window.addEventListener('pointercancel', up);
    return () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
      window.removeEventListener('pointercancel', up);
      setGhost(null);
      setHoverDate(null);
      dragState.current = { payload: null, hoverDate: null };
    };
  }, [dragging, onDropOnDay]);

  function startDrag(payload, e) {
    e.preventDefault();
    dragState.current = { payload, hoverDate: null };
    setGhost({ name: payload.name, x: e.clientX, y: e.clientY });
    setDragging(true);
  }

  // occurrences + suggestions grouped by date
  const byDate = useMemo(() => {
    const m = {};
    for (const o of schedule.occurrences) (m[o.date] ||= { occ: [], sug: [] }).occ.push(o);
    for (const s of schedule.suggestions) (m[s.date] ||= { occ: [], sug: [] }).sug.push(s);
    return m;
  }, [schedule]);

  const rail = useMemo(() =>
    exercises.filter(e => e.status === 'active')
      .sort((a, b) => (a.scheduleType === 'queue' ? -1 : 1) - (b.scheduleType === 'queue' ? -1 : 1)),
    [exercises]);

  const title = scope === 'week'
    ? `Week of ${new Date(from + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`
    : `${MONTHS[anchor.getMonth()]} ${anchor.getFullYear()}`;

  return (
    <div className={`exq-cal${dragging ? ' exq-cal--dragging' : ''}`}>
      <aside className="exq-rail">
        <div className="exq-rail-title">Exercises</div>
        <div className="exq-rail-hint">Drag onto a day →</div>
        {rail.map(ex => (
          <div
            key={ex.id}
            className={`exq-pill exq-pill--${ex.scheduleType}`}
            onPointerDown={e => startDrag({ kind: 'exercise', exerciseId: ex.id, name: ex.name }, e)}
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

        <div className="exq-legend">
          <span className="exq-legend-item"><i className="exq-sw exq-sw--planned" />planned</span>
          <span className="exq-legend-item"><i className="exq-sw exq-sw--suggestion" />suggested (drag to commit)</span>
          <span className="exq-legend-item"><i className="exq-sw exq-sw--done" />done</span>
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
                data-date={ds}
                className={`exq-day${ds === todayIso ? ' exq-day--today' : ''}${inMonth ? '' : ' exq-day--muted'}${hoverDate === ds ? ' exq-day--over' : ''}`}
              >
                <div className="exq-day-num">{d.getDate()}</div>
                <div className="exq-day-items">
                  {cell.occ.map(o => (
                    <div
                      key={`o${o.id}`}
                      className={`exq-chip exq-chip--${o.status}`}
                      onPointerDown={e => startDrag({ kind: 'occurrence', id: o.id, exerciseId: o.exerciseId, date: o.date, name: o.name }, e)}
                    >
                      <span className="exq-chip-name">{o.name}</span>
                      <span className="exq-chip-actions">
                        {/* Only past/today can be completed — you can't have done a future day. */}
                        {o.status !== 'done' && o.date <= todayIso && (
                          <button className="exq-chip-btn" title="Mark done" onPointerDown={e => e.stopPropagation()} onClick={() => onComplete(o.id)}>✓</button>
                        )}
                        <button className="exq-chip-btn" title="Remove" onPointerDown={e => e.stopPropagation()} onClick={() => onRemove(o.id)}>✕</button>
                      </span>
                    </div>
                  ))}
                  {cell.sug.map(s => (
                    <div
                      key={`s${s.exerciseId}-${s.date}`}
                      className="exq-chip exq-chip--suggestion"
                      onPointerDown={e => startDrag({ kind: 'suggestion', exerciseId: s.exerciseId, date: s.date, name: s.name }, e)}
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

      {ghost && (
        <div className="exq-ghost" style={{ left: ghost.x, top: ghost.y }}>{ghost.name}</div>
      )}
    </div>
  );
}
