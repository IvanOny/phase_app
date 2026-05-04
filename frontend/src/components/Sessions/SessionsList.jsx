import { useState, useEffect, Fragment } from 'react';
import {
  getSessionExercises,
  getExerciseSets,
  deleteSessionExercise,
  updateExerciseSet,
  deleteExerciseSet,
} from '../../api/client.js';

const SESSION_TYPES = ['heavy_bench', 'volume_bench', 'speed_bench', 'run', 'pull', 'other'];

function readinessColor(r) {
  if (r == null) return 'var(--text-muted)';
  if (r >= 7) return 'var(--ready-green)';
  if (r >= 5) return 'var(--ready-yellow)';
  return 'var(--ready-red)';
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function toInputDate(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toISOString().slice(0, 10);
}

function formatType(type) {
  return type.replace(/_/g, ' ');
}

// ---- Set row with inline edit ----
function SetRow({ set, sessionExerciseId, onUpdated, onDeleted }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  function startEdit() {
    setForm({ reps: set.reps, loadKg: set.loadKg, isTopSet: set.isTopSet, isWorkingSet: set.isWorkingSet });
    setEditing(true);
  }

  async function saveEdit() {
    setSaving(true);
    try {
      const updated = await updateExerciseSet(sessionExerciseId, set.exerciseSetId, {
        reps: Number(form.reps),
        loadKg: Number(form.loadKg),
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
    if (!confirm('Delete this set?')) return;
    await deleteExerciseSet(sessionExerciseId, set.exerciseSetId);
    onDeleted(set.exerciseSetId);
  }

  if (editing) {
    return (
      <tr className="set-row-editing">
        <td>{set.setNumber}</td>
        <td><input type="number" value={form.loadKg} onChange={e => setForm(f => ({ ...f, loadKg: e.target.value }))} className="inline-input" style={{ width: 60 }} /></td>
        <td><input type="number" value={form.reps} onChange={e => setForm(f => ({ ...f, reps: e.target.value }))} className="inline-input" style={{ width: 50 }} /></td>
        <td><input type="checkbox" checked={form.isTopSet} onChange={e => setForm(f => ({ ...f, isTopSet: e.target.checked }))} /></td>
        <td><input type="checkbox" checked={form.isWorkingSet} onChange={e => setForm(f => ({ ...f, isWorkingSet: e.target.checked }))} /></td>
        <td>
          <button className="icon-btn" onClick={saveEdit} disabled={saving} title="Save">✓</button>
          <button className="icon-btn" onClick={() => setEditing(false)} title="Cancel">✕</button>
        </td>
      </tr>
    );
  }

  return (
    <tr className={set.isTopSet ? 'top-set-row' : ''}>
      <td>{set.setNumber}</td>
      <td>{set.loadKg}</td>
      <td>{set.reps}</td>
      <td>{set.isTopSet ? '★' : ''}</td>
      <td>{set.isWorkingSet ? '✓' : ''}</td>
      <td className="row-actions">
        <button className="icon-btn" onClick={startEdit} title="Edit set">✏</button>
        <button className="icon-btn icon-btn--danger" onClick={handleDelete} title="Delete set">🗑</button>
      </td>
    </tr>
  );
}

// ---- Expanded session detail with exercise/set edit ----
function SessionDetail({ sessionId, exercises: catalog, onExerciseDeleted }) {
  const [data, setData] = useState(null);

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
    if (!confirm(`Delete "${se.exerciseName}" and all its sets from this session?`)) return;
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

  if (!data) {
    return (
      <tr>
        <td colSpan={8} className="session-detail-cell">
          <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Loading…</span>
        </td>
      </tr>
    );
  }

  if (data.length === 0) {
    return (
      <tr>
        <td colSpan={8} className="session-detail-cell">
          <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>No exercises logged.</span>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td colSpan={8} className="session-detail-cell">
        <div className="session-detail">
          {data.map(se => (
            <div key={se.sessionExerciseId} className="exercise-block">
              <div className="exercise-block-header">
                <div className="exercise-name">{se.exerciseName}</div>
                <button
                  className="icon-btn icon-btn--danger"
                  title="Remove exercise from session"
                  onClick={() => handleDeleteExercise(se)}
                >🗑</button>
              </div>
              {se.sets.length > 0 ? (
                <table className="sets-table">
                  <thead>
                    <tr>
                      <th>Set</th>
                      <th>Load (kg)</th>
                      <th>Reps</th>
                      <th>Top set</th>
                      <th>Working</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {se.sets.map(set => (
                      <SetRow
                        key={set.exerciseSetId}
                        set={set}
                        sessionExerciseId={se.sessionExerciseId}
                        onUpdated={updated => handleSetUpdated(se.sessionExerciseId, updated)}
                        onDeleted={exerciseSetId => handleSetDeleted(se.sessionExerciseId, exerciseSetId)}
                      />
                    ))}
                  </tbody>
                </table>
              ) : (
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>No sets logged.</span>
              )}
            </div>
          ))}
        </div>
      </td>
    </tr>
  );
}

// ---- Session row with inline edit ----
function SessionRow({ session, e1rm, vol, isOpen, onToggle, onUpdated, onDeleted, exercises }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

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

  async function handleDelete(e) {
    e.stopPropagation();
    if (!confirm(`Delete session on ${formatDate(session.sessionDate)}?`)) return;
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
          <td><input type="number" min="0" step="0.1" value={form.garminOvernightHrv} onChange={e => setForm(f => ({ ...f, garminOvernightHrv: e.target.value }))} className="inline-input" style={{ width: 60 }} placeholder="—" /></td>
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
        <td className="session-type">{formatType(session.sessionType)}</td>
        <td style={{ color: readinessColor(session.eliteHrvReadiness) }}>
          {session.eliteHrvReadiness ?? '—'}
        </td>
        <td>{session.garminOvernightHrv ?? '—'}</td>
        <td>{e1rm ? e1rm.topSetE1rmKg : '—'}</td>
        <td>{vol ? vol.benchVolumeKgReps : '—'}</td>
        <td className="row-actions" onClick={e => e.stopPropagation()}>
          <button className="icon-btn" onClick={startEdit} title="Edit session">✏</button>
          <button className="icon-btn icon-btn--danger" onClick={handleDelete} title="Delete session">🗑</button>
        </td>
      </tr>
      {isOpen && (
        <SessionDetail
          sessionId={session.sessionId}
          exercises={exercises}
        />
      )}
    </Fragment>
  );
}

// ---- Filter bar ----
function FilterBar({ filters, onChange }) {
  const types = SESSION_TYPES;

  function toggleType(type) {
    const next = filters.types.includes(type)
      ? filters.types.filter(t => t !== type)
      : [...filters.types, type];
    onChange({ ...filters, types: next });
  }

  return (
    <div className="sessions-filter-bar">
      <div className="filter-section">
        <span className="filter-label">Type:</span>
        {types.map(t => (
          <button
            key={t}
            className={`filter-chip${filters.types.includes(t) ? ' active' : ''}`}
            onClick={() => toggleType(t)}
          >
            {formatType(t)}
          </button>
        ))}
      </div>
      <div className="filter-section">
        <span className="filter-label">From:</span>
        <input type="date" value={filters.fromDate} onChange={e => onChange({ ...filters, fromDate: e.target.value })} className="inline-input filter-date" />
        <span className="filter-label">To:</span>
        <input type="date" value={filters.toDate} onChange={e => onChange({ ...filters, toDate: e.target.value })} className="inline-input filter-date" />
      </div>
      {(filters.types.length < SESSION_TYPES.length || filters.fromDate || filters.toDate) && (
        <button
          className="filter-chip"
          onClick={() => onChange({ types: SESSION_TYPES, fromDate: '', toDate: '' })}
        >
          Clear filters
        </button>
      )}
    </div>
  );
}

export default function SessionsList({ sessions, e1rmMap, volumeMap, exercises, onUpdateSession, onDeleteSession }) {
  const [expanded, setExpanded] = useState(new Set());
  const [filters, setFilters] = useState({ types: SESSION_TYPES, fromDate: '', toDate: '' });

  function toggleRow(sessionId) {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(sessionId) ? next.delete(sessionId) : next.add(sessionId);
      return next;
    });
  }

  const filtered = [...sessions]
    .filter(s => filters.types.includes(s.sessionType))
    .filter(s => !filters.fromDate || s.sessionDate >= filters.fromDate)
    .filter(s => !filters.toDate || s.sessionDate <= filters.toDate)
    .sort((a, b) => new Date(b.sessionDate) - new Date(a.sessionDate));

  return (
    <div className="chart-wrapper">
      <div className="card-title">Sessions ({sessions.length})</div>
      <FilterBar filters={filters} onChange={setFilters} />
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
                <th>Elite HRV</th>
                <th>Garmin HRV</th>
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
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
