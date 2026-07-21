import { useState, useEffect, useCallback } from 'react';

// Asks the backend (which asks Claude) where to place a recurring exercise,
// reasoning from the phase-app main-lift week. Suggestion only — the user commits.
export default function SlotSuggestion({ exercise, onSuggest, onPlace, onClose }) {
  const [loading, setLoading] = useState(true);
  const [sug, setSug] = useState(null);      // { date, weekday, rationale }
  const [err, setErr] = useState(null);
  const [placing, setPlacing] = useState(false);
  const [avoid, setAvoid] = useState([]);

  const ask = useCallback(async (avoidList) => {
    setLoading(true); setErr(null);
    try { setSug(await onSuggest(exercise.id, avoidList)); }
    catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  }, [exercise.id, onSuggest]);

  useEffect(() => { ask([]); }, [ask]);

  function another() {
    const next = sug ? [...avoid, sug.date] : avoid;
    setAvoid(next);
    ask(next);
  }

  async function place() {
    setPlacing(true);
    try { await onPlace(exercise.id, sug.date); onClose(); }
    catch (e) { setErr(e.message); setPlacing(false); }
  }

  const fmt = d => new Date(d + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });

  return (
    <div className="exq-modal-backdrop" onClick={onClose}>
      <div className="exq-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 380 }}>
        <div className="exq-modal-head">
          <span>💡 Where to put “{exercise.name}”</span>
          <button className="exq-btn" onClick={onClose}>✕</button>
        </div>

        {loading && <div className="exq-field-note" style={{ padding: '18px 0' }}>Thinking about your week…</div>}
        {err && <div className="exq-error">{err}</div>}

        {!loading && sug && (
          <>
            <div className="exq-suggest-date">{fmt(sug.date)}</div>
            {sug.rationale && <div className="exq-suggest-why">{sug.rationale}</div>}
            <div className="exq-modal-actions">
              <button className="exq-btn" onClick={another} disabled={placing}>Suggest another</button>
              <span style={{ flex: 1 }} />
              <button className="exq-btn" onClick={onClose} disabled={placing}>Not now</button>
              <button className="exq-btn active" onClick={place} disabled={placing}>{placing ? 'Placing…' : 'Place it'}</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
