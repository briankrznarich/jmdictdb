\set ON_ERROR_STOP
BEGIN;

-- Prevent more than one active, approved entry per seq# (IS-213).
-- ...or more accurately, per corpus/seq# pair.

\set dbversion  '''e99634'''  -- Version applied by this update.
\set require    '''c3ee8f'''  -- These updates(s) must be active.

\qecho Checking database version, 0 rows expected...
SELECT vchk (:require);	                       -- Will raise error on failure.
INSERT INTO db(id) VALUES(x:dbversion::INT);   -- Make this version active.
UPDATE db SET active=FALSE WHERE active AND    -- Deactivate all :require.
  LPAD(TO_HEX(id),6,'0') IN (SELECT unnest(string_to_array(:require,',')));

-- Do the update.

CREATE UNIQUE INDEX ON entr (src,seq) WHERE stat=2 AND NOT unap;

COMMIT;
