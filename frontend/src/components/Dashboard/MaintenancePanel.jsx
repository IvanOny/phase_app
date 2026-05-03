function avg(arr) {
  if (!arr.length) return null;
  return arr.reduce((s, v) => s + v, 0) / arr.length;
}

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
  return (
    <span className={`delta ${positive ? 'delta--up' : 'delta--down'}`}>
      {positive ? '▲' : '▼'} {sign}{unit === 'pace' ? formatPace(Math.abs(diff)) : diff.toFixed(1)}{unit && unit !== 'pace' ? ` ${unit}` : ''}
    </span>
  );
}

function MetricRow({ label, currentValue, previousValue, displayFn, higherIsBetter, deltaUnit, count, prevCount }) {
  return (
    <div className="maintenance-row">
      <div className="maintenance-label">{label}</div>
      <div className="maintenance-values">
        <div className="maintenance-current">
          <span className="metric-value">{currentValue != null ? displayFn(currentValue) : '—'}</span>
          {count != null && <span className="metric-count">({count} tests)</span>}
        </div>
        <div className="maintenance-prev">
          <span className="prev-label">prev</span>
          <span className="prev-value">{previousValue != null ? displayFn(previousValue) : '—'}</span>
          {prevCount != null && <span className="metric-count">({prevCount})</span>}
          <Delta current={currentValue} previous={previousValue} higherIsBetter={higherIsBetter} unit={deltaUnit} />
        </div>
      </div>
    </div>
  );
}

export default function MaintenancePanel({ currentBenchmarks, previousBenchmarks }) {
  const curPullups = currentBenchmarks.filter(b => b.benchmarkType === 'max_bodyweight_pullups');
  const prevPullups = previousBenchmarks.filter(b => b.benchmarkType === 'max_bodyweight_pullups');
  const curRuns = currentBenchmarks.filter(b => b.benchmarkType === 'run_aerobic_test');
  const prevRuns = previousBenchmarks.filter(b => b.benchmarkType === 'run_aerobic_test');

  const curPullupAvg = avg(curPullups.map(b => b.reps));
  const prevPullupAvg = avg(prevPullups.map(b => b.reps));
  const curRunAvg = avg(curRuns.map(b => b.paceMinPerKm));
  const prevRunAvg = avg(prevRuns.map(b => b.paceMinPerKm));

  return (
    <div className="maintenance-panel">
      <div className="card-title">Maintenance</div>
      <div className="maintenance-rows">
        <MetricRow
          label="Pull-ups (max reps avg)"
          currentValue={curPullupAvg}
          previousValue={prevPullupAvg}
          displayFn={v => v.toFixed(1)}
          higherIsBetter={true}
          deltaUnit="reps"
          count={curPullups.length || null}
          prevCount={prevPullups.length || null}
        />
        <MetricRow
          label="Run pace avg (40 min @ 140bpm)"
          currentValue={curRunAvg}
          previousValue={prevRunAvg}
          displayFn={formatPace}
          higherIsBetter={false}
          deltaUnit="pace"
          count={curRuns.length || null}
          prevCount={prevRuns.length || null}
        />
      </div>
    </div>
  );
}
