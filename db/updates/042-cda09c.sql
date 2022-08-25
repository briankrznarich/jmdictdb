\set ON_ERROR_STOP
BEGIN;

-- Accumulated (2021-06-04 to 2022-08-23) tag updates from edrdg.org.
-- This script will update a JMdictDB database's kw* (aka tag) tables
-- to match those used currently at edrdg.org.  The last JMdictDB tag
-- update was in 038-d30cfd.sql.
-- This script will not update or insert any conflicting data in the
-- tables but will not fail if such data exists; the script's message
-- output should be examined for INSERTs or UPDATEs that report 0 rows
-- updated rather than 1.  Except for the db version check this script
-- is idempotent and can be run multiple times if the expected version
-- number is restored first.
-- These updates were derived by exporting the current kw* tables from
-- the edrdg.org jmdict database as csv files (using the tools/kwcmp.py
-- program), then diffing those against the current jmdictdb/data/kw*.csv
-- files.
-- The tag updates at edrdg.org are documented at:
--   https://github.com/JMdictProject/JMdictIssues/issues/68

\set dbversion  '''cda09c'''  -- New version supplied by this update.
\set require    '''b5d00f'''  -- These updates(s) must be active.

\qecho Checking database version, 0 rows expected...
SELECT vchk (:require);                      -- Will raise error on failure.
INSERT INTO db(id) VALUES(x:dbversion::INT); -- Make this version active.
-- This update supercedes previous updates.
UPDATE db SET active=FALSE WHERE active AND  -- Deactivate all :require.
LPAD(TO_HEX(id),6,'0') IN (SELECT unnest(string_to_array(:require,',')));

-- Do the update.

-- FLD tags...
UPDATE kwfld SET descr='pharmacology' WHERE id=34 AND kw='pharm' AND descr='pharmacy';
INSERT INTO kwfld VALUES(73,'manga','manga',NULL) ON CONFLICT DO NOTHING;
INSERT INTO kwfld VALUES(74,'dent','dentistry',NULL) ON CONFLICT DO NOTHING;
INSERT INTO kwfld VALUES(75,'cards','card games',NULL) ON CONFLICT DO NOTHING;
INSERT INTO kwfld VALUES(76,'mining','mining',NULL) ON CONFLICT DO NOTHING;
INSERT INTO kwfld VALUES(77,'kabuki','kabuki',NULL) ON CONFLICT DO NOTHING;
INSERT INTO kwfld VALUES(78,'noh','noh',NULL) ON CONFLICT DO NOTHING;
INSERT INTO kwfld VALUES(79,'politics','politics',NULL) ON CONFLICT DO NOTHING;
INSERT INTO kwfld VALUES(80,'stockm','stock market',NULL) ON CONFLICT DO NOTHING;
INSERT INTO kwfld VALUES(81,'ski','skiing',NULL) ON CONFLICT DO NOTHING;
INSERT INTO kwfld VALUES(82,'rommyth','Roman mythology',NULL) ON CONFLICT DO NOTHING;
INSERT INTO kwfld VALUES(83,'psyanal','psychoanalysis',NULL) ON CONFLICT DO NOTHING;
INSERT INTO kwfld VALUES(84,'film','film',NULL) ON CONFLICT DO NOTHING;
INSERT INTO kwfld VALUES(85,'tv','television',NULL) ON CONFLICT DO NOTHING;

-- KINF tags...
INSERT INTO kwkinf VALUES(7,'sK','search-only kanji form',NULL) ON CONFLICT DO NOTHING;

-- MISC tags...
UPDATE kwmisc SET descr='archaic' WHERE id=3 AND kw='arch' AND descr='archaism';
UPDATE kwmisc SET descr='colloquial' WHERE id=5 AND kw='col' AND descr='colloquialism';
UPDATE kwmisc SET kw='rare',descr='rare term' WHERE id=18 AND kw='obsc' AND descr='obscure term';
DELETE FROM kwmisc WHERE id=20 AND kw='rare' AND descr='rare';
INSERT INTO kwmisc VALUES(29,'euph','euphemistic',NULL) ON CONFLICT DO NOTHING;
INSERT INTO kwmisc VALUES(193,'ship','ship name','{"jmnedict":1}') ON CONFLICT DO NOTHING;

-- RINF tags...
UPDATE kwrinf SET kw='sk',descr='search-only kana form' WHERE id=4 AND kw='uK' AND descr='word usually written using kanji alone';

COMMIT;
