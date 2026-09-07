-- Nobody who already uses circles gets told they exist.
--
-- 071 added circles_told_at, NULL for everyone, so the next run of the notice
-- would explain circles to the person who built them and has two. Owning a
-- circle is proof enough of having found the button.
--
-- Anyone in the beta who has not made one is left NULL on purpose: that is
-- exactly who the notice is for.

UPDATE move_users u
SET circles_told_at = NOW()
WHERE circles_told_at IS NULL
  AND EXISTS (SELECT 1 FROM move_circles c WHERE c.owner_tg_id = u.telegram_user_id);
