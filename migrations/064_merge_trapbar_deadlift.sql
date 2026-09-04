-- One deadlift exercise, for the same reason as 063.
--
-- Barbell Deadlift (8 sessions) and Trap-bar Deadlift (1, on 18 June) are both
-- flagged is_deadlift, so the trend showed 9 dots and the volume chart 8 bars.
--
-- 063 left this one alone on the grounds that a trap-bar pull is a different
-- movement rather than a second name for the same one. That was overruled: the
-- charts disagreeing is the more concrete problem, and one session of trap-bar
-- is not a series worth splitting a lift for.
--
-- What this gives up, so it can be undone knowingly: the 18 June session was
-- trap-bar, which is usually pulled heavier than a conventional deadlift for
-- the same effort. Its top set (65 x 6) now sits on the barbell line as if it
-- were conventional. Reversing means recreating the exercise and repointing
-- session_exercise 105 back to it.
--
-- No session holds both, so this is a straight repoint.

UPDATE session_exercises SET exercise_id = 16 WHERE exercise_id = 52;

DELETE FROM exercises WHERE exercise_id = 52;
