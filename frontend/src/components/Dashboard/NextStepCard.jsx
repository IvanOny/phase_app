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

const REP_RANGES = {
  heavy_bench:  { min: 3, max: 5,  increment: 2.5 },
  volume_bench: { min: 6, max: 8,  increment: 2.5 },
  speed_bench:  { min: 3, max: 5,  increment: 2.5 },
  pull:         { min: 6, max: 8,  increment: 2.5 },
};

const ACCESSORY_RANGE = { min: 8, max: 12, increment: 2.5 };

function getRule(item) {
  if (/row/i.test(item.exerciseName)) return ACCESSORY_RANGE;
  const sessionRule = REP_RANGES[item.lastSessionType] ?? null;
  if (!sessionRule) return null;
  // If the athlete was doing well above the session's rep ceiling, treat as accessory
  const avgReps = item.workingSets.reduce((s, w) => s + w.reps, 0) / item.workingSets.length;
  if (avgReps > sessionRule.max * 1.5) return ACCESSORY_RANGE;
  return sessionRule;
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
    if (isBarbell) {
      const plates = calcPlatesLbs(sugg.loadKg);
      platesInfo = plates ? fmtPlates(plates) + ' / side' : null;
    }
  } else {
    loadLabel = `${sugg.loadKg}kg`;
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

  const nextPlanned = useMemo(() => (
    (sessions || [])
      .filter(s => s.isPlanned && String(s.sessionDate).slice(0, 10) >= today)
      .sort((a, b) => new Date(a.sessionDate) - new Date(b.sessionDate))[0] ?? null
  ), [sessions, today]);

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
      lastDate: lastRun.sessionDate,
      lastDistKm: lastRun.distanceKm,
      targetDistKm: Math.round(lastRun.distanceKm * 1.1 * 10) / 10,
    };
  }, [sessions]);

  const [idx, setIdx] = useState(0);
  const [showLbs, setShowLbs] = useState(false);
  const safeIdx = Math.min(idx, Math.max(0, actionable.length - 1));

  const emptyReason = nextPlanned && !lastExecutedOfType
    ? `No prior ${formatType(nextPlanned.sessionType)} session logged.`
    : 'Log a session first to see progression targets.';

  return (
    <div className="chart-wrapper nsc-wrapper">
      <div className="nsc-header">
        <div className="card-title" style={{ marginBottom: 0 }}>Next Step</div>
        {nextPlanned && (
          <div className="nsc-next-session-label">
            {formatDate(nextPlanned.sessionDate)} · {formatType(nextPlanned.sessionType)}
          </div>
        )}
      </div>

      {isRunNext && runSuggestion ? (
        <div className="nsc-suggestion">
          <div className="nsc-target">
            <span className="nsc-load">{runSuggestion.targetDistKm} km</span>
          </div>
          <div className="nsc-kind nsc-kind--up">↑ +10% distance</div>
          <button
            className="nsc-last-session"
            onClick={() => onFocusSession?.({ sessionType: 'run', sessionId: null })}
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
