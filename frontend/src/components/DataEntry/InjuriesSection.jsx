import { useState, useEffect } from 'react';
import { getInjuries, createInjury, updateInjury, deleteInjury } from '../../api/client.js';
import { SEVERITY, daysLimited } from '../Health/InjuriesCard.jsx';

function today() {
  return new Date().toISOString().slice(0, 10);
}

function fmt(iso) {
  const [, m, d] = iso.split('-');
  return `${d}.${m}`;
}

const blank = () => ({ startedOn: today(), area: '', severity: 'moderate', note: '' });

/**
 * Logging an injury, and closing one. The open ones stay on screen, each
 * with the one button it will eventually need; the closed ones fold away
 * like the bodyweight list, reachable only to correct or delete.
 */
export default function InjuriesSection({ isAuthenticated, onChanged }) {
  const [list, setList] = useState([]);
  const [form, setForm] = useState(blank());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    getInjuries().then(r => setList(Array.isArray(r) ? r : [])).catch(() => setList([]));
  }, []);

  function upsert(row) {
    onChanged?.();
    setList(prev => [...prev.filter(i => i.injuryId !== row.injuryId), row]
      .sort((a, b) => (a.startedOn > b.startedOn ? 1 : -1)));
  }

  async function add() {
    if (!form.area.trim()) { setError('Say where — knee, lower back, groin…'); return; }
    setBusy(true); setError(null);
    try {
      upsert(await createInjury(form));
      setForm(blank());
    } catch (e) {
      setError(e?.message || 'Failed to save');
    } finally {
      setBusy(false);
    }
  }

  async function resolve(inj, on) {
    try { upsert(await updateInjury(inj.injuryId, { resolvedOn: on })); } catch { /* list unchanged */ }
  }

  async function remove(inj) {
    try {
      await deleteInjury(inj.injuryId);
      setList(prev => prev.filter(i => i.injuryId !== inj.injuryId));
      onChanged?.();
    } catch { /* list unchanged */ }
  }

  const open = list.filter(i => !i.resolvedOn);
  const closed = [...list.filter(i => i.resolvedOn)].reverse();
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  return (
    <div className="chart-wrapper">
      <div className="chart-title-row">
        <span className="card-title">Injuries</span>
        {closed.length > 0 && (
          <button onClick={() => setShowAll(v => !v)} aria-expanded={showAll}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', marginLeft: 'auto',
                           fontSize: 11, color: 'var(--text-muted)' }}>
            {showAll ? 'hide' : 'resolved ' + closed.length}
          </button>
        )}
      </div>

      {isAuthenticated && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          <input type="date" className="inline-input" value={form.startedOn} max={today()}
                 onChange={e => set('startedOn', e.target.value)} aria-label="Started"
                 style={{ fontSize: 13 }} />
          <input type="text" className="inline-input" placeholder="where — e.g. right knee"
                 value={form.area} onChange={e => set('area', e.target.value)}
                 onKeyDown={e => e.key === 'Enter' && add()}
                 style={{ width: 170 }} />
          <select className="inline-input" value={form.severity} onChange={e => set('severity', e.target.value)}
                  aria-label="Severity" style={{ fontSize: 13 }}>
            {Object.keys(SEVERITY).map(k => <option key={k} value={k}>{k}</option>)}
          </select>
          <input type="text" className="inline-input" placeholder="note (optional)"
                 value={form.note} onChange={e => set('note', e.target.value)}
                 style={{ flex: '1 1 160px', minWidth: 0 }} />
          <button className="btn btn-primary btn-xs" onClick={add} disabled={busy}>
            {busy ? '…' : 'Log'}
          </button>
          {error && <span style={{ fontSize: 12, color: 'var(--ready-red)', width: '100%' }}>{error}</span>}
        </div>
      )}

      {open.length > 0 && (
        <div style={{ marginTop: 'var(--space-3)', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {open.map(inj => (
            <div key={inj.injuryId} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13,
                                             flexWrap: 'wrap' }}>
              <span style={{ width: 8, height: 8, borderRadius: 2,
                             background: (SEVERITY[inj.severity] || SEVERITY.moderate).color }} />
              <span style={{ fontWeight: 600 }}>{inj.area}</span>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                since {fmt(inj.startedOn)} · day {daysLimited(inj)}
              </span>
              {isAuthenticated && (
                <>
                  <button className="btn btn-xs" style={{ marginLeft: 'auto' }}
                          onClick={() => resolve(inj, today())}>Resolved today</button>
                  <button onClick={() => remove(inj)} title="Delete"
                          style={{ background: 'none', border: 'none', cursor: 'pointer',
                                   color: 'var(--text-muted)', fontSize: 13, padding: '0 4px' }}>✕</button>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {showAll && closed.length > 0 && (
        <div style={{ marginTop: 'var(--space-3)', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {closed.map(inj => (
            <div key={inj.injuryId} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13,
                                             padding: '3px 0', borderBottom: '1px solid var(--border)' }}>
              <span style={{ color: 'var(--text-muted)', width: 92 }}>
                {fmt(inj.startedOn)}–{fmt(inj.resolvedOn)}
              </span>
              <span style={{ fontWeight: 600, flex: 1, minWidth: 0 }} title={inj.note || ''}>{inj.area}</span>
              {isAuthenticated && (
                <>
                  <button onClick={() => resolve(inj, null)} title="Reopen"
                          style={{ background: 'none', border: 'none', cursor: 'pointer',
                                   color: 'var(--text-muted)', fontSize: 11 }}>reopen</button>
                  <button onClick={() => remove(inj)} title="Delete"
                          style={{ background: 'none', border: 'none', cursor: 'pointer',
                                   color: 'var(--text-muted)', fontSize: 13, padding: '0 4px' }}>✕</button>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
