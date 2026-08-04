import HoldButton from './HoldButton.jsx';

// Full-width sheet for one day — the roomy alternative to cramped grid cells.
// This is where actions live: the grid chips are display-only so a stray tap
// there can't complete or delete anything. Remove is hold-to-confirm.
export default function DayDetail({ dateLabel, isPast, occ, sug, onComplete, onRemove, onCommit, onClose }) {
  const empty = occ.length === 0 && sug.length === 0;
  return (
    <div className="exq-modal-backdrop" onClick={onClose}>
      <div className="exq-modal exq-day-sheet" onClick={e => e.stopPropagation()}>
        <div className="exq-modal-head">
          <span>{dateLabel}</span>
          <button className="exq-btn" onClick={onClose}>✕</button>
        </div>

        {empty && <div className="exq-field-note" style={{ padding: '12px 0' }}>Nothing scheduled. Drag an exercise here, or commit a suggestion.</div>}

        {occ.map(o => (
          <div key={`o${o.id}`} className={`exq-day-row${o.status === 'done' ? ' exq-day-row--done' : ''}`}>
            <div className="exq-day-row-main">
              <div className="exq-day-row-name">{o.name}{o.status === 'done' ? ' ✓' : ''}</div>
              {o.description && <div className="exq-day-row-desc">{o.description}</div>}
            </div>
            <div className="exq-day-row-actions">
              {o.status !== 'done' && isPast && (
                <button className="exq-btn active" onClick={() => onComplete(o.id)}>Done</button>
              )}
              {/* Destructive — needs a deliberate press-and-hold. */}
              <HoldButton className="exq-btn exq-btn--danger" title="Hold to remove" onActivate={() => onRemove(o.id)}>
                Hold to remove
              </HoldButton>
            </div>
          </div>
        ))}

        {sug.map(s => (
          <div key={`s${s.exerciseId}`} className="exq-day-row exq-day-row--suggestion">
            <div className="exq-day-row-main">
              <div className="exq-day-row-name">{s.name}</div>
              <div className="exq-day-row-desc">{s.description || 'cadence suggestion'}</div>
            </div>
            <div className="exq-day-row-actions">
              <button className="exq-btn" onClick={() => onCommit(s.exerciseId)}>Add</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
