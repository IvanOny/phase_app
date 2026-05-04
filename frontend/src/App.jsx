import { useState, useEffect, useCallback } from 'react';

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
import DataEntryPanel from './components/DataEntry/DataEntryPanel.jsx';
import {
  getPhases,
  getSessionsByPhase,
  getBenchE1rm,
  getBenchVolume,
  getBenchmarksByPhase,
  getExercises,
  updatePhase,
  deletePhase,
  updateSession,
  deleteSession,
  updateBenchmark,
  deleteBenchmark,
  createExercise,
  updateExercise,
} from './api/client.js';

function App() {
  const { theme, toggleTheme } = useTheme();
  const [phases, setPhases] = useState([]);
  const [selectedPhaseId, setSelectedPhaseId] = useState(null);
  const [sessionsMap, setSessionsMap] = useState({});
  const [e1rmMap, setE1rmMap] = useState({});
  const [volumeMap, setVolumeMap] = useState({});
  const [benchmarksMap, setBenchmarksMap] = useState({});
  const [exercises, setExercises] = useState([]);
  const [panelOpen, setPanelOpen] = useState(false);
  const [panelTab, setPanelTab] = useState('session');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getPhases(), getExercises()]).then(([ps, exs]) => {
      setPhases(ps);
      setExercises(exs);
      if (ps.length > 0) {
        const latest = [...ps].sort((a, b) => new Date(b.startDate) - new Date(a.startDate))[0];
        setSelectedPhaseId(latest.phaseId);
      }
      setLoading(false);
    });
  }, []);

  const loadPhaseData = useCallback(async (phaseId) => {
    if (!phaseId) return;
    const [sessions, benchmarks] = await Promise.all([
      getSessionsByPhase(phaseId),
      getBenchmarksByPhase(phaseId),
    ]);
    setSessionsMap(prev => ({ ...prev, [phaseId]: sessions }));
    setBenchmarksMap(prev => ({ ...prev, [phaseId]: benchmarks }));

    const metricResults = await Promise.all(
      sessions.map(async s => {
        const [e1rm, vol] = await Promise.all([
          getBenchE1rm(s.sessionId),
          getBenchVolume(s.sessionId),
        ]);
        return { sessionId: s.sessionId, e1rm, vol };
      })
    );

    const newE1rm = {};
    const newVol = {};
    metricResults.forEach(({ sessionId, e1rm, vol }) => {
      if (e1rm) newE1rm[sessionId] = e1rm;
      if (vol) newVol[sessionId] = vol;
    });
    setE1rmMap(prev => ({ ...prev, ...newE1rm }));
    setVolumeMap(prev => ({ ...prev, ...newVol }));
  }, []);

  useEffect(() => {
    if (selectedPhaseId) loadPhaseData(selectedPhaseId);
  }, [selectedPhaseId, loadPhaseData]);

  const sortedPhases = [...phases].sort((a, b) => new Date(a.startDate) - new Date(b.startDate));
  const selectedIdx = sortedPhases.findIndex(p => p.phaseId === selectedPhaseId);
  const previousPhase = selectedIdx > 0 ? sortedPhases[selectedIdx - 1] : null;

  useEffect(() => {
    if (previousPhase && !benchmarksMap[previousPhase.phaseId]) {
      getBenchmarksByPhase(previousPhase.phaseId).then(b => {
        setBenchmarksMap(prev => ({ ...prev, [previousPhase.phaseId]: b }));
      });
    }
  }, [previousPhase?.phaseId]);

  const selectedPhase = phases.find(p => p.phaseId === selectedPhaseId) || null;
  const sessions = sessionsMap[selectedPhaseId] || [];
  const benchmarks = benchmarksMap[selectedPhaseId] || [];
  const previousBenchmarks = previousPhase ? (benchmarksMap[previousPhase.phaseId] || []) : [];

  function handleSessionLogged(session) {
    setSessionsMap(prev => {
      const existing = prev[session.phaseId] || [];
      return { ...prev, [session.phaseId]: [...existing, session] };
    });
  }

  function handleBenchmarkLogged(benchmark) {
    setBenchmarksMap(prev => {
      const existing = prev[benchmark.phaseId] || [];
      return { ...prev, [benchmark.phaseId]: [...existing, benchmark] };
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
    setBenchmarksMap(prev => { const n = { ...prev }; delete n[phaseId]; return n; });
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

  async function handleUpdateBenchmark(benchmarkId, phaseId, payload) {
    await updateBenchmark(benchmarkId, payload);
    // Re-fetch benchmarks for this phase to get fresh data including child table fields
    const fresh = await getBenchmarksByPhase(phaseId);
    setBenchmarksMap(prev => ({ ...prev, [phaseId]: fresh }));
  }

  async function handleDeleteBenchmark(benchmarkId, phaseId) {
    await deleteBenchmark(benchmarkId);
    setBenchmarksMap(prev => ({
      ...prev,
      [phaseId]: (prev[phaseId] || []).filter(b => b.benchmarkId !== benchmarkId),
    }));
  }

  async function handleCreateExercise(payload) {
    const ex = await createExercise(payload);
    setExercises(prev => [...prev, ex].sort((a, b) => a.exerciseName.localeCompare(b.exerciseName)));
    return ex;
  }

  async function handleUpdateExercise(exerciseId, payload) {
    const updated = await updateExercise(exerciseId, payload);
    setExercises(prev => prev.map(e => e.exerciseId === exerciseId ? { ...e, ...updated } : e)
      .sort((a, b) => a.exerciseName.localeCompare(b.exerciseName)));
    return updated;
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: 'var(--text-secondary)' }}>
        Loading…
      </div>
    );
  }

  return (
    <>
      <Dashboard
        phases={phases}
        selectedPhase={selectedPhase}
        sessions={sessions}
        e1rmMap={e1rmMap}
        volumeMap={volumeMap}
        benchmarks={benchmarks}
        previousBenchmarks={previousBenchmarks}
        exercises={exercises}
        onSelectPhase={setSelectedPhaseId}
        onOpenPanel={() => setPanelOpen(true)}
        onUpdatePhase={handleUpdatePhase}
        onDeletePhase={handleDeletePhase}
        onUpdateSession={(sessionId, payload) => handleUpdateSession(sessionId, selectedPhaseId, payload)}
        onDeleteSession={(sessionId) => handleDeleteSession(sessionId, selectedPhaseId)}
        onUpdateBenchmark={(benchmarkId, payload) => handleUpdateBenchmark(benchmarkId, selectedPhaseId, payload)}
        onDeleteBenchmark={(benchmarkId) => handleDeleteBenchmark(benchmarkId, selectedPhaseId)}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
      <DataEntryPanel
        isOpen={panelOpen}
        onClose={() => setPanelOpen(false)}
        activeTab={panelTab}
        onTabChange={setPanelTab}
        phases={phases}
        selectedPhaseId={selectedPhaseId}
        sessions={sessions}
        exercises={exercises}
        onSessionLogged={session => {
          handleSessionLogged(session);
          setPanelOpen(false);
        }}
        onSetsLogged={() => {
          loadPhaseData(selectedPhaseId);
          setPanelOpen(false);
        }}
        onBenchmarkLogged={benchmark => {
          handleBenchmarkLogged(benchmark);
          setPanelOpen(false);
        }}
        onPhaseCreated={phase => {
          setPhases(prev => [...prev, phase]);
          setSelectedPhaseId(phase.phaseId);
          setPanelOpen(false);
        }}
        onExerciseCreated={handleCreateExercise}
        onExerciseUpdated={handleUpdateExercise}
      />
    </>
  );
}

export default App
