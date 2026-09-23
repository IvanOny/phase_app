-- Injuries, as annotations on the training history.
--
-- A flat month on a trend chart reads as lost discipline unless something on
-- the chart says otherwise. These rows are that something: each is a span,
-- from the day it started to the day it stopped limiting training, drawn over
-- the lift and body charts and listed in its own card.
--
-- resolved_on NULL means still open. "Resolved" is a training fact, not a
-- clinical one -- the day normal loading resumed without symptoms.
--
-- Keyed on nothing but itself: an injury belongs to the person, not to a
-- phase, and the charts it annotates already span every phase.
CREATE TABLE IF NOT EXISTS injuries (
    injury_id    SERIAL PRIMARY KEY,
    started_on   DATE NOT NULL,
    resolved_on  DATE,
    area         TEXT NOT NULL,
    severity     TEXT NOT NULL DEFAULT 'moderate'
                 CHECK (severity IN ('minor', 'moderate', 'severe')),
    note         TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT injuries_span CHECK (resolved_on IS NULL OR resolved_on >= started_on)
);

CREATE INDEX IF NOT EXISTS idx_injuries_started ON injuries (started_on);
