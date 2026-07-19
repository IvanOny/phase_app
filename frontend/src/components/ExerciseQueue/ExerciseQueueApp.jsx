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
} from '../../api/exqClient.js';
import ScheduleCalendar from './ScheduleCalendar.jsx';
import ExerciseLog from './ExerciseLog.jsx';
import ExerciseStats from './ExerciseStats.jsx';

const TABS = [
  { id: 'calendar', label: 'Calendar' },
  { id: 'log', label: 'Log' },
  { id: 'stats', label: 'Stats' },
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
  const [anchor, setAnchor] = useState(() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; });
  const [exercises, setExercises] = useState([]);
  const [schedule, setSchedule] = useState({ occurrences: [], suggestions: [] });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { setExqToken(token); }, [token]);

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

  // ── mutations ──
  const handleDropOnDay = useCallback(async (payload, dateStr) => {
    try {
      if (payload.kind === 'occurrence') {
        if (payload.date === dateStr) return;
        await moveOccurrence(payload.id, dateStr);
      } else {
        // suggestion or exercise from the rail → commit a manual occurrence
        await createOccurrence(payload.exerciseId, dateStr);
      }
      await loadSchedule();
    } catch (e) { setError(e.message); }
  }, [loadSchedule]);

  const handleComplete = useCallback(async (occId) => {
    try { await completeOccurrence(occId); await Promise.all([loadSchedule(), loadExercises()]); }
    catch (e) { setError(e.message); }
  }, [loadSchedule, loadExercises]);

  const handleRemove = useCallback(async (occId) => {
    try { await deleteOccurrence(occId); await loadSchedule(); }
    catch (e) { setError(e.message); }
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
        <span className="exq-title">🗓 Exercise Planner</span>
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
          anchor={anchor}
          onShift={shift}
          onToday={goToday}
          rangeFor={rangeFor}
          exercises={exercises}
          schedule={schedule}
          onDropOnDay={handleDropOnDay}
          onComplete={handleComplete}
          onRemove={handleRemove}
        />
      ) : tab === 'log' ? (
        <ExerciseLog />
      ) : (
        <ExerciseStats />
      )}
    </div>
  );
}
