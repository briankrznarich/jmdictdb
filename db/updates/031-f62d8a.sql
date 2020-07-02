\set ON_ERROR_STOP
BEGIN;

-- Add new version check function.

\set dbversion  '''f62d8a'''  -- Update version applied by this update.
\set require    '''a921f4'''  -- Database must have these updates(s) active
                              --  in order to apply this update.  Versions
                              --  are comma-separated, eg: '''a921f4,5a660c'''

-- Version check done below because we want to use our new vchk() function
-- to do it!  Since transaction will be rolled back on failure, doing the
-- check after the update change is made, is fine.

-- Do the update...

CREATE OR REPLACE FUNCTION vchk(need text) RETURNS setof VOID AS $$
    DECLARE missing TEXT := '';
    BEGIN
        SELECT string_agg (need_.id, ', ') INTO STRICT missing
          FROM unnest(string_to_array(need,',')) AS need_(id)
          LEFT JOIN (SELECT id FROM dbx WHERE active) AS x
             ON need_.id=x.id WHERE x.id IS NULL;
       IF missing != '' THEN
            RAISE 'Database is missing required update(s): %', missing;
            END IF;
        END;
    $$ LANGUAGE plpgsql;

\qecho Checking database version, 0 rows expected...
SELECT vchk (:require);	                       -- Will raise error on failure.
INSERT INTO db(id) VALUES(x:dbversion::INT);   -- Make this version active.
UPDATE db SET active=FALSE WHERE active AND    -- Deactivate all :require.
  LPAD(TO_HEX(id),6,'0') IN (SELECT unnest(string_to_array(:require,',')));

COMMIT;
