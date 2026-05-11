function formatPace(minPerKm) {
  if (minPerKm == null) return '—';
  const mins = Math.floor(minPerKm);
  const secs = Math.round((minPerKm - mins) * 60);
  return `${mins}:${String(secs).padStart(2, '0')} /km`;
}

function Delta({ current, previous, higherIsBetter = true, unit = '' }) {
  if (current == null || previous == null) return null;
  const diff = current - previous;
  if (Math.abs(diff) < 0.01) return <span className="delta delta--neutral">—</span>;
  const positive = higherIsBetter ? diff > 0 : diff < 0;
  const sign = diff > 0 ? '+' : '';
  const formatted = unit === 'pace'
    ? formatPace(Math.abs(diff))
    : `${sign}${Math.round(Math.abs(diff))}`;
  return (
    <span className={`delta ${positive ? 'delta--up' : 'delta--down'}`}>
      {positive ? '▲' : '▼'} {unit === 'pace' ? (diff < 0 ? '−' : '+') : ''}{formatted}{unit && unit !== 'pace' ? ` ${unit}` : ''}
    </span>
  );
}

function MetricRow({ label, currentValue, previousValue, displayFn, higherIsBetter, deltaUnit, sessionCount }) {
  return (
    <div className="maintenance-row">
      <div className="maintenance-label">{label}</div>
      <div className="maintenance-values">
        <div className="maintenance-current">
          <span className="metric-value">{currentValue != null ? displayFn(currentValue) : '—'}</span>
          {sessionCount != null && (
            <span className="metric-count">({sessionCount} session{sessionCount !== 1 ? 's' : ''})</span>
          )}
        </div>
        {previousValue != null && (
          <div className="maintenance-prev">
            <span className="prev-label">prev</span>
            <span className="prev-value">{displayFn(previousValue)}</span>
            <Delta current={currentValue} previous={previousValue} higherIsBetter={higherIsBetter} unit={deltaUnit} />
          </div>
        )}
      </div>
    </div>
  );
}

export default function MaintenancePanel({ exerciseVolumes, exercises, runBenchmarks }) {
  // Pull-ups: bodyweight exercises whose name contains "pull"
  const pullUpRows = (exerciseVolumes ?? [])
    .filter(ev => {
      const ex = (exercises ?? []).find(e => e.exerciseId === ev.exerciseId);
      return ex?.isBodyweight && ev.exerciseName?.toLowerCase().includes('pull');
    })
    .map(ev => {
      const sessions = ev.sessions ?? [];
      if (sessions.length === 0) return null;
      const allSets = sessions.flatMap(s => s.sets ?? []);
      if (allSets.length === 0) return null;
      const peakReps = Math.max(...allSets.map(set => set.reps));
      return { name: ev.exerciseName, peakReps, sessionCount: sessions.length };
    })
    .filter(Boolean);

  // Run: aerobic test benchmarks sorted by date
  const sortedRuns = [...(runBenchmarks ?? [])].sort(
    (a, b) => new Date(a.benchmarkDate) - new Date(b.benchmarkDate)
  );
  const latestRun = sortedRuns.at(-1) ?? null;
  const prevRun = sortedRuns.length > 1 ? sortedRuns[sortedRuns.length - 2] : null;

  const hasData = pullUpRows.length > 0 || latestRun != null;
  if (!hasData) return null;

  return (
    <div className="maintenance-panel">
      <div className="card-title">Maintenance</div>
      <div className="maintenance-rows">
        {pullUpRows.map(row => (
          <MetricRow
            key={row.name}
            label={`${row.name} (peak reps)`}
            currentValue={row.peakReps}
            previousValue={null}
            displayFn={v => String(Math.round(v))}
            higherIsBetter={true}
            deltaUnit="reps"
            sessionCount={row.sessionCount}
          />
        ))}
        {latestRun != null && (
          <MetricRow
            label="Run pace"
            currentValue={latestRun.paceMinPerKm}
            previousValue={prevRun?.paceMinPerKm ?? null}
            displayFn={formatPace}
            higherIsBetter={false}
            deltaUnit="pace"
            sessionCount={sortedRuns.length}
          />
        )}
      </div>
    </div>
  );
}
