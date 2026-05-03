import { useState, useEffect, Fragment } from 'react';
import { getSessionExercises, getExerciseSets } from '../../api/client.js';

function readinessColor(r) {
  if (r == null) return 'var(--text-muted)';
  if (r >= 7) return 'var(--ready-green)';
  if (r >= 5) return 'var(--ready-yellow)';
  return 'var(--ready-red)';
}

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatType(type) {
  return type.replace(/_/g, ' ');
}

function SessionDetail({ sessionId, exercises: catalog }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    getSessionExercises(sessionId).then(async sessionExercises => {
      const withSets = await Promise.all(
        sessionExercises.map(async se => {
          const sets = await getExerciseSets(se.sessionExerciseId);
          const exercise = catalog.find(e => e.exerciseId === se.exerciseId);
          return { ...se, exerciseName: exercise?.exerciseName ?? `Exercise ${se.exerciseId}`, sets };
        })
      );
      withSets.sort((a, b) => a.exerciseOrder - b.exerciseOrder);
      setData(withSets);
    });
  }, [sessionId]);

  if (!data) {
    return (
      <tr>
        <td colSpan={7} className="session-detail-cell">
          <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Loading…</span>
        </td>
      </tr>
    );
  }

  if (data.length === 0) {
    return (
      <tr>
        <td colSpan={7} className="session-detail-cell">
          <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>No exercises logged.</span>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td colSpan={7} className="session-detail-cell">
        <div className="session-detail">
          {data.map(se => (
            <div key={se.sessionExerciseId} className="exercise-block">
              <div className="exercise-name">{se.exerciseName}</div>
              {se.sets.length > 0 ? (
                <table className="sets-table">
                  <thead>
                    <tr>
                      <th>Set</th>
                      <th>Load (kg)</th>
                      <th>Reps</th>
                      <th>Top set</th>
                      <th>Working</th>
                    </tr>
                  </thead>
                  <tbody>
                    {se.sets.map(set => (
                      <tr key={set.exerciseSetId} className={set.isTopSet ? 'top-set-row' : ''}>
                        <td>{set.setNumber}</td>
                        <td>{set.loadKg}</td>
                        <td>{set.reps}</td>
                        <td>{set.isTopSet ? '★' : ''}</td>
                        <td>{set.isWorkingSet ? '✓' : ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>No sets logged.</span>
              )}
            </div>
          ))}
        </div>
      </td>
    </tr>
  );
}

export default function SessionsList({ sessions, e1rmMap, volumeMap, exercises }) {
  const [expanded, setExpanded] = useState(new Set());

  function toggleRow(sessionId) {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(sessionId) ? next.delete(sessionId) : next.add(sessionId);
      return next;
    });
  }

  const sorted = [...sessions].sort((a, b) => new Date(b.sessionDate) - new Date(a.sessionDate));

  return (
    <div className="chart-wrapper">
      <div className="card-title">Sessions ({sessions.length})</div>
      {sorted.length === 0 ? (
        <div className="chart-empty">No sessions logged for this phase</div>
      ) : (
        <div className="sessions-table-wrap">
          <table className="sessions-table">
            <thead>
              <tr>
                <th></th>
                <th>Date</th>
                <th>Type</th>
                <th>Elite HRV</th>
                <th>Garmin HRV</th>
                <th>e1RM (kg)</th>
                <th>Volume (kg·reps)</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(s => {
                const e1rm = e1rmMap[s.sessionId];
                const vol = volumeMap[s.sessionId];
                const isOpen = expanded.has(s.sessionId);
                return (
                  <Fragment key={s.sessionId}>
                    <tr
                      className="session-row"
                      onClick={() => toggleRow(s.sessionId)}
                    >
                      <td className="expand-icon">{isOpen ? '▾' : '▸'}</td>
                      <td>{formatDate(s.sessionDate)}</td>
                      <td className="session-type">{formatType(s.sessionType)}</td>
                      <td style={{ color: readinessColor(s.eliteHrvReadiness) }}>
                        {s.eliteHrvReadiness ?? '—'}
                      </td>
                      <td>{s.garminOvernightHrv ?? '—'}</td>
                      <td>{e1rm ? e1rm.topSetE1rmKg : '—'}</td>
                      <td>{vol ? vol.benchVolumeKgReps : '—'}</td>
                    </tr>
                    {isOpen && (
                      <SessionDetail
                        sessionId={s.sessionId}
                        exercises={exercises}
                      />
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
