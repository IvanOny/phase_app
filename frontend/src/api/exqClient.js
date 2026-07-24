// API client for the Exercise Queue planner. Token-gated via ?token= (the
// exq_token from the bot's /exapp link). Separate from the phase-app client.

const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

let _token = '';
export function setExqToken(t) { _token = t || ''; }

async function req(method, path, body) {
  const sep = path.includes('?') ? '&' : '?';
  const url = `${BASE}${path}${sep}token=${encodeURIComponent(_token)}`;
  const res = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = '';
    try { const e = await res.json(); detail = e.detail || e.error || ''; } catch { /* ignore */ }
    throw new Error(detail ? `${detail} (${res.status})` : `API error ${res.status}`);
  }
  return res.json();
}

export const getExqExercises = () => req('GET', '/v1/exq/exercises').then(r => r.items ?? []);

export const updateExqExercise = (id, patch) => req('PATCH', `/v1/exq/exercises/${id}`, patch);

export const deleteExqExercise = (id) => req('DELETE', `/v1/exq/exercises/${id}`);

export const getExqSchedule = (from, to) =>
  req('GET', `/v1/exq/schedule?from=${from}&to=${to}`);

// mode: 'shift' (future occurrences follow, keeping cadence) | 'single' (only this one).
// fromDate lets 'single' tombstone the day the item was dragged off.
export const createOccurrence = (exerciseId, date, mode = 'single', fromDate = null) =>
  req('POST', '/v1/exq/schedule', { exerciseId, date, mode, fromDate });

export const moveOccurrence = (id, date, mode = 'single') =>
  req('PATCH', `/v1/exq/schedule/${id}`, { date, mode });

export const deleteOccurrence = (id) =>
  req('DELETE', `/v1/exq/schedule/${id}`);

export const completeOccurrence = (id) =>
  req('POST', `/v1/exq/schedule/${id}/done`);

export const getExqHistory = (limit = 50) =>
  req('GET', `/v1/exq/history?limit=${limit}`).then(r => r.items ?? []);

export const getExqStats = () => req('GET', '/v1/exq/stats');

export const suggestSlot = (exerciseId, avoid = []) =>
  req('POST', '/v1/exq/suggest-slot', { exerciseId, avoid });

// Returns { reply, trace? }. trace is present only when debug is true.
export const chatCoach = (messages, debug = false) =>
  req('POST', '/v1/exq/chat', { messages, debug });

export const getCoachContext = () =>
  req('GET', '/v1/exq/context').then(r => r.context);
