const PHASE_LABELS = {
  bench: 'Bench',
  pull_ups: 'Pull-ups',
  run: 'Run',
};

function daysRemaining(endDate) {
  const end = new Date(endDate);
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const diff = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
  return diff;
}

function formatDateRange(start, end) {
  const fmt = d => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  return `${fmt(start)} – ${fmt(end)}`;
}

export default function PhaseHeader({ phase }) {
  if (!phase) return null;

  const days = daysRemaining(phase.endDate);
  const isComplete = days < 0;
  const label = PHASE_LABELS[phase.phaseType] || phase.phaseType;

  return (
    <div className="phase-header">
      <div className="phase-header-left">
        <span className="phase-type-badge">{label}</span>
        <h1 className="phase-name">{phase.name}</h1>
        <p className="phase-dates">{formatDateRange(phase.startDate, phase.endDate)}</p>
      </div>
      <div className="phase-header-right">
        {isComplete ? (
          <span className="days-badge days-badge--done">Completed</span>
        ) : (
          <span className="days-badge">
            <span className="days-number">{days}</span>
            <span className="days-label">days left</span>
          </span>
        )}
      </div>
    </div>
  );
}
