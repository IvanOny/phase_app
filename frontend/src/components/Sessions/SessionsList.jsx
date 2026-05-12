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
import ConfirmDialog from '../Common/ConfirmDialog.jsx';

const SESSION_TYPES = ['heavy_bench', 'volume_bench', 'speed_bench', 'run', 'pull', 'other'];

const TYPE_COLORS = {
  heavy_bench:  '#7c3aed',
  volume_bench: '#a855f7',
  speed_bench:  '#ec4899',
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
function SetRow({ set, displayNumber, sessionExerciseId, onUpdated, onDeleted, isAuthenticated, isBodyweight }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [bwMode, setBwMode] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  function startEdit() {
    const isBw = isBodyweight || set.loadKg === 0;
    setBwMode(isBw);
    setForm({ reps: set.reps, loadKg: isBw ? '' : set.loadKg, isTopSet: set.isTopSet, isWorkingSet: set.isWorkingSet });
    setEditing(true);
  }

  async function saveEdit() {
    setSaving(true);
    try {
      const updated = await updateExerciseSet(sessionExerciseId, set.exerciseSetId, {
        reps: Number(form.reps),
        loadKg: bwMode ? 0 : Number(form.loadKg),
        isTopSet: form.isTopSet,
        isWorkingSet: form.isWorkingSet,
      });
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

  if (editing) {
    return (
      <tr className="set-row-editing">
        <td>{displayNumber}</td>
        <td>
          <span className="load-mode-toggle">
            <button className={`load-mode-btn${!bwMode ? ' active' : ''}`} onClick={() => setBwMode(false)}>kg</button>
            <button className={`load-mode-btn${bwMode ? ' active' : ''}`} onClick={() => setBwMode(true)} title="Bodyweight — no external load">BW</button>
          </span>
          {bwMode
            ? <span className="bw-hint">Bodyweight</span>
            : <input type="number" value={form.loadKg} onChange={e => setForm(f => ({ ...f, loadKg: e.target.value }))} className="inline-input" style={{ width: 55, marginLeft: 4 }} />
          }
        </td>
        <td><input type="number" value={form.reps} onChange={e => setForm(f => ({ ...f, reps: e.target.value }))} className="inline-input" style={{ width: 50 }} /></td>
        <td><input type="checkbox" checked={form.isTopSet} onChange={e => setForm(f => ({ ...f, isTopSet: e.target.checked }))} /></td>
        <td><input type="checkbox" checked={form.isWorkingSet} onChange={e => setForm(f => ({ ...f, isWorkingSet: e.target.checked }))} /></td>
        <td>
          <button className="icon-btn" onClick={saveEdit} disabled={saving || (!bwMode && !form.loadKg) || !form.reps} title="Save">✓</button>
          <button className="icon-btn" onClick={() => setEditing(false)} title="Cancel">✕</button>
        </td>
      </tr>
    );
  }

  const displayLoad = (set.loadKg === 0 || (isBodyweight && !set.loadKg)) ? 'BW' : set.loadKg;

  return (
    <>
      <tr className={set.isTopSet ? 'top-set-row' : ''}>
        <td>{displayNumber}</td>
        <td>{displayLoad}</td>
        <td>{set.reps}</td>
        <td>{set.isTopSet ? '★' : ''}</td>
        <td>{set.isWorkingSet ? '✓' : ''}</td>
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
function AddSetRow({ sessionExerciseId, nextSetNumber, onAdded, isBodyweight }) {
  const [open, setOpen] = useState(false);
  const [bwMode, setBwMode] = useState(isBodyweight ?? false);
  const [form, setForm] = useState({ loadKg: '', reps: '', isTopSet: false, isWorkingSet: true });
  const [saving, setSaving] = useState(false);

  async function handleAdd() {
    if (!form.reps) return;
    if (!bwMode && !form.loadKg) return;
    setSaving(true);
    try {
      const created = await createExerciseSet(sessionExerciseId, {
        setNumber: nextSetNumber,
        reps: Number(form.reps),
        loadKg: bwMode ? 0 : Number(form.loadKg),
        isTopSet: form.isTopSet,
        isWorkingSet: form.isWorkingSet,
      });
      onAdded(created);
      setForm({ loadKg: '', reps: '', isTopSet: false, isWorkingSet: true });
      setOpen(false);
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <tr>
        <td colSpan={6}>
          <button className="add-inline-btn" onClick={() => setOpen(true)}>+ Add set</button>
        </td>
      </tr>
    );
  }

  return (
    <tr className="set-row-editing">
      <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{nextSetNumber}</td>
      <td>
        <span className="load-mode-toggle">
          <button className={`load-mode-btn${!bwMode ? ' active' : ''}`} onClick={() => setBwMode(false)}>kg</button>
          <button className={`load-mode-btn${bwMode ? ' active' : ''}`} onClick={() => setBwMode(true)} title="Bodyweight — no external load">BW</button>
        </span>
        {bwMode
          ? <span className="bw-hint">Bodyweight</span>
          : <input type="number" value={form.loadKg} onChange={e => setForm(f => ({ ...f, loadKg: e.target.value }))} className="inline-input" style={{ width: 55, marginLeft: 4 }} placeholder="kg" autoFocus />
        }
      </td>
      <td><input type="number" value={form.reps} onChange={e => setForm(f => ({ ...f, reps: e.target.value }))} className="inline-input" style={{ width: 50 }} placeholder="reps" autoFocus={bwMode} onKeyDown={e => e.key === 'Enter' && handleAdd()} /></td>
      <td><input type="checkbox" checked={form.isTopSet} onChange={e => setForm(f => ({ ...f, isTopSet: e.target.checked }))} title="Top set" /></td>
      <td><input type="checkbox" checked={form.isWorkingSet} onChange={e => setForm(f => ({ ...f, isWorkingSet: e.target.checked }))} title="Working set" /></td>
      <td>
        <button className="icon-btn" onClick={handleAdd} disabled={saving || (!bwMode && !form.loadKg) || !form.reps} title="Save set">✓</button>
        <button className="icon-btn" onClick={() => setOpen(false)} title="Cancel">✕</button>
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
        <td colSpan={8} className="session-detail-cell">
          <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Loading…</span>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td colSpan={8} className="session-detail-cell">
        <div className="session-detail">
          {data.length === 0 && (
            <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>No exercises logged yet.</span>
          )}
          {data.filter(se => !filterExerciseId || se.exerciseId === Number(filterExerciseId)).map(se => {
            const catalogEx = catalog.find(e => e.exerciseId === se.exerciseId);
            const isBodyweight = catalogEx?.isBodyweight ?? false;
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
                    <th>Load</th>
                    <th>Reps</th>
                    <th>Top set</th>
                    <th>Working</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {se.sets.map((set, idx) => (
                    <SetRow
                      key={set.exerciseSetId}
                      set={set}
                      displayNumber={idx + 1}
                      sessionExerciseId={se.sessionExerciseId}
                      onUpdated={updated => handleSetUpdated(se.sessionExerciseId, updated)}
                      onDeleted={exerciseSetId => handleSetDeleted(se.sessionExerciseId, exerciseSetId)}
                      isAuthenticated={isAuthenticated}
                      isBodyweight={isBodyweight}
                    />
                  ))}
                  {isAuthenticated && (
                    <AddSetRow
                      sessionExerciseId={se.sessionExerciseId}
                      nextSetNumber={se.sets.length + 1}
                      onAdded={newSet => handleSetAdded(se.sessionExerciseId, newSet)}
                      isBodyweight={isBodyweight}
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
function SessionRow({ session, e1rm, vol, isOpen, onToggle, onUpdated, onDeleted, exercises, filterExerciseId, isAuthenticated }) {
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
    });
    setEditing(true);
  }

  async function saveEdit(e) {
    e.stopPropagation();
    setSaving(true);
    try {
      const payload = {
        sessionDate: form.sessionDate,
        sessionType: form.sessionType,
        eliteHrvReadiness: form.eliteHrvReadiness !== '' ? Number(form.eliteHrvReadiness) : null,
        garminOvernightHrv: form.garminOvernightHrv !== '' ? Number(form.garminOvernightHrv) : null,
        notes: form.notes || null,
      };
      const updated = await onUpdated(session.sessionId, payload);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    await onDeleted(session.sessionId);
  }

  if (editing) {
    return (
      <>
        <tr className="session-row session-row--editing">
          <td></td>
          <td><input type="date" value={form.sessionDate} onChange={e => setForm(f => ({ ...f, sessionDate: e.target.value }))} className="inline-input" /></td>
          <td>
            <select value={form.sessionType} onChange={e => setForm(f => ({ ...f, sessionType: e.target.value }))} className="inline-input">
              {SESSION_TYPES.map(t => <option key={t} value={t}>{formatType(t)}</option>)}
            </select>
          </td>
          <td><input type="number" min="0" max="10" step="0.1" value={form.eliteHrvReadiness} onChange={e => setForm(f => ({ ...f, eliteHrvReadiness: e.target.value }))} className="inline-input" style={{ width: 60 }} placeholder="—" /></td>
          <td colSpan={2}>
            <input value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} className="inline-input" style={{ width: '100%' }} placeholder="Notes…" />
          </td>
          <td>
            <button className="icon-btn" onClick={saveEdit} disabled={saving} title="Save">✓</button>
            <button className="icon-btn" onClick={e => { e.stopPropagation(); setEditing(false); }} title="Cancel">✕</button>
          </td>
        </tr>
      </>
    );
  }

  return (
    <Fragment>
      <tr className="session-row" onClick={onToggle}>
        <td className="expand-icon">{isOpen ? '▾' : '▸'}</td>
        <td>
          <div>{formatDate(session.sessionDate)}</div>
          {session.notes && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{session.notes}</div>}
        </td>
        <td className="session-type">
          <span className="type-dot" style={{ background: TYPE_COLORS[session.sessionType] ?? '#64748b' }} />
          {formatType(session.sessionType)}
        </td>
        <td style={{ color: readinessColor(session.eliteHrvReadiness) }}>
          {session.eliteHrvReadiness ?? '—'}
        </td>
        <td>{e1rm ? e1rm.topSetE1rmKg : '—'}</td>
        <td>{vol ? vol.benchVolumeKgReps : '—'}</td>
        <td className="row-actions" onClick={e => e.stopPropagation()}>
          {isAuthenticated && (
            <>
              <button className="icon-btn" onClick={startEdit} title="Edit session">✏</button>
              <button className="icon-btn icon-btn--danger" onClick={e => { e.stopPropagation(); setConfirmOpen(true); }} title="Delete session">🗑</button>
            </>
          )}
        </td>
      </tr>
      {isOpen && (
        <SessionDetail
          sessionId={session.sessionId}
          exercises={exercises}
          filterExerciseId={filterExerciseId}
          isAuthenticated={isAuthenticated}
        />
      )}
      {confirmOpen && (
        <ConfirmDialog
          message={`Delete session on ${formatDate(session.sessionDate)}?`}
          onConfirm={async () => { setConfirmOpen(false); await handleDelete(); }}
          onCancel={() => setConfirmOpen(false)}
        />
      )}
    </Fragment>
  );
}

// ---- Filter bar ----
function FilterBar({ filters, onChange, exercises }) {
  const lastTap = useRef({ type: null, time: 0 });
  const allTypesSelected = filters.types.length === SESSION_TYPES.length;
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
          onClick={() => onChange({ ...filters, types: SESSION_TYPES })}
        >
          All
        </button>
        {SESSION_TYPES.map(t => (
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
      {isActive && (
        <button
          className="filter-chip"
          onClick={() => onChange({ types: SESSION_TYPES, exerciseId: '' })}
        >
          Clear filters
        </button>
      )}
    </div>
  );
}

export default function SessionsList({ sessions, e1rmMap, volumeMap, exercises, exerciseVolumes, onUpdateSession, onDeleteSession, isAuthenticated }) {
  const [expanded, setExpanded] = useState(new Set());
  const [filters, setFilters] = useState({ types: SESSION_TYPES, exerciseId: '' });

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
  const allTypesSelected = filters.types.length === SESSION_TYPES.length;
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
    // Clear exercise filter if it's no longer available after a type change
    const nextAllTypes = next.types.length === SESSION_TYPES.length;
    if (next.exerciseId && !nextAllTypes) {
      const matchingSessionIds = new Set(
        sessions.filter(s => next.types.includes(s.sessionType)).map(s => s.sessionId)
      );
      const exerciseIds = new Set();
      (exerciseVolumes ?? []).forEach(ev => {
        ev.sessions.forEach(s => {
          if (matchingSessionIds.has(s.sessionId)) exerciseIds.add(ev.exerciseId);
        });
      });
      if (!exerciseIds.has(Number(next.exerciseId))) {
        next = { ...next, exerciseId: '' };
      }
    }
    setFilters(next);
  }

  function toggleRow(sessionId) {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(sessionId) ? next.delete(sessionId) : next.add(sessionId);
      return next;
    });
  }

  const filtered = [...sessions]
    .filter(s => filters.types.includes(s.sessionType))
    .filter(s => {
      if (!filters.exerciseId) return true;
      const exIds = sessionExercisesMap[s.sessionId];
      if (exIds === undefined) return true;
      return exIds.includes(Number(filters.exerciseId));
    })
    .sort((a, b) => new Date(b.sessionDate) - new Date(a.sessionDate));

  // Auto-expand all matching sessions when an exercise filter is active
  useEffect(() => {
    if (filters.exerciseId) {
      setExpanded(new Set(filtered.map(s => s.sessionId)));
    }
  }, [filters.exerciseId, filtered.map(s => s.sessionId).join(',')]);

  return (
    <div className="chart-wrapper">
      <div className="card-title">Sessions ({sessions.length})</div>
      <FilterBar filters={filters} onChange={handleFiltersChange} exercises={availableExercises} />
      {filtered.length === 0 ? (
        <div className="chart-empty">
          {sessions.length === 0 ? 'No sessions logged for this phase' : 'No sessions match the current filters'}
        </div>
      ) : (
        <div className="sessions-table-wrap">
          <table className="sessions-table">
            <thead>
              <tr>
                <th></th>
                <th>Date</th>
                <th>Type</th>
                <th>Readiness</th>
                <th>e1RM (kg)</th>
                <th>Volume (kg·reps)</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(s => (
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
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
