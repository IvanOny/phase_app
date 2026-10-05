// Which lift Quick log should have ready. Training alternates two days:
//
//   A  bench, then squat
//   B  deadlift, then pull-ups -- but pull-ups are logged only on a PR
//      attempt, so they join the plan only on a PR day.
//
// Today is the opposite of the last training day, unless that day is
// GAP_DAYS or more back: a return from a break starts with A. A day that
// already has a lift logged is whatever that lift says.
//
// Back-tested on 18 Sep - 5 Oct 2026: right on 13 of 13 days.

export const GAP_DAYS = 3;
// Pull-up PR attempts come every fourth pull-up session counting the PR
// itself: the third B day after the last logged attempt. (25 Sep -> 5 Oct,
// with 27 and 29 Sep in between.)
export const PR_EVERY_B_DAYS = 3;

const PLAN = { A: ['bench', 'squat'], B: ['deadlift', 'pullup'] };

const dayDiff = (a, b) => Math.round((Date.parse(a) - Date.parse(b)) / 86400000);

/**
 * date: 'YYYY-MM-DD' being logged for
 * days: [{date, exerciseIds}] newest first (GET /v1/phases/:id/training-days)
 * ids:  {bench, squat, deadlift, pullup} -> exerciseId (any may be missing)
 *
 * -> { type: 'A'|'B', next: role | null (null = the day is done),
 *      prIn: on a B day, B days until a pull-up PR (0 = today); null on A,
 *      logged: roles already logged on `date` }
 */
export function planDay(date, days, ids) {
  const has = (d, role) => ids[role] != null && d.exerciseIds.includes(ids[role]);
  const typeOf = d => (has(d, 'deadlift') ? 'B' : (has(d, 'bench') || has(d, 'squat')) ? 'A' : null);

  const today = days.find(d => d.date === date);
  const logged = new Set(today ? Object.keys(ids).filter(r => has(today, r)) : []);

  const last = days.find(d => d.date < date && typeOf(d));
  let type = today && typeOf(today);
  if (!type) {
    if (!last || dayDiff(date, last.date) >= GAP_DAYS) type = 'A';
    else type = typeOf(last) === 'A' ? 'B' : 'A';
  }

  // Only a B day has pull-ups. Which B day this is since the last logged
  // attempt, today included; no attempt on record means one is due.
  let prIn = null;
  if (type === 'B') {
    const lastPr = days.find(d => d.date < date && has(d, 'pullup'));
    const nth = lastPr
      ? days.filter(d => d.date > lastPr.date && d.date < date && has(d, 'deadlift')).length + 1
      : PR_EVERY_B_DAYS;
    prIn = Math.max(0, PR_EVERY_B_DAYS - nth);
  }

  const plan = PLAN[type].filter(r => r !== 'pullup' || prIn === 0 || logged.has('pullup'));
  const next = plan.find(r => !logged.has(r) && ids[r] != null) ?? null;
  return { type, next, prIn, logged };
}
