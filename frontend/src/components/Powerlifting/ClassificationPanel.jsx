import { useState } from 'react';

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

function GapBar({ label, gapKg, currentLabel, nextLabel, pct }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          {currentLabel
            ? <><strong style={{ color: 'var(--text-primary)' }}>{currentLabel}</strong> → {nextLabel}</>
            : <>Target: <strong style={{ color: 'var(--text-primary)' }}>{nextLabel}</strong></>
          }
        </span>
        {gapKg != null && (
          <span style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>
            −{gapKg} kg
          </span>
        )}
        {gapKg == null && <span style={{ fontSize: 13, color: 'var(--accent)' }}>All classes achieved 🏆</span>}
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
          pct={pct}
        />
      )}
      {nextLabel && (
        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          +{gapPoints} pts to {nextLabel} ({nextThreshold} pts)
        </div>
      )}
    </div>
  );
}

function UpfStatus({ upf, totalKg }) {
  if (!upf) return null;
  const { currentClass, nextClass, nextClassThresholdKg, gapKg, weightCategory } = upf;
  const currentIdx = currentClass ? UPF_LADDER.indexOf(currentClass) : -1;
  const nextIdx = nextClass ? UPF_LADDER.indexOf(nextClass) : UPF_LADDER.length;

  // Progress within the gap to next class
  // Use the previous class threshold (or 0) as the baseline
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
          {totalKg}
        </span>
        <span style={{ fontSize: 14, color: 'var(--accent)', fontWeight: 600 }}>kg total</span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 4 }}>({weightCategory} kg cat.)</span>
      </div>
      <GapBar
        currentLabel={currentClass}
        nextLabel={nextClass ?? '—'}
        gapKg={gapKg}
        pct={Math.max(0, pct)}
      />
      {/* Class ladder */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 2 }}>
        {UPF_LADDER.map((cls, i) => {
          const achieved = i <= currentIdx;
          const isNext = i === nextIdx;
          return (
            <span key={cls} style={{
              fontSize: 11,
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: 12,
              background: achieved ? 'var(--accent-tint-15)' : isNext ? 'var(--accent-tint-08)' : 'transparent',
              border: `1px solid ${achieved ? 'var(--accent)' : isNext ? 'var(--accent-tint-30)' : 'var(--border)'}`,
              color: achieved ? 'var(--accent)' : isNext ? 'var(--text-secondary)' : 'var(--text-muted)',
            }}>
              {achieved && '✓ '}{cls}
            </span>
          );
        })}
      </div>
    </div>
  );
}

export default function ClassificationPanel({ classification, loading }) {
  // federation toggle: 'upf' | 'gl'
  const [federation, setFederation] = useState('upf');

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

  return (
    <div className="chart-wrapper">
      <div className="chart-title-row">
        <span className="card-title">Classification</span>
        {/* Federation toggle — reuses existing load-mode-toggle pattern */}
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
        <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
          {[['Squat', 'squat', '#6366f1'], ['Bench', 'bench', '#0891b2'], ['Deadlift', 'deadlift', '#10b981']].map(([label, key, color]) => (
            <div key={key} style={{
              flex: '1 1 80px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              padding: '8px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
            }}>
              <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color }}>{label}</span>
              <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>
                {liftMaxes[key] ? `${liftMaxes[key]} kg` : '—'}
              </span>
            </div>
          ))}
        </div>
      )}

      {federation === 'upf'
        ? <UpfStatus upf={upf} totalKg={totalKg} />
        : <GlPoints gl={gl} />
      }
    </div>
  );
}
