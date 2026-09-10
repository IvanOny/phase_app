-- An invite must outlive the registration it interrupts.
--
-- Who invited you was carried in move_state, as "await_name:<id>" -- and
-- move_state is a ten-minute scratchpad, built for "which question am I
-- answering", where forgetting is the correct behaviour. Registration is not
-- that: it has three steps, one of them a name somebody has to think of, and
-- it can be abandoned and resumed a day later.
--
-- Україночка opened Iv's link on 8 September, finished her name on the 9th,
-- and arrived a stranger. The two only connected because she happened to open
-- the same link a second time afterwards, which nothing told her to do.
--
-- So it lives on the person now, not on the question they were being asked.
ALTER TABLE move_users
    ADD COLUMN IF NOT EXISTS pending_inviter_id BIGINT;
