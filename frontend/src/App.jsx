import { useState, useEffect, useCallback } from 'react';
import { useAuth } from './auth/useAuth.js';
import LoginModal from './auth/LoginModal.jsx';

const STORAGE_KEY = 'phase-app-theme';

function useTheme() {
  const [theme, setTheme] = useState(() => localStorage.getItem(STORAGE_KEY) || 'dark');

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.removeAttribute('data-theme');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
    }
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(t => (t === 'dark' ? 'solarized-light' : 'dark'));
  }, []);

  return { theme, toggleTheme };
}
import Dashboard from './components/Dashboard/Dashboard.jsx';
import FaqPage from './components/Faq/FaqPage.jsx';
import DataEntryPanel from './components/DataEntry/DataEntryPanel.jsx';
import {
  getPhases,
  getSessionsByPhase,
  getPhaseSessionBenchMetrics,
  getPhaseExerciseVolumes,
  getRunBenchmarks,
  getPhaseProgression,
  getExercises,
  updatePhase,
  deletePhase,
  updateSession,
  deleteSession,
  createExercise,
  updateExercise,
  deleteExercise,
  mergeExercise,
} from './api/client.js';

function App() {
  const { theme, toggleTheme } = useTheme();
  const { isAuthenticated, login, logout } = useAuth();
  const [showLogin, setShowLogin] = useState(false);
  const [phases, setPhases] = useState([]);
  const [selectedPhaseId, setSelectedPhaseId] = useState(null);
  const [sessionsMap, setSessionsMap] = useState({});
  const [e1rmMap, setE1rmMap] = useState({});
  const [volumeMap, setVolumeMap] = useState({});
  const [exerciseVolumesMap, setExerciseVolumesMap] = useState({});
  const [runBenchmarksMap, setRunBenchmarksMap] = useState({});
  const [progressionMap, setProgressionMap] = useState({});
  const [exercises, setExercises] = useState([]);
  const [summaryKey, setSummaryKey] = useState(0);
  const [panelOpen, setPanelOpen] = useState(false);
  const [panelTab, setPanelTab] = useState('import');
  const [initialPhaseType, setInitialPhaseType] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState('dashboard');
  const [bwKey, setBwKey] = useState(0);

  useEffect(() => {
    Promise.all([getPhases(), getExercises()]).then(([ps, exs]) => {
      setPhases(ps);
      setExercises(exs);
      if (ps.length > 0) {
        const today = new Date().toISOString().slice(0, 10);
        const active = ps.find(p => p.startDate <= today && (!p.endDate || p.endDate >= today));
        const fallback = [...ps].sort((a, b) => new Date(b.startDate) - new Date(a.startDate))[0];
        setSelectedPhaseId((active ?? fallback).phaseId);
      }
      setLoading(false);
    });
  }, []);

  const loadPhaseData = useCallback(async (phaseId) => {
    if (!phaseId) return;
    const [sessions, exerciseVolumes, runBenchmarks, progression] = await Promise.all([
      getSessionsByPhase(phaseId),
      getPhaseExerciseVolumes(phaseId),
      getRunBenchmarks(phaseId).catch(() => []),
      getPhaseProgression(phaseId).catch(() => []),
    ]);
    setSessionsMap(prev => ({ ...prev, [phaseId]: sessions }));
    setExerciseVolumesMap(prev => ({ ...prev, [phaseId]: exerciseVolumes }));
    setRunBenchmarksMap(prev => ({ ...prev, [phaseId]: runBenchmarks }));
    setProgressionMap(prev => ({ ...prev, [phaseId]: progression }));

    const benchMetrics = await getPhaseSessionBenchMetrics(phaseId).catch(() => ({ e1rm: {}, volume: {} }));
    setE1rmMap(prev => ({ ...prev, ...benchMetrics.e1rm }));
    setVolumeMap(prev => ({ ...prev, ...benchMetrics.volume }));
  }, []);

  useEffect(() => {
    if (selectedPhaseId) loadPhaseData(selectedPhaseId);
  }, [selectedPhaseId, loadPhaseData]);

  const sortedPhases = [...phases].sort((a, b) => new Date(a.startDate) - new Date(b.startDate));
  const selectedIdx = sortedPhases.findIndex(p => p.phaseId === selectedPhaseId);
  const previousPhase = selectedIdx > 0 ? sortedPhases[selectedIdx - 1] : null;

  const selectedPhase = phases.find(p => p.phaseId === selectedPhaseId) || null;
  const sessions = sessionsMap[selectedPhaseId] || [];

  function handleSessionLogged(session) {
    setSessionsMap(prev => {
      const existing = prev[session.phaseId] || [];
      const sessionDate = String(session.sessionDate).slice(0, 10);
      // If this is a real session, remove planned sessions for the same date
      const base = session.isPlanned
        ? existing
        : existing.filter(s => !(s.isPlanned && String(s.sessionDate).slice(0, 10) === sessionDate));
      return { ...prev, [session.phaseId]: [...base, session] };
    });
  }

  async function handleUpdatePhase(phaseId, payload) {
    const updated = await updatePhase(phaseId, payload);
    setPhases(prev => prev.map(p => p.phaseId === phaseId ? { ...p, ...updated } : p));
    return updated;
  }

  async function handleDeletePhase(phaseId) {
    await deletePhase(phaseId);
    setPhases(prev => {
      const next = prev.filter(p => p.phaseId !== phaseId);
      if (selectedPhaseId === phaseId && next.length > 0) {
        const latest = [...next].sort((a, b) => new Date(b.startDate) - new Date(a.startDate))[0];
        setSelectedPhaseId(latest.phaseId);
      } else if (next.length === 0) {
        setSelectedPhaseId(null);
      }
      return next;
    });
    setSessionsMap(prev => { const n = { ...prev }; delete n[phaseId]; return n; });
  }

  async function handleUpdateSession(sessionId, phaseId, payload) {
    const updated = await updateSession(sessionId, payload);
    setSessionsMap(prev => ({
      ...prev,
      [phaseId]: (prev[phaseId] || []).map(s => s.sessionId === sessionId ? { ...s, ...updated } : s),
    }));
    return updated;
  }

  async function handleDeleteSession(sessionId, phaseId) {
    await deleteSession(sessionId);
    setSessionsMap(prev => ({
      ...prev,
      [phaseId]: (prev[phaseId] || []).filter(s => s.sessionId !== sessionId),
    }));
    setE1rmMap(prev => { const n = { ...prev }; delete n[sessionId]; return n; });
    setVolumeMap(prev => { const n = { ...prev }; delete n[sessionId]; return n; });
  }

  async function handleCreateExercise(payload) {
    const ex = await createExercise(payload);
    setExercises(prev => [...prev, ex].sort((a, b) => a.exerciseName.localeCompare(b.exerciseName)));
    return ex;
  }

  async function handleDeleteExercise(exerciseId) {
    await deleteExercise(exerciseId);
    setExercises(prev => prev.filter(e => e.exerciseId !== exerciseId));
  }

  async function handleUpdateExercise(exerciseId, payload) {
    const updated = await updateExercise(exerciseId, payload);
    setExercises(prev => prev.map(e => e.exerciseId === exerciseId ? { ...e, ...updated } : e)
      .sort((a, b) => a.exerciseName.localeCompare(b.exerciseName)));
    return updated;
  }

  async function handleMergeExercise(sourceId, targetId) {
    await mergeExercise(sourceId, targetId);
    setExercises(prev => prev.filter(e => e.exerciseId !== sourceId));
  }

  function handleAddPhase(phaseType) {
    setInitialPhaseType(phaseType);
    setPanelTab('phase');
    setPanelOpen(true);
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: 'var(--text-secondary)' }}>
        Loading…
      </div>
    );
  }

  if (page === 'faq') {
    return <FaqPage onBack={() => setPage('dashboard')} />;
  }

  return (
    <>
      {showLogin && (
        <LoginModal
          onLogin={login}
          onClose={() => setShowLogin(false)}
        />
      )}
      <Dashboard
        phases={phases}
        selectedPhase={selectedPhase}
        sessions={sessions}
        e1rmMap={e1rmMap}
        volumeMap={volumeMap}
        exerciseVolumes={exerciseVolumesMap[selectedPhaseId] || []}
        runBenchmarks={runBenchmarksMap[selectedPhaseId] || []}
        progression={progressionMap[selectedPhaseId] || []}
        exercises={exercises}
        onSelectPhase={setSelectedPhaseId}
        onOpenPanel={() => setPanelOpen(true)}
        onAddPhase={handleAddPhase}
        onUpdatePhase={handleUpdatePhase}
        onDeletePhase={handleDeletePhase}
        onUpdateSession={(sessionId, payload) => handleUpdateSession(sessionId, selectedPhaseId, payload)}
        onDeleteSession={(sessionId) => handleDeleteSession(sessionId, selectedPhaseId)}
        onSessionCreated={handleSessionLogged}
        summaryKey={summaryKey}
        theme={theme}
        onToggleTheme={toggleTheme}
        isAuthenticated={isAuthenticated}
        onLogout={logout}
        onLoginClick={() => setShowLogin(true)}
        onFaqClick={() => setPage('faq')}
        bwRefreshKey={bwKey}
      />
      {isAuthenticated && (
        <DataEntryPanel
          isOpen={panelOpen}
          onClose={() => { setPanelOpen(false); setInitialPhaseType(null); }}
          activeTab={panelTab}
          onTabChange={setPanelTab}
          initialPhaseType={initialPhaseType}
          phases={phases}
          selectedPhaseId={selectedPhaseId}
          sessions={sessions}
          exercises={exercises}
          isAuthenticated={isAuthenticated}
          onSessionLogged={session => {
            handleSessionLogged(session);
            setPanelOpen(false);
          }}
          onSetsLogged={() => {
            loadPhaseData(selectedPhaseId);
            setSummaryKey(k => k + 1);
            setPanelOpen(false);
          }}
          onPhaseCreated={phase => {
            setPhases(prev => [...prev, phase]);
            setSelectedPhaseId(phase.phaseId);
            setPanelOpen(false);
          }}
          onExerciseCreated={handleCreateExercise}
          onExerciseUpdated={handleUpdateExercise}
          onExerciseDeleted={handleDeleteExercise}
          onExerciseMerged={handleMergeExercise}
          onImportComplete={session => {
            handleSessionLogged(session);
            loadPhaseData(session.phaseId);
            setSummaryKey(k => k + 1);
            setPanelOpen(false);
          }}
          onBodyweightSaved={() => setBwKey(k => k + 1)}
        />
      )}
    </>
  );
}

export default App
