import { useMemo, useRef, useState, useEffect } from 'react';
import ExerciseEditor from './ExerciseEditor.jsx';
import DayDetail from './DayDetail.jsx';
import SlotSuggestion from './SlotSuggestion.jsx';

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
  onSuggestSlot, onPlaceSuggested,
}) {
  const [editing, setEditing] = useState(null); // exercise being edited
  const [detailDate, setDetailDate] = useState(null); // day sheet open for this ISO date
  const [suggestFor, setSuggestFor] = useState(null); // exercise to suggest a slot for
  const [from, to] = rangeFor(scope, anchor);
  const days = useMemo(() => datesInRange(from, to), [from, to]);
  const todayIso = iso(new Date());

  // ── pointer-based drag (mouse + touch) ──
  const dragState = useRef({ payload: null, hoverDate: null });
  const [dragging, setDragging] = useState(false);
  const [ghost, setGhost] = useState(null);        // { name, x, y }
  const [hoverDate, setHoverDate] = useState(null);
  const [hoverTier, setHoverTier] = useState(null);

  useEffect(() => {
    if (!dragging) return;
    function move(e) {
      const x = e.clientX, y = e.clientY;
      const st = dragState.current;
      // Only treat it as a drag once the pointer clears a small threshold —
      // below that it's a tap, which opens the day sheet instead.
      if (!st.moved && Math.hypot(x - st.startX, y - st.startY) > 6) {
        st.moved = true;
        setGhost({ name: st.payload?.name, x, y });   // ghost appears only on a real drag
      }
      if (!st.moved) return;
      const el = document.elementFromPoint(x, y);
      const day = el && el.closest('[data-date]');
      const hd = day ? day.getAttribute('data-date') : null;
      st.hoverDate = hd;
      setHoverDate(hd);
      // A rail group is the other thing you can drop on: dragging a pill from
      // one tier to another is how you change how often it comes up. Only a
      // pill dragged out of the rail qualifies — an occurrence belongs to a day.
      const grp = !hd && el && el.closest('[data-tier]');
      const ht = grp && st.payload?.kind === 'exercise'
        ? Number(grp.getAttribute('data-tier')) : null;
      st.hoverTier = ht;
      setHoverTier(ht);
      setGhost(g => (g ? { ...g, x, y } : g));
    }
    function up() {
      const { payload, hoverDate: hd, hoverTier: ht, moved } = dragState.current;
      if (moved) {
        if (payload && hd) onDropOnDay(payload, hd);
        else if (payload?.exerciseId && ht && ht !== payload.tier) {
          // onUpdateExercise rethrows so the editor can show the message; there
          // is no editor here, and an uncaught rejection would just be a console
          // error. The reload on success is what moves the pill, so a failure
          // leaves it in its old group — which is the feedback.
          Promise.resolve(onUpdateExercise(payload.exerciseId, { tier: ht })).catch(() => {});
        }
      } else if (payload?.date) {
        // A tap on a chip — open that day's sheet, where actions are deliberate.
        setDetailDate(payload.date);
      }
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
      setHoverTier(null);
      dragState.current = { payload: null, hoverDate: null, hoverTier: null, startX: 0, startY: 0, moved: false };
    };
  }, [dragging, onDropOnDay, onUpdateExercise]);

  function startDrag(payload, e) {
    e.preventDefault();
    dragState.current = { payload, hoverDate: null, hoverTier: null, startX: e.clientX, startY: e.clientY, moved: false };
    setDragging(true);
  }

  // occurrences + suggestions grouped by date
  const byDate = useMemo(() => {
    const m = {};
    for (const o of schedule.occurrences) (m[o.date] ||= { occ: [], sug: [] }).occ.push(o);
    for (const s of schedule.suggestions) (m[s.date] ||= { occ: [], sug: [] }).sug.push(s);
    return m;
  }, [schedule]);

  // Grouped by tier, most-frequent first. The rail used to split queue from
  // recurring, but every item is a queue item now, so that put everything in
  // one bucket. Tier is the distinction that's left, and it's the one that
  // decides how often something comes up.
  const TIER_LABELS = { 1: 'Tier 1 — most often', 2: 'Tier 2 — regular',
                       3: 'Tier 3 — occasional', 4: 'Tier 4 — rare',
                       5: 'Tier 5 — hardly ever' };
  const groups = useMemo(() => {
    const active = exercises.filter(e => e.status === 'active');
    const byTier = { 1: [], 2: [], 3: [], 4: [], 5: [] };
    for (const e of active) (byTier[e.tier] ?? byTier[2]).push(e);
    for (const t of [1, 2, 3, 4, 5]) byTier[t].sort((a, b) => a.name.localeCompare(b.name));
    return byTier;
  }, [exercises]);
  const total = [1, 2, 3, 4, 5].reduce((n, t) => n + groups[t].length, 0);

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
    const tier = ex.tier ?? 2;
    return (
      <div
        key={ex.id}
        className={`exq-pill exq-pill--tier${tier}`}
        onPointerDown={e => startDrag({ kind: 'exercise', exerciseId: ex.id, name: ex.name, tier }, e)}
        title={ex.description || ex.name}
      >
        <span className="exq-pill-name">{ex.name}</span>
        <span className="exq-pill-tag">T{tier}</span>
        <button
          className="exq-pill-edit"
          title="Suggest a slot"
          onPointerDown={e => e.stopPropagation()}
          onClick={() => setSuggestFor(ex)}
        >💡</button>
        <button
          className="exq-pill-edit"
          title="Edit exercise"
          onPointerDown={e => e.stopPropagation()}
          onClick={() => setEditing(ex)}
        >✎</button>
      </div>
    );
  }

  function renderGroup(key, title, items, tier) {
    // Rendered even when empty: an empty tier still has to be droppable.
    const empty = items.length === 0;
    const isCol = !!collapsed[key];
    return (
      <div
        className={`exq-rail-group${hoverTier === tier ? ' exq-rail-group--over' : ''}`}
        data-tier={tier}
        key={key}
      >
        <button className="exq-rail-group-hd" onClick={() => toggleGroup(key)}>
          <span className="exq-caret">{isCol ? '▸' : '▾'}</span>
          <span>{title}</span>
          <span className="exq-rail-group-count">{items.length}</span>
        </button>
        {!isCol && items.map(renderPill)}
        {!isCol && empty && <div className="exq-rail-group-empty">drop here</div>}
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
        {total === 0 ? (
          <div className="exq-rail-empty">No exercises yet — add via the bot (/add).</div>
        ) : (
          <>
            {[1, 2, 3, 4, 5].map(t => renderGroup(`tier${t}`, TIER_LABELS[t], groups[t], t))}
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
                <button className="exq-day-num" onClick={() => setDetailDate(ds)} title="Open day">{d.getDate()}</button>
                <div className="exq-day-items">
                  {/* Chips are display-only: drag to move, tap to open the day sheet.
                      Done/Remove live there, where the buttons are big and labelled
                      and can't be hit by a stray tap in a narrow cell. */}
                  {cell.occ.map(o => (
                    <div
                      key={`o${o.id}`}
                      className={`exq-chip exq-chip--${o.status}`}
                      title={o.description || o.name}
                      onPointerDown={e => startDrag({ kind: 'occurrence', id: o.id, exerciseId: o.exerciseId, date: o.date, name: o.name }, e)}
                    >
                      <span className="exq-chip-name">{o.status === 'done' ? '✓ ' : ''}{o.name}</span>
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

      {suggestFor && (
        <SlotSuggestion
          exercise={suggestFor}
          onSuggest={onSuggestSlot}
          onPlace={onPlaceSuggested}
          onClose={() => setSuggestFor(null)}
        />
      )}

      {detailDate && (() => {
        const cell = byDate[detailDate] || { occ: [], sug: [] };
        return (
          <DayDetail
            dateLabel={new Date(detailDate + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
            isPast={detailDate <= todayIso}
            occ={cell.occ}
            sug={cell.sug}
            onComplete={onComplete}
            onRemove={onRemove}
            onCommit={exId => onDropOnDay({ kind: 'suggestion', exerciseId: exId, date: detailDate }, detailDate)}
            onClose={() => setDetailDate(null)}
          />
        );
      })()}
    </div>
  );
}
