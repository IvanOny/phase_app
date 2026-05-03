import { useState } from 'react';
import { createPhase } from '../../api/client.js';

const PHASE_TYPES = ['bench', 'pull_ups', 'run'];

function today() {
  return new Date().toISOString().slice(0, 10);
}

export default function CreatePhaseForm({ onPhaseCreated }) {
  const [phaseType, setPhaseType] = useState('bench');
  const [name, setName] = useState('');
  const [startDate, setStartDate] = useState(today());
  const [endDate, setEndDate] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    if (endDate && endDate < startDate) {
      setError('End date must be after start date');
      return;
    }
    setSubmitting(true);
    try {
      const phase = await createPhase({ phaseType, startDate, endDate, name: name || null });
      onPhaseCreated(phase);
      setName('');
      setEndDate('');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <label>Phase Type</label>
        <select value={phaseType} onChange={e => setPhaseType(e.target.value)}>
          {PHASE_TYPES.map(t => <option key={t} value={t}>{t.replace('_', '-')}</option>)}
        </select>
      </div>
      <div className="form-group">
        <label>Name (optional)</label>
        <input type="text" placeholder="e.g. Q2 Bench Focus" value={name} onChange={e => setName(e.target.value)} />
      </div>
      <div className="form-group">
        <label>Start Date</label>
        <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} required />
      </div>
      <div className="form-group">
        <label>End Date</label>
        <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} required />
      </div>
      {error && <div className="form-error">{error}</div>}
      <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={submitting}>
        {submitting ? 'Creating…' : 'Create Phase'}
      </button>
    </form>
  );
}
