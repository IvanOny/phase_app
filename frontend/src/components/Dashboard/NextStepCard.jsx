import { useState, useMemo } from 'react';

const BAR_LBS = 45;
const PLATE_SIZES_LBS = [45, 35, 25, 10, 5, 2.5];

function calcPlatesLbs(totalKg) {
  // Round to nearest 5 lbs (smallest real increment is 2×2.5 lb plates)
  const totalLbs = Math.round(totalKg * 2.20462 / 5) * 5;
  const perSide = (totalLbs - BAR_LBS) / 2;
  if (perSide <= 0) return null;
  let rem = perSide;
  const plates = [];
  for (const p of PLATE_SIZES_LBS) {
    while (rem >= p - 0.01) {
      plates.push(p);
      rem = Math.round((rem - p) * 100) / 100;
    }
  }
  return plates.length > 0 ? plates : null;
}

function fmtPlates(plates) {
  const counts = [];
  for (const p of plates) {
    if (counts.length && counts[counts.length - 1].p === p) counts[counts.length - 1].n++;
    else counts.push({ p, n: 1 });
  }
  return counts.map(({ p, n }) => n > 1 ? `${n}×${p}` : `${p}`).join(' + ');
}

const SESSION_RANGES = {
  heavy_bench:  { min: 3, max: 5,  increment: 2.5 },
  volume_bench: { min: 6, max: 8,  increment: 2.5 },
  speed_bench:  { min: 3, max: 5,  increment: 2.5 },
  pull:         { min: 6, max: 8,  increment: 2.5 },
};

function getRule(item) {
  if (item.repMin != null && item.repMax != null) {
    return { min: item.repMin, max: item.repMax, increment: 2.5 };
  }
  return SESSION_RANGES[item.lastSessionType] ?? null;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const m = String(dateStr).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[3]}.${m[2]}.${m[1]}`;
  return String(dateStr);
}

function formatType(type) {
  return (type || '').replace(/_/g, ' ');
}

function computeSuggestion(item) {
  const rule = getRule(item);
  const { lastSessionType, workingSets } = item;
  if (!rule || !workingSets || workingSets.length === 0) return null;

  const isBwPull = lastSessionType === 'pull' && workingSets.every(s => s.loadKg === 0);
  if (isBwPull) {
    const maxReps = Math.max(...workingSets.map(s => s.reps));
    return { kind: 'bw_reps', loadKg: null, targetReps: maxReps + 1 };
  }

  const load = workingSets[0].loadKg;
  const allAtMax = workingSets.every(s => s.reps >= rule.max);
  if (allAtMax) {
    return { kind: 'weight_up', loadKg: load + rule.increment, targetReps: rule.min };
  }
  return { kind: 'same_weight', loadKg: load, targetReps: rule.max };
}

function SuggestionDisplay({ item, onFocusSession, showLastSession = true, showLbs, onToggleLbs }) {
  const sugg = computeSuggestion(item);

  if (!sugg) {
    return (
      <div className="nsc-empty">
        No progression target for {formatType(item.lastSessionType)} sessions.
      </div>
    );
  }

  const isBarbell = item.isBarbellBenchPress || /barbell/i.test(item.exerciseName);
  let loadLabel, platesInfo = null;
  if (sugg.loadKg === null) {
    loadLabel = 'BW';
  } else if (showLbs) {
    const lbs = Math.round(sugg.loadKg * 2.20462 / 5) * 5;
    loadLabel = `${lbs} lbs`;
  } else {
    loadLabel = `${sugg.loadKg}kg`;
  }
  if (isBarbell && sugg.loadKg !== null) {
    const plates = calcPlatesLbs(sugg.loadKg);
    platesInfo = plates ? fmtPlates(plates) + ' / side' : null;
  }

  const kindLabel = {
    weight_up:   '↑ increase weight',
    same_weight: '= hold weight',
    bw_reps:     '↑ +1 rep',
  }[sugg.kind];
  const kindClass = sugg.kind === 'weight_up' ? 'nsc-kind--up' : 'nsc-kind--hold';
  const canToggle = sugg.loadKg !== null && onToggleLbs;

  return (
    <div className="nsc-suggestion">
      <div className="nsc-target">
        <span
          className={`nsc-load${canToggle ? ' nsc-load--toggle' : ''}`}
          onClick={canToggle ? onToggleLbs : undefined}
          title={canToggle ? (showLbs ? 'Show kg' : 'Show lbs') : undefined}
        >{loadLabel}</span>
        <span className="nsc-x">×</span>
        <span className="nsc-reps">{sugg.targetReps}<span className="nsc-reps-label"> reps</span></span>
      </div>
      {platesInfo && <div className="nsc-plates">{platesInfo}</div>}
      <div className={`nsc-kind ${kindClass}`}>{kindLabel}</div>
      {showLastSession && (
        <button
          className="nsc-last-session"
          onClick={() => onFocusSession?.({ exerciseId: item.exerciseId, sessionType: item.lastSessionType })}
          title="Expand this session in the log"
        >
          Last: {formatDate(item.lastSessionDate)} · {formatType(item.lastSessionType)} ↓
        </button>
      )}
    </div>
  );
}

export function NextStepTile({ progression, sessions, onFocusSession }) {
  const today = new Date().toISOString().slice(0, 10);

  const upcomingPlanned = useMemo(() => (
    (sessions || [])
      .filter(s => s.isPlanned && String(s.sessionDate).slice(0, 10) >= today)
      .sort((a, b) => new Date(a.sessionDate) - new Date(b.sessionDate))
  ), [sessions, today]);

  const [plannedIdx, setPlannedIdx] = useState(0);
  const safePlannedIdx = Math.min(plannedIdx, Math.max(0, upcomingPlanned.length - 1));
  const nextPlanned = upcomingPlanned[safePlannedIdx] ?? null;

  // Last executed session of the upcoming type — drives the exercise list
  const lastExecutedOfType = useMemo(() => {
    if (!nextPlanned) return null;
    return (sessions || [])
      .filter(s => !s.isPlanned && s.sessionType === nextPlanned.sessionType)
      .sort((a, b) => new Date(b.sessionDate) - new Date(a.sessionDate))[0] ?? null;
  }, [sessions, nextPlanned]);

  // Only exercises that (a) have a rule and (b) were logged in the last executed session
  // of the upcoming type. Order is preserved from the backend (exercise_order).
  const actionable = useMemo(() => {
    if (!nextPlanned) {
      return progression.filter(p => getRule(p));
    }
    if (!lastExecutedOfType) return [];
    return progression.filter(p =>
      getRule(p) &&
      p.lastSessionType === nextPlanned.sessionType &&
      p.lastSessionId === lastExecutedOfType.sessionId
    );
  }, [progression, nextPlanned, lastExecutedOfType]);

  const isRunNext = nextPlanned?.sessionType === 'run' || (!nextPlanned && progression.length === 0);

  const runSuggestion = useMemo(() => {
    const lastRun = (sessions || [])
      .filter(s => !s.isPlanned && s.sessionType === 'run' && s.distanceKm != null)
      .sort((a, b) => new Date(b.sessionDate) - new Date(a.sessionDate))[0] ?? null;
    if (!lastRun) return null;
    return {
      lastSessionId: lastRun.sessionId,
      lastDate: lastRun.sessionDate,
      lastDistKm: lastRun.distanceKm,
      targetDistKm: Math.round(lastRun.distanceKm * 1.1 * 10) / 10,
    };
  }, [sessions]);

  const [idx, setIdx] = useState(0);
  const [showLbs, setShowLbs] = useState(false);
  const [deloadPct, setDeloadPct] = useState(20);
  const safeIdx = Math.min(idx, Math.max(0, actionable.length - 1));

  const deloadExercises = useMemo(() => {
    if (!nextPlanned?.isDeload || !lastExecutedOfType) return [];
    return progression.filter(p =>
      p.lastSessionType === nextPlanned.sessionType &&
      p.lastSessionId === lastExecutedOfType.sessionId
    );
  }, [progression, nextPlanned, lastExecutedOfType]);

  const emptyReason = nextPlanned && !lastExecutedOfType
    ? `No prior ${formatType(nextPlanned.sessionType)} session logged.`
    : 'Log a session first to see progression targets.';

  return (
    <div className="chart-wrapper nsc-wrapper">
      <div className="nsc-header">
        <div className="card-title" style={{ marginBottom: 0 }}>Next Step</div>
        {nextPlanned && (
          <div className="nsc-session-nav">
            <button className="nsc-nav-btn" onClick={() => setPlannedIdx(i => Math.max(0, i - 1))} disabled={safePlannedIdx === 0}>‹</button>
            <div className="nsc-next-session-label">
              {formatDate(nextPlanned.sessionDate)} · {formatType(nextPlanned.sessionType)}
              {upcomingPlanned.length > 1 && <span style={{ opacity: 0.5, marginLeft: 4 }}>{safePlannedIdx + 1}/{upcomingPlanned.length}</span>}
            </div>
            <button className="nsc-nav-btn" onClick={() => setPlannedIdx(i => Math.min(upcomingPlanned.length - 1, i + 1))} disabled={safePlannedIdx === upcomingPlanned.length - 1}>›</button>
          </div>
        )}
      </div>

      {nextPlanned?.isDeload ? (
        <div className="nsc-suggestion">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 'var(--space-3)' }}>
            <span className="nsc-kind" style={{ color: 'var(--text-secondary)' }}>↓ Deload</span>
            <label style={{ display: 'flex', gap: 5, alignItems: 'center', fontSize: 12, color: 'var(--text-secondary)' }}>
              <input
                type="number" min="5" max="50" step="5"
                value={deloadPct}
                onChange={e => setDeloadPct(Number(e.target.value))}
                className="inline-input"
                style={{ width: 46, fontSize: 13, textAlign: 'center' }}
              />
              % drop
            </label>
          </div>
          {deloadExercises.length === 0 ? (
            <div className="nsc-empty" style={{ marginTop: 0 }}>No prior {formatType(nextPlanned.sessionType)} session logged.</div>
          ) : deloadExercises.map(item => {
            const maxKg = Math.max(...item.workingSets.map(s => s.loadKg));
            const targetKg = maxKg * (1 - deloadPct / 100);
            const targetLbs = Math.round(targetKg * 2.20462 / 5) * 5;
            const isBarbell = item.isBarbellBenchPress || /barbell/i.test(item.exerciseName);
            const plates = isBarbell ? calcPlatesLbs(targetKg) : null;
            const platesInfo = plates ? fmtPlates(plates) + ' / side' : null;
            return (
              <div key={item.exerciseId} style={{ padding: '3px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', fontSize: 13 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{item.exerciseName}</span>
                  <button className="nsc-load" style={{ fontSize: 15, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                    onClick={() => setShowLbs(v => !v)}
                    title="Toggle lbs / kg"
                  >
                    {showLbs ? `${targetLbs} lbs` : `${targetKg.toFixed(1)} kg`}
                  </button>
                </div>
                {platesInfo && <div className="nsc-plates" style={{ textAlign: 'right' }}>{platesInfo}</div>}
              </div>
            );
          })}
          {deloadExercises.length > 0 && (
            <button className="nsc-last-session" style={{ marginTop: 'var(--space-3)' }}
              onClick={() => onFocusSession?.({ exerciseId: null, sessionType: nextPlanned.sessionType, sessionId: lastExecutedOfType?.sessionId })}>
              Last: {formatDate(lastExecutedOfType?.sessionDate)} · {formatType(nextPlanned.sessionType)} ↓
            </button>
          )}
        </div>
      ) : isRunNext && runSuggestion ? (
        <div className="nsc-suggestion">
          <div className="nsc-target">
            <span className="nsc-load">{runSuggestion.targetDistKm} km</span>
          </div>
          <div className="nsc-kind nsc-kind--up">↑ +10% distance</div>
          <button
            className="nsc-last-session"
            onClick={() => onFocusSession?.({ sessionType: 'run', sessionId: runSuggestion.lastSessionId })}
          >
            Last: {formatDate(runSuggestion.lastDate)} · {runSuggestion.lastDistKm} km ↓
          </button>
        </div>
      ) : isRunNext ? (
        <div className="nsc-empty">No prior run logged.</div>
      ) : actionable.length === 0 ? (
        <div className="nsc-empty">{emptyReason}</div>
      ) : (
        <>
          {/* Mobile: arrow carousel — one exercise at a time */}
          <div className="nsc-mobile-carousel">
            <div className="nsc-tile-nav">
              <button
                className="nsc-nav-btn"
                onClick={() => setIdx(i => Math.max(0, i - 1))}
                disabled={safeIdx === 0}
              >‹</button>
              <div className="nsc-tile-title">
                <span className="nsc-exercise-name">{actionable[safeIdx]?.exerciseName}</span>
                {actionable.length > 1 && (
                  <span className="nsc-counter">{safeIdx + 1} / {actionable.length}</span>
                )}
              </div>
              <button
                className="nsc-nav-btn"
                onClick={() => setIdx(i => Math.min(actionable.length - 1, i + 1))}
                disabled={safeIdx === actionable.length - 1}
              >›</button>
            </div>
            <SuggestionDisplay item={actionable[safeIdx]} onFocusSession={onFocusSession} showLastSession={false} showLbs={showLbs} onToggleLbs={() => setShowLbs(v => !v)} />
          </div>

          {/* Desktop: all exercises side by side */}
          <div className="nsc-desktop-grid">
            {actionable.map(item => (
              <div key={item.exerciseId + item.lastSessionType} className="nsc-exercise-card">
                <div className="nsc-exercise-name" style={{ marginBottom: 'var(--space-3)' }}>{item.exerciseName}</div>
                <SuggestionDisplay item={item} onFocusSession={onFocusSession} showLastSession={false} showLbs={showLbs} onToggleLbs={() => setShowLbs(v => !v)} />
              </div>
            ))}
          </div>
          <button
            className="nsc-last-session"
            style={{ marginTop: 'var(--space-3)' }}
            onClick={() => onFocusSession?.({ exerciseId: null, sessionType: actionable[0].lastSessionType, sessionId: actionable[0].lastSessionId })}
            title="Expand this session in the log"
          >
            Last: {formatDate(actionable[0].lastSessionDate)} · {formatType(actionable[0].lastSessionType)} ↓
          </button>
        </>
      )}
    </div>
  );
}
