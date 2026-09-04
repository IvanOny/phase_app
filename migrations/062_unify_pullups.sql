-- One Pull-up, everywhere.
--
-- Migration 061 folded Weighted Pull-up and Weighted Pull-ups into Pull-up but
-- left Chin-up standing, and left two sessions holding two Pull-up rows each
-- (25, from that merge; 93, once Chin-up joins them). This finishes the job:
-- one exercise, one row per session, sets renumbered underneath.
--
-- Chin-up goes too. It is the same movement with the hands turned round, it
-- already counted toward the pull-up trend via is_pullup, and keeping it as a
-- separate catalog entry meant the add screen offered a choice that changes
-- nothing about what gets recorded.
--
-- Written generically rather than against the two known session ids, so it does
-- the right thing if it is ever run against a database in a different state.

-- 1. Chin-up becomes Pull-up.
UPDATE session_exercises SET exercise_id = 19 WHERE exercise_id = 38;

-- 2. Only one set per exercise per session may be marked as the top set
--    (uq_exercise_sets_one_top_set), and merging brings two marked sets
--    together in session 93: a weighted 14x5 and a bodyweight 12. Something has
--    to give, so the better e1RM keeps the mark -- (bodyweight + load) *
--    (1 + reps/30), the same number the lift trend plots, with bodyweight read
--    from the nearest log entry for the phase. Here that keeps the bodyweight
--    12 (103.6) over the weighted five (102.7).
WITH grouped AS (
    SELECT es.exercise_set_id, es.load_kg, es.reps, s.phase_id, s.session_date,
           MIN(se2.session_exercise_id) OVER (PARTITION BY se.session_id) AS keep_id
    FROM exercise_sets es
    JOIN session_exercises se ON se.session_exercise_id = es.session_exercise_id
    JOIN session_exercises se2 ON se2.session_id = se.session_id AND se2.exercise_id = 19
    JOIN sessions s ON s.session_id = se.session_id
    WHERE se.exercise_id = 19 AND es.is_top_set = 1
),
scored AS (
    SELECT g.exercise_set_id, g.keep_id,
           (COALESCE(bw.weight_kg, 0) + g.load_kg) * (1 + g.reps / 30.0) AS e1rm
    FROM (SELECT DISTINCT * FROM grouped) g
    LEFT JOIN LATERAL (
        SELECT weight_kg FROM bodyweight_log b WHERE b.phase_id = g.phase_id
        ORDER BY (b.logged_date > g.session_date::date),
                 ABS(b.logged_date - g.session_date::date) LIMIT 1
    ) bw ON TRUE
),
losers AS (
    SELECT exercise_set_id FROM (
        SELECT exercise_set_id, keep_id,
               ROW_NUMBER() OVER (PARTITION BY keep_id ORDER BY e1rm DESC, exercise_set_id) AS rn
        FROM scored
    ) r WHERE rn > 1
)
UPDATE exercise_sets SET is_top_set = 0
WHERE exercise_set_id IN (SELECT exercise_set_id FROM losers);

-- 3. Where a session now holds more than one Pull-up row, the earliest row
--    keeps the exercise and the rest hand over their sets, renumbered to
--    continue after the ones already there. (session_exercise_id, set_number)
--    is unique, so the numbering has to be rebuilt rather than copied.
WITH keeper AS (
    SELECT session_id, MIN(session_exercise_id) AS keep_id
    FROM session_exercises WHERE exercise_id = 19
    GROUP BY session_id HAVING COUNT(*) > 1
),
moving AS (
    SELECT se.session_exercise_id, k.keep_id
    FROM session_exercises se
    JOIN keeper k ON k.session_id = se.session_id
    WHERE se.exercise_id = 19 AND se.session_exercise_id <> k.keep_id
),
renumbered AS (
    SELECT es.exercise_set_id, m.keep_id,
           (SELECT COALESCE(MAX(set_number), 0) FROM exercise_sets
            WHERE session_exercise_id = m.keep_id)
           + ROW_NUMBER() OVER (PARTITION BY m.keep_id
                                ORDER BY es.session_exercise_id, es.set_number) AS new_number
    FROM exercise_sets es
    JOIN moving m ON m.session_exercise_id = es.session_exercise_id
)
UPDATE exercise_sets es
SET session_exercise_id = r.keep_id, set_number = r.new_number
FROM renumbered r WHERE r.exercise_set_id = es.exercise_set_id;

-- 4. The rows that handed their sets over are now empty.
DELETE FROM session_exercises se
WHERE se.exercise_id = 19
  AND NOT EXISTS (SELECT 1 FROM exercise_sets es
                  WHERE es.session_exercise_id = se.session_exercise_id)
  AND EXISTS (SELECT 1 FROM session_exercises o
              WHERE o.session_id = se.session_id AND o.exercise_id = 19
                AND o.session_exercise_id < se.session_exercise_id);

-- 5. Nothing references Chin-up any more. ON DELETE RESTRICT is the check.
DELETE FROM exercises WHERE exercise_id = 38;

