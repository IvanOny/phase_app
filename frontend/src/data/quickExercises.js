// The "tier-1" quick-add exercise list. Stored server-side (single account)
// via GET/PUT /v1/settings/quick-exercises so it's the same on every browser.
//
// Each entry is resolved to a catalog exercise by, in order:
//   1. exerciseId    (custom entries added from the catalog — immune to renames)
//   2. matchFlag     (barbell lifts / run: isBarbellBenchPress / isSquat / isDeadlift / isRun)
//   3. exact name    (case-insensitive)
//   4. normalized    (ignores case, punctuation, spacing and a trailing plural:
//                     "Weighted Pull-ups" → "Weighted Pull-up")
//   5. unique prefix (only when exactly ONE catalog entry matches:
//                     "Pull" → "Pull-up". Ambiguous prefixes resolve to nothing.)
//
// Steps 4–5 exist so a near-miss label resolves to the existing exercise instead
// of silently creating a duplicate (which is how "Pull" once became a new row).

export const QUICK_EXERCISES_KEY = 'quick-exercises';

export const DEFAULT_QUICK_EXERCISES = [
  { label: 'Barbell Bench Press', sessionType: 'heavy_bench', flags: { isBarbellBenchPress: true }, matchFlag: 'isBarbellBenchPress', type: 'strength' },
  { label: 'Barbell Squat',       sessionType: 'squat',       flags: { isSquat: true },             matchFlag: 'isSquat',             type: 'strength' },
  { label: 'Barbell Deadlift',    sessionType: 'deadlift',    flags: { isDeadlift: true },          matchFlag: 'isDeadlift',          type: 'strength' },
  { label: 'Pull-up',             sessionType: 'pull',        flags: { isBodyweight: true },                                          type: 'bodyweight' },
  { label: 'Weighted Pull-up',    sessionType: 'pull',        flags: {},                                                              type: 'strength' },
  { label: 'Run',                 sessionType: 'run',         flags: { isRun: true },               matchFlag: 'isRun',               type: 'run' },
];

// Lowercase, drop everything but letters/digits, then strip a trailing plural.
// "Weighted Pull-ups" and "weighted pull up" both → "weightedpullup".
function normalizeName(name) {
  const flat = String(name || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  return flat.endsWith('s') && flat.length > 3 ? flat.slice(0, -1) : flat;
}

// Resolve one quick-add entry to its catalog exercise (or undefined).
export function resolveQuickEntry(entry, exercises) {
  if (!entry) return undefined;
  const list = exercises || [];
  if (entry.exerciseId) return list.find(e => e.exerciseId === entry.exerciseId);
  if (entry.matchFlag)  return list.find(e => e[entry.matchFlag] === true);

  const label = String(entry.label || '');
  if (!label) return undefined;

  const exact = list.find(e => e.exerciseName.toLowerCase() === label.toLowerCase());
  if (exact) return exact;

  const target = normalizeName(label);
  if (!target) return undefined;

  const normalized = list.find(e => normalizeName(e.exerciseName) === target);
  if (normalized) return normalized;

  // Last resort: a prefix match, but only if it's unambiguous. "Pull" resolves to
  // "Pull-up" when that's the sole candidate; if "Pull-over" also existed we
  // return undefined rather than guess wrong.
  const prefixed = list.filter(e => normalizeName(e.exerciseName).startsWith(target));
  return prefixed.length === 1 ? prefixed[0] : undefined;
}

// The set of catalog exerciseIds that are "tier 1" (present in the quick list).
export function resolveTierOneExerciseIds(quickList, exercises) {
  const ids = new Set();
  (quickList || []).forEach(entry => {
    const ex = resolveQuickEntry(entry, exercises || []);
    if (ex) ids.add(ex.exerciseId);
  });
  return ids;
}
