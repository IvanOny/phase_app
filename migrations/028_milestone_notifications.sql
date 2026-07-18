CREATE TABLE IF NOT EXISTS milestone_notifications (
    participant TEXT NOT NULL,
    month DATE NOT NULL,
    milestone_reps INTEGER NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (participant, month, milestone_reps)
);
