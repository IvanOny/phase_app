import './DataEntryPanel.css';
import LogSessionForm from './LogSessionForm.jsx';
import LogSetsForm from './LogSetsForm.jsx';
import CreatePhaseForm from './CreatePhaseForm.jsx';
import ExerciseCatalogForm from './ExerciseCatalogForm.jsx';
import ScreenshotImportForm from './ScreenshotImportForm.jsx';
import BodyweightPanel from '../Powerlifting/BodyweightPanel.jsx';
import QuickLogForm from './QuickLogForm.jsx';

const TABS = [
  { id: 'quick',       label: 'Quick' },
  { id: 'import',      label: 'Import' },
  { id: 'session',     label: 'Session' },
  { id: 'sets',        label: 'Sets' },
  { id: 'bodyweight',  label: 'Bodyweight' },
  { id: 'exercises',   label: 'Exercises' },
  { id: 'phase',       label: 'Phase' },
];

export default function DataEntryPanel({
  isOpen,
  onClose,
  activeTab,
  onTabChange,
  initialPhaseType,
  phases,
  selectedPhaseId,
  sessions,
  exercises,
  isAuthenticated,
  onSessionLogged,
  onSetsLogged,
  onPhaseCreated,
  onExerciseCreated,
  onExerciseUpdated,
  onExerciseDeleted,
  onExerciseMerged,
  onImportComplete,
  onBodyweightSaved,
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
          {activeTab === 'quick' && (
            <QuickLogForm
              phaseId={selectedPhaseId}
              exercises={exercises}
              onSessionCreated={onSessionLogged}
            />
          )}
          {activeTab === 'phase' && (
            <CreatePhaseForm
              initialPhaseType={initialPhaseType}
              onPhaseCreated={phase => { onPhaseCreated(phase); onClose(); }}
            />
          )}
          {activeTab === 'session' && (
            <LogSessionForm
              phases={phases}
              selectedPhaseId={selectedPhaseId}
              sessions={sessions}
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
          {activeTab === 'bodyweight' && (
            <BodyweightPanel
              phaseId={selectedPhaseId}
              isAuthenticated={isAuthenticated}
              onSaved={onBodyweightSaved}
            />
          )}
          {activeTab === 'exercises' && (
            <ExerciseCatalogForm
              exercises={exercises}
              onExerciseCreated={onExerciseCreated}
              onExerciseUpdated={onExerciseUpdated}
              onExerciseDeleted={onExerciseDeleted}
              onExerciseMerged={onExerciseMerged}
            />
          )}
          {activeTab === 'import' && (
            <ScreenshotImportForm
              phases={phases}
              selectedPhaseId={selectedPhaseId}
              exercises={exercises}
              onImportComplete={onImportComplete}
              onExerciseCreated={onExerciseCreated}
            />
          )}
        </div>
      </div>
    </>
  );
}
