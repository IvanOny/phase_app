import { useState } from 'react';
import { createSessionExercise, createExerciseSet } from '../../api/client.js';

export default function LogSetsForm({ sessions, exercises, onSetsLogged }) {
  const [sessionId, setSessionId] = useState('');
  const [exerciseId, setExerciseId] = useState('');
  const [sessionExerciseId, setSessionExerciseId] = useState(null);
  const [addingExercise, setAddingExercise] = useState(false);
  const [sets, setSets] = useState([]);
  const [setNumber, setSetNumber] = useState(1);

  const [reps, setReps] = useState('');
  const [loadKg, setLoadKg] = useState('');
  const [isTopSet, setIsTopSet] = useState(false);
  const [isWorkingSet, setIsWorkingSet] = useState(true);
  const [error, setError] = useState(null);
  const [submittingSet, setSubmittingSet] = useState(false);

  async function handleAddExercise() {
    if (!sessionId || !exerciseId) {
      setError('Select a session and exercise first');
      return;
    }
    setError(null);
    setAddingExercise(true);
    try {
      const se = await createSessionExercise(Number(sessionId), {
        exerciseId: Number(exerciseId),
        exerciseOrder: 1,
      });
      setSessionExerciseId(se.sessionExerciseId);
      setSets([]);
      setSetNumber(1);
    } catch (err) {
      setError(err.message);
    } finally {
      setAddingExercise(false);
    }
  }

  async function handleAddSet(e) {
    e.preventDefault();
    if (!sessionExerciseId) {
      setError('Add exercise to session first');
      return;
    }
    setError(null);
    setSubmittingSet(true);
    try {
      const set = await createExerciseSet(sessionExerciseId, {
        setNumber,
        reps: Number(reps),
        loadKg: Number(loadKg),
        isTopSet,
        isWorkingSet,
      });
      setSets(prev => [...prev, { ...set, reps: Number(reps), loadKg: Number(loadKg), isTopSet, isWorkingSet, setNumber }]);
      setSetNumber(n => n + 1);
      setReps('');
      setLoadKg('');
      setIsTopSet(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmittingSet(false);
    }
  }

  function handleDone() {
    if (sets.length > 0) onSetsLogged(sets);
    setSessionId('');
    setExerciseId('');
    setSessionExerciseId(null);
    setSets([]);
    setSetNumber(1);
    setError(null);
  }

  const selectedExercise = exercises.find(ex => ex.exerciseId === Number(exerciseId));

  return (
    <div>
      <div className="form-group">
        <label>Session</label>
        <select
          value={sessionId}
          onChange={e => { setSessionId(e.target.value); setSessionExerciseId(null); setSets([]); }}
          disabled={!!sessionExerciseId}
        >
          <option value="">Select session…</option>
          {[...sessions].sort((a, b) => new Date(b.sessionDate) - new Date(a.sessionDate)).map(s => (
            <option key={s.sessionId} value={s.sessionId}>
              {s.sessionDate} — {s.sessionType.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>Exercise</label>
        <select
          value={exerciseId}
          onChange={e => { setExerciseId(e.target.value); setSessionExerciseId(null); setSets([]); }}
          disabled={!!sessionExerciseId}
        >
          <option value="">Select exercise…</option>
          {exercises.map(ex => (
            <option key={ex.exerciseId} value={ex.exerciseId}>{ex.exerciseName}</option>
          ))}
        </select>
      </div>

      {!sessionExerciseId ? (
        <button
          type="button"
          className="btn btn-ghost"
          style={{ width: '100%', marginBottom: 'var(--space-4)' }}
          onClick={handleAddExercise}
          disabled={addingExercise || !sessionId || !exerciseId}
        >
          {addingExercise ? 'Adding…' : 'Add Exercise to Session'}
        </button>
      ) : (
        <div className="exercise-active-label">
          {selectedExercise?.exerciseName} — adding sets
        </div>
      )}

      {sessionExerciseId && (
        <form onSubmit={handleAddSet}>
          <div className="form-row">
            <div className="form-group">
              <label>Set #</label>
              <input type="number" value={setNumber} readOnly style={{ opacity: 0.6 }} />
            </div>
            <div className="form-group">
              <label>Reps</label>
              <input type="number" min="1" value={reps} onChange={e => setReps(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Load (kg)</label>
              <input type="number" min="0" step="0.5" value={loadKg} onChange={e => setLoadKg(e.target.value)} required />
            </div>
          </div>

          <div className="form-checkboxes">
            <label className="checkbox-label">
              <input type="checkbox" checked={isTopSet} onChange={e => setIsTopSet(e.target.checked)} />
              Top set
            </label>
            <label className="checkbox-label">
              <input type="checkbox" checked={isWorkingSet} onChange={e => setIsWorkingSet(e.target.checked)} />
              Working set
            </label>
          </div>

          <button type="submit" className="btn btn-ghost" style={{ width: '100%' }} disabled={submittingSet}>
            {submittingSet ? 'Adding…' : '+ Add Set'}
          </button>
        </form>
      )}

      {sets.length > 0 && (
        <div className="sets-list">
          <div className="sets-list-header">
            <span>Set</span><span>Load</span><span>Reps</span><span>Flags</span>
          </div>
          {sets.map(s => (
            <div key={s.setNumber} className="set-row">
              <span>{s.setNumber}</span>
              <span>{s.loadKg} kg</span>
              <span>{s.reps}</span>
              <span className="set-flags">
                {s.isTopSet && <span className="flag-badge flag-top">TOP</span>}
                {s.isWorkingSet && <span className="flag-badge flag-work">W</span>}
              </span>
            </div>
          ))}
          <button
            type="button"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 'var(--space-4)' }}
            onClick={handleDone}
          >
            Done
          </button>
        </div>
      )}

      {error && <div className="form-error">{error}</div>}
    </div>
  );
}
