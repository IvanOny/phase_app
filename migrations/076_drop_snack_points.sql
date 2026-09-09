-- The points are gone; overdue-ness is computed.
--
-- Three columns existed to hold a score that rose every day and fell when a
-- snack was ticked, and it could not answer the only question it was for. Lock,
-- done two days ago, and Abbs r, untouched for twenty-four, both read 58: same
-- tier, same accrual since the column was created, and neither row knew when
-- its snack had last been done. Nor could the two be compared across tiers — a
-- tier-2 kept exactly on cadence still climbed to 170 in a month.
--
-- What replaces it is arithmetic on last_done_at, which the table has always
-- had: days since, over the interval the tier asks for. 100 is due now. There
-- is nothing to store, accrue, reset, floor or cap.
--
-- exercise_history keeps every row. What was done and when is the record; what
-- it was worth was a number we invented and stopped using.

ALTER TABLE exercise_items DROP COLUMN IF EXISTS score;
ALTER TABLE exercise_items DROP COLUMN IF EXISTS score_day;
ALTER TABLE exercise_history DROP COLUMN IF EXISTS points;
