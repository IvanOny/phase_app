const PHASE_LABELS = {
  bench: 'Bench',
  pull_ups: 'Pull-ups',
  run: 'Run',
};

export default function PhaseNav({ phases, selectedPhaseId, onSelect }) {
  const sorted = [...phases].sort((a, b) => new Date(b.startDate) - new Date(a.startDate));

  return (
    <div className="phase-nav">
      {sorted.map(phase => (
        <button
          key={phase.phaseId}
          className={`phase-nav-pill${phase.phaseId === selectedPhaseId ? ' active' : ''}`}
          onClick={() => onSelect(phase.phaseId)}
        >
          <span className="pill-type">{PHASE_LABELS[phase.phaseType] || phase.phaseType}</span>
          <span className="pill-name">{phase.name}</span>
        </button>
      ))}
    </div>
  );
}
