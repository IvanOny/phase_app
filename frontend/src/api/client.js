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
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
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

// ---- Session Exercises ----

export async function createSessionExercise(sessionId, payload) {
  if (MOCK_MODE) {
    const se = { sessionExerciseId: nextId(), sessionId, ...payload };
    _sessionExercises.push(se);
    return Promise.resolve(se);
  }
  return apiFetch('POST', `/v1/sessions/${sessionId}/exercises`, payload);
}

// ---- Sets ----

export async function createExerciseSet(sessionExerciseId, payload) {
  if (MOCK_MODE) {
    const set = { exerciseSetId: nextId(), sessionExerciseId, ...payload };
    return Promise.resolve(set);
  }
  return apiFetch('POST', `/v1/session-exercises/${sessionExerciseId}/sets`, payload);
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
