import { useState } from 'react';
import './Dashboard.css';
import PhaseHeader from './PhaseHeader.jsx';
import PhaseNav from './PhaseNav.jsx';
import MaintenancePanel from './MaintenancePanel.jsx';
import PhaseSummaryCard from './PhaseSummaryCard.jsx';
import E1rmChart from '../Charts/E1rmChart.jsx';
import VolumeChart from '../Charts/VolumeChart.jsx';
import SessionsList from '../Sessions/SessionsList.jsx';
import { NextStepTile } from './NextStepCard.jsx';
import PowerliftingDashboard from '../Powerlifting/PowerliftingDashboard.jsx';

export default function Dashboard({
  phases,
  selectedPhase,
  sessions,
  e1rmMap,
  volumeMap,
  exerciseVolumes,
  runBenchmarks,
  exercises,
  progression,
  onSelectPhase,
  onOpenPanel,
  onAddPhase,
  onUpdatePhase,
  onDeletePhase,
  onUpdateSession,
  onDeleteSession,
  onSessionCreated,
  summaryKey,
  theme,
  onToggleTheme,
  isAuthenticated,
  onLogout,
  onLoginClick,
  onFaqClick,
}) {
  const [focusFilter, setFocusFilter] = useState(null);

  function handleFocusSession(filter) {
    setFocusFilter(null);
    setTimeout(() => setFocusFilter(filter), 0);
  }

  // Powerlifting phases get their own dedicated dashboard
  if (selectedPhase?.phaseType === 'powerlifting') {
    return (
      <PowerliftingDashboard
        phases={phases}
        selectedPhase={selectedPhase}
        sessions={sessions}
        exercises={exercises}
        exerciseVolumes={exerciseVolumes}
        onSelectPhase={onSelectPhase}
        onOpenPanel={onOpenPanel}
        onAddPhase={onAddPhase}
        onUpdatePhase={onUpdatePhase}
        onDeletePhase={onDeletePhase}
        onUpdateSession={onUpdateSession}
        onDeleteSession={onDeleteSession}
        theme={theme}
        onToggleTheme={onToggleTheme}
        isAuthenticated={isAuthenticated}
        onLogout={onLogout}
        onLoginClick={onLoginClick}
        onFaqClick={onFaqClick}
      />
    );
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const phaseEndDate = selectedPhase?.endDate ? new Date(selectedPhase.endDate) : null;
  const isCurrentPhase = !phaseEndDate || phaseEndDate >= today;

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
        onFaqClick={onFaqClick}
      />
      {sessions.length === 0 ? (
        <div className="phase-no-data">
          <p>Дасть ся чути.</p>
          <p>То ще треба дожити.</p>
        </div>
      ) : (
        <>
          {progression && isCurrentPhase && (
            <NextStepTile
              progression={progression}
              sessions={sessions}
              onFocusSession={handleFocusSession}
            />
          )}
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
        </>
      )}
      <SessionsList
        key={selectedPhase?.phaseId}
        phase={selectedPhase}
        sessions={sessions}
        e1rmMap={e1rmMap}
        volumeMap={volumeMap}
        exercises={exercises}
        exerciseVolumes={exerciseVolumes}
        onUpdateSession={onUpdateSession}
        onDeleteSession={onDeleteSession}
        onSessionCreated={onSessionCreated}
        isAuthenticated={isAuthenticated}
        focusFilter={focusFilter}
      />
      {sessions.length > 0 && (
        <MaintenancePanel
          exerciseVolumes={exerciseVolumes}
          exercises={exercises}
          runBenchmarks={runBenchmarks}
          sessions={sessions}
        />
      )}
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
