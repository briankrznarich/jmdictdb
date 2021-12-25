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
