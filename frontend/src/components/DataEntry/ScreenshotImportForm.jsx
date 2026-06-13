import { useState, useRef, useCallback, useEffect } from 'react';
import {
  importScreenshots,
  createSession,
  createSessionExercise,
  createExercise,
  createExerciseSet,
  getExercises,
} from '../../api/client.js';
import { formatDuration, formatPace, parseDuration, parsePace } from '../../utils/runMetrics.js';
import './ScreenshotImportForm.css';

const SESSION_TYPES_BY_PHASE = {
  bench:        ['heavy_bench', 'volume_bench', 'speed_bench', 'run', 'pull', 'other'],
  pull_ups:     ['pull', 'run', 'other'],
  run:          ['run', 'other'],
  powerlifting: ['squat', 'deadlift', 'mix', 'run', 'other'],
};
const SESSION_TYPES_DEFAULT = ['heavy_bench', 'volume_bench', 'speed_bench', 'run', 'pull', 'other'];

function sessionTypesForPhase(phases, phaseId) {
  const phase = phases.find(p => p.phaseId === Number(phaseId));
  return SESSION_TYPES_BY_PHASE[phase?.phaseType] ?? SESSION_TYPES_DEFAULT;
}

export default function ScreenshotImportForm({ phases, selectedPhaseId, exercises, onImportComplete, onExerciseCreated }) {
  const [stage, setStage] = useState('idle');
  const [dragOver, setDragOver] = useState(false);
  const [pendingImages, setPendingImages] = useState([]);
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
    Array.from(e.dataTransfer.files).forEach(f => addFile(f));
  }, []);

  const handleFileInput = (e) => {
    Array.from(e.target.files).forEach(f => addFile(f));
    e.target.value = '';
  };

  useEffect(() => {
    function handlePaste(e) {
      if (stage !== 'idle') return;
      const items = Array.from(e.clipboardData?.items || []);
      const imageItem = items.find(item => item.type.startsWith('image/'));
      if (imageItem) {
        const file = imageItem.getAsFile();
        if (file) addFile(file);
      }
    }
    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [stage]);

  function addFile(file) {
    if (!file.type.startsWith('image/')) {
      setError('Please use image files (PNG, JPEG, or WEBP).');
      return;
    }
    setError(null);
    const previewUrl = URL.createObjectURL(file);
    setPendingImages(prev => [...prev, { file, previewUrl }]);
  }

  function removeImage(idx) {
    setPendingImages(prev => {
      URL.revokeObjectURL(prev[idx].previewUrl);
      return prev.filter((_, i) => i !== idx);
    });
  }

  async function parsePending() {
    if (!pendingImages.length) return;
    setError(null);
    setStage('parsing');
    try {
      const result = await importScreenshots(pendingImages.map(p => p.file));
      if (!result.sessionDate) result.sessionDate = new Date().toISOString().slice(0, 10);
      result.eliteHrvReadiness = '';
      setEditedData(JSON.parse(JSON.stringify(result)));
      setStage('preview');
    } catch (err) {
      setError(err.message || 'Failed to parse screenshots.');
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
    try {
      const created = await createExercise({ exerciseName: exerciseName.trim() });
      onExerciseCreated?.(created);
      return created.exerciseId;
    } catch {
      // Exercise may already exist (stale local list) — re-fetch and retry lookup
      const all = await getExercises();
      const found = all.find(ex => ex.exerciseName.toLowerCase() === normalized);
      if (found) return found.exerciseId;
      throw new Error(`Could not resolve exercise: ${exerciseName}`);
    }
  }

  async function handleConfirm() {
    if (!phaseId) { setError('Select a phase first.'); return; }
    setError(null);
    setStage('importing');
    try {
      setImportProgress('Creating session…');
      const runFields = editedData.sessionType === 'run' ? {
        runType: editedData.runType || null,
        distanceKm: editedData.distanceKm ?? null,
        durationSeconds: editedData.durationSeconds ?? null,
        avgHr: editedData.avgHr ?? null,
        maxHr: editedData.maxHr ?? null,
        avgPaceSecPerKm: editedData.avgPaceSecPerKm ?? null,
        avgGapPaceSecPerKm: editedData.avgGapPaceSecPerKm ?? null,
        avgCadence: editedData.avgCadence ?? null,
        avgGctMs: editedData.avgGctMs ?? null,
        avgVoCm: editedData.avgVoCm ?? null,
        ascentM: editedData.ascentM ?? null,
        rpe: editedData.rpe !== '' && editedData.rpe != null ? Number(editedData.rpe) : null,
      } : {};
      const session = await createSession({
        phaseId: Number(phaseId),
        sessionDate: editedData.sessionDate,
        sessionType: editedData.sessionType,
        eliteHrvReadiness: editedData.eliteHrvReadiness !== '' ? Number(editedData.eliteHrvReadiness) : null,
        notes: editedData.notes || null,
        ...runFields,
      });

      const exercisesWithSets = editedData.exercises.filter(ex => ex.sets.length > 0);
      for (let exIdx = 0; exIdx < exercisesWithSets.length; exIdx++) {
        const ex = exercisesWithSets[exIdx];
        setImportProgress(`Adding exercise ${exIdx + 1}/${exercisesWithSets.length}: ${ex.exerciseName}…`);
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
    setPendingImages(prev => { prev.forEach(p => URL.revokeObjectURL(p.previewUrl)); return []; });
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
            multiple
            style={{ display: 'none' }}
            onChange={handleFileInput}
          />
          {stage === 'parsing' ? (
            <>
              <div className="screenshot-spinner" />
              <p className="screenshot-hint">Analysing {pendingImages.length} screenshot{pendingImages.length !== 1 ? 's' : ''}&hellip;</p>
            </>
          ) : (
            <>
              <div className="screenshot-icon">&#128247;</div>
              <p className="screenshot-hint">{pendingImages.length > 0 ? 'Add more screenshots' : 'Drop or paste workout screenshots'}</p>
              <p className="screenshot-subhint">drag &amp; drop, Ctrl+V, or click to browse &mdash; PNG, JPEG, WEBP</p>
            </>
          )}
        </div>

        {pendingImages.length > 0 && stage === 'idle' && (
          <div className="screenshot-queue">
            {pendingImages.map((img, i) => (
              <div key={i} className="screenshot-thumb">
                <img src={img.previewUrl} alt={`Screenshot ${i + 1}`} />
                <button
                  type="button"
                  className="screenshot-thumb-remove"
                  onClick={e => { e.stopPropagation(); removeImage(i); }}
                  aria-label="Remove screenshot"
                >&#x2715;</button>
              </div>
            ))}
          </div>
        )}

        {pendingImages.length > 0 && stage === 'idle' && (
          <button type="button" className="btn btn-primary" style={{ marginTop: 12, width: '100%' }} onClick={parsePending}>
            Parse {pendingImages.length} screenshot{pendingImages.length !== 1 ? 's' : ''}
          </button>
        )}

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
            {sessionTypesForPhase(phases, phaseId).map(t => (
              <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>HRV readiness</label>
          <input
            type="number"
            min="0"
            max="10"
            step="0.1"
            placeholder="0–10"
            value={editedData.eliteHrvReadiness ?? ''}
            onChange={e => updateField('eliteHrvReadiness', e.target.value)}
            style={{ width: 70 }}
          />
        </div>
      </div>

      <div className="form-group">
        <label>Notes</label>
        <input
          type="text"
          placeholder="Optional notes…"
          value={editedData.notes || ''}
          onChange={e => updateField('notes', e.target.value)}
        />
      </div>

      {editedData.sessionType === 'run' && (
        <>
          <div className="form-row" style={{ flexWrap: 'wrap' }}>
            <div className="form-group">
              <label>Run type</label>
              <input
                type="text" placeholder="easy, long, tempo…"
                value={editedData.runType ?? ''}
                onChange={e => updateField('runType', e.target.value || null)}
              />
            </div>
            <div className="form-group">
              <label>Distance (km)</label>
              <input
                type="number" min="0" step="0.01" placeholder="6.01"
                value={editedData.distanceKm ?? ''}
                onChange={e => updateField('distanceKm', e.target.value === '' ? null : Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label>Duration (MM:SS)</label>
              <input
                type="text" placeholder="32:43"
                defaultValue={editedData.durationSeconds != null ? formatDuration(editedData.durationSeconds) : ''}
                onBlur={e => updateField('durationSeconds', parseDuration(e.target.value))}
              />
            </div>
          </div>
          <div className="form-row" style={{ flexWrap: 'wrap' }}>
            <div className="form-group">
              <label>Avg pace (M:SS/km)</label>
              <input
                type="text" placeholder="5:27"
                defaultValue={editedData.avgPaceSecPerKm != null ? formatPace(editedData.avgPaceSecPerKm).replace(' /km', '') : ''}
                onBlur={e => updateField('avgPaceSecPerKm', parsePace(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label>GAP (M:SS/km)</label>
              <input
                type="text" placeholder="5:12"
                defaultValue={editedData.avgGapPaceSecPerKm != null ? formatPace(editedData.avgGapPaceSecPerKm).replace(' /km', '') : ''}
                onBlur={e => updateField('avgGapPaceSecPerKm', parsePace(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label>Avg HR</label>
              <input
                type="number" min="0" placeholder="152"
                value={editedData.avgHr ?? ''}
                onChange={e => updateField('avgHr', e.target.value === '' ? null : Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label>Max HR</label>
              <input
                type="number" min="0" placeholder="178"
                value={editedData.maxHr ?? ''}
                onChange={e => updateField('maxHr', e.target.value === '' ? null : Number(e.target.value))}
              />
            </div>
          </div>
          <div className="form-row" style={{ flexWrap: 'wrap' }}>
            <div className="form-group">
              <label>Cadence (spm)</label>
              <input
                type="number" min="0" placeholder="170"
                value={editedData.avgCadence ?? ''}
                onChange={e => updateField('avgCadence', e.target.value === '' ? null : Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label>GCT (ms)</label>
              <input
                type="number" min="0" placeholder="230"
                value={editedData.avgGctMs ?? ''}
                onChange={e => updateField('avgGctMs', e.target.value === '' ? null : Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label>Vert. osc. (cm)</label>
              <input
                type="number" min="0" step="0.1" placeholder="9.2"
                value={editedData.avgVoCm ?? ''}
                onChange={e => updateField('avgVoCm', e.target.value === '' ? null : Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label>Ascent (m)</label>
              <input
                type="number" min="0" placeholder="48"
                value={editedData.ascentM ?? ''}
                onChange={e => updateField('ascentM', e.target.value === '' ? null : Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label>RPE (1–10)</label>
              <input
                type="number" min="1" max="10" step="0.5" placeholder="6"
                value={editedData.rpe ?? ''}
                onChange={e => updateField('rpe', e.target.value === '' ? null : Number(e.target.value))}
              />
            </div>
          </div>
        </>
      )}

      {editedData.sessionType !== 'run' && editedData.exercises.map((ex, exIdx) => (
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
