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

  const avgHrv = summary.avgHrv != null ? summary.avgHrv.toFixed(1) : null;
  const peakE1rm = summary.peakE1rmKg != null ? `${summary.peakE1rmKg} kg` : null;
  const latestE1rm = summary.latestE1rmKg != null ? `${summary.latestE1rmKg} kg` : null;
  const totalVol = summary.totalBenchVolumeKgReps != null
    ? `${Math.round(summary.totalBenchVolumeKgReps).toLocaleString()} kg·reps`
    : null;

  return (
    <div className="phase-summary-card">
      <StatTile label="Sessions" value={summary.sessionCount} />
      <StatTile label="Peak e1RM" value={peakE1rm} />
      <StatTile label="Latest e1RM" value={latestE1rm} />
      <StatTile label="Total volume" value={totalVol} />
      <StatTile label="Avg HRV" value={avgHrv} />
    </div>
  );
}
