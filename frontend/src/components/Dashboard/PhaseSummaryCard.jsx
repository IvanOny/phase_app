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

function improvementStyle(pct) {
  if (pct >= 15) return { color: '#f59e0b', bg: 'rgba(245,158,11,0.10)', fontSize: 28 };
  if (pct >= 10) return { color: '#22c55e', bg: 'rgba(34,197,94,0.10)', fontSize: 26 };
  if (pct >= 5)  return { color: '#10b981', bg: 'rgba(16,185,129,0.08)', fontSize: 24 };
  if (pct >= 2)  return { color: '#0d9488', bg: 'rgba(13,148,136,0.07)', fontSize: 22 };
  return          { color: 'var(--text-secondary)', bg: 'transparent', fontSize: 20 };
}

function ImprovementTile({ pct, label }) {
  const { color, bg, fontSize } = improvementStyle(pct);
  return (
    <div className="summary-tile improvement-tile" style={{ background: bg, borderColor: color + '33' }}>
      <div className="summary-tile-value" style={{ color, fontSize }}>{`+${pct.toFixed(1)}%`}</div>
      <div className="summary-tile-label">{label}</div>
    </div>
  );
}

export default function PhaseSummaryCard({ phaseId, refreshKey }) {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    if (!phaseId) return;
    setSummary(null);
    getPhaseSummary(phaseId).then(setSummary);
  }, [phaseId, refreshKey]);

  if (!summary) return null;

  const peakE1rm = summary.peakE1rmKg != null ? `${summary.peakE1rmKg} kg` : null;

  let improvementPct = null;
  if (
    summary.peakE1rmKg != null &&
    summary.lowestE1rmKg != null &&
    summary.peakE1rmKg !== summary.lowestE1rmKg
  ) {
    improvementPct = ((summary.peakE1rmKg - summary.lowestE1rmKg) / summary.lowestE1rmKg) * 100;
  }

  return (
    <div className="phase-summary-card">
      <StatTile label="Peak e1RM" value={peakE1rm} />
      {improvementPct != null && <ImprovementTile pct={improvementPct} label="Improvement" />}
    </div>
  );
}
