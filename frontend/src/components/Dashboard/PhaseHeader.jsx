import { useState } from 'react';
import { useExpandable } from '../../hooks/useExpandable.js';
import ConfirmDialog from '../Common/ConfirmDialog.jsx';

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

function daysUntilStart(startDate) {
  const start = new Date(startDate);
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  start.setHours(0, 0, 0, 0);
  return Math.ceil((start - now) / (1000 * 60 * 60 * 24));
}

function fmtShortDate(dateStr) {
  if (!dateStr) return '';
  const s = String(dateStr).split('T')[0];
  const [, mm, dd] = s.split('-');
  return `${dd}.${mm}`;
}

function phaseProgress(startDate, endDate) {
  if (!startDate || !endDate) return null;
  const start = new Date(startDate);
  const end = new Date(endDate);
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const total = end - start;
  if (total <= 0) return null;
  const elapsed = now - start;
  return Math.min(100, Math.max(0, Math.round((elapsed / total) * 100)));
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

export default function PhaseHeader({ phase, onUpdatePhase, onDeletePhase, theme, onToggleTheme, isAuthenticated, onLogout, onLoginClick, onFaqClick }) {
  const [editing, setEditing] = useState(false);
  const [showDays, toggleDays, headerRef] = useExpandable('phase-days');
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  if (!phase) return null;

  const daysLeft = daysRemaining(phase.endDate);
  const daysToStart = daysUntilStart(phase.startDate);
  // future: not started yet | current: in progress | past: ended
  const phaseState = daysToStart > 0 ? 'future' : daysLeft >= 0 ? 'current' : 'past';
  const label = PHASE_LABELS[phase.phaseType] || phase.phaseType;
  const pct = phaseProgress(phase.startDate, phase.endDate);
  const start = new Date(phase.startDate);
  const end = new Date(phase.endDate);
  const totalDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
  const dayNum = totalDays - daysLeft;

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
    <div ref={headerRef} className="phase-header">
      {pct !== null && (
        <div className="phase-progress">
          <div className="phase-progress-bar">
            <div className="phase-progress-fill" style={{ width: `${pct}%` }} />
            <span className="phase-progress-date-start">{fmtShortDate(phase.startDate)}</span>
            <span className="phase-progress-date-end">{fmtShortDate(phase.endDate)}</span>
            <span
              className={`phase-progress-label${pct >= 50 ? ' phase-progress-label--inside' : ''}`}
              style={{ left: `${pct}%` }}
            >{pct}%</span>
          </div>
        </div>
      )}
      <div className="phase-header-row">
      <div className="phase-header-left">
        <h1 className="phase-name">{phase.name}</h1>
        {phase.notes && <p className="phase-notes">{phase.notes}</p>}
        <div className="phase-actions">
          <button
            className="icon-btn theme-toggle-btn"
            title={theme === 'dark' ? 'Switch to Solarized Light' : 'Switch to Dark'}
            onClick={onToggleTheme}
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? '☀' : '🌙'}
          </button>
          {isAuthenticated ? (
            <>
              <button className="icon-btn" title="Edit phase" onClick={startEdit}>✏</button>
              <button className="icon-btn icon-btn--danger" title="Delete phase" onClick={() => setConfirmOpen(true)}>🗑</button>
              <button className="icon-btn" title="Log out" onClick={onLogout} style={{ fontSize: 14 }}>⏏</button>
            </>
          ) : (
            <button className="btn btn-ghost" title="Log in" onClick={onLoginClick} style={{ fontSize: 13, padding: '3px 10px' }}>
              Log in
            </button>
          )}
          <button className="btn btn-ghost" onClick={onFaqClick} style={{ fontSize: 13, padding: '3px 10px' }}>
            FAQ
          </button>
        </div>
      </div>
      <div className="phase-header-right">
        {phaseState === 'future' && (
          <div className="days-badge days-badge--future">
            <span className="days-number">{daysToStart}</span>
            <span className="days-label">days to start</span>
          </div>
        )}
        {phaseState === 'current' && (
          <button className={`days-badge${showDays ? ' days-badge--open' : ''}`} onClick={toggleDays} style={{ cursor: 'pointer' }}>
            <span className="days-number">{daysLeft}</span>
            <span className="days-label">days left</span>
          </button>
        )}
        {phaseState === 'past' && (
          <div className="days-badge days-badge--past">
            <span className="days-number">{Math.abs(daysLeft)}</span>
            <span className="days-label">days ago</span>
          </div>
        )}
      </div>
      </div>
      {showDays && (
        <div className="e1rm-explanation" style={{ marginTop: 'var(--space-2)' }}>
          <p>{formatDateRange(phase.startDate, phase.endDate)}</p>
          <p>Day {dayNum} of {totalDays} — <strong>{daysLeft} days</strong> remaining (<strong>{pct}%</strong> complete)</p>
        </div>
      )}
      {confirmOpen && (
        <ConfirmDialog
          message={`Delete phase "${phase.name || phase.phaseType}"? This cannot be undone.`}
          onConfirm={async () => { setConfirmOpen(false); await handleDelete(); }}
          onCancel={() => setConfirmOpen(false)}
        />
      )}
    </div>
  );
}
