\set ON_ERROR_STOP
BEGIN;

-- Prevent more than one active, approved entry per seq# (IS-213).
-- (or more accurately, per corpus/seq# pair.)
-- Also add and extra column to table "entr" for use when importing
-- bulk data.
-- And finally, fix an index that prevented multiple versions of
-- "kanjidic" corpora in a database.

\set dbversion  '''8fac2c'''  -- Version applied by this update.
\set require    '''c3ee8f'''  -- These updates(s) must be active.

\qecho Checking database version, 0 rows expected...
SELECT vchk (:require);	                       -- Will raise error on failure.
INSERT INTO db(id) VALUES(x:dbversion::INT);   -- Make this version active.
UPDATE db SET active=FALSE WHERE active AND    -- Deactivate all :require.
  LPAD(TO_HEX(id),6,'0') IN (SELECT unnest(string_to_array(:require,',')));

-- Do the update.

-- Prevent multiple A entries.
CREATE UNIQUE INDEX ON entr (src,seq) WHERE stat=2 AND NOT unap;

-- Extra column in "entr" to aid bulk data imports.
ALTER TABLE entr ADD COLUMN idx INT;

-- Replace old index that prevented having more than one "kanjidic"
-- corpus in a database, with a more flexible version.
DROP INDEX chr_chr_idx;
CREATE UNIQUE INDEX ON chr(entr,chr);

COMMIT;
