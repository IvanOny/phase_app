import { useState } from 'react';

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

function toInputDate(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toISOString().slice(0, 10);
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

function BenchmarkRow({ benchmark, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  const isPullup = benchmark.benchmarkType === 'max_bodyweight_pullups';
  const isRun = benchmark.benchmarkType === 'run_aerobic_test';

  function formatDate(d) {
    if (!d) return '';
    const [yyyy, mm, dd] = d.split('T')[0].split('-');
    return `${dd}.${mm}.${yyyy}`;
  }

  function startEdit() {
    setForm({
      benchmarkDate: toInputDate(benchmark.benchmarkDate),
      notes: benchmark.notes || '',
      ...(isPullup ? { reps: benchmark.reps ?? '' } : {}),
      ...(isRun ? {
        avgHr: benchmark.avgHr ?? '',
        paceMinPerKm: benchmark.paceMinPerKm ?? '',
      } : {}),
    });
    setEditing(true);
  }

  async function saveEdit() {
    setSaving(true);
    try {
      const payload = {
        benchmarkDate: form.benchmarkDate,
        notes: form.notes || null,
        ...(isPullup && form.reps !== '' ? { reps: Number(form.reps) } : {}),
        ...(isRun && form.avgHr !== '' ? { avgHr: Number(form.avgHr) } : {}),
        ...(isRun && form.paceMinPerKm !== '' ? { paceMinPerKm: Number(form.paceMinPerKm) } : {}),
      };
      await onUpdate(benchmark.benchmarkId, payload);
      setEditing(false);
    } catch {
      alert('Failed to save.');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    const label = isPullup
      ? `pull-up benchmark (${benchmark.reps} reps)`
      : `run benchmark (${formatDate(benchmark.benchmarkDate)})`;
    if (!confirm(`Delete ${label}?`)) return;
    try {
      await onDelete(benchmark.benchmarkId);
    } catch {
      alert('Failed to delete benchmark.');
    }
  }

  if (editing) {
    return (
      <div className="benchmark-item benchmark-item--editing">
        <div className="benchmark-edit-row">
          <div className="form-group" style={{ margin: 0 }}>
            <label>Date</label>
            <input type="date" value={form.benchmarkDate} onChange={e => setForm(f => ({ ...f, benchmarkDate: e.target.value }))} className="inline-input" />
          </div>
          {isPullup && (
            <div className="form-group" style={{ margin: 0 }}>
              <label>Reps</label>
              <input type="number" value={form.reps} onChange={e => setForm(f => ({ ...f, reps: e.target.value }))} className="inline-input" style={{ width: 70 }} />
            </div>
          )}
          {isRun && (
            <>
              <div className="form-group" style={{ margin: 0 }}>
                <label>Avg HR</label>
                <input type="number" value={form.avgHr} onChange={e => setForm(f => ({ ...f, avgHr: e.target.value }))} className="inline-input" style={{ width: 70 }} />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label>Pace (min/km)</label>
                <input type="number" step="0.01" value={form.paceMinPerKm} onChange={e => setForm(f => ({ ...f, paceMinPerKm: e.target.value }))} className="inline-input" style={{ width: 80 }} />
              </div>
            </>
          )}
          <div className="form-group" style={{ margin: 0, flexGrow: 1 }}>
            <label>Notes</label>
            <input value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} className="inline-input" />
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button className="btn btn-primary" style={{ padding: '4px 12px', fontSize: 13 }} onClick={saveEdit} disabled={saving}>{saving ? 'Saving…' : '✓ Save'}</button>
          <button className="btn btn-ghost" style={{ padding: '4px 12px', fontSize: 13 }} onClick={() => setEditing(false)}>✕ Cancel</button>
        </div>
      </div>
    );
  }

  return (
    <div className="benchmark-item">
      <div className="benchmark-item-info">
        <span className="benchmark-date">{formatDate(benchmark.benchmarkDate)}</span>
        {isPullup && <span className="benchmark-value">{benchmark.reps} reps</span>}
        {isRun && <span className="benchmark-value">{formatPace(benchmark.paceMinPerKm)} · {benchmark.avgHr} bpm</span>}
        {benchmark.notes && <span className="benchmark-notes">{benchmark.notes}</span>}
      </div>
      <div className="benchmark-item-actions">
        <button className="icon-btn" onClick={startEdit} title="Edit benchmark">✏</button>
        <button className="icon-btn icon-btn--danger" onClick={handleDelete} title="Delete benchmark">🗑</button>
      </div>
    </div>
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

export default function MaintenancePanel({ currentBenchmarks, previousBenchmarks, onUpdateBenchmark, onDeleteBenchmark }) {
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

      {currentBenchmarks.length > 0 && (
        <div className="benchmark-list">
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8, fontWeight: 600 }}>Current phase benchmarks</div>
          {currentBenchmarks.map(b => (
            <BenchmarkRow
              key={b.benchmarkId}
              benchmark={b}
              onUpdate={onUpdateBenchmark}
              onDelete={onDeleteBenchmark}
            />
          ))}
        </div>
      )}
    </div>
  );
}
