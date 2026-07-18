CREATE TABLE IF NOT EXISTS burpee_participants (
    name TEXT PRIMARY KEY
);

-- Seed known participants who may not have bot accounts or entries yet
INSERT INTO burpee_participants (name) VALUES ('Ivan'), ('Yurii'), ('Benni')
    ON CONFLICT DO NOTHING;
