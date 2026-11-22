-- Verletzungen: Heben oder Laufen.
--
-- Die Tabelle warf beides in einen Topf, und beim Durchsehen der Einträge war
-- genau das die Verwechslung: das rechte Knie steht zwischen Rücken, BWS und
-- Leiste, obwohl es das Heben nie eingeschränkt hat -- es betrifft das Laufen.
-- Ohne die Unterscheidung liest sich die Liste, als sei das Heben dreimal so
-- oft unterbrochen worden wie tatsächlich.
--
-- 'lifting' als Default, weil jeder bestehende Eintrag ausser dem Knie einer
-- ist; das Knie wird unten einzeln gesetzt.

ALTER TABLE injuries
  ADD COLUMN IF NOT EXISTS discipline TEXT NOT NULL DEFAULT 'lifting';

ALTER TABLE injuries DROP CONSTRAINT IF EXISTS injuries_discipline_check;
ALTER TABLE injuries
  ADD CONSTRAINT injuries_discipline_check
  CHECK (discipline IN ('lifting', 'running', 'both'));

UPDATE injuries SET discipline = 'running' WHERE area ILIKE '%knee%';
