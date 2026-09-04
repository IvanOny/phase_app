-- One pull-up exercise, with the added weight as a number on the set.
--
-- The catalog held "Pull-up" (bodyweight) and "Weighted Pull-up" / "Weighted
-- Pull-ups" as separate exercises, so the same movement was split across three
-- rows depending on whether anything was hanging off you that day. The add
-- screen offered two of them side by side and you had to pick.
--
-- After this there is one: Pull-up, with load_kg meaning added weight and 0
-- meaning bodyweight alone. That is already how the lift trend reads it —
-- e1RM is (bodyweight + load_kg) * (1 + reps/30), migration 060.
--
-- Session 25 has both a Pull-up and a Weighted Pull-up row and will end up with
-- two Pull-up rows. Deliberately left that way: the sets under each stay
-- distinct, exercise_sets numbers per session_exercise so merging them would
-- mean renumbering, and every query that reads a top set takes the best one per
-- session anyway.

UPDATE session_exercises SET exercise_id = 19 WHERE exercise_id IN (12, 68);

-- Nothing references them now. ON DELETE RESTRICT would have stopped this if
-- anything still did, which is the check that matters.
DELETE FROM exercises WHERE exercise_id IN (12, 68);
