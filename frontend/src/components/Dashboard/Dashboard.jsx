import './Dashboard.css';
import PhaseHeader from './PhaseHeader.jsx';
import PhaseNav from './PhaseNav.jsx';
import MaintenancePanel from './MaintenancePanel.jsx';
import PhaseSummaryCard from './PhaseSummaryCard.jsx';
import E1rmChart from '../Charts/E1rmChart.jsx';
import VolumeChart from '../Charts/VolumeChart.jsx';
import SessionsList from '../Sessions/SessionsList.jsx';

export default function Dashboard({
  phases,
  selectedPhase,
  sessions,
  e1rmMap,
  volumeMap,
  exerciseVolumes,
  benchmarks,
  previousBenchmarks,
  exercises,
  onSelectPhase,
  onOpenPanel,
  onAddPhase,
  onUpdatePhase,
  onDeletePhase,
  onUpdateSession,
  onDeleteSession,
  onUpdateBenchmark,
  onDeleteBenchmark,
  summaryKey,
  theme,
  onToggleTheme,
  isAuthenticated,
  onLogout,
  onLoginClick,
}) {
  return (
    <div className="dashboard">
      <PhaseHeader
        phase={selectedPhase}
        onUpdatePhase={onUpdatePhase}
        onDeletePhase={onDeletePhase}
        theme={theme}
        onToggleTheme={onToggleTheme}
        isAuthenticated={isAuthenticated}
        onLogout={onLogout}
        onLoginClick={onLoginClick}
      />
      {selectedPhase && <PhaseSummaryCard phaseId={selectedPhase.phaseId} refreshKey={summaryKey} />}
      <E1rmChart sessions={sessions} metricsMap={e1rmMap} />
      <VolumeChart sessions={sessions} exerciseVolumes={exerciseVolumes} exercises={exercises} />
      <SessionsList
        sessions={sessions}
        e1rmMap={e1rmMap}
        volumeMap={volumeMap}
        exercises={exercises}
        onUpdateSession={onUpdateSession}
        onDeleteSession={onDeleteSession}
        isAuthenticated={isAuthenticated}
      />
      <MaintenancePanel
        currentBenchmarks={benchmarks}
        previousBenchmarks={previousBenchmarks}
        onUpdateBenchmark={onUpdateBenchmark}
        onDeleteBenchmark={onDeleteBenchmark}
        isAuthenticated={isAuthenticated}
      />
      <PhaseNav
        phases={phases}
        selectedPhaseId={selectedPhase?.phaseId}
        onSelect={onSelectPhase}
        onAddPhase={onAddPhase}
        onUpdatePhase={onUpdatePhase}
        onDeletePhase={onDeletePhase}
      />
      {isAuthenticated && (
        <button
          className="fab"
          title="Log data"
          onClick={onOpenPanel}
        >
          +
        </button>
      )}
    </div>
  );
}
