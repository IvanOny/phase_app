import { useState, useEffect } from 'react';
import { getMonthlyMetrics, saveMonthlyMetrics, getMonthlyRun, saveMonthlyRun } from '../../api/client.js';
import BodyweightPanel from '../Powerlifting/BodyweightPanel.jsx';
import InjuriesSection from './InjuriesSection.jsx';
import { thisMonth, shiftMonth, monthLabel, clock } from '../../utils/months.js';

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

function fmtStamp(iso) {
  if (!iso) return '';
  const s = String(iso).slice(0, 10);
  const [, mm, dd] = s.split('-');
  return `${dd}.${mm}`;
}

const empty = () => Object.fromEntries(FIELDS.map(f => [f.key, '']));

// What a parsed Garmin row shows as, before and after saving: the numbers
// that say what kind of month it was, not all twenty-two.
const RUN_SUMMARY = [
  ['runs',      r => r.activities],
  ['distance',  r => `${r.totalKm} km`],
  ['time',      r => clock(r.totalTimeS)],
  ['pace',      r => `${clock(r.avgPaceS, true)} /km`],
  ['GAP',       r => `${clock(r.gapPaceS, true)} /km`],
  ['avg HR',    r => `${r.avgHr} bpm`],
  ['ascent',    r => `${r.totalAscentM} m`],
  ['cadence',   r => `${r.avgCadenceSpm} spm`],
  ['stride',    r => `${r.avgStrideM} m`],
];

// The Garmin monthly running row, pasted whole. One field instead of
// twenty-two: the row is what the browser puts on the clipboard from Garmin
// Connect's table, and the server parses it -- units, h:m:s, /km and all --
// or says which cell it could not read.
function RunSection({ month, isAuthenticated }) {
  const [saved, setSaved] = useState(null);      // the stored row for `month`, if any
  const [raw, setRaw] = useState('');
  const [preview, setPreview] = useState(null);  // parsed but not saved
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let live = true;
    setPreview(null); setError(null); setRaw('');
    getMonthlyRun(month).then(r => { if (live) setSaved(r); }).catch(() => {});
    return () => { live = false; };
  }, [month]);

  async function parse(text) {
    setRaw(text);
    setPreview(null);
    setError(null);
    if (!text.trim()) return;
    setBusy(true);
    try {
      setPreview(await saveMonthlyRun({ raw: text, preview: true }));
    } catch (e) {
      setError(e?.message || 'Could not read that row');
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const r = await saveMonthlyRun({ raw });
      setSaved(r);
      setPreview(null);
      setRaw('');
    } catch (e) {
      setError(e?.message || 'Failed to save');
    } finally {
      setBusy(false);
    }
  }

  const shown = preview || saved;
  const otherMonth = preview && preview.month !== month;

  return (
    <div className="chart-wrapper">
      <div className="chart-title-row">
        <span className="card-title">Running</span>
        {saved && !preview && (
          <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
            saved {fmtStamp(saved.updatedAt)}
          </span>
        )}
      </div>

      {isAuthenticated && (
        <>
          <input
            type="text"
            className="inline-input"
            placeholder="Paste the month's row from Garmin here"
            value={raw}
            onChange={e => parse(e.target.value)}
            onPaste={e => { e.preventDefault(); parse(e.clipboardData.getData('text')); }}
            style={{ width: '100%', fontSize: 12, fontFamily: 'var(--font-mono, monospace)' }}
          />
          {error && <div style={{ fontSize: 12, color: 'var(--ready-red)', marginTop: 6 }}>{error}</div>}
        </>
      )}

      {shown && (
        <div style={{ marginTop: 'var(--space-3)' }}>
          {preview && (
            <div style={{ fontSize: 12, color: otherMonth ? 'var(--ready-red)' : 'var(--text-muted)', marginBottom: 6 }}>
              {otherMonth
                ? `This row is ${monthLabel(preview.month)} — it will be saved there, not in ${monthLabel(month)}.`
                : `Read as ${monthLabel(preview.month)}. Check, then save.`}
            </div>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, auto 1fr)', columnGap: 10, rowGap: 4, fontSize: 13 }}>
            {RUN_SUMMARY.map(([label, get]) => (
              <div key={label} style={{ display: 'contents' }}>
                <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                <span style={{ fontWeight: 600 }}>{get(shown)}</span>
              </div>
            ))}
          </div>
          {preview && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 'var(--space-3)' }}>
              <button className="btn btn-primary btn-xs" onClick={save} disabled={busy}>
                {busy ? '…' : saved && !otherMonth ? 'Replace month' : 'Save month'}
              </button>
              <button className="btn btn-xs" onClick={() => { setPreview(null); setRaw(''); }}>Discard</button>
            </div>
          )}
        </div>
      )}

      {!shown && !isAuthenticated && (
        <div className="chart-empty">No running data for {monthLabel(month)}</div>
      )}
    </div>
  );
}

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

        {/* Two columns: the metric, then its fields in a row that wraps. On a
            phone the row folds and "average" drops under "best" instead of
            running off the right edge. */}
        <div style={{ display: 'grid', gridTemplateColumns: 'auto minmax(0, 1fr)', rowGap: 10, columnGap: 12,
                      alignItems: 'center', fontSize: 13 }}>
          {GROUPS.map(g => {
            const fs = FIELDS.filter(f => f.group === g);
            return (
              <div key={g} style={{ display: 'contents' }}>
                <span style={{ color: 'var(--text-secondary)', fontWeight: 600, whiteSpace: 'nowrap' }}>{g}</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 16px' }}>
                  {fs.map(f => (
                    <label key={f.key} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ color: 'var(--text-muted)' }}>{f.label}</span>
                      <input
                        type="number"
                        className="inline-input"
                        value={values[f.key]}
                        onChange={e => set(f.key, e.target.value)}
                        disabled={!isAuthenticated}
                        inputMode="decimal"
                        step={f.step}
                        min="0"
                        style={{ width: 64 }}
                        title={f.hint || ''}
                      />
                      {f.unit && <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{f.unit}</span>}
                    </label>
                  ))}
                </div>
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

      <RunSection month={month} isAuthenticated={isAuthenticated} />

      <InjuriesSection isAuthenticated={isAuthenticated} onChanged={onBodyweightSaved} />

      {/* The old Bodyweight tab, as a section. Its data is per date, not per
          month — the pull-up e1RM leans on that — so nothing about it changed
          except where it lives. The month above doesn't filter it. */}
      <BodyweightPanel phaseId={phaseId} isAuthenticated={isAuthenticated} onSaved={onBodyweightSaved} />
    </>
  );
}
