import { useState, useRef, useEffect } from 'react';

// GL label ordering for the progress bar
const GL_LADDER = [
  { label: 'Untrained',       min: 0   },
  { label: 'Beginner',        min: 50  },
  { label: 'Intermediate',    min: 75  },
  { label: 'Recreational',    min: 100 },
  { label: 'Advanced',        min: 125 },
  { label: 'National-level',  min: 150 },
  { label: 'World-class',     min: 175 },
];

const UPF_LADDER = ['Class 3', 'Class 2', 'Class 1', 'Candidate Master', 'Master of Sport'];

const LABEL_PAD = 28; // px of vertical space reserved above/below the dot row for labels

/** Zigzag dot stepper — full labels alternating above/below, dashed connectors */
function ClassStepper({ items, currentIdx, nextIdx }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center' }}>
      {items.flatMap((label, i) => {
        const achieved  = i <= currentIdx;
        const isNext    = i === nextIdx;
        const above     = i % 2 === 0;
        const isLast    = i === items.length - 1;
        const color     = achieved ? 'var(--accent)' : isNext ? 'var(--text-secondary)' : 'var(--text-muted)';
        const lineColor = i < currentIdx ? 'var(--accent)' : 'var(--border)';

        const dotCol = (
          <div
            key={`d${i}`}
            style={{
              flex: '0 0 auto',
              position: 'relative',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              paddingTop: LABEL_PAD, paddingBottom: LABEL_PAD,
            }}
          >
            {/* dot */}
            <div style={{
              width: 10, height: 10, borderRadius: '50%', flexShrink: 0,
              background: achieved ? 'var(--accent)' : 'transparent',
              border: `2px solid ${achieved || isNext ? 'var(--accent)' : 'var(--border)'}`,
            }} />
            {/* label: centered on dot, single line, allowed to overflow visually */}
            <span style={{
              position: 'absolute',
              ...(above ? { bottom: 'calc(50% + 7px)' } : { top: 'calc(50% + 7px)' }),
              left: '50%', transform: 'translateX(-50%)',
              fontSize: 9, fontWeight: 600,
              whiteSpace: 'nowrap',
              color,
            }}>
              {label}
            </span>
          </div>
        );

        const connector = !isLast ? (
          <div
            key={`l${i}`}
            style={{
              flex: 1,
              height: 2,
              background: lineColor,
              opacity: 0.4,
            }}
          />
        ) : null;

        return connector ? [dotCol, connector] : [dotCol];
      })}
    </div>
  );
}

function GapBar({ label, gapKg, targetKg, rightLabel, currentLabel, nextLabel, pct, showGapLabel = true }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          {currentLabel
            ? <><strong style={{ color: 'var(--text-primary)' }}>{currentLabel}</strong> → {nextLabel}</>
            : <>Target: <strong style={{ color: 'var(--text-primary)' }}>{nextLabel}</strong></>
          }
        </span>
        {showGapLabel && rightLabel && (
          <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>
            {rightLabel}
          </span>
        )}
        {showGapLabel && !rightLabel && gapKg != null && (
          <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>
            {Math.round(gapKg)} kg to {Math.round(targetKg)} kg
          </span>
        )}
        {showGapLabel && !rightLabel && gapKg == null && <span style={{ fontSize: 13, color: 'var(--accent)' }}>All classes achieved 🏆</span>}
      </div>
      <div style={{ height: 8, background: 'var(--accent-tint-12)', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${Math.min(pct * 100, 100)}%`,
          background: 'linear-gradient(90deg, var(--accent-tint-30), var(--accent))',
          borderRadius: 4,
          transition: 'width 0.4s ease',
        }} />
      </div>
    </div>
  );
}

function GlPoints({ gl }) {
  if (!gl) return null;
  const { points, label, nextThreshold, nextLabel, gapPoints } = gl;
  const currentIdx = GL_LADDER.findIndex(l => l.label === label);
  const current = GL_LADDER[currentIdx] ?? GL_LADDER[0];
  const next = GL_LADDER[currentIdx + 1];
  const pct = next
    ? (points - current.min) / (next.min - current.min)
    : 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
        <span style={{ fontSize: 32, fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>
          {points}
        </span>
        <span style={{ fontSize: 14, color: 'var(--accent)', fontWeight: 600 }}>GL pts</span>
        <span style={{ fontSize: 13, color: 'var(--text-secondary)', marginLeft: 4 }}>— {label}</span>
      </div>
      {nextLabel && (
        <GapBar
          currentLabel={label}
          nextLabel={nextLabel}
          gapKg={null}
          rightLabel={`+${gapPoints} pts to ${nextThreshold}`}
          pct={pct}
        />
      )}
      <ClassStepper items={GL_LADDER.map(l => l.label)} currentIdx={currentIdx} nextIdx={currentIdx + 1} />
    </div>
  );
}

function UpfStatus({ upf, totalKg }) {
  if (!upf) return null;
  const { currentClass, nextClass, nextClassThresholdKg, gapKg, weightCategory } = upf;
  const currentIdx = currentClass ? UPF_LADDER.indexOf(currentClass) : -1;
  const nextIdx = nextClass ? UPF_LADDER.indexOf(nextClass) : UPF_LADDER.length;

  const UPF_THRESHOLDS_83 = { 'Class 3': 365, 'Class 2': 422.5, 'Class 1': 480, 'Candidate Master': 540, 'Master of Sport': 602.5 };
  const UPF_THRESHOLDS_74 = { 'Class 3': 340, 'Class 2': 397.5, 'Class 1': 452.5, 'Candidate Master': 510, 'Master of Sport': 570 };
  const thresholds = weightCategory === 74 ? UPF_THRESHOLDS_74 : UPF_THRESHOLDS_83;
  const prevThreshold = currentClass ? thresholds[currentClass] : 0;
  const nextThreshold = nextClassThresholdKg ?? prevThreshold;
  const pct = nextThreshold > prevThreshold
    ? (totalKg - prevThreshold) / (nextThreshold - prevThreshold)
    : 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
        <span style={{ fontSize: 32, fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>
          {Math.round(totalKg)}
        </span>
        <span style={{ fontSize: 14, color: 'var(--accent)', fontWeight: 600 }}>kg total</span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 4 }}>({weightCategory} kg cat.)</span>
      </div>
      <GapBar
        currentLabel={currentClass}
        nextLabel={nextClass ?? '—'}
        gapKg={gapKg}
        targetKg={nextClassThresholdKg}
        pct={Math.max(0, pct)}
      />
      <ClassStepper items={UPF_LADDER} currentIdx={currentIdx} nextIdx={nextIdx} />
    </div>
  );
}

function formatShortDate(dateStr) {
  if (!dateStr) return '';
  const [, mm, dd] = (dateStr.split('T')[0] || dateStr).split('-');
  return `${dd}.${mm}`;
}

export default function ClassificationPanel({ classification, loading }) {
  // All hooks must come before any conditional returns
  const [federation, setFederation] = useState('upf');
  const [liftTooltip, setLiftTooltip] = useState(null); // { lift, x, y }
  const tilesRef = useRef(null);

  useEffect(() => {
    if (!liftTooltip) return;
    function dismiss() { setLiftTooltip(null); }
    document.addEventListener('pointerdown', dismiss, { capture: true, once: true });
    return () => document.removeEventListener('pointerdown', dismiss, { capture: true });
  }, [liftTooltip]);

  if (loading) {
    return (
      <div className="chart-wrapper">
        <div className="chart-title-row"><span className="card-title">Classification</span></div>
        <div className="chart-empty">Loading…</div>
      </div>
    );
  }

  if (!classification) {
    return (
      <div className="chart-wrapper">
        <div className="chart-title-row"><span className="card-title">Classification</span></div>
        <div className="chart-empty">Log bodyweight to enable classification tracking</div>
      </div>
    );
  }

  const { upf, gl, totalKg, liftMaxes } = classification;

  const LIFT_TILE_CONFIG = {
    squat:    { label: 'Squat',    color: '#6366f1' },
    bench:    { label: 'Bench',    color: '#0891b2' },
    deadlift: { label: 'Deadlift', color: '#10b981' },
  };

  function handleTileEnter(e, key) {
    if (!tilesRef.current) return;
    const rect = tilesRef.current.getBoundingClientRect();
    const tileRect = e.currentTarget.getBoundingClientRect();
    setLiftTooltip({ lift: key, x: tileRect.left - rect.left + tileRect.width / 2, y: tileRect.top - rect.top });
  }

  function handleTileClick(e, key) {
    if (!tilesRef.current) return;
    const rect = tilesRef.current.getBoundingClientRect();
    const tileRect = e.currentTarget.getBoundingClientRect();
    const isSame = liftTooltip?.lift === key;
    setLiftTooltip(isSame ? null : { lift: key, x: tileRect.left - rect.left + tileRect.width / 2, y: tileRect.top - rect.top });
  }

  const isDesktop = typeof window !== 'undefined' && window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  return (
    <div className="chart-wrapper">
      <div className="chart-title-row">
        <span className="card-title">Classification</span>
        {/* Federation toggle */}
        <div className="load-mode-toggle" style={{ marginLeft: 'auto' }}>
          <button
            className={`load-mode-btn${federation === 'upf' ? ' active' : ''}`}
            onClick={() => setFederation('upf')}
          >UPF</button>
          <button
            className={`load-mode-btn${federation === 'gl' ? ' active' : ''}`}
            onClick={() => setFederation('gl')}
          >IPF GL</button>
        </div>
      </div>

      {/* Lift maxes row */}
      {liftMaxes && (
        <div ref={tilesRef} style={{ position: 'relative', display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}
          onMouseLeave={() => isDesktop && setLiftTooltip(null)}>
          {[['squat', '#6366f1'], ['bench', '#0891b2'], ['deadlift', '#10b981']].map(([key, color]) => {
            const isActive = liftTooltip?.lift === key;
            return (
              <div key={key}
                onPointerDown={e => e.stopPropagation()}
                onClick={e => !isDesktop && handleTileClick(e, key)}
                onMouseEnter={e => isDesktop && handleTileEnter(e, key)}
                style={{
                  flex: '1 1 80px',
                  background: 'var(--bg-elevated)',
                  border: `1px solid ${isActive ? color : 'var(--border)'}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '8px 12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 2,
                  cursor: 'default',
                }}>
                <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color }}>{LIFT_TILE_CONFIG[key].label}</span>
                <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                  {liftMaxes[key] ? `${Math.round(liftMaxes[key].value ?? liftMaxes[key])} kg` : '—'}
                </span>
              </div>
            );
          })}
          {liftTooltip && (() => {
            const key = liftTooltip.lift;
            return (
              <div className="chart-tooltip" style={{
                position: 'absolute',
                left: liftTooltip.x,
                top: liftTooltip.y,
                transform: 'translate(-50%, -110%)',
                zIndex: 10,
                minWidth: 120,
                pointerEvents: isDesktop ? 'none' : 'auto',
              }}
                onClick={!isDesktop ? () => setLiftTooltip(null) : undefined}>
                {(() => {
                  const entry = liftMaxes[key];
                  const date = entry?.date;
                  const load = entry?.topSetLoadKg;
                  const reps = entry?.topSetReps;
                  return (
                    <>
                      {load != null && reps != null && (
                        <div className="tooltip-row">
                          <span style={{ whiteSpace: 'nowrap' }}>top set:</span>
                          <strong>{load}×{reps}</strong>
                        </div>
                      )}
                      {date && (
                        <div className="tooltip-row">
                          <span>date:</span>
                          <strong>{formatShortDate(date)}</strong>
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
            );
          })()}
        </div>
      )}

      {federation === 'upf'
        ? <UpfStatus upf={upf} totalKg={totalKg} />
        : <GlPoints gl={gl} />
      }
    </div>
  );
}
