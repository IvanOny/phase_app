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
  benchmarks,
  previousBenchmarks,
  exercises,
  onSelectPhase,
  onOpenPanel,
  onUpdatePhase,
  onDeletePhase,
  onUpdateSession,
  onDeleteSession,
  onUpdateBenchmark,
  onDeleteBenchmark,
  theme,
  onToggleTheme,
}) {
  return (
    <div className="dashboard">
      <PhaseHeader
        phase={selectedPhase}
        onUpdatePhase={onUpdatePhase}
        onDeletePhase={onDeletePhase}
        theme={theme}
        onToggleTheme={onToggleTheme}
      />
      <PhaseNav
        phases={phases}
        selectedPhaseId={selectedPhase?.phaseId}
        onSelect={onSelectPhase}
      />
      {selectedPhase && <PhaseSummaryCard phaseId={selectedPhase.phaseId} />}
      <E1rmChart sessions={sessions} metricsMap={e1rmMap} />
      <VolumeChart sessions={sessions} metricsMap={volumeMap} />
      <SessionsList
        sessions={sessions}
        e1rmMap={e1rmMap}
        volumeMap={volumeMap}
        exercises={exercises}
        onUpdateSession={onUpdateSession}
        onDeleteSession={onDeleteSession}
      />
      <MaintenancePanel
        currentBenchmarks={benchmarks}
        previousBenchmarks={previousBenchmarks}
        onUpdateBenchmark={onUpdateBenchmark}
        onDeleteBenchmark={onDeleteBenchmark}
      />
      <button
        className="fab"
        title="Log data"
        onClick={onOpenPanel}
      >
        +
      </button>
    </div>
  );
}
