\set ON_ERROR_STOP
BEGIN;

-- Add "eid" column to table "hist".

\set dbversion  '''b5d00f'''  -- New version supplied by this update.
\set require    '''972bf3'''  -- These updates(s) must be active.

\qecho Checking database version, 0 rows expected...
SELECT vchk (:require);                      -- Will raise error on failure.
INSERT INTO db(id) VALUES(x:dbversion::INT); -- Make this version active.
-- This update supercedes previous updates.
UPDATE db SET active=FALSE WHERE active AND  -- Deactivate all :require.
LPAD(TO_HEX(id),6,'0') IN (SELECT unnest(string_to_array(:require,',')));

-- Do the update.

  -- This field will allow better correlation of current
  -- database entries with historical log file messages.
ALTER TABLE hist
    ADD eid INT;   -- entry id# that history was first attached to.

COMMIT;
