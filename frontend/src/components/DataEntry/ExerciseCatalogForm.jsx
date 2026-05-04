import { useState } from 'react';

function ExerciseRow({ exercise, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  function startEdit() {
    setForm({
      exerciseName: exercise.exerciseName,
      isBarbellBenchPress: exercise.isBarbellBenchPress,
      isBodyweight: exercise.isBodyweight,
    });
    setEditing(true);
  }

  async function saveEdit() {
    setSaving(true);
    try {
      await onUpdate(exercise.exerciseId, form);
      setEditing(false);
    } catch {
      alert('Failed to save exercise.');
    } finally {
      setSaving(false);
    }
  }

  if (editing) {
    return (
      <tr>
        <td>
          <input
            value={form.exerciseName}
            onChange={e => setForm(f => ({ ...f, exerciseName: e.target.value }))}
            className="inline-input"
            style={{ width: '100%' }}
          />
        </td>
        <td style={{ textAlign: 'center' }}>
          <input type="checkbox" checked={form.isBarbellBenchPress} onChange={e => setForm(f => ({ ...f, isBarbellBenchPress: e.target.checked }))} />
        </td>
        <td style={{ textAlign: 'center' }}>
          <input type="checkbox" checked={form.isBodyweight} onChange={e => setForm(f => ({ ...f, isBodyweight: e.target.checked }))} />
        </td>
        <td>
          <button className="icon-btn" onClick={saveEdit} disabled={saving} title="Save">✓</button>
          <button className="icon-btn" onClick={() => setEditing(false)} title="Cancel">✕</button>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td>{exercise.exerciseName}</td>
      <td style={{ textAlign: 'center' }}>{exercise.isBarbellBenchPress ? '✓' : ''}</td>
      <td style={{ textAlign: 'center' }}>{exercise.isBodyweight ? '✓' : ''}</td>
      <td>
        <button className="icon-btn" onClick={startEdit} title="Edit exercise">✏</button>
      </td>
    </tr>
  );
}

export default function ExerciseCatalogForm({ exercises, onExerciseCreated, onExerciseUpdated }) {
  const [newName, setNewName] = useState('');
  const [newIsBench, setNewIsBench] = useState(false);
  const [newIsBodyweight, setNewIsBodyweight] = useState(false);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState(null);

  async function handleAdd() {
    if (!newName.trim()) { setError('Name is required.'); return; }
    setAdding(true);
    setError(null);
    try {
      await onExerciseCreated({
        exerciseName: newName.trim(),
        isBarbellBenchPress: newIsBench,
        isBodyweight: newIsBodyweight,
      });
      setNewName('');
      setNewIsBench(false);
      setNewIsBodyweight(false);
    } catch {
      setError('Failed to add exercise. Name may already exist.');
    } finally {
      setAdding(false);
    }
  }

  return (
    <div>
      <table className="sets-table" style={{ width: '100%', marginBottom: 16 }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>Exercise</th>
            <th>Bench press</th>
            <th>Bodyweight</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {exercises.map(ex => (
            <ExerciseRow key={ex.exerciseId} exercise={ex} onUpdate={onExerciseUpdated} />
          ))}
        </tbody>
      </table>

      <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Add exercise</div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ margin: 0, flex: '1 1 160px' }}>
            <label>Name</label>
            <input value={newName} onChange={e => setNewName(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleAdd()} />
          </div>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center', paddingBottom: 2 }}>
            <label style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 13, color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <input type="checkbox" checked={newIsBench} onChange={e => setNewIsBench(e.target.checked)} />
              Barbell bench
            </label>
            <label style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 13, color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <input type="checkbox" checked={newIsBodyweight} onChange={e => setNewIsBodyweight(e.target.checked)} />
              Bodyweight
            </label>
          </div>
          <button className="btn btn-primary" onClick={handleAdd} disabled={adding} style={{ whiteSpace: 'nowrap' }}>
            {adding ? 'Adding…' : '+ Add'}
          </button>
        </div>
        {error && <div style={{ color: 'var(--ready-red)', fontSize: 12, marginTop: 6 }}>{error}</div>}
      </div>
    </div>
  );
}
