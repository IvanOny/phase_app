import { useState, useEffect } from 'react';
import { getBodyweightLog, createBodyweightEntry, deleteBodyweightEntry } from '../../api/client.js';

function today() {
  return new Date().toISOString().slice(0, 10);
}

function fmtDate(d) {
  const s = String(d).slice(0, 10);
  const [, mm, dd] = s.split('-');
  return `${dd}.${mm}`;
}

export default function BodyweightPanel({ phaseId, isAuthenticated, onSaved }) {
  const [log, setLog] = useState([]);
  const [weightKg, setWeightKg] = useState('');
  const [date, setDate] = useState(today());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!phaseId) return;
    getBodyweightLog(phaseId).then(setLog).catch(() => setLog([]));
  }, [phaseId]);

  async function handleSave() {
    const w = parseFloat(weightKg);
    if (!w || w <= 0) { setError('Enter a valid weight'); return; }
    setSaving(true);
    setError(null);
    try {
      const entry = await createBodyweightEntry({ phaseId, weightKg: w, loggedDate: date });
      setLog(prev => [...prev, entry].sort((a, b) => a.loggedDate > b.loggedDate ? 1 : -1));
      setWeightKg('');
      onSaved?.();
    } catch {
      setError('Failed to save');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(logId) {
    try {
      await deleteBodyweightEntry(logId);
      setLog(prev => prev.filter(e => e.logId !== logId));
      onSaved?.();
    } catch {}
  }

  const latest = log.length > 0 ? log[log.length - 1] : null;

  return (
    <div className="chart-wrapper">
      <div className="chart-title-row">
        <span className="card-title">Bodyweight</span>
        {latest && (
          <span style={{ fontSize: 13, color: 'var(--text-secondary)', marginLeft: 'auto' }}>
            {latest.weightKg} kg <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>· {fmtDate(latest.loggedDate)}</span>
          </span>
        )}
      </div>

      {isAuthenticated && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: log.length ? 'var(--space-4)' : 0 }}>
          <input
            type="number"
            className="inline-input"
            placeholder="kg"
            value={weightKg}
            onChange={e => setWeightKg(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSave()}
            style={{ width: 72 }}
            min="0"
            step="0.1"
          />
          <input
            type="date"
            className="inline-input"
            value={date}
            onChange={e => setDate(e.target.value)}
            style={{ fontSize: 13 }}
          />
          <button
            className="btn btn-primary btn-xs"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? '…' : 'Save'}
          </button>
          {error && <span style={{ fontSize: 12, color: 'var(--ready-red)' }}>{error}</span>}
        </div>
      )}

      {log.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {[...log].reverse().map(entry => (
            <div key={entry.logId} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '3px 0', fontSize: 13, borderBottom: '1px solid var(--border)',
            }}>
              <span style={{ color: 'var(--text-muted)' }}>{fmtDate(entry.loggedDate)}</span>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{entry.weightKg} kg</span>
              {isAuthenticated && (
                <button
                  onClick={() => handleDelete(entry.logId)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 13, padding: '0 4px' }}
                  title="Delete"
                >✕</button>
              )}
            </div>
          ))}
        </div>
      )}

      {!log.length && !isAuthenticated && (
        <div className="chart-empty">No bodyweight logged yet</div>
      )}
    </div>
  );
}
