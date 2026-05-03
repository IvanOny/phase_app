import './Dashboard.css';
import PhaseHeader from './PhaseHeader.jsx';
import PhaseNav from './PhaseNav.jsx';
import MaintenancePanel from './MaintenancePanel.jsx';
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
}) {
  return (
    <div className="dashboard">
      <PhaseHeader phase={selectedPhase} />
      <PhaseNav
        phases={phases}
        selectedPhaseId={selectedPhase?.phaseId}
        onSelect={onSelectPhase}
      />
      <E1rmChart sessions={sessions} metricsMap={e1rmMap} />
      <VolumeChart sessions={sessions} metricsMap={volumeMap} />
      <SessionsList sessions={sessions} e1rmMap={e1rmMap} volumeMap={volumeMap} exercises={exercises} />
      <MaintenancePanel
        currentBenchmarks={benchmarks}
        previousBenchmarks={previousBenchmarks}
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
