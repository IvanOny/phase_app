import { useState, useEffect } from 'react';
import { getPhaseSummary } from '../../api/client.js';
import { useExpandable } from '../../hooks/useExpandable.js';

function improvementStyle(pct) {
  if (pct >= 15) return { color: '#f59e0b', bg: 'rgba(245,158,11,0.10)', fontSize: 28 };
  if (pct >= 10) return { color: '#22c55e', bg: 'rgba(34,197,94,0.10)', fontSize: 26 };
  if (pct >= 5)  return { color: '#10b981', bg: 'rgba(16,185,129,0.08)', fontSize: 24 };
  if (pct >= 2)  return { color: '#0d9488', bg: 'rgba(13,148,136,0.07)', fontSize: 22 };
  return          { color: 'var(--text-secondary)', bg: 'transparent', fontSize: 20 };
}

function ImprovementTile({ pct, kgDelta, label, onClick, isOpen }) {
  const { color, bg, fontSize } = improvementStyle(pct);
  return (
    <button
      className={`summary-tile improvement-tile${isOpen ? ' summary-tile--open' : ''}`}
      style={{ '--tile-bg': bg, borderColor: color + '33', cursor: 'pointer', textAlign: 'inherit' }}
      onClick={onClick}
    >
      <div className="summary-tile-value" style={{ color, fontSize, whiteSpace: 'nowrap' }}>{`+${kgDelta.toFixed(1)} kg (${pct.toFixed(1)}%)`}</div>
      <div className="summary-tile-label">{label}</div>
    </button>
  );
}

export default function PhaseSummaryCard({ phaseId, previousPhaseId, bestSet, refreshKey }) {
  const [summary, setSummary] = useState(null);
  const [prevSummary, setPrevSummary] = useState(null);
  const [showInfo, toggleInfo, cardRef] = useExpandable('peak-e1rm');
  const [showProgress, toggleProgress] = useExpandable('progress', cardRef);

  useEffect(() => {
    if (!phaseId) return;
    setSummary(null);
    getPhaseSummary(phaseId).then(setSummary);
  }, [phaseId, refreshKey]);

  useEffect(() => {
    if (!previousPhaseId) { setPrevSummary(null); return; }
    getPhaseSummary(previousPhaseId).then(setPrevSummary);
  }, [previousPhaseId]);

  if (!summary) return null;

  const peakE1rm = summary.peakE1rmKg != null ? `${summary.peakE1rmKg} kg` : null;

  const exampleSet = bestSet
    ?? (summary.peakTopSetLoadKg != null
      ? { loadKg: summary.peakTopSetLoadKg, reps: summary.peakTopSetReps, e1rmKg: summary.peakE1rmKg }
      : null)
    ?? (prevSummary?.peakTopSetLoadKg != null
      ? { loadKg: prevSummary.peakTopSetLoadKg, reps: prevSummary.peakTopSetReps, e1rmKg: prevSummary.peakE1rmKg, prevPhase: true }
      : null);

  let improvementPct = null;
  if (
    summary.peakE1rmKg != null &&
    summary.startE1rmKg != null &&
    summary.peakE1rmKg !== summary.startE1rmKg
  ) {
    improvementPct = ((summary.peakE1rmKg - summary.startE1rmKg) / summary.startE1rmKg) * 100;
  }

  return (
    <div ref={cardRef} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      <div className="phase-summary-card">
        <button
          className={`summary-tile${showInfo ? ' summary-tile--open' : ''}`}
          onClick={toggleInfo}
          style={{ cursor: 'pointer', textAlign: 'inherit' }}
        >
          <div className="summary-tile-value">{peakE1rm ?? '—'}</div>
          <div className="summary-tile-label">Peak e1RM</div>
        </button>
        {improvementPct != null && (
          <ImprovementTile
            pct={improvementPct}
            kgDelta={summary.peakE1rmKg - summary.startE1rmKg}
            label="Progress"
            onClick={toggleProgress}
            isOpen={showProgress}
          />
        )}
      </div>
      {showProgress && summary.startE1rmKg != null && summary.peakE1rmKg != null && (
        <div className="e1rm-explanation">
          <p>Phase start e1RM: <strong>{summary.startE1rmKg} kg</strong> ({summary.startTopSetLoadKg} kg × {summary.startTopSetReps} reps)</p>
          <p>Phase peak e1RM: <strong>{summary.peakE1rmKg} kg</strong> ({summary.peakTopSetLoadKg} kg × {summary.peakTopSetReps} reps)</p>
          <p style={{ fontFamily: 'monospace' }}>
            <span style={{ fontFamily: 'inherit', color: 'var(--text-muted)' }}>
              ({summary.peakE1rmKg} − {summary.startE1rmKg}) / {summary.startE1rmKg} × 100
            </span>
            {' = '}
            <strong>+{improvementPct.toFixed(1)}%</strong>
          </p>
        </div>
      )}
      {showInfo && (
        <div className="e1rm-explanation">
          <p><strong>e1RM</strong> — estimated 1-rep max — a prediction of the maximum weight you could lift for 1 rep, calculated from a top set.</p>
          <p style={{ fontFamily: 'monospace' }}>e1RM = w × (1 + r / 30)</p>
          {exampleSet && (
            <p style={{ fontFamily: 'monospace' }}>
              <span style={{ fontFamily: 'inherit', color: 'var(--text-secondary)' }}>{exampleSet.prevPhase ? 'Prev phase best' : 'Phase best'}: {exampleSet.loadKg} kg × {exampleSet.reps} reps</span>
              <br />
              {exampleSet.loadKg} × (1 + {exampleSet.reps} / 30) = <strong>{exampleSet.e1rmKg} kg</strong>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
