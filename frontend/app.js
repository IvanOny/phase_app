let sessionId = null;
let sessionExerciseId = null;

async function post(path, payload) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return res.json();
}

async function get(path) {
  const res = await fetch(path);
  return res.json();
}

document.getElementById('createSessionBtn').addEventListener('click', async () => {
  const payload = {
    phaseId: Number(document.getElementById('phaseId').value),
    sessionDate: document.getElementById('sessionDate').value,
    sessionType: document.getElementById('sessionType').value,
  };
  const out = await post('/v1/sessions', payload);
  sessionId = out.sessionId;
  document.getElementById('sessionId').textContent = sessionId ?? 'error';
});

document.getElementById('addExerciseBtn').addEventListener('click', async () => {
  if (!sessionId) return;
  const payload = {
    exerciseId: Number(document.getElementById('exerciseId').value),
    exerciseOrder: 1,
  };
  const out = await post(`/v1/sessions/${sessionId}/exercises`, payload);
  sessionExerciseId = out.sessionExerciseId;
  document.getElementById('sessionExerciseId').textContent = sessionExerciseId ?? 'error';
});

document.getElementById('addSetBtn').addEventListener('click', async () => {
  if (!sessionExerciseId) return;
  const payload = {
    setNumber: Number(document.getElementById('setNumber').value),
    reps: Number(document.getElementById('reps').value),
    loadKg: Number(document.getElementById('loadKg').value),
    isTopSet: document.getElementById('isTopSet').checked,
    isWorkingSet: true,
  };
  await post(`/v1/session-exercises/${sessionExerciseId}/sets`, payload);
});

document.getElementById('refreshMetricsBtn').addEventListener('click', async () => {
  if (!sessionId) return;
  const topSet = await get(`/v1/metrics/sessions/${sessionId}/bench-top-set-e1rm`);
  const volume = await get(`/v1/metrics/sessions/${sessionId}/bench-volume`);
  document.getElementById('metricsOutput').textContent = JSON.stringify({ topSet, volume }, null, 2);
});
