-- Move: unguessable invite links.
--
-- The deep link used to be `invitation_of_<name>_<telegram_user_id>`, and
-- /start on it connected the two accounts outright. A Telegram user id is not
-- a secret — it is visible to every bot the person has ever talked to, and it
-- is short enough to walk — so anyone who could type a URL could bolt
-- themselves onto a stranger's crew and start receiving their daily videos.
--
-- The id is replaced by a random per-user code. Knowing someone's id no longer
-- gets you anything; you need the string they actually sent you.
--
-- Shape: 'm' + 15 hex chars. The leading letter is deliberate — it means a
-- code can never be all digits, which is how the parser still tells a new code
-- apart from a legacy numeric id in an old link someone kept.
--
-- Existing links stop working. That is the point of the change, and the user
-- base is small enough to re-share.

ALTER TABLE move_users ADD COLUMN IF NOT EXISTS invite_code TEXT;

UPDATE move_users
   SET invite_code = 'm' || substr(md5(random()::text || clock_timestamp()::text
                                       || telegram_user_id::text), 1, 15)
 WHERE invite_code IS NULL;

-- A default keeps every future row valid without the bot having to remember,
-- so reading a code is always a plain SELECT.
ALTER TABLE move_users
  ALTER COLUMN invite_code SET DEFAULT 'm' || substr(md5(random()::text || clock_timestamp()::text), 1, 15);

ALTER TABLE move_users ALTER COLUMN invite_code SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS move_users_invite_code_idx ON move_users (invite_code);
