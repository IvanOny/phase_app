import { useState } from 'react';
import { createBenchmark } from '../../api/client.js';

function today() {
  return new Date().toISOString().slice(0, 10);
}

export default function LogBenchmarkForm({ phases, selectedPhaseId, onBenchmarkLogged }) {
  const [phaseId, setPhaseId] = useState(selectedPhaseId || (phases[0]?.phaseId ?? ''));
  const [benchmarkDate, setBenchmarkDate] = useState(today());
  const [type, setType] = useState('max_bodyweight_pullups');

  // Pull-up fields
  const [reps, setReps] = useState('');
  const [formStandardVersion, setFormStandardVersion] = useState('v1.0');

  // Run fields
  const [avgHr, setAvgHr] = useState('');
  const [targetHr] = useState(140);
  const [durationMin] = useState(40);
  const [paceMinPerKm, setPaceMinPerKm] = useState('');
  const [protocolCompliant, setProtocolCompliant] = useState(true);

  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const base = {
        phaseId: Number(phaseId),
        benchmarkDate,
        benchmarkType: type,
      };
      const extra = type === 'max_bodyweight_pullups'
        ? { reps: Number(reps), formStandardVersion }
        : {
            avgHr: Number(avgHr),
            targetHr,
            durationMin,
            paceMinPerKm: Number(paceMinPerKm),
            protocolCompliant,
          };

      const benchmark = await createBenchmark({ ...base, ...extra });
      onBenchmarkLogged(benchmark);

      setReps('');
      setAvgHr('');
      setPaceMinPerKm('');
      setBenchmarkDate(today());
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
        <input type="date" value={benchmarkDate} onChange={e => setBenchmarkDate(e.target.value)} required />
      </div>

      <div className="benchmark-type-toggle">
        <button
          type="button"
          className={`toggle-btn${type === 'max_bodyweight_pullups' ? ' active' : ''}`}
          onClick={() => setType('max_bodyweight_pullups')}
        >
          Pull-ups
        </button>
        <button
          type="button"
          className={`toggle-btn${type === 'run_aerobic_test' ? ' active' : ''}`}
          onClick={() => setType('run_aerobic_test')}
        >
          Run
        </button>
      </div>

      {type === 'max_bodyweight_pullups' && (
        <>
          <div className="benchmark-info-row">
            Bodyweight only · One max set
          </div>
          <div className="form-group">
            <label>Max Reps</label>
            <input type="number" min="1" value={reps} onChange={e => setReps(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Form Standard Version</label>
            <input type="text" value={formStandardVersion} onChange={e => setFormStandardVersion(e.target.value)} />
          </div>
        </>
      )}

      {type === 'run_aerobic_test' && (
        <>
          <div className="benchmark-info-row">
            40 min · Target HR 140 bpm
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Avg HR (bpm)</label>
              <input type="number" min="80" max="200" value={avgHr} onChange={e => setAvgHr(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Pace (min/km)</label>
              <input
                type="number"
                min="3"
                max="12"
                step="0.01"
                placeholder="e.g. 5.42"
                value={paceMinPerKm}
                onChange={e => setPaceMinPerKm(e.target.value)}
                required
              />
            </div>
          </div>
          <label className="checkbox-label" style={{ marginBottom: 'var(--space-4)' }}>
            <input type="checkbox" checked={protocolCompliant} onChange={e => setProtocolCompliant(e.target.checked)} />
            Protocol compliant (40 min, ~140 bpm)
          </label>
        </>
      )}

      {error && <div className="form-error">{error}</div>}

      <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={submitting}>
        {submitting ? 'Saving…' : 'Log Benchmark'}
      </button>
    </form>
  );
}
