\set ON_ERROR_STOP
BEGIN;

-- Change kwsrc.srct column to reference srct.kw rather than .id

-- Many code functions that need to deal with corpus infomation
-- in table kwsrc also need to know the corpus type name in
-- kwsrct.kw.  kwsrct was formerly referenced from kwsrc by
-- id number.  Since the name is unique we can reference it
-- by name rather than id from kwsrc.  This results in the
-- corpus type name being in kwsrc often eliminating  a
-- lookup or join with kwsrct in the common case where the
-- name is the only thing we are interested in from kwsrct.

\set dbversion  '''c3ee8f'''  -- Version applied by this update.
\set require    '''042c98'''  -- These updates(s) must be active.

\qecho Checking database version, 0 rows expected...
SELECT vchk (:require);	                       -- Will raise error on failure.
INSERT INTO db(id) VALUES(x:dbversion::INT);   -- Make this version active.
UPDATE db SET active=FALSE WHERE active AND    -- Deactivate all :require.
  LPAD(TO_HEX(id),6,'0') IN (SELECT unnest(string_to_array(:require,',')));

-- Do the update.

ALTER TABLE kwsrc DROP CONSTRAINT kwsrc_srct_fkey; -- To allow reuse of name.
ALTER TABLE kwsrc RENAME COLUMN srct TO _x;
ALTER TABLE kwsrc ADD COLUMN srct TEXT REFERENCES kwsrct(kw);
UPDATE kwsrc SET srct=(SELECT kw FROM kwsrct WHERE kwsrct.id=kwsrc._x);
ALTER TABLE kwsrc ALTER COLUMN srct SET NOT NULL;
ALTER TABLE kwsrc DROP COLUMN _x;

COMMIT;
