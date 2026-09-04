-- One squat exercise, and a dead deadlift entry removed.
--
-- The lift trend groups by the is_squat flag and saw 9 sessions; the volume
-- chart is per exercise and saw 7. Neither was wrong — the catalog held
-- "Barbell Back Squat" (7 sessions) and "Squat" (2, on 18 and 21 July), both
-- flagged is_squat. Any chart that picks one exercise disagrees with any chart
-- that picks the flag, for as long as both rows exist.
--
-- No session holds both, so this is a straight repoint with no set renumbering
-- and no top-set collision — unlike the pull-up merges in 061 and 062.
--
-- "Deadlift" (67) goes too: zero sessions have ever used it, and it is flagged
-- is_deadlift, so the first time anything is logged against it the deadlift
-- trend and the deadlift volume chart start disagreeing the same way.
--
-- Left alone deliberately: "Trap-bar Deadlift" (1 session, also is_deadlift).
-- That is a real variant, not a duplicate name for the same lift, and whether
-- it belongs in the same line is a training judgement rather than a cleanup.

UPDATE session_exercises SET exercise_id = 36 WHERE exercise_id = 66;

DELETE FROM exercises WHERE exercise_id = 66;
DELETE FROM exercises WHERE exercise_id = 67;
