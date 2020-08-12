\set ON_ERROR_STOP
BEGIN;

-- Add extra column to "entr" to aid data import.management.

\set dbversion  '''329fa4'''  -- Version applied by this update.
\set require    '''e99634'''  -- These updates(s) must be active.

\qecho Checking database version, 0 rows expected...
SELECT vchk (:require);	                       -- Will raise error on failure.
INSERT INTO db(id) VALUES(x:dbversion::INT);   -- Make this version active.
UPDATE db SET active=FALSE WHERE active AND    -- Deactivate all :require.
  LPAD(TO_HEX(id),6,'0') IN (SELECT unnest(string_to_array(:require,',')));

-- Do the update.

ALTER TABLE entr ADD COLUMN idx INT;

COMMIT;
