import {
  MOCK_PHASES,
  MOCK_SESSIONS,
  MOCK_E1RM_METRICS,
  MOCK_VOLUME_METRICS,
  MOCK_BENCHMARKS,
  MOCK_EXERCISES,
} from '../data/mockData.js';

const MOCK_MODE = import.meta.env.VITE_MOCK_MODE === 'true';
const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

// Mutable in-memory store (resets on page refresh)
let _phases = MOCK_PHASES.map(p => ({ ...p }));
let _sessions = MOCK_SESSIONS.map(s => ({ ...s }));
let _e1rmMetrics = { ...MOCK_E1RM_METRICS };
let _volumeMetrics = { ...MOCK_VOLUME_METRICS };
let _benchmarks = MOCK_BENCHMARKS.map(b => ({ ...b }));
let _exercises = MOCK_EXERCISES.map(e => ({ ...e }));
let _sessionExercises = [];
let _nextId = 9000;

function nextId() {
  return ++_nextId;
}

async function apiFetch(method, path, body, { allow404 = false } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 404 && allow404) return null;
  if (!res.ok) {
    let detail = '';
    try {
      const err = await res.json();
      detail = err.detail || err.message || err.error || '';
    } catch { /* ignore */ }
    throw new Error(detail ? `${detail} (${res.status})` : `API error ${res.status}: ${path}`);
  }
  return res.json();
}

async function apiFetchList(method, path, body) {
  const data = await apiFetch(method, path, body);
  return data.items ?? data;
}

// ---- Phases ----

export async function getPhases() {
  if (MOCK_MODE) return Promise.resolve([..._phases]);
  return apiFetchList('GET', '/v1/phases');
}

export async function createPhase(payload) {
  if (MOCK_MODE) {
    const phase = { phaseId: nextId(), ...payload };
    _phases.push(phase);
    return Promise.resolve(phase);
  }
  return apiFetch('POST', '/v1/phases', payload);
}

export async function updatePhase(phaseId, payload) {
  if (MOCK_MODE) {
    const idx = _phases.findIndex(p => p.phaseId === phaseId);
    if (idx !== -1) _phases[idx] = { ..._phases[idx], ...payload };
    return Promise.resolve(_phases[idx]);
  }
  return apiFetch('PATCH', `/v1/phases/${phaseId}`, payload);
}

export async function deletePhase(phaseId) {
  if (MOCK_MODE) {
    _phases = _phases.filter(p => p.phaseId !== phaseId);
    return Promise.resolve({ deleted: true });
  }
  return apiFetch('DELETE', `/v1/phases/${phaseId}`);
}

// ---- Sessions ----

export async function getSessionsByPhase(phaseId) {
  if (MOCK_MODE) {
    return Promise.resolve(_sessions.filter(s => s.phaseId === phaseId));
  }
  return apiFetchList('GET', `/v1/sessions?phaseId=${phaseId}`);
}

export async function createSession(payload) {
  if (MOCK_MODE) {
    const session = { sessionId: nextId(), ...payload };
    _sessions.push(session);
    return Promise.resolve(session);
  }
  return apiFetch('POST', '/v1/sessions', payload);
}

export async function updateSession(sessionId, payload) {
  if (MOCK_MODE) {
    const idx = _sessions.findIndex(s => s.sessionId === sessionId);
    if (idx !== -1) _sessions[idx] = { ..._sessions[idx], ...payload };
    return Promise.resolve(_sessions[idx]);
  }
  return apiFetch('PATCH', `/v1/sessions/${sessionId}`, payload);
}

export async function deleteSession(sessionId) {
  if (MOCK_MODE) {
    _sessions = _sessions.filter(s => s.sessionId !== sessionId);
    return Promise.resolve({ deleted: true });
  }
  return apiFetch('DELETE', `/v1/sessions/${sessionId}`);
}

// ---- Session Exercises ----

export async function createSessionExercise(sessionId, payload) {
  if (MOCK_MODE) {
    const se = { sessionExerciseId: nextId(), sessionId, ...payload };
    _sessionExercises.push(se);
    return Promise.resolve(se);
  }
  return apiFetch('POST', `/v1/sessions/${sessionId}/exercises`, payload);
}

export async function updateSessionExercise(sessionId, sessionExerciseId, payload) {
  if (MOCK_MODE) return Promise.resolve({ sessionExerciseId, ...payload });
  return apiFetch('PATCH', `/v1/sessions/${sessionId}/exercises/${sessionExerciseId}`, payload);
}

export async function deleteSessionExercise(sessionId, sessionExerciseId) {
  if (MOCK_MODE) return Promise.resolve({ deleted: true });
  return apiFetch('DELETE', `/v1/sessions/${sessionId}/exercises/${sessionExerciseId}`);
}

// ---- Sets ----

export async function createExerciseSet(sessionExerciseId, payload) {
  if (MOCK_MODE) {
    const set = { exerciseSetId: nextId(), sessionExerciseId, ...payload };
    return Promise.resolve(set);
  }
  return apiFetch('POST', `/v1/session-exercises/${sessionExerciseId}/sets`, payload);
}

export async function updateExerciseSet(sessionExerciseId, exerciseSetId, payload) {
  if (MOCK_MODE) return Promise.resolve({ exerciseSetId, sessionExerciseId, ...payload });
  return apiFetch('PATCH', `/v1/session-exercises/${sessionExerciseId}/sets/${exerciseSetId}`, payload);
}

export async function deleteExerciseSet(sessionExerciseId, exerciseSetId) {
  if (MOCK_MODE) return Promise.resolve({ deleted: true });
  return apiFetch('DELETE', `/v1/session-exercises/${sessionExerciseId}/sets/${exerciseSetId}`);
}

export async function getSessionExercises(sessionId) {
  if (MOCK_MODE) return Promise.resolve([]);
  return apiFetchList('GET', `/v1/sessions/${sessionId}/exercises`);
}

export async function getExerciseSets(sessionExerciseId) {
  if (MOCK_MODE) return Promise.resolve([]);
  return apiFetchList('GET', `/v1/session-exercises/${sessionExerciseId}/sets`);
}

// ---- Exercises catalog ----

export async function getExercises() {
  if (MOCK_MODE) return Promise.resolve([..._exercises]);
  return apiFetchList('GET', '/v1/exercises');
}

export async function createExercise(payload) {
  if (MOCK_MODE) {
    const ex = { exerciseId: nextId(), ...payload };
    _exercises.push(ex);
    return Promise.resolve(ex);
  }
  return apiFetch('POST', '/v1/exercises', payload);
}

export async function updateExercise(exerciseId, payload) {
  if (MOCK_MODE) {
    const idx = _exercises.findIndex(e => e.exerciseId === exerciseId);
    if (idx !== -1) _exercises[idx] = { ..._exercises[idx], ...payload };
    return Promise.resolve(_exercises[idx]);
  }
  return apiFetch('PATCH', `/v1/exercises/${exerciseId}`, payload);
}

// ---- Metrics ----

export async function getBenchE1rm(sessionId) {
  if (MOCK_MODE) {
    const m = _e1rmMetrics[sessionId];
    return Promise.resolve(m || null);
  }
  return apiFetch('GET', `/v1/metrics/sessions/${sessionId}/bench-top-set-e1rm`, undefined, { allow404: true });
}

export async function getBenchVolume(sessionId) {
  if (MOCK_MODE) {
    const m = _volumeMetrics[sessionId];
    return Promise.resolve(m || null);
  }
  return apiFetch('GET', `/v1/metrics/sessions/${sessionId}/bench-volume`, undefined, { allow404: true });
}

// ---- Benchmarks ----

export async function getBenchmarksByPhase(phaseId) {
  if (MOCK_MODE) {
    return Promise.resolve(_benchmarks.filter(b => b.phaseId === phaseId));
  }
  return apiFetchList('GET', `/v1/benchmarks?phaseId=${phaseId}`);
}

export async function createBenchmark(payload) {
  if (MOCK_MODE) {
    const benchmark = { benchmarkId: nextId(), ...payload };
    _benchmarks.push(benchmark);
    return Promise.resolve(benchmark);
  }
  return apiFetch('POST', '/v1/benchmarks', payload);
}

export async function updateBenchmark(benchmarkId, payload) {
  if (MOCK_MODE) {
    const idx = _benchmarks.findIndex(b => b.benchmarkId === benchmarkId);
    if (idx !== -1) _benchmarks[idx] = { ..._benchmarks[idx], ...payload };
    return Promise.resolve(_benchmarks[idx]);
  }
  return apiFetch('PATCH', `/v1/benchmarks/${benchmarkId}`, payload);
}

export async function deleteBenchmark(benchmarkId) {
  if (MOCK_MODE) {
    _benchmarks = _benchmarks.filter(b => b.benchmarkId !== benchmarkId);
    return Promise.resolve({ deleted: true });
  }
  return apiFetch('DELETE', `/v1/benchmarks/${benchmarkId}`);
}

// ---- Phase summary metrics ----

export async function getPhaseSummary(phaseId) {
  if (MOCK_MODE) return Promise.resolve(null);
  return apiFetch('GET', `/v1/metrics/phases/${phaseId}/summary`, undefined, { allow404: true });
}

// ---- Screenshot import ----

export async function importScreenshot(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = async (e) => {
      const [header, imageBase64] = e.target.result.split(',');
      const mediaType = header.match(/data:([^;]+)/)[1];
      if (MOCK_MODE) {
        resolve({
          sessionDate: new Date().toISOString().slice(0, 10),
          sessionType: 'heavy_bench',
          notes: null,
          exercises: [{
            exerciseName: 'Bench Press',
            sets: [
              { setNumber: 1, reps: 5, loadKg: 60, isTopSet: false, isWorkingSet: false },
              { setNumber: 2, reps: 5, loadKg: 80, isTopSet: false, isWorkingSet: true },
              { setNumber: 3, reps: 3, loadKg: 100, isTopSet: true, isWorkingSet: true },
            ],
          }],
        });
        return;
      }
      try {
        resolve(await apiFetch('POST', '/v1/import/screenshot', { imageBase64, mediaType }));
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
}
