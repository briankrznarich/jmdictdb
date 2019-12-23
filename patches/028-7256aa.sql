\set ON_ERROR_STOP
BEGIN;

-- Add new kwmisc values "net-sl", "dated", "hist", "lit".
-- Change kwpos value "cop-da" to "cop".

\set dbversion  '''7256aa'''  -- Update version applied by this update.
\set require    '''12b5e2'''  -- Database must be at this version in
                              --  order to apply this update.

\qecho Checking database version...
SELECT CASE WHEN (EXISTS (SELECT 1 FROM db WHERE id=x:require::INT)) THEN NULL 
    ELSE (SELECT err('Database at wrong update level, need version '||:require)) END;
INSERT INTO db(id) VALUES(x:dbversion::INT);
UPDATE db SET active=FALSE WHERE id!=x:dbversion::INT;


-- Do the update

INSERT INTO kwmisc VALUES(85,'net-sl','Internet slang');
INSERT INTO kwmisc VALUES(86,'dated','dated term');
INSERT INTO kwmisc VALUES(87,'hist','historical term');
INSERT INTO kwmisc VALUES(88,'lit','literary or formal term');
UPDATE kwpos SET kw='cop' WHERE id=15;

COMMIT;
