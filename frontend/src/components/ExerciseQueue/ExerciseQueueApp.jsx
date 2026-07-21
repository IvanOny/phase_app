import { useState, useEffect, useCallback } from 'react';
import './ExerciseQueue.css';
import {
  setExqToken,
  getExqExercises,
  getExqSchedule,
  createOccurrence,
  moveOccurrence,
  deleteOccurrence,
  completeOccurrence,
  updateExqExercise,
  deleteExqExercise,
  suggestSlot,
} from '../../api/exqClient.js';
import ScheduleCalendar from './ScheduleCalendar.jsx';
import ExerciseLog from './ExerciseLog.jsx';
import ExerciseStats from './ExerciseStats.jsx';
import CoachChat from './CoachChat.jsx';

const TABS = [
  { id: 'calendar', label: 'Calendar' },
  { id: 'log', label: 'Log' },
  { id: 'stats', label: 'Stats' },
  { id: 'coach', label: 'Coach' },
];

// Monday-start week containing `d`.
function startOfWeek(d) {
  const x = new Date(d);
  const dow = (x.getDay() + 6) % 7; // Mon=0
  x.setDate(x.getDate() - dow);
  x.setHours(0, 0, 0, 0);
  return x;
}
function iso(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// [from, to] ISO strings for the visible range.
function rangeFor(scope, anchor) {
  if (scope === 'week') {
    const s = startOfWeek(anchor);
    const e = new Date(s); e.setDate(s.getDate() + 6);
    return [iso(s), iso(e)];
  }
  // month: pad to full weeks (6 rows)
  const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  const s = startOfWeek(first);
  const e = new Date(s); e.setDate(s.getDate() + 41);
  return [iso(s), iso(e)];
}

export default function ExerciseQueueApp({ token }) {
  const [tab, setTab] = useState('calendar');
  const [scope, setScope] = useState('week');
  // Default drag behaviour, remembered between visits.
  const [dragMode, setDragMode] = useState(() => localStorage.getItem('exq-drag-mode') || 'single');
  const [anchor, setAnchor] = useState(() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; });
  const [exercises, setExercises] = useState([]);
  const [schedule, setSchedule] = useState({ occurrences: [], suggestions: [] });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { setExqToken(token); }, [token]);
  useEffect(() => { document.title = 'Movement Snacks'; }, []);

  const loadExercises = useCallback(async () => {
    try { setExercises(await getExqExercises()); }
    catch (e) { setError(e.message); }
  }, []);

  const loadSchedule = useCallback(async () => {
    const [from, to] = rangeFor(scope, anchor);
    try { setSchedule(await getExqSchedule(from, to)); }
    catch (e) { setError(e.message); }
  }, [scope, anchor]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      await Promise.all([loadExercises(), loadSchedule()]);
      setLoading(false);
    })();
  }, [loadExercises, loadSchedule]);

  // The bot edits the same data — re-sync when the tab comes back into focus so
  // exercises added/completed in Telegram show up without a manual reload.
  useEffect(() => {
    function resync() {
      if (document.hidden) return;
      loadExercises();
      loadSchedule();
    }
    window.addEventListener('focus', resync);
    document.addEventListener('visibilitychange', resync);
    return () => {
      window.removeEventListener('focus', resync);
      document.removeEventListener('visibilitychange', resync);
    };
  }, [loadExercises, loadSchedule]);

  // ── mutations ──
  const handleDropOnDay = useCallback(async (payload, dateStr) => {
    try {
      const mode = payload.mode || dragMode;
      if (payload.kind === 'occurrence') {
        if (payload.date === dateStr) return;
        await moveOccurrence(payload.id, dateStr, mode);
      } else {
        // suggestion or rail exercise → commit a manual occurrence.
        // payload.date (a suggestion's original day) lets 'single' tombstone it.
        await createOccurrence(payload.exerciseId, dateStr, mode, payload.date || null);
      }
      await Promise.all([loadSchedule(), loadExercises()]);
    } catch (e) { setError(e.message); }
  }, [loadSchedule, loadExercises, dragMode]);

  const handleComplete = useCallback(async (occId) => {
    try { await completeOccurrence(occId); await Promise.all([loadSchedule(), loadExercises()]); }
    catch (e) { setError(e.message); }
  }, [loadSchedule, loadExercises]);

  const handleRemove = useCallback(async (occId) => {
    try { await deleteOccurrence(occId); await loadSchedule(); }
    catch (e) { setError(e.message); }
  }, [loadSchedule]);

  const handleUpdateExercise = useCallback(async (id, patch) => {
    await updateExqExercise(id, patch);           // let the editor surface errors
    await Promise.all([loadExercises(), loadSchedule()]);
  }, [loadExercises, loadSchedule]);

  const handleDeleteExercise = useCallback(async (id) => {
    try { await deleteExqExercise(id); await Promise.all([loadExercises(), loadSchedule()]); }
    catch (e) { setError(e.message); }
  }, [loadExercises, loadSchedule]);

  const handleSuggestSlot = useCallback((id, avoid) => suggestSlot(id, avoid), []);
  const handlePlaceSuggested = useCallback(async (id, date) => {
    await createOccurrence(id, date, 'single');
    await loadSchedule();
  }, [loadSchedule]);

  function shift(delta) {
    const d = new Date(anchor);
    if (scope === 'week') d.setDate(d.getDate() + delta * 7);
    else d.setMonth(d.getMonth() + delta);
    setAnchor(d);
  }
  function goToday() { const d = new Date(); d.setHours(0, 0, 0, 0); setAnchor(d); }

  return (
    <div className="exq-app">
      <header className="exq-header">
        <span className="exq-title">🍎 Movement Snacks</span>
        <nav className="exq-tabs">
          {TABS.map(t => (
            <button key={t.id} className={`exq-tab${tab === t.id ? ' active' : ''}`} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      {error && <div className="exq-error" onClick={() => setError(null)}>{error} (tap to dismiss)</div>}

      {loading ? (
        <div className="exq-loading">Loading…</div>
      ) : tab === 'calendar' ? (
        <ScheduleCalendar
          scope={scope}
          setScope={setScope}
          dragMode={dragMode}
          setDragMode={m => { setDragMode(m); localStorage.setItem('exq-drag-mode', m); }}
          anchor={anchor}
          onShift={shift}
          onToday={goToday}
          rangeFor={rangeFor}
          exercises={exercises}
          schedule={schedule}
          onDropOnDay={handleDropOnDay}
          onComplete={handleComplete}
          onRemove={handleRemove}
          onUpdateExercise={handleUpdateExercise}
          onDeleteExercise={handleDeleteExercise}
          onSuggestSlot={handleSuggestSlot}
          onPlaceSuggested={handlePlaceSuggested}
        />
      ) : tab === 'log' ? (
        <ExerciseLog />
      ) : tab === 'stats' ? (
        <ExerciseStats />
      ) : (
        <CoachChat />
      )}
    </div>
  );
}
