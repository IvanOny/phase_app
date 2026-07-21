import { useMemo, useRef, useState, useEffect } from 'react';
import ExerciseEditor from './ExerciseEditor.jsx';

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
  scope, setScope, anchor, onShift, onToday, rangeFor, dragMode, setDragMode,
  exercises, schedule, onDropOnDay, onComplete, onRemove, onUpdateExercise, onDeleteExercise,
}) {
  const [editing, setEditing] = useState(null); // exercise being edited
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

  // Days between repeats — sorts the recurring group most-frequent first.
  const freq = e => e.scheduleType === 'acquisition' ? (e.acqIntervalDays ?? 9999) : (e.repeatIntervalDays ?? 9999);
  const groups = useMemo(() => {
    const active = exercises.filter(e => e.status === 'active');
    const queue = active.filter(e => e.scheduleType === 'queue')
      .sort((a, b) => a.name.localeCompare(b.name));
    const recurring = active.filter(e => e.scheduleType !== 'queue')
      .sort((a, b) => (freq(a) - freq(b)) || a.name.localeCompare(b.name));
    return { queue, recurring };
  }, [exercises]);

  const [collapsed, setCollapsed] = useState(() => {
    try { return JSON.parse(localStorage.getItem('exq-rail-collapsed') || '{}'); }
    catch { return {}; }
  });
  function toggleGroup(k) {
    setCollapsed(c => {
      const next = { ...c, [k]: !c[k] };
      localStorage.setItem('exq-rail-collapsed', JSON.stringify(next));
      return next;
    });
  }

  function renderPill(ex) {
    const tag = ex.scheduleType === 'queue' ? 'queue' : `${freq(ex)}d`;
    return (
      <div
        key={ex.id}
        className={`exq-pill exq-pill--${ex.scheduleType}`}
        onPointerDown={e => startDrag({ kind: 'exercise', exerciseId: ex.id, name: ex.name }, e)}
        title={ex.description || ex.name}
      >
        <span className="exq-pill-name">{ex.name}</span>
        <span className="exq-pill-tag">{tag}</span>
        <button
          className="exq-pill-edit"
          title="Edit exercise"
          onPointerDown={e => e.stopPropagation()}
          onClick={() => setEditing(ex)}
        >✎</button>
      </div>
    );
  }

  function renderGroup(key, title, items) {
    if (items.length === 0) return null;
    const isCol = !!collapsed[key];
    return (
      <div className="exq-rail-group" key={key}>
        <button className="exq-rail-group-hd" onClick={() => toggleGroup(key)}>
          <span className="exq-caret">{isCol ? '▸' : '▾'}</span>
          <span>{title}</span>
          <span className="exq-rail-group-count">{items.length}</span>
        </button>
        {!isCol && items.map(renderPill)}
      </div>
    );
  }

  const title = scope === 'week'
    ? `Week of ${new Date(from + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`
    : `${MONTHS[anchor.getMonth()]} ${anchor.getFullYear()}`;

  return (
    <div className={`exq-cal${dragging ? ' exq-cal--dragging' : ''}`}>
      <aside className="exq-rail">
        <div className="exq-rail-title">Exercises</div>
        <div className="exq-rail-hint">Drag onto a day →</div>
        {groups.queue.length === 0 && groups.recurring.length === 0 ? (
          <div className="exq-rail-empty">No exercises yet — add via the bot (/add).</div>
        ) : (
          <>
            {renderGroup('queue', 'Queue', groups.queue)}
            {renderGroup('recurring', 'Recurring', groups.recurring)}
          </>
        )}
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

        <div className="exq-controls">
          <div className="exq-dragmode">
            <span className="exq-dragmode-lbl">On drag:</span>
            <button
              className={`exq-btn${dragMode === 'shift' ? ' active' : ''}`}
              onClick={() => setDragMode('shift')}
              title="Future occurrences follow, keeping the cadence"
            >Shift series</button>
            <button
              className={`exq-btn${dragMode === 'single' ? ' active' : ''}`}
              onClick={() => setDragMode('single')}
              title="Only this one moves; future occurrences stay put"
            >Only this</button>
          </div>
          <div className="exq-legend">
            <span className="exq-legend-item"><i className="exq-sw exq-sw--planned" />planned</span>
            <span className="exq-legend-item"><i className="exq-sw exq-sw--suggestion" />suggested</span>
            <span className="exq-legend-item"><i className="exq-sw exq-sw--done" />done</span>
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
                data-date={ds}
                className={`exq-day${ds === todayIso ? ' exq-day--today' : ''}${inMonth ? '' : ' exq-day--muted'}${hoverDate === ds ? ' exq-day--over' : ''}`}
              >
                <div className="exq-day-num">{d.getDate()}</div>
                <div className="exq-day-items">
                  {cell.occ.map(o => (
                    <div
                      key={`o${o.id}`}
                      className={`exq-chip exq-chip--${o.status}`}
                      title={o.description || o.name}
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
                      title={`${s.description || s.name} — cadence suggestion, drag to commit`}
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

      {editing && (
        <ExerciseEditor
          exercise={editing}
          onSave={onUpdateExercise}
          onDelete={onDeleteExercise}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}
