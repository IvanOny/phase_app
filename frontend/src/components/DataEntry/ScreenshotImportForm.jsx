import { useState, useRef, useCallback } from 'react';
import {
  importScreenshot,
  createSession,
  createSessionExercise,
  createExercise,
  createExerciseSet,
} from '../../api/client.js';
import './ScreenshotImportForm.css';

const SESSION_TYPES = ['heavy_bench', 'volume_bench', 'speed_bench', 'run', 'pull', 'other'];

export default function ScreenshotImportForm({ phases, selectedPhaseId, exercises, onImportComplete, onExerciseCreated }) {
  const [stage, setStage] = useState('idle');
  const [dragOver, setDragOver] = useState(false);
  const [editedData, setEditedData] = useState(null);
  const [phaseId, setPhaseId] = useState(selectedPhaseId || phases[0]?.phaseId || '');
  const [error, setError] = useState(null);
  const [importProgress, setImportProgress] = useState('');
  const fileInputRef = useRef(null);

  const handleDragOver = useCallback((e) => { e.preventDefault(); setDragOver(true); }, []);
  const handleDragLeave = useCallback(() => setDragOver(false), []);
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  }, []);

  const handleFileInput = (e) => {
    if (e.target.files[0]) processFile(e.target.files[0]);
  };

  async function processFile(file) {
    if (!file.type.startsWith('image/')) {
      setError('Please drop an image file (PNG, JPEG, or WEBP).');
      return;
    }
    setError(null);
    setStage('parsing');
    try {
      const result = await importScreenshot(file);
      setEditedData(JSON.parse(JSON.stringify(result)));
      setStage('preview');
    } catch (err) {
      setError(err.message || 'Failed to parse screenshot.');
      setStage('idle');
    }
  }

  function updateField(field, value) {
    setEditedData(prev => ({ ...prev, [field]: value }));
  }

  function updateSetField(exIdx, setIdx, field, value) {
    setEditedData(prev => ({
      ...prev,
      exercises: prev.exercises.map((ex, i) =>
        i !== exIdx ? ex : {
          ...ex,
          sets: ex.sets.map((s, j) => j !== setIdx ? s : { ...s, [field]: value }),
        }
      ),
    }));
  }

  function removeSet(exIdx, setIdx) {
    setEditedData(prev => ({
      ...prev,
      exercises: prev.exercises.map((ex, i) =>
        i !== exIdx ? ex : { ...ex, sets: ex.sets.filter((_, j) => j !== setIdx) }
      ),
    }));
  }

  function removeExercise(exIdx) {
    setEditedData(prev => ({
      ...prev,
      exercises: prev.exercises.filter((_, i) => i !== exIdx),
    }));
  }

  function toggleSetFlag(exIdx, setIdx, field) {
    setEditedData(prev => ({
      ...prev,
      exercises: prev.exercises.map((ex, i) =>
        i !== exIdx ? ex : {
          ...ex,
          sets: ex.sets.map((s, j) => j !== setIdx ? s : { ...s, [field]: !s[field] }),
        }
      ),
    }));
  }

  async function resolveExerciseId(exerciseName) {
    const normalized = exerciseName.trim().toLowerCase();
    const match = exercises.find(ex => ex.exerciseName.toLowerCase() === normalized);
    if (match) return match.exerciseId;
    const created = await createExercise({ exerciseName: exerciseName.trim() });
    onExerciseCreated?.(created);
    return created.exerciseId;
  }

  async function handleConfirm() {
    if (!phaseId) { setError('Select a phase first.'); return; }
    setError(null);
    setStage('importing');
    try {
      setImportProgress('Creating session…');
      const session = await createSession({
        phaseId: Number(phaseId),
        sessionDate: editedData.sessionDate,
        sessionType: editedData.sessionType,
        notes: editedData.notes || null,
      });

      for (let exIdx = 0; exIdx < editedData.exercises.length; exIdx++) {
        const ex = editedData.exercises[exIdx];
        setImportProgress(`Adding exercise ${exIdx + 1}/${editedData.exercises.length}: ${ex.exerciseName}…`);
        const exerciseId = await resolveExerciseId(ex.exerciseName);
        const sessionExercise = await createSessionExercise(session.sessionId, {
          exerciseId,
          exerciseOrder: exIdx + 1,
        });
        for (const set of ex.sets) {
          await createExerciseSet(sessionExercise.sessionExerciseId, {
            setNumber: set.setNumber,
            reps: Number(set.reps),
            loadKg: Number(set.loadKg),
            isTopSet: Boolean(set.isTopSet),
            isWorkingSet: Boolean(set.isWorkingSet),
          });
        }
      }

      setStage('done');
      onImportComplete(session);
    } catch (err) {
      setError(err.message || 'Import failed.');
      setStage('preview');
    }
  }

  function handleReset() {
    setStage('idle');
    setEditedData(null);
    setError(null);
    setImportProgress('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  if (stage === 'idle' || stage === 'parsing') {
    return (
      <div>
        <div
          className={`screenshot-drop-zone${dragOver ? ' drag-over' : ''}${stage === 'parsing' ? ' parsing' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => stage === 'idle' && fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={e => e.key === 'Enter' && stage === 'idle' && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={handleFileInput}
          />
          {stage === 'parsing' ? (
            <>
              <div className="screenshot-spinner" />
              <p className="screenshot-hint">Analysing screenshot&hellip;</p>
            </>
          ) : (
            <>
              <div className="screenshot-icon">&#128247;</div>
              <p className="screenshot-hint">Drop a workout screenshot here</p>
              <p className="screenshot-subhint">or click to browse &mdash; PNG, JPEG, WEBP</p>
            </>
          )}
        </div>
        {error && <div className="form-error">{error}</div>}
      </div>
    );
  }

  if (stage === 'importing') {
    return (
      <div className="screenshot-importing">
        <div className="screenshot-spinner" />
        <p className="screenshot-hint">{importProgress}</p>
      </div>
    );
  }

  if (stage === 'done') {
    return (
      <div className="panel-success screenshot-done">
        Session imported successfully!
        <button className="btn btn-ghost screenshot-again-btn" onClick={handleReset}>
          Import another
        </button>
      </div>
    );
  }

  // preview stage
  return (
    <div>
      <div className="form-group">
        <label>Phase</label>
        <select value={phaseId} onChange={e => setPhaseId(e.target.value)}>
          {phases.map(p => (
            <option key={p.phaseId} value={p.phaseId}>{p.name}</option>
          ))}
        </select>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Date</label>
          <input
            type="date"
            value={editedData.sessionDate || ''}
            onChange={e => updateField('sessionDate', e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Type</label>
          <select value={editedData.sessionType} onChange={e => updateField('sessionType', e.target.value)}>
            {SESSION_TYPES.map(t => (
              <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
      </div>

      {editedData.exercises.map((ex, exIdx) => (
        <div key={exIdx} className="screenshot-exercise-block">
          <div className="screenshot-exercise-header">
            <div className="exercise-active-label">{ex.exerciseName}</div>
            <button
              type="button"
              className="screenshot-remove-exercise"
              onClick={() => removeExercise(exIdx)}
              aria-label={`Remove ${ex.exerciseName}`}
            >&#x2715;</button>
          </div>
          <div className="sets-list">
            <div className="sets-list-header screenshot-sets-header">
              <span>Set</span>
              <span>Load (kg)</span>
              <span>Reps</span>
              <span>Flags</span>
              <span></span>
            </div>
            {ex.sets.map((set, setIdx) => (
              <div key={setIdx} className="set-row screenshot-set-row">
                <span>{set.setNumber}</span>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  value={set.loadKg}
                  onChange={e => updateSetField(exIdx, setIdx, 'loadKg', e.target.value)}
                  className="screenshot-set-input"
                />
                <input
                  type="number"
                  min="1"
                  value={set.reps}
                  onChange={e => updateSetField(exIdx, setIdx, 'reps', e.target.value)}
                  className="screenshot-set-input"
                />
                <span className="set-flags">
                  <button
                    type="button"
                    className={`flag-badge flag-top${set.isTopSet ? '' : ' flag-inactive'}`}
                    onClick={() => toggleSetFlag(exIdx, setIdx, 'isTopSet')}
                    aria-pressed={set.isTopSet}
                    title="Toggle top set"
                  >TOP</button>
                  <button
                    type="button"
                    className={`flag-badge flag-work${set.isWorkingSet ? '' : ' flag-inactive'}`}
                    onClick={() => toggleSetFlag(exIdx, setIdx, 'isWorkingSet')}
                    aria-pressed={set.isWorkingSet}
                    title="Toggle working set"
                  >W</button>
                </span>
                <button
                  type="button"
                  className="screenshot-remove-set"
                  onClick={() => removeSet(exIdx, setIdx)}
                  aria-label="Remove set"
                >
                  &#x2715;
                </button>
              </div>
            ))}
          </div>
        </div>
      ))}

      {error && <div className="form-error">{error}</div>}

      <div className="screenshot-actions">
        <button type="button" className="btn btn-ghost" onClick={handleReset}>
          Start over
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleConfirm}
          disabled={!editedData.sessionDate || !phaseId}
        >
          Import Session
        </button>
      </div>
    </div>
  );
}
