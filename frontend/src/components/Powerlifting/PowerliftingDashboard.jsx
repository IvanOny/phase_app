import { useState, useEffect, useCallback } from 'react';
import PhaseHeader from '../Dashboard/PhaseHeader.jsx';
import PhaseNav from '../Dashboard/PhaseNav.jsx';
import SessionsList from '../Sessions/SessionsList.jsx';
import LiftTrendChart from './LiftTrendChart.jsx';
import ClassificationPanel from './ClassificationPanel.jsx';
import VolumeChart from '../Charts/VolumeChart.jsx';
import { getSessionPlMetrics, getClassification } from '../../api/client.js';

export default function PowerliftingDashboard({
  phases,
  selectedPhase,
  sessions,
  exercises,
  exerciseVolumes,
  onSelectPhase,
  onOpenPanel,
  onAddPhase,
  onUpdatePhase,
  onDeletePhase,
  onUpdateSession,
  onDeleteSession,
  theme,
  onToggleTheme,
  isAuthenticated,
  onLogout,
  onLoginClick,
  onFaqClick,
  bwRefreshKey,
}) {
  const [plMetrics, setPlMetrics] = useState(null);
  const [classification, setClassification] = useState(null);
  const [classLoading, setClassLoading] = useState(false);

  const loadPlData = useCallback(async (phaseId) => {
    if (!phaseId) return;
    try {
      const metrics = await getSessionPlMetrics(phaseId);
      setPlMetrics(metrics);
    } catch {
      setPlMetrics(null);
    }
    setClassLoading(true);
    try {
      const cl = await getClassification(phaseId, null);
      setClassification(cl);
    } catch {
      setClassification(null);
    } finally {
      setClassLoading(false);
    }
  }, []);

  useEffect(() => {
    setPlMetrics(null);
    setClassification(null);
    if (selectedPhase?.phaseId) {
      loadPlData(selectedPhase.phaseId);
    }
  }, [selectedPhase?.phaseId, loadPlData]);

  useEffect(() => {
    if (selectedPhase?.phaseId && sessions.length > 0) {
      getClassification(selectedPhase.phaseId, null)
        .then(setClassification)
        .catch(() => {});
    }
  }, [sessions.length, selectedPhase?.phaseId]);

  useEffect(() => {
    if (bwRefreshKey > 0 && selectedPhase?.phaseId) {
      getClassification(selectedPhase.phaseId, null)
        .then(setClassification)
        .catch(() => {});
    }
  }, [bwRefreshKey, selectedPhase?.phaseId]);

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
        showProgress={false}
      />

      {sessions.length === 0 ? (
        <div className="phase-no-data">
          <p>No sessions yet.</p>
          <p>Log your first squat, bench, or deadlift session to start tracking.</p>
        </div>
      ) : (
        <>
          <ClassificationPanel
            classification={classification}
            loading={classLoading}
          />
          <LiftTrendChart sessions={sessions} plMetrics={plMetrics} showTotal={false} />
          <VolumeChart sessions={sessions} exerciseVolumes={exerciseVolumes} exercises={exercises} hideBenchFilter />
        </>
      )}

      <SessionsList
        phase={selectedPhase}
        sessions={sessions}
        e1rmMap={{}}
        volumeMap={{}}
        exercises={exercises}
        exerciseVolumes={exerciseVolumes}
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
        <button className="fab" title="Log data" onClick={onOpenPanel}>+</button>
      )}
    </div>
  );
}
