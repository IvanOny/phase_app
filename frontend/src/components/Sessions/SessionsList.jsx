import { useState, useEffect, useRef, useMemo, Fragment } from 'react';
import {
  getSessionExercises,
  getExerciseSets,
  createSessionExercise,
  deleteSessionExercise,
  createExerciseSet,
  updateExerciseSet,
  deleteExerciseSet,
} from '../../api/client.js';
import { formatDuration, formatPace, parseDuration, parsePace, runSummary } from '../../utils/runMetrics.js';
import ConfirmDialog from '../Common/ConfirmDialog.jsx';
import PhaseCalendar from './PhaseCalendar.jsx';

const SESSION_TYPES_BENCH = ['heavy_bench', 'volume_bench', 'speed_bench', 'run', 'pull'];
const SESSION_TYPES_PL    = ['squat', 'deadlift', 'run', 'other'];
const SESSION_TYPES_DEFAULT = SESSION_TYPES_BENCH;

const TYPE_COLORS = {
  heavy_bench:  '#7c3aed',
  volume_bench: '#a855f7',
  speed_bench:  '#ec4899',
  squat:        '#6366f1',
  deadlift:     '#10b981',
  mixed:        '#f59e0b',
  run:          '#22c55e',
  pull:         '#3b82f6',
  other:        '#64748b',
};

const EXERCISE_PALETTE = [
  '#818cf8', '#34d399', '#f97316', '#fbbf24',
  '#a78bfa', '#fb7185', '#38bdf8', '#4ade80',
  '#fb923c', '#e879f9', '#2dd4bf', '#facc15',
];

function exerciseColor(exerciseId) {
  return EXERCISE_PALETTE[((exerciseId ?? 0) - 1) % EXERCISE_PALETTE.length];
}

function readinessColor(r) {
  if (r == null) return 'var(--text-muted)';
  if (r >= 7) return 'var(--ready-green)';
  if (r >= 5) return 'var(--ready-yellow)';
  return 'var(--ready-red)';
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const m = String(dateStr).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[3]}.${m[2]}.${m[1]}`;
  return String(dateStr);
}

function toInputDate(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toISOString().slice(0, 10);
}

function formatType(type) {
  return type.replace(/_/g, ' ');
}

// ---- Set row with inline edit ----
function SetRow({ set, displayNumber, sessionExerciseId, onUpdated, onDeleted, isAuthenticated, isBodyweight, isTimed, isTopSet }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [bwMode, setBwMode] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  function startEdit() {
    if (isTimed) {
      setForm({ timeMinutes: set.timeMinutes ?? '' });
    } else {
      const isBw = isBodyweight || set.loadKg === 0;
      setBwMode(isBw);
      setForm({ reps: set.reps, loadKg: isBw ? '' : set.loadKg, isWorkingSet: set.isWorkingSet, isTopSet: isTopSet });
    }
    setEditing(true);
  }

  async function saveEdit() {
    setSaving(true);
    try {
      const payload = isTimed
        ? { timeMinutes: Number(form.timeMinutes) }
        : { reps: Number(form.reps), loadKg: bwMode ? 0 : Number(form.loadKg), isTopSet: Boolean(form.isTopSet), isWorkingSet: Boolean(form.isWorkingSet) };
      const updated = await updateExerciseSet(sessionExerciseId, set.exerciseSetId, payload);
      onUpdated(updated);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    await deleteExerciseSet(sessionExerciseId, set.exerciseSetId);
    onDeleted(set.exerciseSetId);
  }

  const displayLoad = (set.loadKg === 0 || (isBodyweight && !set.loadKg)) ? '—' : set.loadKg;

  if (editing) {
    return (
      <tr className="set-row-editing">
        <td colSpan={4} style={{ padding: 0 }}>
          <div className="set-edit-inner">
            <span className="set-edit-num">{displayNumber}</span>
            {isTimed ? (
              <input type="number" step="0.5" min="0" value={form.timeMinutes} onChange={e => setForm(f => ({ ...f, timeMinutes: e.target.value }))} className="inline-input" style={{ width: 60 }} placeholder="min" autoFocus />
            ) : (
              <>
                <span className="load-mode-toggle">
                  <button className={`load-mode-btn${!bwMode ? ' active' : ''}`} onClick={() => setBwMode(false)}>kg</button>
                  <button className={`load-mode-btn${bwMode ? ' active' : ''}`} onClick={() => setBwMode(true)} title="Bodyweight — no external load">BW</button>
                </span>
                {bwMode
                  ? <span className="bw-hint">Bodyweight</span>
                  : <input type="number" value={form.loadKg} onChange={e => setForm(f => ({ ...f, loadKg: e.target.value }))} className="inline-input" style={{ width: 55 }} />
                }
                <input type="number" value={form.reps} onChange={e => setForm(f => ({ ...f, reps: e.target.value }))} className="inline-input" style={{ width: 50 }} placeholder="reps" />
                <span className="set-flags">
                  <button type="button" className={`flag-badge flag-top${form.isTopSet ? '' : ' flag-inactive'}`} onClick={() => setForm(f => ({ ...f, isTopSet: !f.isTopSet }))} title="Toggle top set">TOP</button>
                  <button type="button" className={`flag-badge flag-work${form.isWorkingSet ? '' : ' flag-inactive'}`} onClick={() => setForm(f => ({ ...f, isWorkingSet: !f.isWorkingSet }))} title="Toggle working set">W</button>
                </span>
              </>
            )}
            <div className="session-edit-actions">
              <button className="icon-btn" onClick={saveEdit} disabled={saving || (isTimed ? !form.timeMinutes : (!bwMode && !form.loadKg) || !form.reps)} title="Save">✓</button>
              <button className="icon-btn" onClick={() => setEditing(false)} title="Cancel">✕</button>
            </div>
          </div>
        </td>
      </tr>
    );
  }

  return (
    <>
      <tr className={isTopSet ? 'top-set-row' : ''}>
        <td>{displayNumber}</td>
        {isTimed
          ? <td colSpan={2}>{set.timeMinutes != null ? `${set.timeMinutes} min` : '—'}</td>
          : <><td>{displayLoad}</td><td>{set.reps}</td></>
        }
        <td className="row-actions">
          {isAuthenticated && (
            <>
              <button className="icon-btn" onClick={startEdit} title="Edit set">✏</button>
              <button className="icon-btn icon-btn--danger" onClick={() => setConfirmOpen(true)} title="Delete set">🗑</button>
            </>
          )}
        </td>
      </tr>
      {confirmOpen && (
        <ConfirmDialog
          message="Delete this set?"
          onConfirm={async () => { setConfirmOpen(false); await handleDelete(); }}
          onCancel={() => setConfirmOpen(false)}
        />
      )}
    </>
  );
}

// ---- Add-set inline form ----
function AddSetRow({ sessionExerciseId, nextSetNumber, onAdded, isBodyweight, isTimed }) {
  const [open, setOpen] = useState(false);
  const [bwMode, setBwMode] = useState(isBodyweight ?? false);
  const [form, setForm] = useState({ loadKg: '', reps: '', timeMinutes: '' });
  const [saving, setSaving] = useState(false);

  async function handleAdd() {
    if (isTimed) {
      if (!form.timeMinutes) return;
    } else {
      if (!form.reps) return;
      if (!bwMode && !form.loadKg) return;
    }
    setSaving(true);
    try {
      const payload = isTimed
        ? { setNumber: nextSetNumber, timeMinutes: Number(form.timeMinutes), isWorkingSet: true }
        : { setNumber: nextSetNumber, reps: Number(form.reps), loadKg: bwMode ? 0 : Number(form.loadKg), isTopSet: false, isWorkingSet: true };
      const created = await createExerciseSet(sessionExerciseId, payload);
      onAdded(created);
      setForm({ loadKg: '', reps: '', timeMinutes: '' });
      setOpen(false);
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <tr>
        <td colSpan={4}>
          <button className="add-inline-btn" onClick={() => setOpen(true)}>+ Add set</button>
        </td>
      </tr>
    );
  }

  return (
    <tr className="set-row-editing">
      <td colSpan={4} style={{ padding: 0 }}>
        <div className="set-edit-inner">
          <span className="set-edit-num">{nextSetNumber}</span>
          {isTimed ? (
            <input type="number" step="0.5" min="0" value={form.timeMinutes} onChange={e => setForm(f => ({ ...f, timeMinutes: e.target.value }))} className="inline-input" style={{ width: 60 }} placeholder="min" autoFocus onKeyDown={e => e.key === 'Enter' && handleAdd()} />
          ) : (
            <>
              <span className="load-mode-toggle">
                <button className={`load-mode-btn${!bwMode ? ' active' : ''}`} onClick={() => setBwMode(false)}>kg</button>
                <button className={`load-mode-btn${bwMode ? ' active' : ''}`} onClick={() => setBwMode(true)} title="Bodyweight — no external load">BW</button>
              </span>
              {bwMode
                ? <span className="bw-hint">Bodyweight</span>
                : <input type="number" value={form.loadKg} onChange={e => setForm(f => ({ ...f, loadKg: e.target.value }))} className="inline-input" style={{ width: 55 }} placeholder="kg" autoFocus />
              }
              <input type="number" value={form.reps} onChange={e => setForm(f => ({ ...f, reps: e.target.value }))} className="inline-input" style={{ width: 50 }} placeholder="reps" autoFocus={bwMode} onKeyDown={e => e.key === 'Enter' && handleAdd()} />
            </>
          )}
          <div className="session-edit-actions">
            <button className="icon-btn" onClick={handleAdd} disabled={saving || (isTimed ? !form.timeMinutes : (!bwMode && !form.loadKg) || !form.reps)} title="Save set">✓</button>
            <button className="icon-btn" onClick={() => setOpen(false)} title="Cancel">✕</button>
          </div>
        </div>
      </td>
    </tr>
  );
}

// ---- Add-exercise inline form ----
function AddExerciseRow({ sessionId, catalog, nextOrder, onAdded }) {
  const [open, setOpen] = useState(false);
  const [exerciseId, setExerciseId] = useState('');
  const [saving, setSaving] = useState(false);

  async function handleAdd() {
    if (!exerciseId) return;
    setSaving(true);
    try {
      const se = await createSessionExercise(sessionId, {
        exerciseId: Number(exerciseId),
        exerciseOrder: nextOrder,
      });
      const exercise = catalog.find(e => e.exerciseId === Number(exerciseId));
      onAdded({ ...se, exerciseName: exercise?.exerciseName ?? `Exercise ${exerciseId}`, sets: [] });
      setExerciseId('');
      setOpen(false);
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button className="add-inline-btn" style={{ marginTop: 8 }} onClick={() => setOpen(true)}>
        + Add exercise
      </button>
    );
  }

  return (
    <div className="add-exercise-row">
      <select value={exerciseId} onChange={e => setExerciseId(e.target.value)} className="inline-input" autoFocus>
        <option value="">Select exercise…</option>
        {catalog.map(ex => (
          <option key={ex.exerciseId} value={ex.exerciseId}>{ex.exerciseName}</option>
        ))}
      </select>
      <button className="icon-btn" onClick={handleAdd} disabled={saving || !exerciseId} title="Add">✓</button>
      <button className="icon-btn" onClick={() => setOpen(false)} title="Cancel">✕</button>
    </div>
  );
}

// ---- Expanded session detail with exercise/set edit ----
function SessionDetail({ sessionId, exercises: catalog, filterExerciseId, onExerciseDeleted, isAuthenticated }) {
  const [data, setData] = useState(null);
  const [confirmExercise, setConfirmExercise] = useState(null);

  useEffect(() => {
    loadData();
  }, [sessionId]);

  async function loadData() {
    const sessionExercises = await getSessionExercises(sessionId);
    const withSets = await Promise.all(
      sessionExercises.map(async se => {
        const sets = await getExerciseSets(se.sessionExerciseId);
        const exercise = catalog.find(e => e.exerciseId === se.exerciseId);
        return { ...se, exerciseName: exercise?.exerciseName ?? `Exercise ${se.exerciseId}`, sets };
      })
    );
    withSets.sort((a, b) => a.exerciseOrder - b.exerciseOrder);
    setData(withSets);
  }

  async function handleDeleteExercise(se) {
    try {
      await deleteSessionExercise(sessionId, se.sessionExerciseId);
      setData(prev => prev.filter(x => x.sessionExerciseId !== se.sessionExerciseId));
      onExerciseDeleted?.();
    } catch {
      alert('Failed to delete exercise.');
    }
  }

  function handleSetUpdated(sessionExerciseId, updated) {
    setData(prev => prev.map(se =>
      se.sessionExerciseId === sessionExerciseId
        ? { ...se, sets: se.sets.map(s => s.exerciseSetId === updated.exerciseSetId ? { ...s, ...updated } : s) }
        : se
    ));
  }

  function handleSetDeleted(sessionExerciseId, exerciseSetId) {
    setData(prev => prev.map(se =>
      se.sessionExerciseId === sessionExerciseId
        ? { ...se, sets: se.sets.filter(s => s.exerciseSetId !== exerciseSetId) }
        : se
    ));
  }

  function handleSetAdded(sessionExerciseId, newSet) {
    setData(prev => prev.map(se =>
      se.sessionExerciseId === sessionExerciseId
        ? { ...se, sets: [...se.sets, newSet] }
        : se
    ));
  }

  function handleExerciseAdded(newSe) {
    setData(prev => [...prev, newSe]);
  }

  if (!data) {
    return (
      <tr>
        <td colSpan={4} className="session-detail-cell">
          <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Loading…</span>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td colSpan={4} className="session-detail-cell">
        <div className="session-detail">
          {data.length === 0 && (
            <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>No exercises logged yet.</span>
          )}
          {data.filter(se => !filterExerciseId || se.exerciseId === Number(filterExerciseId)).map(se => {
            const catalogEx = catalog.find(e => e.exerciseId === se.exerciseId);
            const isBodyweight = catalogEx?.isBodyweight ?? false;
            const isTimed = catalogEx?.isTimed ?? false;
            return (
            <div key={se.sessionExerciseId} className="exercise-block">
              <div className="exercise-block-header">
                <div className="exercise-name" style={{ color: exerciseColor(se.exerciseId) }}>
                  <span className="exercise-color-dot" style={{ background: exerciseColor(se.exerciseId) }} />
                  {se.exerciseName}
                </div>
                {isAuthenticated && (
                  <button
                    className="icon-btn icon-btn--danger"
                    title="Remove exercise from session"
                    onClick={() => setConfirmExercise(se)}
                  >🗑</button>
                )}
              </div>
              <table className="sets-table">
                <thead>
                  <tr>
                    <th>Set</th>
                    {isTimed ? <th colSpan={2}>Time (min)</th> : <><th>Load</th><th>Reps</th></>}
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {se.sets.filter(s => s.isWorkingSet).map((set, idx) => (
                    <SetRow
                      key={set.exerciseSetId}
                      set={set}
                      displayNumber={idx + 1}
                      sessionExerciseId={se.sessionExerciseId}
                      onUpdated={updated => handleSetUpdated(se.sessionExerciseId, updated)}
                      onDeleted={exerciseSetId => handleSetDeleted(se.sessionExerciseId, exerciseSetId)}
                      isAuthenticated={isAuthenticated}
                      isBodyweight={isBodyweight}
                      isTimed={isTimed}
                      isTopSet={Boolean(set.isTopSet)}
                    />
                  ))}
                  {isAuthenticated && (
                    <AddSetRow
                      sessionExerciseId={se.sessionExerciseId}
                      nextSetNumber={se.sets.length + 1}
                      onAdded={newSet => handleSetAdded(se.sessionExerciseId, newSet)}
                      isBodyweight={isBodyweight}
                      isTimed={isTimed}
                    />
                  )}
                </tbody>
              </table>
            </div>
            );
          })}
          {isAuthenticated && (
            <AddExerciseRow
              sessionId={sessionId}
              catalog={catalog}
              nextOrder={data.length + 1}
              onAdded={handleExerciseAdded}
            />
          )}
        </div>
      </td>
      {confirmExercise && (
        <ConfirmDialog
          message={`Delete "${confirmExercise.exerciseName}" and all its sets?`}
          onConfirm={async () => { const se = confirmExercise; setConfirmExercise(null); await handleDeleteExercise(se); }}
          onCancel={() => setConfirmExercise(null)}
        />
      )}
    </tr>
  );
}

// ---- Session row with inline edit ----
function SessionRow({ session, e1rm, vol, isOpen, onToggle, onUpdated, onDeleted, exercises, filterExerciseId, isAuthenticated, rowRef, onBackToCalendar }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  function startEdit(e) {
    e.stopPropagation();
    setForm({
      sessionDate: toInputDate(session.sessionDate),
      sessionType: session.sessionType,
      eliteHrvReadiness: session.eliteHrvReadiness ?? '',
      garminOvernightHrv: session.garminOvernightHrv ?? '',
      notes: session.notes || '',
      runType: session.runType ?? '',
      distanceKm: session.distanceKm ?? '',
      durationDisplay: session.durationSeconds != null ? formatDuration(session.durationSeconds) : '',
      avgHr: session.avgHr ?? '',
      maxHr: session.maxHr ?? '',
      paceDisplay: session.avgPaceSecPerKm != null ? formatPace(session.avgPaceSecPerKm).replace(' /km', '') : '',
      gapDisplay: session.avgGapPaceSecPerKm != null ? formatPace(session.avgGapPaceSecPerKm).replace(' /km', '') : '',
      avgCadence: session.avgCadence ?? '',
      avgGctMs: session.avgGctMs ?? '',
      avgVoCm: session.avgVoCm ?? '',
      ascentM: session.ascentM ?? '',
      rpe: session.rpe ?? '',
    });
    setEditing(true);
  }

  async function saveEdit(e) {
    e.stopPropagation();
    setSaving(true);
    try {
      const isRun = form.sessionType === 'run';
      const payload = {
        sessionDate: form.sessionDate,
        sessionType: form.sessionType,
        eliteHrvReadiness: form.eliteHrvReadiness !== '' ? Number(form.eliteHrvReadiness) : null,
        garminOvernightHrv: form.garminOvernightHrv !== '' ? Number(form.garminOvernightHrv) : null,
        notes: form.notes || null,
        ...(isRun ? {
          runType: form.runType || null,
          distanceKm: form.distanceKm !== '' ? Number(form.distanceKm) : null,
          durationSeconds: parseDuration(form.durationDisplay),
          avgHr: form.avgHr !== '' ? Number(form.avgHr) : null,
          maxHr: form.maxHr !== '' ? Number(form.maxHr) : null,
          avgPaceSecPerKm: parsePace(form.paceDisplay),
          avgGapPaceSecPerKm: parsePace(form.gapDisplay),
          avgCadence: form.avgCadence !== '' ? Number(form.avgCadence) : null,
          avgGctMs: form.avgGctMs !== '' ? Number(form.avgGctMs) : null,
          avgVoCm: form.avgVoCm !== '' ? Number(form.avgVoCm) : null,
          ascentM: form.ascentM !== '' ? Number(form.ascentM) : null,
          rpe: form.rpe !== '' ? Number(form.rpe) : null,
        } : {}),
      };
      await onUpdated(session.sessionId, payload);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    await onDeleted(session.sessionId);
  }

  if (editing) {
    const isRunEdit = form.sessionType === 'run';
    return (
      <tr className="session-row session-row--editing">
        <td colSpan={4} style={{ padding: 0 }}>
          <div className="session-edit-inner">
            <div className="session-edit-row1">
              <input type="date" value={form.sessionDate} onChange={e => setForm(f => ({ ...f, sessionDate: e.target.value }))} className="inline-input" />
              <select value={form.sessionType} onChange={e => setForm(f => ({ ...f, sessionType: e.target.value }))} className="inline-input">
                {['squat','deadlift','mixed','heavy_bench','volume_bench','speed_bench','run','pull','rest','other'].map(t => <option key={t} value={t}>{formatType(t)}</option>)}
              </select>
              <input type="number" min="0" max="10" step="0.1" value={form.eliteHrvReadiness} onChange={e => setForm(f => ({ ...f, eliteHrvReadiness: e.target.value }))} className="inline-input" style={{ width: 60 }} placeholder="HRV" />
              <div className="session-edit-actions">
                <button className="icon-btn" onClick={saveEdit} disabled={saving} title="Save">✓</button>
                <button className="icon-btn" onClick={e => { e.stopPropagation(); setEditing(false); }} title="Cancel">✕</button>
              </div>
            </div>
            {isRunEdit ? (
              <>
                <div className="session-edit-row2 session-edit-run-row">
                  <input type="text" value={form.runType} onChange={e => setForm(f => ({ ...f, runType: e.target.value }))} className="inline-input" style={{ width: 90 }} placeholder="run type" title="Run type (easy, tempo…)" />
                  <input type="number" min="0" step="0.01" value={form.distanceKm} onChange={e => setForm(f => ({ ...f, distanceKm: e.target.value }))} className="inline-input" style={{ width: 65 }} placeholder="km" title="Distance (km)" />
                  <input type="text" value={form.durationDisplay} onChange={e => setForm(f => ({ ...f, durationDisplay: e.target.value }))} className="inline-input" style={{ width: 62 }} placeholder="MM:SS" title="Duration (MM:SS)" />
                  <input type="text" value={form.paceDisplay} onChange={e => setForm(f => ({ ...f, paceDisplay: e.target.value }))} className="inline-input" style={{ width: 52 }} placeholder="pace" title="Avg pace (M:SS/km)" />
                  <input type="text" value={form.gapDisplay} onChange={e => setForm(f => ({ ...f, gapDisplay: e.target.value }))} className="inline-input" style={{ width: 52 }} placeholder="GAP" title="Grade Adjusted Pace (M:SS/km)" />
                  <input type="number" min="0" value={form.avgHr} onChange={e => setForm(f => ({ ...f, avgHr: e.target.value }))} className="inline-input" style={{ width: 50 }} placeholder="HR" title="Avg HR (bpm)" />
                  <input type="number" min="0" value={form.maxHr} onChange={e => setForm(f => ({ ...f, maxHr: e.target.value }))} className="inline-input" style={{ width: 50 }} placeholder="maxHR" title="Max HR (bpm)" />
                </div>
                <div className="session-edit-row2 session-edit-run-row">
                  <input type="number" min="0" value={form.avgCadence} onChange={e => setForm(f => ({ ...f, avgCadence: e.target.value }))} className="inline-input" style={{ width: 58 }} placeholder="spm" title="Avg cadence (steps/min)" />
                  <input type="number" min="0" value={form.avgGctMs} onChange={e => setForm(f => ({ ...f, avgGctMs: e.target.value }))} className="inline-input" style={{ width: 58 }} placeholder="GCT ms" title="Avg ground contact time (ms)" />
                  <input type="number" min="0" step="0.1" value={form.avgVoCm} onChange={e => setForm(f => ({ ...f, avgVoCm: e.target.value }))} className="inline-input" style={{ width: 58 }} placeholder="VO cm" title="Avg vertical oscillation (cm)" />
                  <input type="number" min="0" value={form.ascentM} onChange={e => setForm(f => ({ ...f, ascentM: e.target.value }))} className="inline-input" style={{ width: 58 }} placeholder="↑ m" title="Ascent (m)" />
                  <input type="number" min="1" max="10" step="0.5" value={form.rpe} onChange={e => setForm(f => ({ ...f, rpe: e.target.value }))} className="inline-input" style={{ width: 52 }} placeholder="RPE" title="RPE (1–10)" />
                  <input value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} className="inline-input" style={{ flex: 1 }} placeholder="Notes…" />
                </div>
              </>
            ) : (
              <div className="session-edit-row2">
                <input value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} className="inline-input" style={{ width: '100%' }} placeholder="Notes…" />
              </div>
            )}
          </div>
        </td>
      </tr>
    );
  }

  const isPlanned = Boolean(session.isPlanned);

  return (
    <Fragment>
      <tr
        ref={rowRef}
        className={`session-row${isPlanned ? ' session-row--planned' : ''}`}
        onClick={isPlanned ? undefined : onToggle}
        style={isPlanned ? { cursor: 'default', opacity: 0.65 } : {}}
      >
        <td className="expand-icon">
          {isPlanned
            ? <span className="planned-badge">plan</span>
            : <span className={`expand-caret${isOpen ? ' expand-caret--open' : ''}`} />
          }
        </td>
        <td className="session-date-cell">
          <div>{formatDate(session.sessionDate)}</div>
          {session.sessionType === 'run' && runSummary(session) ? (
            <div className="session-notes-preview session-run-summary">
              {runSummary(session)}
            </div>
          ) : session.notes ? (
            <div className={`session-notes-preview${isOpen ? ' session-notes-preview--expanded' : ''}`}>
              {session.notes}
            </div>
          ) : null}
        </td>
        <td className="session-type">
          <span className="type-dot" style={{ background: TYPE_COLORS[session.sessionType] ?? '#64748b' }} />
          {formatType(session.sessionType)}
        </td>
        <td className="row-actions" onClick={e => e.stopPropagation()}>
          {isAuthenticated && (
            <>
              {!isPlanned && <button className="icon-btn" onClick={startEdit} title="Edit session">✏</button>}
              <button className="icon-btn icon-btn--danger" onClick={e => { e.stopPropagation(); setConfirmOpen(true); }} title="Delete session">🗑</button>
            </>
          )}
        </td>
      </tr>
      {isOpen && !isPlanned && onBackToCalendar && (
        <tr>
          <td colSpan={4} style={{ paddingBottom: 0, paddingLeft: 'var(--space-6)', paddingTop: 'var(--space-4)' }}>
            <button className="sessions-back-to-cal-btn" onClick={onBackToCalendar}>
              ↑ Schedule &amp; Filters
            </button>
          </td>
        </tr>
      )}
      {isOpen && !isPlanned && session.sessionType === 'run' && (
        <tr>
          <td colSpan={4} className="session-detail-cell">
            <div className="session-detail session-run-detail">
              {session.runType && <div className="run-type-badge">{session.runType}</div>}
              <div className="run-metrics-grid">
                {session.distanceKm != null && <div className="run-metric-item"><span className="run-metric-label">Distance</span><span className="run-metric-value">{session.distanceKm} km</span></div>}
                {session.durationSeconds != null && <div className="run-metric-item"><span className="run-metric-label">Duration</span><span className="run-metric-value">{formatDuration(session.durationSeconds)}</span></div>}
                {session.avgPaceSecPerKm != null && <div className="run-metric-item"><span className="run-metric-label">Avg pace</span><span className="run-metric-value">{formatPace(session.avgPaceSecPerKm)}</span></div>}
                {session.avgGapPaceSecPerKm != null && <div className="run-metric-item"><span className="run-metric-label">GAP</span><span className="run-metric-value">{formatPace(session.avgGapPaceSecPerKm)}</span></div>}
                {session.avgHr != null && <div className="run-metric-item"><span className="run-metric-label">Avg HR</span><span className="run-metric-value">{session.avgHr} bpm</span></div>}
                {session.maxHr != null && <div className="run-metric-item"><span className="run-metric-label">Max HR</span><span className="run-metric-value">{session.maxHr} bpm</span></div>}
                {session.avgCadence != null && <div className="run-metric-item"><span className="run-metric-label">Cadence</span><span className="run-metric-value">{session.avgCadence} spm</span></div>}
                {session.avgGctMs != null && <div className="run-metric-item"><span className="run-metric-label">GCT</span><span className="run-metric-value">{session.avgGctMs} ms</span></div>}
                {session.avgVoCm != null && <div className="run-metric-item"><span className="run-metric-label">Vert. osc.</span><span className="run-metric-value">{session.avgVoCm} cm</span></div>}
                {session.ascentM != null && <div className="run-metric-item"><span className="run-metric-label">Ascent</span><span className="run-metric-value">{session.ascentM} m</span></div>}
                {session.rpe != null && <div className="run-metric-item"><span className="run-metric-label">RPE</span><span className="run-metric-value">{session.rpe}/10</span></div>}
              </div>
              {session.notes && <div className="run-metrics-notes">{session.notes}</div>}
            </div>
          </td>
        </tr>
      )}
      {isOpen && !isPlanned && session.sessionType !== 'run' && (
        <SessionDetail
          sessionId={session.sessionId}
          exercises={exercises}
          filterExerciseId={filterExerciseId}
          isAuthenticated={isAuthenticated}
        />
      )}
      {confirmOpen && (
        <ConfirmDialog
          message={isPlanned
            ? `Remove planned session on ${formatDate(session.sessionDate)}?`
            : `Delete session on ${formatDate(session.sessionDate)}?`}
          onConfirm={async () => { setConfirmOpen(false); await handleDelete(); }}
          onCancel={() => setConfirmOpen(false)}
        />
      )}
    </Fragment>
  );
}

// ---- Filter bar ----
function FilterBar({ filters, onChange, exercises, sessionTypes = SESSION_TYPES_DEFAULT }) {
  const lastTap = useRef({ type: null, time: 0 });
  const allTypesSelected = filters.types.length === sessionTypes.length;
  const isActive = !allTypesSelected || filters.exerciseId;

  function handleTypeClick(type, e) {
    const multiSelect = e.ctrlKey || e.metaKey;
    if (multiSelect) {
      // Ctrl/Cmd — add or remove from selection
      const next = filters.types.includes(type)
        ? filters.types.filter(t => t !== type)
        : [...filters.types, type];
      onChange({ ...filters, types: next.length ? next : [type] });
    } else {
      // Single click — solo-select this type
      onChange({ ...filters, types: [type] });
    }
  }

  function handleTypeTouchEnd(type, e) {
    const now = Date.now();
    const DOUBLE_TAP_MS = 300;
    if (lastTap.current.type === type && now - lastTap.current.time < DOUBLE_TAP_MS) {
      // Double-tap — toggle multi-select
      e.preventDefault();
      const next = filters.types.includes(type)
        ? filters.types.filter(t => t !== type)
        : [...filters.types, type];
      onChange({ ...filters, types: next.length ? next : [type] });
      lastTap.current = { type: null, time: 0 };
    } else {
      lastTap.current = { type, time: now };
    }
  }

  return (
    <div className="sessions-filter-bar">
      <div className="filter-section">
        <span className="filter-label">Type:</span>
        <button
          className={`filter-chip${allTypesSelected ? ' active' : ''}`}
          onClick={() => onChange({ ...filters, types: sessionTypes })}
        >
          All
        </button>
        {sessionTypes.map(t => (
          <button
            key={t}
            className={`filter-chip${filters.types.includes(t) ? ' active' : ''}`}
            onClick={e => handleTypeClick(t, e)}
            onTouchEnd={e => handleTypeTouchEnd(t, e)}
          >
            {formatType(t)}
          </button>
        ))}
      </div>
      {!filters.types.every(t => t === 'run') && (
        <div className="filter-section">
          <span className="filter-label">Exercise:</span>
          <select
            value={filters.exerciseId}
            onChange={e => onChange({ ...filters, exerciseId: e.target.value })}
            className="inline-input"
          >
            <option value="">All</option>
            {exercises.map(ex => (
              <option key={ex.exerciseId} value={ex.exerciseId}>{ex.exerciseName}</option>
            ))}
          </select>
        </div>
      )}
      {isActive && (
        <button
          className="filter-chip"
          onClick={() => onChange({ types: sessionTypes, exerciseId: '' })}
        >
          Clear filters
        </button>
      )}
    </div>
  );
}

export default function SessionsList({ phase, sessions, e1rmMap, volumeMap, exercises, exerciseVolumes, onUpdateSession, onDeleteSession, onSessionCreated, isAuthenticated, focusFilter }) {
  const sessionTypes = phase?.phaseType === 'powerlifting' ? SESSION_TYPES_PL : SESSION_TYPES_DEFAULT;
  const [expanded, setExpanded] = useState(new Set());
  const [filters, setFilters] = useState({ types: sessionTypes, exerciseId: '' });
  const [showAll, setShowAll] = useState(false);
  const rowRefs = useRef({});
  const wrapperRef = useRef(null);
  const tableRef = useRef(null);

  // Derive session→[exerciseIds] map from exerciseVolumes (already fetched by parent)
  // instead of firing N individual GET /v1/sessions/{id}/exercises requests.
  const sessionExercisesMap = useMemo(() => {
    const map = {};
    (exerciseVolumes ?? []).forEach(ev => {
      ev.sessions.forEach(s => {
        if (!map[s.sessionId]) map[s.sessionId] = [];
        map[s.sessionId].push(ev.exerciseId);
      });
    });
    return map;
  }, [exerciseVolumes]);

  // Exercises that appear in at least one session matching the active type filter
  const allTypesSelected = filters.types.length === sessionTypes.length;
  const availableExercises = useMemo(() => {
    if (allTypesSelected) return exercises;
    const matchingSessionIds = new Set(
      sessions.filter(s => filters.types.includes(s.sessionType)).map(s => s.sessionId)
    );
    const exerciseIds = new Set();
    (exerciseVolumes ?? []).forEach(ev => {
      ev.sessions.forEach(s => {
        if (matchingSessionIds.has(s.sessionId)) exerciseIds.add(ev.exerciseId);
      });
    });
    return exercises.filter(e => exerciseIds.has(e.exerciseId));
  }, [sessions, filters.types, exerciseVolumes, exercises, allTypesSelected]);

  function handleFiltersChange(next) {
    const typesChanged = next.types.join(',') !== filters.types.join(',');
    if (typesChanged && next.exerciseId) {
      next = { ...next, exerciseId: '' };
    }
    setFilters(next);
    const isRunOnly = next.types.length === 1 && next.types[0] === 'run';
    if (isRunOnly) {
      const runIds = sessions.filter(s => s.sessionType === 'run' && !s.isPlanned).map(s => s.sessionId);
      setExpanded(new Set(runIds));
      setShowAll(true);
    }
  }

  function toggleRow(sessionId) {
    setExpanded(prev =>
      prev.has(sessionId) ? new Set() : new Set([sessionId])
    );
    setFilters(f => ({ ...f, exerciseId: '' }));
  }

  function handleCalendarSelectSession(sessionId) {
    // Clear all filters so the session is visible regardless of type or exercise filter
    setFilters({ types: sessionTypes, exerciseId: '' });
    setShowAll(true);
    setExpanded(new Set([sessionId]));
    setTimeout(() => {
      const el = rowRefs.current[sessionId];
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
  }

  function handleCalendarSessionCreated(session) {
    onSessionCreated?.(session);
  }

  async function handleCalendarSessionDeleted(sessionId) {
    await onDeleteSession?.(sessionId);
  }

  const baseFiltered = [...sessions]
    .filter(s => filters.types.includes(s.sessionType))
    .filter(s => {
      if (!filters.exerciseId) return true;
      if (s.isPlanned) return false; // planned sessions have no logged exercises
      const exIds = sessionExercisesMap[s.sessionId];
      if (exIds === undefined) return false;
      return exIds.includes(Number(filters.exerciseId));
    });

  const executedFiltered = baseFiltered
    .filter(s => !s.isPlanned)
    .sort((a, b) => new Date(b.sessionDate) - new Date(a.sessionDate));

  const plannedFiltered = baseFiltered
    .filter(s => s.isPlanned)
    .sort((a, b) => new Date(a.sessionDate) - new Date(b.sessionDate));

  const filtered = [...executedFiltered, ...plannedFiltered];

  const VISIBLE_COUNT = 3;
  const forceShowAll = Boolean(filters.exerciseId);
  const effectiveShowAll = showAll || forceShowAll;
  const visibleSessions = effectiveShowAll ? filtered : executedFiltered.slice(0, VISIBLE_COUNT);
  const hiddenCount = filtered.length - visibleSessions.length;

  // Auto-expand all matching sessions when an exercise filter is active
  useEffect(() => {
    if (filters.exerciseId) {
      setExpanded(new Set(filtered.map(s => s.sessionId)));
      setTimeout(() => {
        tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 80);
    }
  }, [filters.exerciseId, filtered.map(s => s.sessionId).join(',')]);

  // Apply exercise+type filters triggered externally (e.g. from NextStep card)
  useEffect(() => {
    if (!focusFilter) return;
    setFilters({ types: [focusFilter.sessionType], exerciseId: focusFilter.exerciseId ? String(focusFilter.exerciseId) : '' });
    const targetId = focusFilter.sessionId ?? [...sessions]
      .filter(s => !s.isPlanned && s.sessionType === focusFilter.sessionType)
      .sort((a, b) => new Date(b.sessionDate) - new Date(a.sessionDate))[0]?.sessionId;
    if (targetId) {
      setShowAll(true);
      setExpanded(new Set([targetId]));
    }
    setTimeout(() => {
      tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
  }, [focusFilter]);

  const realCount    = executedFiltered.length;
  const plannedCount = plannedFiltered.length;

  return (
    <div className="chart-wrapper" ref={wrapperRef}>
      <div className="sessions-cal-filter-layout">
        {phase && (
          <div className="sessions-cal-col">
            <PhaseCalendar
              phase={phase}
              sessions={sessions}
              exerciseVolumes={exerciseVolumes}
              activeTypes={filters.types}
              onSelectSession={handleCalendarSelectSession}
              onSessionCreated={handleCalendarSessionCreated}
              onSessionDeleted={handleCalendarSessionDeleted}
              isAuthenticated={isAuthenticated}
            />
          </div>
        )}
        <div className="sessions-filter-col">
          <FilterBar filters={filters} onChange={handleFiltersChange} exercises={availableExercises} sessionTypes={sessionTypes} />
        </div>
      </div>
      <div style={{ marginBottom: 'var(--space-3)', marginTop: 'var(--space-2)' }}>
        <div className="card-title" style={{ marginBottom: 0 }}>
          {realCount} done{plannedCount > 0 ? ` · ${plannedCount} planned` : ''}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="chart-empty">
          {sessions.length === 0 ? 'No sessions logged for this phase' : 'No sessions match the current filters'}
        </div>
      ) : (
        <div className="sessions-table-wrap" ref={tableRef}>
          <table className="sessions-table">
            <thead>
              <tr>
                <th></th>
                <th>Date</th>
                <th>Type</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {visibleSessions.map(s => (
                <SessionRow
                  key={s.sessionId}
                  session={s}
                  e1rm={e1rmMap[s.sessionId]}
                  vol={volumeMap[s.sessionId]}
                  isOpen={expanded.has(s.sessionId)}
                  onToggle={() => toggleRow(s.sessionId)}
                  onUpdated={onUpdateSession}
                  onDeleted={onDeleteSession}
                  exercises={exercises}
                  filterExerciseId={filters.exerciseId}
                  isAuthenticated={isAuthenticated}
                  rowRef={el => { rowRefs.current[s.sessionId] = el; }}
                  onBackToCalendar={phase ? () => wrapperRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }) : undefined}
                />
              ))}
            </tbody>
          </table>
          {!forceShowAll && hiddenCount > 0 && (
            <button className="sessions-show-more-btn" onClick={() => setShowAll(true)}>
              Show {hiddenCount} more
            </button>
          )}
          {!forceShowAll && showAll && (
            <button className="sessions-show-more-btn" onClick={() => setShowAll(false)}>
              Show less
            </button>
          )}
        </div>
      )}
    </div>
  );
}
