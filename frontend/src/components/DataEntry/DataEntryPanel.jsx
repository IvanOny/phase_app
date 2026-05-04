import './DataEntryPanel.css';
import LogSessionForm from './LogSessionForm.jsx';
import LogSetsForm from './LogSetsForm.jsx';
import LogBenchmarkForm from './LogBenchmarkForm.jsx';
import CreatePhaseForm from './CreatePhaseForm.jsx';
import ExerciseCatalogForm from './ExerciseCatalogForm.jsx';

const TABS = [
  { id: 'phase',     label: 'Phase' },
  { id: 'session',   label: 'Session' },
  { id: 'sets',      label: 'Sets' },
  { id: 'benchmark', label: 'Benchmark' },
  { id: 'exercises', label: 'Exercises' },
];

export default function DataEntryPanel({
  isOpen,
  onClose,
  activeTab,
  onTabChange,
  phases,
  selectedPhaseId,
  sessions,
  exercises,
  onSessionLogged,
  onSetsLogged,
  onBenchmarkLogged,
  onPhaseCreated,
  onExerciseCreated,
  onExerciseUpdated,
}) {
  return (
    <>
      <div
        className={`panel-backdrop${isOpen ? ' open' : ''}`}
        onClick={onClose}
      />
      <div className={`panel-drawer${isOpen ? ' open' : ''}`}>
        <div className="panel-header">
          <span className="panel-title">Log Data</span>
          <button className="panel-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="panel-tabs">
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={`panel-tab${activeTab === tab.id ? ' active' : ''}`}
              onClick={() => onTabChange(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="panel-body">
          {activeTab === 'phase' && (
            <CreatePhaseForm onPhaseCreated={phase => { onPhaseCreated(phase); onClose(); }} />
          )}
          {activeTab === 'session' && (
            <LogSessionForm
              phases={phases}
              selectedPhaseId={selectedPhaseId}
              onSessionLogged={session => {
                onSessionLogged(session);
              }}
            />
          )}
          {activeTab === 'sets' && (
            <LogSetsForm
              sessions={sessions}
              exercises={exercises}
              onSetsLogged={onSetsLogged}
            />
          )}
          {activeTab === 'benchmark' && (
            <LogBenchmarkForm
              phases={phases}
              selectedPhaseId={selectedPhaseId}
              onBenchmarkLogged={benchmark => {
                onBenchmarkLogged(benchmark);
              }}
            />
          )}
          {activeTab === 'exercises' && (
            <ExerciseCatalogForm
              exercises={exercises}
              onExerciseCreated={onExerciseCreated}
              onExerciseUpdated={onExerciseUpdated}
            />
          )}
        </div>
      </div>
    </>
  );
}
