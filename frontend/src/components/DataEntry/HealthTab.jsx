import { useState, useEffect } from 'react';
import { getMonthlyMetrics, saveMonthlyMetrics } from '../../api/client.js';
import BodyweightPanel from '../Powerlifting/BodyweightPanel.jsx';

// One row per month, typed in at month's end. "Best" is best, not highest:
// the field says which way is up, the table stores what was typed.
const FIELDS = [
  { key: 'hrvBest',    group: 'HRV',          label: 'best',    unit: 'ms',        step: '1',   hint: 'higher is better' },
  { key: 'hrvAvg',     group: 'HRV',          label: 'average', unit: 'ms',        step: '1' },
  { key: 'rhrBest',    group: 'Resting HR',   label: 'best',    unit: 'bpm',       step: '1',   hint: 'lowest' },
  { key: 'rhrAvg',     group: 'Resting HR',   label: 'average', unit: 'bpm',       step: '1' },
  { key: 'vo2maxBest', group: 'VO₂ max',      label: 'best',    unit: 'ml/kg/min', step: '0.1' },
  { key: 'sleepAvg',   group: 'Sleep score',  label: 'average', unit: '',          step: '1' },
];
const GROUPS = ['HRV', 'Resting HR', 'VO₂ max', 'Sleep score'];

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                'August', 'September', 'October', 'November', 'December'];

function thisMonth() {
  return new Date().toISOString().slice(0, 7);
}

function shiftMonth(ym, by) {
  const [y, m] = ym.split('-').map(Number);
  const d = new Date(Date.UTC(y, m - 1 + by, 1));
  return d.toISOString().slice(0, 7);
}

function monthLabel(ym) {
  const [y, m] = ym.split('-').map(Number);
  return `${MONTHS[m - 1]} ${y}`;
}

function fmtStamp(iso) {
  if (!iso) return '';
  const s = String(iso).slice(0, 10);
  const [, mm, dd] = s.split('-');
  return `${dd}.${mm}`;
}

const empty = () => Object.fromEntries(FIELDS.map(f => [f.key, '']));

export default function HealthTab({ phaseId, isAuthenticated, onBodyweightSaved }) {
  const [month, setMonth] = useState(thisMonth());
  const [values, setValues] = useState(empty());
  const [savedAt, setSavedAt] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Opening a month shows what it already holds, so saving overwrites rather
  // than duplicates. A month with nothing yet is a blank form.
  useEffect(() => {
    let live = true;
    setError(null);
    getMonthlyMetrics(month).then(row => {
      if (!live) return;
      const next = empty();
      if (row) FIELDS.forEach(f => { next[f.key] = row[f.key] ?? ''; });
      setValues(next);
      setSavedAt(row?.updatedAt ?? null);
      setDirty(false);
    }).catch(() => { if (live) setError('Could not load this month'); });
    return () => { live = false; };
  }, [month]);

  function set(key, v) {
    setValues(prev => ({ ...prev, [key]: v }));
    setDirty(true);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const row = await saveMonthlyMetrics({ month, ...values });
      setSavedAt(row.updatedAt);
      setDirty(false);
    } catch {
      setError('Failed to save');
    } finally {
      setSaving(false);
    }
  }

  const isCurrent = month === thisMonth();
  const anyValue = FIELDS.some(f => values[f.key] !== '' && values[f.key] != null);

  return (
    <>
      <div className="chart-wrapper">
        <div className="chart-title-row">
          <span className="card-title">Recovery</span>
          {savedAt && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
              saved {fmtStamp(savedAt)}
            </span>
          )}
        </div>

        {/* The month, with a step either way. The current month is the default
            and can't be stepped past: there is nothing to enter for October
            in September. */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 'var(--space-4)' }}>
          <button className="btn btn-xs" onClick={() => setMonth(m => shiftMonth(m, -1))}
                  aria-label="Previous month">‹</button>
          <span style={{ fontWeight: 600, minWidth: 140, textAlign: 'center' }}>{monthLabel(month)}</span>
          <button className="btn btn-xs" onClick={() => setMonth(m => shiftMonth(m, 1))}
                  disabled={isCurrent} aria-label="Next month">›</button>
          {!isCurrent && (
            <button className="btn btn-xs" onClick={() => setMonth(thisMonth())}
                    style={{ marginLeft: 4 }}>This month</button>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr 1fr', rowGap: 10, columnGap: 12,
                      alignItems: 'center', fontSize: 13 }}>
          {GROUPS.map(g => {
            const fs = FIELDS.filter(f => f.group === g);
            return (
              <div key={g} style={{ display: 'contents' }}>
                <span style={{ color: 'var(--text-secondary)', fontWeight: 600, whiteSpace: 'nowrap' }}>{g}</span>
                {fs.map(f => (
                  <label key={f.key} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ color: 'var(--text-muted)', width: 52 }}>{f.label}</span>
                    <input
                      type="number"
                      className="inline-input"
                      value={values[f.key]}
                      onChange={e => set(f.key, e.target.value)}
                      disabled={!isAuthenticated}
                      inputMode="decimal"
                      step={f.step}
                      min="0"
                      style={{ width: 68 }}
                      title={f.hint || ''}
                    />
                    {f.unit && <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{f.unit}</span>}
                  </label>
                ))}
                {fs.length === 1 && <span />}
              </div>
            );
          })}
        </div>

        {isAuthenticated && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 'var(--space-4)' }}>
            <button className="btn btn-primary btn-xs" onClick={handleSave}
                    disabled={saving || !dirty || !anyValue}>
              {saving ? '…' : savedAt ? 'Update month' : 'Save month'}
            </button>
            {dirty && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>unsaved changes</span>}
            {error && <span style={{ fontSize: 12, color: 'var(--ready-red)' }}>{error}</span>}
          </div>
        )}
      </div>

      {/* The old Bodyweight tab, as a section. Its data is per date, not per
          month — the pull-up e1RM leans on that — so nothing about it changed
          except where it lives. The month above doesn't filter it. */}
      <BodyweightPanel phaseId={phaseId} isAuthenticated={isAuthenticated} onSaved={onBodyweightSaved} />
    </>
  );
}
