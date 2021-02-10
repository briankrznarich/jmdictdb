\set ON_ERROR_STOP
BEGIN;

-- Update misspelled 'literaly' descr field in ginf table.

\set dbversion  '''46354d'''  -- Additional version applied by this update.
\set require    '''8fac2c'''  -- These updates(s) must be active.

\qecho Checking database version, 0 rows expected...
SELECT vchk (:require);	                       -- Will raise error on failure.
INSERT INTO db(id) VALUES(x:dbversion::INT);   -- Make this version active.
-- This update is auxiliary to the existing 8fac2c database update
-- version so don't deactivate that version.
--UPDATE db SET active=FALSE WHERE active AND    -- Deactivate all :require.
--  LPAD(TO_HEX(id),6,'0') IN (SELECT unnest(string_to_array(:require,',')));

-- Do the update.
UPDATE kwginf SET descr='literally' WHERE id=2 AND descr='literaly';

COMMIT;
