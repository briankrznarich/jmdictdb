\set ON_ERROR_STOP
BEGIN;

-- Add new kwfld value "Christn".

\set dbversion  '''12b5e2'''  -- Update version applied by this update.
\set require    '''1ef804'''  -- Database must be at this version in
                              --  order to apply this update.

\qecho Checking database version...
SELECT CASE WHEN (EXISTS (SELECT 1 FROM db WHERE id=x:require::INT)) THEN NULL
    ELSE (SELECT err('Database at wrong update level, need version '||:require)) END;
INSERT INTO db(id) VALUES(x:dbversion::INT);
UPDATE db SET active=FALSE WHERE id!=x:dbversion::INT;


-- Do the update

INSERT INTO kwfld VALUES(31,'Christn','Christian term');

COMMIT;
