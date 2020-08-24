\set ON_ERROR_STOP
BEGIN;

-- Add support for XML DTD entity information in kw* tables.

\set dbversion  '''042c98'''  -- Update version applied by this update.
\set require    '''f62d8a,aa7ceb'''  -- These updates(s) must be active.

\qecho Checking database version, 0 rows expected...
SELECT vchk (:require);	                       -- Will raise error on failure.
INSERT INTO db(id) VALUES(x:dbversion::INT);   -- Make this version active.
UPDATE db SET active=FALSE WHERE active AND    -- Deactivate all :require.
  LPAD(TO_HEX(id),6,'0') IN (SELECT unnest(string_to_array(:require,',')));

-- Do the update.

ALTER TABLE kwdial ADD COLUMN ents JSONB;
ALTER TABLE kwfld  ADD COLUMN ents JSONB;
ALTER TABLE kwkinf ADD COLUMN ents JSONB;
ALTER TABLE kwmisc ADD COLUMN ents JSONB;
ALTER TABLE kwpos  ADD COLUMN ents JSONB;
ALTER TABLE kwrinf ADD COLUMN ents JSONB;

UPDATE kwdial SET ents='{"jmdict":0}' WHERE id=1;

UPDATE kwmisc SET ents='{"jmdict":{"v":"female term or language"},"jmnedict":{"v":"female given name or forename"}}' WHERE id=9;
UPDATE kwmisc SET ents='{"jmdict":{"v":"male term or language"},"jmnedict":{"e":"masc", "v":"male given name or forename"}}' WHERE id=15;
UPDATE kwmisc SET ents='{"jmdict":0}' WHERE id=82;
UPDATE kwmisc SET ents='{"jmnedict":1}' WHERE id BETWEEN 181 AND 192;

UPDATE kwrinf SET ents='{"jmdict":0}' WHERE id BETWEEN 103 AND 132;

COMMIT;
