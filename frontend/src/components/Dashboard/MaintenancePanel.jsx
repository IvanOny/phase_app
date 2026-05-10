// Phase focus map — add a new entry here when a new phase type is introduced.
// dataKey must match what the backend returns from /maintenance.
const PHASE_FOCUS = {
  pull_ups: {
    label: 'Pull-ups',
    dataKey: 'pullups',
    empty: 'No pull sessions this phase',
    valueOf: item => `${item.topReps} reps`,
  },
  run: {
    label: 'Running',
    dataKey: 'run',
    empty: 'No run sessions this phase',
    valueOf: () => null,
  },
  bench: {
    label: 'Bench press',
    dataKey: 'bench',
    empty: 'No bench sessions this phase',
    valueOf: item => `${item.e1rmKg} kg`,
  },
};

function formatDate(dateStr) {
  if (!dateStr) return '';
  const [, mm, dd] = String(dateStr).split('T')[0].split('-');
  return `${dd}.${mm}`;
}

function FocusSection({ focus, items }) {
  return (
    <div className="maintenance-focus">
      <div className="maintenance-focus-header">
        <span className="maintenance-focus-label">{focus.label}</span>
        {items.length > 0 && (
          <span className="maintenance-focus-count">{items.length} sessions</span>
        )}
      </div>
      {items.length === 0 ? (
        <div className="maintenance-empty">{focus.empty}</div>
      ) : (
        <div className="maintenance-session-list">
          {[...items].reverse().map(item => {
            const val = focus.valueOf(item);
            return (
              <div key={item.sessionId} className="maintenance-session-row">
                <span className="maintenance-session-date">{formatDate(item.sessionDate)}</span>
                {val && <span className="maintenance-session-val">{val}</span>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function MaintenancePanel({ maintenanceData, currentPhaseType }) {
  if (!maintenanceData) return null;

  const foci = Object.entries(PHASE_FOCUS).filter(([type]) => type !== currentPhaseType);

  return (
    <div className="maintenance-panel">
      <div className="card-title">Maintenance</div>
      <div className="maintenance-foci">
        {foci.map(([type, focus]) => (
          <FocusSection
            key={type}
            focus={focus}
            items={maintenanceData[focus.dataKey] || []}
          />
        ))}
      </div>
    </div>
  );
}
