// The "tier-1" quick-add exercise list. Stored server-side (single account)
// via GET/PUT /v1/settings/quick-exercises so it's the same on every browser.
//
// Each entry is resolved to a catalog exercise by, in order:
//   1. exerciseId  (custom entries added from the catalog)
//   2. matchFlag   (barbell lifts: isBarbellBenchPress / isSquat / isDeadlift)
//   3. isRun flag  (the Run entry)
//   4. name match  (fallback)

export const QUICK_EXERCISES_KEY = 'quick-exercises';

export const DEFAULT_QUICK_EXERCISES = [
  { label: 'Barbell Bench Press', sessionType: 'heavy_bench', flags: { isBarbellBenchPress: true }, matchFlag: 'isBarbellBenchPress', type: 'strength' },
  { label: 'Barbell Squat',       sessionType: 'squat',       flags: { isSquat: true },             matchFlag: 'isSquat',             type: 'strength' },
  { label: 'Barbell Deadlift',    sessionType: 'deadlift',    flags: { isDeadlift: true },          matchFlag: 'isDeadlift',          type: 'strength' },
  { label: 'Pull',                sessionType: 'pull',        flags: { isBodyweight: true },                                          type: 'bodyweight' },
  { label: 'Weighted Pull-ups',   sessionType: 'pull',        flags: {},                                                              type: 'strength' },
  { label: 'Run',                 sessionType: 'run',         flags: { isRun: true },               matchFlag: 'isRun',               type: 'run' },
];

// Resolve one quick-add entry to its catalog exercise (or undefined).
export function resolveQuickEntry(entry, exercises) {
  if (!entry) return undefined;
  if (entry.exerciseId) return exercises.find(e => e.exerciseId === entry.exerciseId);
  if (entry.matchFlag)  return exercises.find(e => e[entry.matchFlag] === true);
  return exercises.find(e => e.exerciseName.toLowerCase() === entry.label.toLowerCase());
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
