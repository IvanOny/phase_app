function StatPair({ label, value }) {
  return (
    <div className="maintenance-stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}

export default function MaintenancePanel({ exerciseVolumes, exercises, runBenchmarks }) {
  const pullUpRows = (exerciseVolumes ?? [])
    .filter(ev => {
      const ex = (exercises ?? []).find(e => e.exerciseId === ev.exerciseId);
      return ex?.isBodyweight && ev.exerciseName?.toLowerCase().includes('pull');
    })
    .map(ev => {
      const allSets = (ev.sessions ?? []).flatMap(s => s.sets ?? []);
      if (allSets.length === 0) return null;
      const peakReps = Math.max(...allSets.map(s => s.reps));
      const sessionPeaks = (ev.sessions ?? []).map(s => Math.max(...(s.sets ?? []).map(set => set.reps)));
      const avgReps = sessionPeaks.reduce((sum, p) => sum + p, 0) / sessionPeaks.length;
      return { name: ev.exerciseName, peakReps, avgReps };
    })
    .filter(Boolean);

  if (pullUpRows.length === 0) return null;

  return (
    <div className="maintenance-panel">
      <div className="card-title">Maintenance</div>
      <div className="maintenance-rows">
        {pullUpRows.map(row => (
          <div key={row.name} className="maintenance-row">
            <div className="maintenance-row-label">{row.name}</div>
            <div className="maintenance-stats">
              <StatPair label="Peak reps" value={Math.round(row.peakReps)} />
              <StatPair label="Avg / phase" value={row.avgReps.toFixed(1)} />
            </div>
          </div>
        ))}
        {/* TODO: replace with real distanceKm data once API returns it */}
        <div className="maintenance-row">
          <div className="maintenance-row-label">Run</div>
          <div className="maintenance-stats">
            <StatPair label="Max distance" value="7.36 km" />
            <StatPair label="Total distance" value="48.81 km" />
          </div>
        </div>
      </div>
    </div>
  );
}
