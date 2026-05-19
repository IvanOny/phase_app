import { useState, useMemo } from 'react';

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

function SuggestionDisplay({ item, onFocusSession }) {
  const sugg = computeSuggestion(item);

  if (!sugg) {
    return (
      <div className="nsc-empty">
        No progression target for {formatType(item.lastSessionType)} sessions.
      </div>
    );
  }

  const loadLabel = sugg.loadKg === null ? 'BW' : `${sugg.loadKg}kg`;
  const kindLabel = {
    weight_up:   '↑ increase weight',
    same_weight: '= hold weight',
    bw_reps:     '↑ +1 rep',
  }[sugg.kind];
  const kindClass = sugg.kind === 'weight_up' ? 'nsc-kind--up' : 'nsc-kind--hold';

  return (
    <div className="nsc-suggestion">
      <div className="nsc-target">
        <span className="nsc-load">{loadLabel}</span>
        <span className="nsc-x">×</span>
        <span className="nsc-reps">{sugg.targetReps}<span className="nsc-reps-label"> reps</span></span>
      </div>
      <div className={`nsc-kind ${kindClass}`}>{kindLabel}</div>
      <button
        className="nsc-last-session"
        onClick={() => onFocusSession?.({ exerciseId: item.exerciseId, sessionType: item.lastSessionType })}
        title="Expand this session in the log"
      >
        Last: {formatDate(item.lastSessionDate)} · {formatType(item.lastSessionType)} ↓
      </button>
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

  const [idx, setIdx] = useState(0);
  const safeIdx = Math.min(idx, Math.max(0, actionable.length - 1));
  const item = actionable[safeIdx] ?? null;

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

      {actionable.length === 0 ? (
        <div className="nsc-empty">{emptyReason}</div>
      ) : (
        <>
          <div className="nsc-tile-nav">
            <button
              className="nsc-nav-btn"
              onClick={() => setIdx(i => Math.max(0, i - 1))}
              disabled={safeIdx === 0}
            >‹</button>
            <div className="nsc-tile-title">
              <span className="nsc-exercise-name">{item?.exerciseName}</span>
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
          {item && <SuggestionDisplay item={item} onFocusSession={onFocusSession} />}
        </>
      )}
    </div>
  );
}
