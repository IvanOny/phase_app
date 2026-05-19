// Format seconds → "M:SS" or "H:MM:SS"
export function formatDuration(seconds) {
  if (seconds == null) return '';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

// Format pace seconds/km → "M:SS /km"
export function formatPace(secPerKm) {
  if (secPerKm == null) return '';
  const m = Math.floor(secPerKm / 60);
  const s = secPerKm % 60;
  return `${m}:${String(s).padStart(2, '0')} /km`;
}

// Parse "M:SS" or "H:MM:SS" → seconds (null on invalid)
export function parseDuration(str) {
  if (!str) return null;
  const parts = String(str).trim().split(':').map(Number);
  if (parts.some(isNaN)) return null;
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  return null;
}

// Parse "M:SS" pace → seconds/km (null on invalid)
export function parsePace(str) {
  if (!str) return null;
  const parts = String(str).trim().replace(/\s*\/km$/, '').split(':').map(Number);
  if (parts.length !== 2 || parts.some(isNaN)) return null;
  return parts[0] * 60 + parts[1];
}

// One-line summary for display in session row
export function runSummary(session) {
  const parts = [];
  if (session.distanceKm != null)       parts.push(`${session.distanceKm} km`);
  if (session.durationSeconds != null)  parts.push(formatDuration(session.durationSeconds));
  if (session.avgPaceSecPerKm != null)  parts.push(formatPace(session.avgPaceSecPerKm));
  if (session.avgHr != null)            parts.push(`${session.avgHr} bpm`);
  return parts.join(' · ');
}
