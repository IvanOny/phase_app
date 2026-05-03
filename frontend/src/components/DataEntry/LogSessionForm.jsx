import { useState } from 'react';
import { createSession } from '../../api/client.js';

const SESSION_TYPES = [
  'heavy_bench',
  'volume_bench',
  'speed_bench',
  'run',
  'pull',
  'other',
];

function today() {
  return new Date().toISOString().slice(0, 10);
}

export default function LogSessionForm({ phases, selectedPhaseId, onSessionLogged }) {
  const [phaseId, setPhaseId] = useState(selectedPhaseId || (phases[0]?.phaseId ?? ''));
  const [date, setDate] = useState(today());
  const [sessionType, setSessionType] = useState('heavy_bench');
  const [eliteHrv, setEliteHrv] = useState('');
  const [garminHrv, setGarminHrv] = useState('');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (eliteHrv !== '' && (Number(eliteHrv) < 0 || Number(eliteHrv) > 10)) {
      setError('Elite HRV readiness must be between 0 and 10');
      return;
    }

    setSubmitting(true);
    try {
      const session = await createSession({
        phaseId: Number(phaseId),
        sessionDate: date,
        sessionType,
        eliteHrvReadiness: eliteHrv !== '' ? Number(eliteHrv) : null,
        garminOvernightHrv: garminHrv !== '' ? Number(garminHrv) : null,
        notes: notes || null,
      });
      onSessionLogged(session);
      setDate(today());
      setEliteHrv('');
      setGarminHrv('');
      setNotes('');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <label>Phase</label>
        <select value={phaseId} onChange={e => setPhaseId(e.target.value)} required>
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
          {SESSION_TYPES.map(t => (
            <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Elite HRV Readiness (0–10)</label>
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
        <label>Notes</label>
        <textarea
          placeholder="optional"
          value={notes}
          onChange={e => setNotes(e.target.value)}
        />
      </div>

      {error && <div className="form-error">{error}</div>}

      <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={submitting}>
        {submitting ? 'Saving…' : 'Log Session'}
      </button>
    </form>
  );
}
