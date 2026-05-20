import { useState } from 'react';

function fmtDate(dateStr) {
  if (!dateStr) return '';
  const s = String(dateStr).slice(0, 10);
  const [, mm, dd] = s.split('-');
  return `${dd}.${mm}`;
}

function formatPace(secPerKm) {
  if (secPerKm == null) return '—';
  const m = Math.floor(secPerKm / 60);
  const s = Math.round(secPerKm % 60).toString().padStart(2, '0');
  return `${m}:${s} /km`;
}

function formatDuration(totalSeconds) {
  if (totalSeconds == null) return '—';
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function StatTooltip({ rows }) {
  if (!rows.length) return null;
  return (
    <div className="chart-tooltip pull-stat-tooltip">
      {rows.map((r, i) => (
        <div key={i} className="tooltip-row">
          <span>{fmtDate(r.date)}</span>
          <span>{r.value}</span>
        </div>
      ))}
    </div>
  );
}

function StatPair({ label, value, tooltip }) {
  const [show, setShow] = useState(false);
  return (
    <div
      className={`maintenance-stat${tooltip ? ' maintenance-stat--hoverable' : ''}`}
      onMouseEnter={tooltip ? () => setShow(true) : undefined}
      onMouseLeave={tooltip ? () => setShow(false) : undefined}
    >
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {show && tooltip}
    </div>
  );
}

export default function MaintenancePanel({ exerciseVolumes, exercises, sessions }) {
  const pullExercises = (exerciseVolumes ?? []).filter(ev =>
    ev.exerciseName?.toLowerCase().includes('pull')
  );

  // Merge all pull sessions by date, split sets into bw vs weighted
  const byDate = {};
  pullExercises.forEach(ev => {
    (ev.sessions ?? []).forEach(s => {
      const date = String(s.sessionDate).slice(0, 10);
      if (!byDate[date]) byDate[date] = { bw: [], weighted: [] };
      (s.sets ?? []).forEach(set => {
        if (set.loadKg > 0) byDate[date].weighted.push(set);
        else byDate[date].bw.push(set);
      });
    });
  });

  const sortedDates = Object.keys(byDate).sort();

  const weightedVol = sortedDates.reduce((sum, d) =>
    sum + byDate[d].weighted.reduce((s, set) => s + set.loadKg * set.reps, 0), 0);
  const bwReps = sortedDates.reduce((sum, d) =>
    sum + byDate[d].bw.reduce((s, set) => s + set.reps, 0), 0);

  const hasPullUps = sortedDates.length > 0;

  const bwTooltipRows = sortedDates
    .filter(d => byDate[d].bw.length > 0)
    .map(d => ({ date: d, value: byDate[d].bw.map(s => s.reps).join(' · ') }));

  const weightedTooltipRows = sortedDates
    .filter(d => byDate[d].weighted.length > 0)
    .map(d => ({ date: d, value: byDate[d].weighted.map(s => `${s.loadKg}kg×${s.reps}`).join(' · ') }));

  // Run metrics
  const runSessions = (sessions ?? []).filter(s => s.sessionType === 'run' && !s.isPlanned);
  const runWithDist = runSessions.filter(s => s.distanceKm != null);
  const runWithHr   = runSessions.filter(s => s.avgHr != null);
  const runWithPace = runSessions.filter(s => s.avgPaceSecPerKm != null);
  const runWithDur  = runSessions.filter(s => s.durationSeconds != null);

  const totalDistKm = runWithDist.reduce((sum, s) => sum + s.distanceKm, 0);
  const totalDurSec = runWithDur.reduce((sum, s) => sum + s.durationSeconds, 0);
  const avgHr       = runWithHr.length ? Math.round(runWithHr.reduce((sum, s) => sum + s.avgHr, 0) / runWithHr.length) : null;
  const avgPaceSec  = runWithPace.length ? runWithPace.reduce((sum, s) => sum + s.avgPaceSecPerKm, 0) / runWithPace.length : null;

  const hasRuns = runSessions.length > 0;

  if (!hasPullUps && !hasRuns) return null;

  return (
    <div className="maintenance-panel">
      <div className="card-title">Maintenance</div>
      <div className="maintenance-rows">
        {hasPullUps && (
          <div className="maintenance-row">
            <div className="maintenance-row-label">Pull-ups</div>
            <div className="maintenance-stats">
              {weightedVol > 0 && (
                <StatPair
                  label="Weighted vol"
                  value={`${Math.round(weightedVol).toLocaleString()} kg`}
                  tooltip={<StatTooltip rows={weightedTooltipRows} />}
                />
              )}
              {bwReps > 0 && (
                <StatPair
                  label="Bodyweight reps"
                  value={bwReps}
                  tooltip={<StatTooltip rows={bwTooltipRows} />}
                />
              )}
            </div>
          </div>
        )}
        {hasRuns && (
          <div className="maintenance-row">
            <div className="maintenance-row-label">Run</div>
            <div className="maintenance-stats">
              {runWithDist.length > 0 && (
                <StatPair
                  label="Total distance"
                  value={`${totalDistKm.toFixed(1)} km`}
                  tooltip={<StatTooltip rows={runWithDist.map(s => ({ date: s.sessionDate, value: `${s.distanceKm} km` }))} />}
                />
              )}
              {runWithDur.length > 0 && (
                <StatPair
                  label="Total time"
                  value={formatDuration(totalDurSec)}
                  tooltip={<StatTooltip rows={runWithDur.map(s => ({ date: s.sessionDate, value: formatDuration(s.durationSeconds) }))} />}
                />
              )}
              {avgHr != null && (
                <StatPair
                  label="Avg HR"
                  value={`${avgHr} bpm`}
                  tooltip={<StatTooltip rows={runWithHr.map(s => ({ date: s.sessionDate, value: `${s.avgHr} bpm` }))} />}
                />
              )}
              {avgPaceSec != null && (
                <StatPair
                  label="Avg pace"
                  value={formatPace(avgPaceSec)}
                  tooltip={<StatTooltip rows={runWithPace.map(s => ({ date: s.sessionDate, value: formatPace(s.avgPaceSecPerKm) }))} />}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
