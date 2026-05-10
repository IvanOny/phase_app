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
  maintenanceData,
  exercises,
  onSelectPhase,
  onOpenPanel,
  onAddPhase,
  onUpdatePhase,
  onDeletePhase,
  onUpdateSession,
  onDeleteSession,
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
      {sessions.length === 0 ? (
        <div className="phase-no-data">
          <p>Дасть ся чути.</p>
          <p>То ще треба дожити.</p>
        </div>
      ) : (
        <>
          {selectedPhase && (() => {
            const sorted = [...phases].sort((a, b) => new Date(a.startDate) - new Date(b.startDate));
            const idx = sorted.findIndex(p => p.phaseId === selectedPhase.phaseId);
            const prevPhaseId = idx > 0 ? sorted[idx - 1].phaseId : undefined;
            const bestSet = sessions.reduce((best, s) => {
              const m = e1rmMap[s.sessionId];
              if (!m || !m.topSetE1rmKg) return best;
              if (!best || m.topSetE1rmKg > best.e1rmKg) {
                return { loadKg: m.topSetLoadKg, reps: m.topSetReps, e1rmKg: m.topSetE1rmKg };
              }
              return best;
            }, null);
            return <PhaseSummaryCard phaseId={selectedPhase.phaseId} previousPhaseId={prevPhaseId} bestSet={bestSet} refreshKey={summaryKey} />;
          })()}
          <E1rmChart sessions={sessions} metricsMap={e1rmMap} />
          <VolumeChart sessions={sessions} exerciseVolumes={exerciseVolumes} exercises={exercises} />
          <MaintenancePanel
            maintenanceData={maintenanceData}
            currentPhaseType={selectedPhase?.phaseType}
          />
        </>
      )}
      <SessionsList
        sessions={sessions}
        e1rmMap={e1rmMap}
        volumeMap={volumeMap}
        exercises={exercises}
        onUpdateSession={onUpdateSession}
        onDeleteSession={onDeleteSession}
        isAuthenticated={isAuthenticated}
      />
      <PhaseNav
        phases={phases}
        selectedPhaseId={selectedPhase?.phaseId}
        onSelect={onSelectPhase}
        onAddPhase={onAddPhase}
        onUpdatePhase={onUpdatePhase}
        onDeletePhase={onDeletePhase}
        isAuthenticated={isAuthenticated}
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
