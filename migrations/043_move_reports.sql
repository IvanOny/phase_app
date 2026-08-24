-- Move: let a radar viewer report a move to the humans.
--
-- Blocking (move_radar_block) is self-service and private: "stop showing me
-- this person". Reporting is different — it says someone should look at this,
-- so the row is kept for an audit trail and the log channel is pinged.
--
-- One report per person per entry: the PK makes a second tap a no-op rather
-- than a second ping.

CREATE TABLE IF NOT EXISTS move_reports (
    entry_id INTEGER NOT NULL REFERENCES move_entries(id) ON DELETE CASCADE,
    reporter_tg_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (entry_id, reporter_tg_id)
);

CREATE INDEX IF NOT EXISTS idx_move_reports_created ON move_reports (created_at DESC);
