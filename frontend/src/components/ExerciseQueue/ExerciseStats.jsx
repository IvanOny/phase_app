import { useState, useEffect } from 'react';
import { getExqStats } from '../../api/exqClient.js';

function fmtDate(iso) {
  if (!iso) return 'never';
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function ExerciseStats() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getExqStats().then(setStats).catch(e => setError(e.message));
  }, []);

  if (error) return <div className="exq-error">{error}</div>;
  if (!stats) return <div className="exq-loading">Loading…</div>;

  const max = Math.max(1, ...stats.perExercise.map(e => e.timesDone));

  return (
    <div className="exq-stats">
      <div className="exq-stat-tiles">
        <div className="exq-tile"><div className="exq-tile-num">{stats.totalDone}</div><div className="exq-tile-lbl">total done</div></div>
        <div className="exq-tile"><div className="exq-tile-num">{stats.activeDays}</div><div className="exq-tile-lbl">active days</div></div>
        <div className="exq-tile"><div className="exq-tile-num">{stats.perExercise.length}</div><div className="exq-tile-lbl">exercises</div></div>
      </div>

      <div className="exq-stat-list">
        {stats.perExercise.map(e => (
          <div key={e.id} className="exq-stat-row">
            <div className="exq-stat-head">
              <span className="exq-stat-name">{e.name}</span>
              <span className="exq-stat-count">{e.timesDone}</span>
            </div>
            <div className="exq-stat-bar"><div className="exq-stat-fill" style={{ width: `${(e.timesDone / max) * 100}%` }} /></div>
            <div className="exq-stat-sub">{e.scheduleType}{e.status !== 'active' ? ` · ${e.status}` : ''} · last {fmtDate(e.lastDone)}</div>
          </div>
        ))}
        {stats.perExercise.length === 0 && <div className="exq-empty">No exercises yet.</div>}
      </div>
    </div>
  );
}
