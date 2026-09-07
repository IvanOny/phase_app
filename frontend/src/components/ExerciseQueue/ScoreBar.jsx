import { useEffect, useState } from 'react';
import { getExqScore } from '../../api/exqClient.js';

// The snack score, tier-weighted: a tier-1 item counts 12 and a tier-5 counts 1,
// so ten easy ticks don't outrank the one thing that was hard. The weights are
// frozen into each history row when the snack is ticked, which is why re-rating
// an exercise today leaves last month's numbers alone.
//
// Same numbers the bot answers /score with — one function computes both, in
// exercise_bot.score_summary, so the two surfaces can't drift.

const SPARK_DAYS = 21;

function Spark({ days }) {
  if (days.length < 2) return null;
  const recent = days.slice(-SPARK_DAYS);
  const max = Math.max(...recent.map(d => d.points), 1);
  return (
    <div className="exq-score-spark" title={`last ${recent.length} scoring days`}>
      {recent.map(d => (
        <span
          key={d.day}
          className="exq-score-bar"
          style={{ height: `${Math.max(8, (d.points / max) * 100)}%` }}
          title={`${d.day}: ${d.points} pts · ${d.snacks} snack${d.snacks === 1 ? '' : 's'}`}
        />
      ))}
    </div>
  );
}

export default function ScoreBar({ refreshKey }) {
  const [score, setScore] = useState(null);
  const [failed, setFailed] = useState(false);

  // refreshKey changes whenever something is ticked off elsewhere in the app,
  // so the score doesn't sit there stale next to a calendar that has moved on.
  useEffect(() => {
    let live = true;
    getExqScore()
      .then(s => { if (live) { setScore(s); setFailed(false); } })
      .catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, [refreshKey]);

  // Silent when it can't load: this is a header ornament, and an error banner
  // for it would sit above a planner that is working perfectly well.
  if (failed || !score) return null;

  const run = score.streak > 0
    ? `${score.streak} day${score.streak === 1 ? '' : 's'}`
    : '—';

  return (
    <div className="exq-score">
      <div className="exq-score-figure">
        <span className="exq-score-value">{score.today}</span>
        <span className="exq-score-unit">pts today</span>
      </div>
      <div className="exq-score-rest">
        <span><strong>{score.week}</strong> this week</span>
        <span><strong>{run}</strong> run</span>
        <span><strong>{score.best}</strong> best day</span>
      </div>
      <Spark days={score.days ?? []} />
    </div>
  );
}
