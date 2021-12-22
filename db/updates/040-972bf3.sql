\set ON_ERROR_STOP
BEGIN;

-- Improved edit tree support.
-- This update replaces the PL/pgSQL functions get_subtree() and get_edroot()
-- with a more versatile set of views.
-- For more documentation on the new views see db/mkviews.sql.
--
-- This update also adds a database constraint on entr.dfrm that enforces
-- a condition (approved entries can't be edits of some other entry) that
-- was previously maintained by the JMdictDB software.

\set dbversion  '''972bf3'''  -- New version supplied by this update.
\set require    '''d30cfd'''  -- These updates(s) must be active.

\qecho Checking database version, 0 rows expected...
SELECT vchk (:require);                      -- Will raise error on failure.
INSERT INTO db(id) VALUES(x:dbversion::INT); -- Make this version active.
-- This update supercedes previous updates.
UPDATE db SET active=FALSE WHERE active AND  -- Deactivate all :require.
LPAD(TO_HEX(id),6,'0') IN (SELECT unnest(string_to_array(:require,',')));

-- Do the update.

  -- The following constraint has always been maintained by the
  -- JMdictDB application code but we make it official from now on:
  -- No approved entry may have a non-NULL dfrm value (i.e. be an
  -- edit of some other entry.)
ALTER TABLE entr    -- Prohibit non-null dfrm value in appr'd entries.
  ADD CONSTRAINT entr_dfrm_check CHECK (dfrm IS NULL OR unap);

  -- These two functions are no longer used.
DROP FUNCTION get_subtree (eid INT);
DROP FUNCTION get_edroot (eid INT);

  -- More generally useful replacements for the get_edroot() and
  -- get_subtree() functions removed above.   See comments in
  -- db/mkviews.sql for details.

CREATE OR REPLACE VIEW edbase AS (
    WITH RECURSIVE sg (id, dfrm, path, cycle) AS (
        SELECT g.id, g.dfrm, ARRAY[g.id], false
          FROM entr g LEFT JOIN entr h ON h.id=g.dfrm
          WHERE g.unap
        UNION ALL
        SELECT g.id, g.dfrm, g.id||path, g.id=ANY(path)
          FROM entr g, sg
          WHERE g.id = sg.dfrm AND NOT cycle)
    SELECT id, path AS path FROM sg WHERE dfrm IS NULL);

CREATE OR REPLACE VIEW edpath AS (
    SELECT id AS root, path FROM edbase e WHERE NOT EXISTS (
        SELECT 1 FROM edbase f
        WHERE e.id=f.id AND f.path@>e.path AND e.path!=f.path));

CREATE OR REPLACE VIEW edpaths AS (
    SELECT e1.id, e2.root, e2.path
        FROM
           (SELECT root, path, unnest(path) AS id
            FROM edpath
            WHERE array_length(path,1)>1) AS e1
        JOIN edpath e2 ON e1.root=e2.root);

COMMIT;
