import { useState } from 'react';
import {
  createSession,
  getSessionExercises,
  createSessionExercise,
  createExerciseSet,
  getExerciseSets,
  createExercise,
} from '../../api/client.js';

const QUICK_EXERCISES = [
  { label: 'Bench Press',       sessionType: 'heavy_bench', flags: { isBarbellBenchPress: true },  matchFlag: 'isBarbellBenchPress', weighted: true  },
  { label: 'Squat',             sessionType: 'squat',        flags: { isSquat: true },              weighted: true  },
  { label: 'Deadlift',          sessionType: 'deadlift',     flags: { isDeadlift: true },           weighted: true  },
  { label: 'Pull-ups',          sessionType: 'pull',         flags: { isBodyweight: true },         weighted: false },
  { label: 'Weighted Pull-ups', sessionType: 'pull',         flags: {},                             weighted: true  },
];

export default function QuickLogForm({ phaseId, phaseType, exercises, onSessionCreated }) {
  const [selectedIdx, setSelectedIdx] = useState(null);
  const [weight, setWeight] = useState('');
  const [reps, setReps] = useState('');
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null); // { type: 'ok'|'err', message }

  const selected = selectedIdx !== null ? QUICK_EXERCISES[selectedIdx] : null;

  async function handleLog() {
    if (!selected || !reps) return;
    if (selected.weighted && !weight) return;
    if (!phaseId) { setStatus({ type: 'err', message: 'No phase selected.' }); return; }

    setSaving(true);
    setStatus(null);
    try {
      const today = new Date().toISOString().slice(0, 10);

      // 1. Find or create today's session.
      // In a powerlifting phase all lifts on a day share ONE 'mixed' session,
      // so the trend chart plots them on the same date and they appear together
      // in the log. (Lift attribution is by exercise flag, not session type.)
      const sessionType = phaseType === 'powerlifting' ? 'mixed' : selected.sessionType;
      const session = await createSession({
        phaseId: Number(phaseId),
        sessionDate: today,
        sessionType,
      });
      const sessionId = session.sessionId;

      // 2. Resolve exercise — match by flag first (avoids "Bench Press" vs "Barbell Bench Press" mismatch),
      //    then fall back to name
      let catalogEx = selected.matchFlag
        ? exercises.find(e => e[selected.matchFlag] === true)
        : exercises.find(e => e.exerciseName.toLowerCase() === selected.label.toLowerCase());
      if (!catalogEx) {
        catalogEx = await createExercise({
          exerciseName: selected.label,
          ...selected.flags,
        });
      }
      const exerciseId = catalogEx.exerciseId;

      // 3. Find or create session_exercise entry
      const sessionExercises = await getSessionExercises(sessionId);
      let se = sessionExercises.find(e => e.exerciseId === exerciseId);
      let existingSets = [];
      if (!se) {
        se = await createSessionExercise(sessionId, {
          exerciseId,
          exerciseOrder: sessionExercises.length + 1,
        });
      } else {
        existingSets = await getExerciseSets(se.sessionExerciseId);
      }

      // 4. Next set number continues from existing sets
      const setNumber = existingSets.length + 1;

      // 5. Create the set (first set is top set; subsequent are working sets)
      await createExerciseSet(se.sessionExerciseId, {
        setNumber,
        reps: Number(reps),
        loadKg: selected.weighted ? Number(weight) : 0,
        isTopSet: existingSets.length === 0,
        isWorkingSet: true,
      });

      setStatus({ type: 'ok', message: `Logged ${selected.label}: ${selected.weighted ? `${weight} kg × ` : ''}${reps} reps` });
      setReps('');
      setWeight('');
      onSessionCreated?.();
    } catch (err) {
      setStatus({ type: 'err', message: err.message || 'Failed to log.' });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Exercise</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {QUICK_EXERCISES.map((ex, idx) => (
            <button
              key={ex.label}
              onClick={() => { setSelectedIdx(idx); setStatus(null); }}
              style={{
                textAlign: 'left',
                padding: '10px 14px',
                borderRadius: 'var(--radius)',
                border: selectedIdx === idx ? '1.5px solid var(--accent)' : '1.5px solid var(--border)',
                background: selectedIdx === idx ? 'var(--accent-tint-10, color-mix(in srgb, var(--accent) 10%, transparent))' : 'transparent',
                color: selectedIdx === idx ? 'var(--accent)' : 'var(--text-primary)',
                fontSize: 14,
                fontWeight: selectedIdx === idx ? 600 : 400,
                cursor: 'pointer',
                transition: 'border-color 0.12s, background 0.12s, color 0.12s',
              }}
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>

      {selected && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Top set</div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
            {selected.weighted && (
              <div className="form-group" style={{ margin: 0 }}>
                <label>Weight (kg)</label>
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  value={weight}
                  onChange={e => setWeight(e.target.value)}
                  style={{ width: 80 }}
                  autoFocus
                />
              </div>
            )}
            <div className="form-group" style={{ margin: 0 }}>
              <label>Reps</label>
              <input
                type="number"
                min="1"
                value={reps}
                onChange={e => setReps(e.target.value)}
                style={{ width: 64 }}
                autoFocus={!selected.weighted}
                onKeyDown={e => e.key === 'Enter' && handleLog()}
              />
            </div>
            <button
              className="btn btn-primary"
              onClick={handleLog}
              disabled={saving || !reps || (selected.weighted && !weight)}
              style={{ marginBottom: 1 }}
            >
              {saving ? 'Logging…' : 'Log'}
            </button>
          </div>
        </div>
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
