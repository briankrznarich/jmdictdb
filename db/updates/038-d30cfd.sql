\set ON_ERROR_STOP
BEGIN;

-- Tag updates per jwb 2021-06-04

\set dbversion  '''d30cfd'''  -- New version supplied by this update.
  -- Some of the updates here are to tags added in db update e4aa1c, hence
  -- that requirement.  Update 46354d is not technically needed here but we
  -- require it so that updates subsequent to this one need only require
  -- this one.
\set require    '''8fac2c,e4aa1c,46354d''' -- These updates(s) must be active.

\qecho Checking database version, 0 rows expected...
SELECT vchk (:require);	                       -- Will raise error on failure.
INSERT INTO db(id) VALUES(x:dbversion::INT);   -- Make this version active.
-- This update replaces the previous updates.
UPDATE db SET active=FALSE WHERE active AND    -- Deactivate all :require.
  LPAD(TO_HEX(id),6,'0') IN (SELECT unnest(string_to_array(:require,',')));

-- Do the update.

INSERT INTO kwdial VALUES(13,'bra','Brazilian',NULL);
INSERT INTO kwfld VALUES(70,'rail','railway',NULL);
INSERT INTO kwfld VALUES(71,'psy','psychiatry',NULL);
INSERT INTO kwfld VALUES(72,'cloth','clothing',NULL);
UPDATE kwfld SET descr='architecture' WHERE id=11;
UPDATE kwfld SET descr='meteorology' WHERE id=38;
UPDATE kwfld SET descr='psychology' WHERE id=42;
UPDATE kwfld SET descr='horse racing' WHERE id=54;
UPDATE kwfld SET descr='audiovisual' WHERE id=67;
UPDATE kwfld SET descr='video games' WHERE id=68;
INSERT INTO kwginf VALUES(5,'tm','trademark');
INSERT INTO kwkinf VALUES(6,'rK','rarely-used kanji form',NULL);
UPDATE kwkinf SET descr='word containing out-dated kanji or kanji usage' WHERE id=3;
INSERT INTO kwmisc VALUES(178,'doc','document','{"jmnedict": 1}');
INSERT INTO kwmisc VALUES(179,'group','group','{"jmnedict": 1}');
UPDATE kwmisc SET kw='form',descr='formal or literary term' WHERE id=88;

COMMIT;
