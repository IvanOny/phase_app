import { useState } from 'react';
import {
  createSession,
  updateSession,
  getSessionExercises,
  createSessionExercise,
  createExerciseSet,
  getExerciseSets,
  createExercise,
} from '../../api/client.js';
import { DEFAULT_QUICK_EXERCISES, resolveQuickEntry } from '../../data/quickExercises.js';

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

export default function QuickLogForm({ phaseId, phaseType, exercises, quickList, onQuickListChange, onSessionCreated }) {
  const list = (quickList && quickList.length > 0) ? quickList : DEFAULT_QUICK_EXERCISES;

  const [selectedIdx, setSelectedIdx] = useState(null);
  const [date, setDate]             = useState(todayStr);
  const [weight, setWeight]         = useState('');
  const [reps, setReps]             = useState('');
  // run fields
  const [distKm, setDistKm]         = useState('');
  const [durMin, setDurMin]         = useState('');
  const [avgHr, setAvgHr]           = useState('');
  const [rpe, setRpe]               = useState('');
  // ui state
  const [editMode, setEditMode]     = useState(false);
  const [addSearch, setAddSearch]   = useState('');
  const [saving, setSaving]         = useState(false);
  const [status, setStatus]         = useState(null);

  const selected = selectedIdx !== null ? list[selectedIdx] : null;

  function removeExercise(idx) {
    onQuickListChange?.(list.filter((_, i) => i !== idx));
    if (selectedIdx === idx) setSelectedIdx(null);
    else if (selectedIdx > idx) setSelectedIdx(i => i - 1);
  }

  function addExercise(ex) {
    const entry = {
      label: ex.exerciseName,
      sessionType: ex.isRun ? 'run' : 'other',
      flags: {},
      exerciseId: ex.exerciseId,
      type: ex.isRun ? 'run' : (ex.isBodyweight ? 'bodyweight' : 'strength'),
    };
    onQuickListChange?.([...list, entry]);
    setAddSearch('');
  }

  const alreadyInList = new Set(list.map(e => e.exerciseId).filter(Boolean));
  const catalogOptions = (exercises || [])
    .filter(ex => !alreadyInList.has(ex.exerciseId))
    .filter(ex => !addSearch || ex.exerciseName.toLowerCase().includes(addSearch.toLowerCase()));

  async function handleLogStrength() {
    if (!selected || !reps) return;
    if (selected.type === 'strength' && !weight) return;
    if (!phaseId) { setStatus({ type: 'err', message: 'No phase selected.' }); return; }

    setSaving(true);
    setStatus(null);
    try {
      const sessionType = phaseType === 'powerlifting' ? 'mix' : selected.sessionType;
      const session = await createSession({ phaseId: Number(phaseId), sessionDate: date, sessionType });
      const sessionId = session.sessionId;

      let catalogEx = resolveQuickEntry(selected, exercises);
      if (!catalogEx) {
        catalogEx = await createExercise({ exerciseName: selected.label, ...selected.flags });
      }
      const exerciseId = catalogEx.exerciseId;

      const sessionExercises = await getSessionExercises(sessionId);
      let se = sessionExercises.find(e => e.exerciseId === exerciseId);
      let existingSets = [];
      if (!se) {
        se = await createSessionExercise(sessionId, { exerciseId, exerciseOrder: sessionExercises.length + 1 });
      } else {
        existingSets = await getExerciseSets(se.sessionExerciseId);
      }

      await createExerciseSet(se.sessionExerciseId, {
        setNumber: existingSets.length + 1,
        reps: Number(reps),
        loadKg: selected.type === 'strength' ? Number(weight) : 0,
        isTopSet: existingSets.length === 0,
        isWorkingSet: true,
      });

      setStatus({ type: 'ok', message: `Logged ${selected.label}: ${selected.type === 'strength' ? `${weight} kg × ` : ''}${reps} reps` });
      setReps('');
      setWeight('');
      onSessionCreated?.();
    } catch (err) {
      setStatus({ type: 'err', message: err.message || 'Failed to log.' });
    } finally {
      setSaving(false);
    }
  }

  async function handleLogRun() {
    if (!distKm || !durMin) return;
    if (!phaseId) { setStatus({ type: 'err', message: 'No phase selected.' }); return; }

    setSaving(true);
    setStatus(null);
    try {
      const session = await createSession({ phaseId: Number(phaseId), sessionDate: date, sessionType: 'run' });
      const patch = {
        distanceKm: Number(distKm),
        durationSeconds: Math.round(Number(durMin) * 60),
      };
      if (avgHr) patch.avgHr = Number(avgHr);
      if (rpe)   patch.rpe   = Number(rpe);
      await updateSession(session.sessionId, patch);

      // Link the run session to the Run catalog exercise so it has a real
      // catalog identity. Metrics stay on the session (above); this is just
      // the association. Best-effort — a missing Run exercise won't block logging.
      try {
        let runEx = resolveQuickEntry(selected, exercises) || (exercises || []).find(e => e.isRun);
        if (!runEx) runEx = await createExercise({ exerciseName: 'Run', isRun: true });
        const sessionExercises = await getSessionExercises(session.sessionId);
        if (!sessionExercises.find(e => e.exerciseId === runEx.exerciseId)) {
          await createSessionExercise(session.sessionId, { exerciseId: runEx.exerciseId, exerciseOrder: 1 });
        }
      } catch { /* non-fatal: run is still logged at session level */ }

      const parts = [`${distKm} km`, `${durMin} min`];
      if (avgHr) parts.push(`${avgHr} bpm`);
      if (rpe)   parts.push(`RPE ${rpe}`);
      setStatus({ type: 'ok', message: `Logged run: ${parts.join(' · ')}` });
      setDistKm(''); setDurMin(''); setAvgHr(''); setRpe('');
      onSessionCreated?.();
    } catch (err) {
      setStatus({ type: 'err', message: err.message || 'Failed to log.' });
    } finally {
      setSaving(false);
    }
  }

  const isToday = date === todayStr();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* Date row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>Date</div>
        <input
          type="date"
          value={date}
          onChange={e => setDate(e.target.value)}
          style={{ fontSize: 13, padding: '4px 8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-input, var(--bg-elevated))', color: 'var(--text-primary)', cursor: 'pointer' }}
        />
        {!isToday && (
          <button
            onClick={() => setDate(todayStr())}
            style={{ fontSize: 12, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
          >
            Today
          </button>
        )}
      </div>

      {/* Exercise list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Exercise</div>
          <button
            onClick={() => setEditMode(m => !m)}
            style={{ fontSize: 12, color: editMode ? 'var(--accent)' : 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
          >
            {editMode ? 'Done' : 'Edit'}
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {list.map((ex, idx) => (
            <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <button
                onClick={() => { if (!editMode) { setSelectedIdx(idx); setStatus(null); } }}
                style={{
                  flex: 1,
                  textAlign: 'left',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius)',
                  border: selectedIdx === idx ? '1.5px solid var(--accent)' : '1.5px solid var(--border)',
                  background: selectedIdx === idx ? 'var(--accent-tint-10, color-mix(in srgb, var(--accent) 10%, transparent))' : 'transparent',
                  color: selectedIdx === idx ? 'var(--accent)' : 'var(--text-primary)',
                  fontSize: 14,
                  fontWeight: selectedIdx === idx ? 600 : 400,
                  cursor: editMode ? 'default' : 'pointer',
                  transition: 'border-color 0.12s, background 0.12s, color 0.12s',
                }}
              >
                {ex.label}
              </button>
              {editMode && (
                <button
                  onClick={() => removeExercise(idx)}
                  style={{ fontSize: 16, lineHeight: 1, color: 'var(--ready-red, #e05)', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 6px', flexShrink: 0 }}
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Add exercise in edit mode */}
        {editMode && (
          <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <input
              type="text"
              placeholder="Search catalog to add…"
              value={addSearch}
              onChange={e => setAddSearch(e.target.value)}
              style={{ fontSize: 13, padding: '7px 10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-input, var(--bg-elevated))', color: 'var(--text-primary)', width: '100%', boxSizing: 'border-box' }}
            />
            {addSearch && (
              <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', maxHeight: 180, overflowY: 'auto' }}>
                {catalogOptions.length === 0
                  ? <div style={{ padding: '8px 12px', fontSize: 13, color: 'var(--text-muted)' }}>No matches</div>
                  : catalogOptions.slice(0, 20).map(ex => (
                    <button
                      key={ex.exerciseId}
                      onClick={() => addExercise(ex)}
                      style={{ display: 'block', width: '100%', textAlign: 'left', padding: '8px 12px', fontSize: 13, color: 'var(--text-primary)', background: 'none', border: 'none', cursor: 'pointer', borderBottom: '1px solid var(--border)' }}
                    >
                      {ex.exerciseName}
                    </button>
                  ))
                }
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input section */}
      {selected && !editMode && (
        <>
          {selected.type === 'run' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Run details</div>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label>Distance (km)</label>
                  <input type="number" min="0" step="0.01" value={distKm} onChange={e => setDistKm(e.target.value)} style={{ width: 80 }} autoFocus />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label>Duration (min)</label>
                  <input type="number" min="0" step="1" value={durMin} onChange={e => setDurMin(e.target.value)} style={{ width: 80 }} />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label>Avg HR (bpm)</label>
                  <input type="number" min="0" step="1" value={avgHr} onChange={e => setAvgHr(e.target.value)} style={{ width: 72 }} />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label>RPE</label>
                  <input type="number" min="1" max="10" step="0.5" value={rpe} onChange={e => setRpe(e.target.value)} style={{ width: 56 }} onKeyDown={e => e.key === 'Enter' && handleLogRun()} />
                </div>
                <button
                  className="btn btn-primary"
                  onClick={handleLogRun}
                  disabled={saving || !distKm || !durMin}
                  style={{ marginBottom: 1 }}
                >
                  {saving ? 'Logging…' : 'Log'}
                </button>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Top set</div>
              <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
                {selected.type === 'strength' && (
                  <div className="form-group" style={{ margin: 0 }}>
                    <label>Weight (kg)</label>
                    <input type="number" min="0" step="0.5" value={weight} onChange={e => setWeight(e.target.value)} style={{ width: 80 }} autoFocus />
                  </div>
                )}
                <div className="form-group" style={{ margin: 0 }}>
                  <label>Reps</label>
                  <input
                    type="number" min="1" value={reps} onChange={e => setReps(e.target.value)} style={{ width: 64 }}
                    autoFocus={selected.type !== 'strength'}
                    onKeyDown={e => e.key === 'Enter' && handleLogStrength()}
                  />
                </div>
                <button
                  className="btn btn-primary"
                  onClick={handleLogStrength}
                  disabled={saving || !reps || (selected.type === 'strength' && !weight)}
                  style={{ marginBottom: 1 }}
                >
                  {saving ? 'Logging…' : 'Log'}
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {status && (
        <div style={{
          fontSize: 13,
          padding: '8px 12px',
          borderRadius: 'var(--radius-sm)',
          background: status.type === 'ok' ? 'var(--green-tint-10)' : 'var(--red-tint-10, color-mix(in srgb, var(--ready-red) 10%, transparent))',
          color: status.type === 'ok' ? 'var(--ready-green)' : 'var(--ready-red)',
          border: `1px solid ${status.type === 'ok' ? 'var(--green-tint-30)' : 'var(--ready-red)'}`,
        }}>
          {status.message}
        </div>
      )}
    </div>
  );
}
