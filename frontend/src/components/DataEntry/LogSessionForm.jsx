import { useState } from 'react';
import { createSession, createBodyweightEntry } from '../../api/client.js';
import { parseDuration, parsePace } from '../../utils/runMetrics.js';

const SESSION_TYPES_BY_PHASE = {
  bench:        ['heavy_bench', 'volume_bench', 'speed_bench', 'run', 'pull', 'rest', 'other'],
  pull_ups:     ['pull', 'run', 'rest', 'other'],
  run:          ['run', 'rest', 'other'],
  powerlifting: ['squat', 'deadlift', 'mix', 'run', 'other'],
};
const SESSION_TYPES_DEFAULT = ['heavy_bench', 'volume_bench', 'speed_bench', 'run', 'pull', 'rest', 'other'];

function sessionTypesForPhase(phases, phaseId) {
  const phase = phases.find(p => p.phaseId === Number(phaseId));
  return SESSION_TYPES_BY_PHASE[phase?.phaseType] ?? SESSION_TYPES_DEFAULT;
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

export default function LogSessionForm({ phases, selectedPhaseId, sessions = [], onSessionLogged }) {
  const [phaseId, setPhaseId] = useState(selectedPhaseId || (phases[0]?.phaseId ?? ''));
  const [date, setDate] = useState(today());
  const sessionTypes = sessionTypesForPhase(phases, phaseId);
  const [sessionType, setSessionType] = useState(sessionTypes[0] ?? 'other');
  const [eliteHrv, setEliteHrv] = useState('');
  const [garminHrv, setGarminHrv] = useState('');
  const [bodyweight, setBodyweight] = useState('');
  const [notes, setNotes] = useState('');
  const [runType, setRunType] = useState('');
  const [distanceKm, setDistanceKm] = useState('');
  const [duration, setDuration] = useState('');    // "MM:SS"
  const [avgHr, setAvgHr] = useState('');
  const [maxHr, setMaxHr] = useState('');
  const [pace, setPace] = useState('');             // "M:SS"
  const [gap, setGap] = useState('');               // "M:SS"
  const [avgCadence, setAvgCadence] = useState('');
  const [avgGctMs, setAvgGctMs] = useState('');
  const [avgVoCm, setAvgVoCm] = useState('');
  const [ascentM, setAscentM] = useState('');
  const [rpe, setRpe] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [conflict, setConflict] = useState(null);

  const isRun = sessionType === 'run';

  function resetForm() {
    setDate(today());
    setEliteHrv('');
    setGarminHrv('');
    setBodyweight('');
    setNotes('');
    setRunType('');
    setDistanceKm('');
    setDuration('');
    setAvgHr('');
    setMaxHr('');
    setPace('');
    setGap('');
    setAvgCadence('');
    setAvgGctMs('');
    setAvgVoCm('');
    setAscentM('');
    setRpe('');
    setConflict(null);
  }

  async function doCreate() {
    setSubmitting(true);
    try {
      const session = await createSession({
        phaseId: Number(phaseId),
        sessionDate: date,
        sessionType,
        eliteHrvReadiness: eliteHrv !== '' ? Number(eliteHrv) : null,
        garminOvernightHrv: garminHrv !== '' ? Number(garminHrv) : null,
        notes: notes || null,
        runType: runType || null,
        distanceKm: distanceKm !== '' ? Number(distanceKm) : null,
        durationSeconds: duration !== '' ? parseDuration(duration) : null,
        avgHr: avgHr !== '' ? Number(avgHr) : null,
        maxHr: maxHr !== '' ? Number(maxHr) : null,
        avgPaceSecPerKm: pace !== '' ? parsePace(pace) : null,
        avgGapPaceSecPerKm: gap !== '' ? parsePace(gap) : null,
        avgCadence: avgCadence !== '' ? Number(avgCadence) : null,
        avgGctMs: avgGctMs !== '' ? Number(avgGctMs) : null,
        avgVoCm: avgVoCm !== '' ? Number(avgVoCm) : null,
        ascentM: ascentM !== '' ? Number(ascentM) : null,
        rpe: rpe !== '' ? Number(rpe) : null,
      });
      // Log bodyweight if provided
      if (bodyweight !== '') {
        await createBodyweightEntry({
          phaseId: Number(phaseId),
          sessionId: session.sessionId,
          loggedDate: date,
          weightKg: Number(bodyweight),
        });
      }
      onSessionLogged(session);
      resetForm();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (!date) {
      setError('Date is required');
      return;
    }

    if (eliteHrv !== '' && (Number(eliteHrv) < 0 || Number(eliteHrv) > 10)) {
      setError('Readiness must be between 0 and 10');
      return;
    }

    // Check for a single existing session with same phase/date/type
    const matches = sessions.filter(
      s => s.phaseId === Number(phaseId) && s.sessionDate === date && s.sessionType === sessionType
    );
    if (matches.length === 1) {
      setConflict(matches[0]);
      return;
    }

    await doCreate();
  }

  function handleAppend() {
    onSessionLogged(conflict);
    resetForm();
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <label>Phase</label>
        <select value={phaseId} onChange={e => { setPhaseId(e.target.value); setSessionType(sessionTypesForPhase(phases, e.target.value)[0] ?? 'other'); }} required>
          {phases.map(p => (
            <option key={p.phaseId} value={p.phaseId}>{p.name}</option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>Date</label>
        <input type="date" value={date} onChange={e => setDate(e.target.value)} required />
      </div>

      <div className="form-group">
        <label>Session Type</label>
        <select value={sessionType} onChange={e => setSessionType(e.target.value)}>
          {sessionTypes.map(t => (
            <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Readiness (0–10)</label>
          <input
            type="number"
            min="0"
            max="10"
            step="0.1"
            placeholder="optional"
            value={eliteHrv}
            onChange={e => setEliteHrv(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Garmin Overnight HRV</label>
          <input
            type="number"
            min="0"
            step="0.1"
            placeholder="optional"
            value={garminHrv}
            onChange={e => setGarminHrv(e.target.value)}
          />
        </div>
      </div>

      <div className="form-group">
        <label>Bodyweight (kg) <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>optional — updates GL score</span></label>
        <input
          type="number"
          min="40"
          max="200"
          step="0.1"
          placeholder="e.g. 82.5"
          value={bodyweight}
          onChange={e => setBodyweight(e.target.value)}
        />
      </div>

      <div className="form-group">
        <label>Notes</label>
        <textarea
          placeholder="optional"
          value={notes}
          onChange={e => setNotes(e.target.value)}
        />
      </div>

      {isRun && (
        <>
          <div className="form-row" style={{ flexWrap: 'wrap' }}>
            <div className="form-group">
              <label>Run type</label>
              <input type="text" placeholder="easy, long, tempo…" value={runType} onChange={e => setRunType(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Distance (km)</label>
              <input type="number" min="0" step="0.01" placeholder="6.01" value={distanceKm} onChange={e => setDistanceKm(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Duration (MM:SS)</label>
              <input type="text" placeholder="32:43" value={duration} onChange={e => setDuration(e.target.value)} />
            </div>
          </div>
          <div className="form-row" style={{ flexWrap: 'wrap' }}>
            <div className="form-group">
              <label>Avg pace (M:SS/km)</label>
              <input type="text" placeholder="5:27" value={pace} onChange={e => setPace(e.target.value)} />
            </div>
            <div className="form-group">
              <label>GAP (M:SS/km)</label>
              <input type="text" placeholder="5:12" value={gap} onChange={e => setGap(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Avg HR</label>
              <input type="number" min="0" placeholder="152" value={avgHr} onChange={e => setAvgHr(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Max HR</label>
              <input type="number" min="0" placeholder="178" value={maxHr} onChange={e => setMaxHr(e.target.value)} />
            </div>
          </div>
          <div className="form-row" style={{ flexWrap: 'wrap' }}>
            <div className="form-group">
              <label>Cadence (spm)</label>
              <input type="number" min="0" placeholder="170" value={avgCadence} onChange={e => setAvgCadence(e.target.value)} />
            </div>
            <div className="form-group">
              <label>GCT (ms)</label>
              <input type="number" min="0" placeholder="230" value={avgGctMs} onChange={e => setAvgGctMs(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Vert. osc. (cm)</label>
              <input type="number" min="0" step="0.1" placeholder="9.2" value={avgVoCm} onChange={e => setAvgVoCm(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Ascent (m)</label>
              <input type="number" min="0" placeholder="48" value={ascentM} onChange={e => setAscentM(e.target.value)} />
            </div>
            <div className="form-group">
              <label>RPE (1–10)</label>
              <input type="number" min="1" max="10" step="0.5" placeholder="6" value={rpe} onChange={e => setRpe(e.target.value)} />
            </div>
          </div>
        </>
      )}

      {error && <div className="form-error">{error}</div>}

      {conflict ? (
        <div className="session-conflict">
          <p className="session-conflict-msg">
            A <strong>{sessionType.replace(/_/g, ' ')}</strong> session already exists on {date}. What would you like to do?
          </p>
          <div className="session-conflict-actions">
            <button type="button" className="btn btn-ghost" style={{ flex: 1 }} onClick={handleAppend}>
              Append to existing
            </button>
            <button type="button" className="btn btn-primary" style={{ flex: 1 }} onClick={doCreate} disabled={submitting}>
              {submitting ? 'Saving…' : 'Create separate'}
            </button>
          </div>
          <button type="button" className="btn-link" onClick={() => setConflict(null)}>
            Cancel
          </button>
        </div>
      ) : (
        <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={submitting}>
          {submitting ? 'Saving…' : 'Log Session'}
        </button>
      )}
    </form>
  );
}
