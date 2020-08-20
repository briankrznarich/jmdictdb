\set ON_ERROR_STOP
BEGIN;

-- Prevent more than one active, approved entry per seq# (IS-213).
--   (or more accurately, per corpus/seq# pair.)
-- Also add and extra column to table "entr" for use when importing
--   bulk data.
-- Fix an index that prevented multiple versions of "kanjidic"
--   corpora in a database.
-- Update the kwxref table for two very old (2011) changes.
-- Remove control characters that were previously allowed into history
--   records.

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

-- Additional updates to the kw* tables to bring contents into
-- confomance with the DTDs and kw*.csv tables.  The most recent
-- of these were made in 032-aa7ceb.sql but the following two
-- were overlooked.

  -- This is an ancient change (110831-346f2b0) that never made it
  -- into a database update until now.
UPDATE kwxref SET descr='cf.' WHERE id=4 AND descr='C.f.';
  -- As is this (110122-8553eea).
INSERT INTO kwxref VALUES(9,'vtvi','Transitive-intransitive verb pair')
    ON CONFLICT DO NOTHING;

-- Remove control characters excluding '\t' ('\x9') and '\n' ('\xa'):
-- The JMdictDB code did not (until rev 200816-ad91323) strip control
-- characters from text destined for the database so we clean up any
-- that were improperly allowed in, here.
-- In the following statements the E'...' [*] prefixes are crucial; without
-- them the values will be treated as BYTEA with the result that both the
-- wrong rows will be selected and the translate function will trash the text.
-- The concatenations (||) are just to allow visually aligning the rows.
-- [*] This assumes a conventional Postgresql configuration where the
--  settings 'standard_conforming_strings', 'escape_string_warning' and
--  'backslash_quote' all have the default values used by recent versions
--  of Popstgresql.

\echo Updating hist.refs
UPDATE hist SET refs=translate (refs,
      E'\x01\x02\x03\x04\x05\x06\x07\x08' ||  E'\x0b\x0c\x0d\x0e\x0f' ||
  E'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f', '')
    WHERE refs ~ E'[\x1-\x8\xb-\x1f]';

\echo Updating hist.notes
UPDATE hist SET notes=translate (notes,
      E'\x01\x02\x03\x04\x05\x06\x07\x08' ||  E'\x0b\x0c\x0d\x0e\x0f' ||
  E'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f', '')
    WHERE notes ~ E'[\x1-\x8\xb-\x1f]';

\echo Updating hist.diff
UPDATE hist SET diff=translate (diff,
      E'\x01\x02\x03\x04\x05\x06\x07\x08' ||  E'\x0b\x0c\x0d\x0e\x0f' ||
  E'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f', '')
    WHERE diff ~ E'[\x1-\x8\xb-\x1f]';

\echo Updating gloss.txt
UPDATE gloss SET txt=translate (txt,
      E'\x01\x02\x03\x04\x05\x06\x07\x08' ||  E'\x0b\x0c\x0d\x0e\x0f' ||
  E'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f', '')
    WHERE txt ~ E'[\x1-\x8\xb-\x1f]';

CREATE TABLE krslv (
    entr INT NOT NULL
      REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    kw SMALLINT NOT NULL,
    value VARCHAR(50) NOT NULL,
      PRIMARY KEY (entr,kw,value));
INSERT INTO krslv (SELECT * FROM kresolv);

COMMIT;
