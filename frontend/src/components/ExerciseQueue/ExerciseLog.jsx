import { useState, useEffect } from 'react';
import { getExqHistory } from '../../api/exqClient.js';

function fmt(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }) +
    ' · ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

export default function ExerciseLog() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getExqHistory(100).then(setItems).catch(e => setError(e.message));
  }, []);

  if (error) return <div className="exq-error">{error}</div>;
  if (!items) return <div className="exq-loading">Loading…</div>;
  if (items.length === 0) return <div className="exq-empty">Nothing logged yet.</div>;

  return (
    <div className="exq-log">
      {items.map(h => (
        <div key={h.id} className="exq-log-row">
          <div className="exq-log-name">{h.name || '(removed)'}</div>
          <div className="exq-log-meta">
            {fmt(h.doneAt)}
            {h.doseActual ? ` · ${h.doseActual}` : ''}
            {h.source ? <span className="exq-log-src">{h.source}</span> : null}
          </div>
        </div>
      ))}
    </div>
  );
}
