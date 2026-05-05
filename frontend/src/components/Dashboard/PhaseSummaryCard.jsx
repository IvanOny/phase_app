import { useState, useEffect } from 'react';
import { getPhaseSummary } from '../../api/client.js';

function StatTile({ label, value }) {
  return (
    <div className="summary-tile">
      <div className="summary-tile-value">{value ?? '—'}</div>
      <div className="summary-tile-label">{label}</div>
    </div>
  );
}

export default function PhaseSummaryCard({ phaseId }) {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    if (!phaseId) return;
    setSummary(null);
    getPhaseSummary(phaseId).then(setSummary);
  }, [phaseId]);

  if (!summary) return null;

  const peakE1rm = summary.peakE1rmKg != null ? `${summary.peakE1rmKg} kg` : null;
  const latestE1rm = summary.latestE1rmKg != null ? `${summary.latestE1rmKg} kg` : null;
  const showLatest = summary.latestE1rmKg != null && summary.latestE1rmKg !== summary.peakE1rmKg;

  let improvement = null;
  if (
    summary.peakE1rmKg != null &&
    summary.lowestE1rmKg != null &&
    summary.peakE1rmKg !== summary.lowestE1rmKg
  ) {
    const pct = ((summary.peakE1rmKg - summary.lowestE1rmKg) / summary.lowestE1rmKg) * 100;
    improvement = `+${pct.toFixed(1)}%`;
  }

  return (
    <div className="phase-summary-card">
      <StatTile label="Peak e1RM" value={peakE1rm} />
      {showLatest && <StatTile label="Latest e1RM" value={latestE1rm} />}
      {improvement && <StatTile label="Improvement" value={improvement} />}
    </div>
  );
}
