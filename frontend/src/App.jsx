import { useState, useEffect, useCallback } from 'react';
import Dashboard from './components/Dashboard/Dashboard.jsx';
import DataEntryPanel from './components/DataEntry/DataEntryPanel.jsx';
import {
  getPhases,
  getSessionsByPhase,
  getBenchE1rm,
  getBenchVolume,
  getBenchmarksByPhase,
  getExercises,
} from './api/client.js';

function App() {
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
        onSetsLogged={() => setPanelOpen(false)}
        onBenchmarkLogged={benchmark => {
          handleBenchmarkLogged(benchmark);
          setPanelOpen(false);
        }}
        onPhaseCreated={phase => {
          setPhases(prev => [...prev, phase]);
          setSelectedPhaseId(phase.phaseId);
          setPanelOpen(false);
        }}
      />
    </>
  );
}

export default App
