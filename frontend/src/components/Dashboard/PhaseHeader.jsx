import { useState } from 'react';

const PHASE_LABELS = {
  bench: 'Bench',
  pull_ups: 'Pull-ups',
  run: 'Run',
};

const PHASE_TYPES = [
  { value: 'bench', label: 'Bench' },
  { value: 'pull_ups', label: 'Pull-ups' },
  { value: 'run', label: 'Run' },
];

function daysRemaining(endDate) {
  const end = new Date(endDate);
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return Math.ceil((end - now) / (1000 * 60 * 60 * 24));
}

function toInputDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toISOString().slice(0, 10);
}

function formatDateRange(start, end) {
  const fmt = d => {
    if (!d) return '';
    const [yyyy, mm, dd] = d.split('T')[0].split('-');
    return `${dd}.${mm}.${yyyy}`;
  };
  return `${fmt(start)} – ${fmt(end)}`;
}

export default function PhaseHeader({ phase, onUpdatePhase, onDeletePhase, theme, onToggleTheme }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  if (!phase) return null;

  const days = daysRemaining(phase.endDate);
  const isComplete = days < 0;
  const label = PHASE_LABELS[phase.phaseType] || phase.phaseType;

  function startEdit() {
    setForm({
      name: phase.name || '',
      phaseType: phase.phaseType,
      startDate: toInputDate(phase.startDate),
      endDate: toInputDate(phase.endDate),
      notes: phase.notes || '',
    });
    setError(null);
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setError(null);
  }

  async function saveEdit() {
    setSaving(true);
    setError(null);
    try {
      await onUpdatePhase(phase.phaseId, form);
      setEditing(false);
    } catch (e) {
      setError('Save failed. Check dates and try again.');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete phase "${phase.name || phase.phaseType}"? This cannot be undone.`)) return;
    try {
      await onDeletePhase(phase.phaseId);
    } catch (e) {
      alert('Cannot delete: phase has linked sessions or benchmarks. Delete those first.');
    }
  }

  if (editing) {
    return (
      <div className="phase-header phase-header--editing">
        <div className="phase-edit-grid">
          <div className="form-group" style={{ margin: 0 }}>
            <label>Name</label>
            <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label>Type</label>
            <select value={form.phaseType} onChange={e => setForm(f => ({ ...f, phaseType: e.target.value }))}>
              {PHASE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label>Start date</label>
            <input type="date" value={form.startDate} onChange={e => setForm(f => ({ ...f, startDate: e.target.value }))} />
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label>End date</label>
            <input type="date" value={form.endDate} onChange={e => setForm(f => ({ ...f, endDate: e.target.value }))} />
          </div>
          <div className="form-group" style={{ margin: 0, gridColumn: '1 / -1' }}>
            <label>Notes</label>
            <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={2} />
          </div>
        </div>
        {error && <div style={{ color: 'var(--ready-red)', fontSize: 12, marginTop: 8 }}>{error}</div>}
        <div className="phase-edit-actions">
          <button className="btn btn-primary" onClick={saveEdit} disabled={saving}>
            {saving ? 'Saving…' : '✓ Save'}
          </button>
          <button className="btn btn-ghost" onClick={cancelEdit} disabled={saving}>✕ Cancel</button>
        </div>
      </div>
    );
  }

  return (
    <div className="phase-header">
      <div className="phase-header-left">
        <span className="phase-type-badge">{label}</span>
        <h1 className="phase-name">{phase.name}</h1>
        <p className="phase-dates">{formatDateRange(phase.startDate, phase.endDate)}</p>
        {phase.notes && <p className="phase-notes">{phase.notes}</p>}
      </div>
      <div className="phase-header-right">
        {isComplete ? (
          <span className="days-badge days-badge--done">Completed</span>
        ) : (
          <span className="days-badge">
            <span className="days-number">{days}</span>
            <span className="days-label">days left</span>
          </span>
        )}
        <div className="phase-actions">
          <button
            className="icon-btn theme-toggle-btn"
            title={theme === 'dark' ? 'Switch to Solarized Light' : 'Switch to Dark'}
            onClick={onToggleTheme}
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? '☀' : '🌙'}
          </button>
          <button className="icon-btn" title="Edit phase" onClick={startEdit}>✏</button>
          <button className="icon-btn icon-btn--danger" title="Delete phase" onClick={handleDelete}>🗑</button>
        </div>
      </div>
    </div>
  );
}
