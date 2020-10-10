\set ON_ERROR_STOP
BEGIN;

-- Update existing, and create new, field tags.
-- These changes are from Jim Breen @edrdg.org verbatim.

\set dbversion  '''e4aa1c'''  -- Additional version applied by this update.
\set require    '''8fac2c'''  -- These updates(s) must be active.

\qecho Checking database version, 0 rows expected...
SELECT vchk (:require);	                       -- Will raise error on failure.
INSERT INTO db(id) VALUES(x:dbversion::INT);   -- Make this version active.
-- This update is auxiliary to the existing 8fac2c database update
-- version so don't deactivate that version.
--UPDATE db SET active=FALSE WHERE active AND    -- Deactivate all :require.
--  LPAD(TO_HEX(id),6,'0') IN (SELECT unnest(string_to_array(:require,',')));

-- Do the update.

-- Update existing tag descriptions.
UPDATE kwfld SET descr='Buddhism' WHERE id=1;
UPDATE kwfld SET descr='computing' WHERE id=2;
UPDATE kwfld SET descr='food, cooking' WHERE id=3;
UPDATE kwfld SET descr='geometry' WHERE id=4;
UPDATE kwfld SET descr='linguistics' WHERE id=5;
UPDATE kwfld SET descr='martial arts' WHERE id=6;
UPDATE kwfld SET descr='mathematics' WHERE id=7;
UPDATE kwfld SET descr='military' WHERE id=8;
UPDATE kwfld SET descr='physics' WHERE id=9;
UPDATE kwfld SET descr='chemistry' WHERE id=10;
UPDATE kwfld SET descr='architecture, building' WHERE id=11;
UPDATE kwfld SET descr='astronomy' WHERE id=12;
UPDATE kwfld SET descr='baseball' WHERE id=13;
UPDATE kwfld SET descr='biology' WHERE id=14;
UPDATE kwfld SET descr='botany' WHERE id=15;
UPDATE kwfld SET descr='business' WHERE id=16;
UPDATE kwfld SET descr='economics' WHERE id=17;
UPDATE kwfld SET descr='engineering' WHERE id=18;
UPDATE kwfld SET descr='finance' WHERE id=19;
UPDATE kwfld SET descr='geology' WHERE id=20;
UPDATE kwfld SET descr='law' WHERE id=21;
UPDATE kwfld SET descr='medicine' WHERE id=22;
UPDATE kwfld SET descr='music' WHERE id=23;
UPDATE kwfld SET descr='Shinto' WHERE id=24;
UPDATE kwfld SET descr='sports' WHERE id=25;
UPDATE kwfld SET descr='sumo' WHERE id=26;
UPDATE kwfld SET descr='zoology' WHERE id=27;
UPDATE kwfld SET descr='anatomy' WHERE id=28;
UPDATE kwfld SET descr='mahjong' WHERE id=29;
UPDATE kwfld SET descr='shogi' WHERE id=30;
UPDATE kwfld SET descr='Christianity' WHERE id=31;

-- Add new tags.
INSERT INTO kwfld VALUES(32,'phil','philosophy');
INSERT INTO kwfld VALUES(33,'physiol','physiology');
INSERT INTO kwfld VALUES(34,'pharm','pharmacy');
INSERT INTO kwfld VALUES(35,'elec','electricity, elec. eng.');
INSERT INTO kwfld VALUES(36,'ent','entomology');
INSERT INTO kwfld VALUES(37,'biochem','biochemistry');
INSERT INTO kwfld VALUES(38,'met','climate, weather');
INSERT INTO kwfld VALUES(39,'tradem','trademark');
INSERT INTO kwfld VALUES(40,'gramm','grammar');
INSERT INTO kwfld VALUES(41,'electr','electronics');
INSERT INTO kwfld VALUES(42,'psych','psychology, psychiatry');
INSERT INTO kwfld VALUES(43,'photo','photography');
INSERT INTO kwfld VALUES(44,'grmyth','Greek mythology');
INSERT INTO kwfld VALUES(45,'archeol','archeology');
INSERT INTO kwfld VALUES(46,'logic','logic');
INSERT INTO kwfld VALUES(47,'golf','golf');
INSERT INTO kwfld VALUES(48,'cryst','crystallography');
INSERT INTO kwfld VALUES(49,'pathol','pathology');
INSERT INTO kwfld VALUES(50,'paleo','paleontology');
INSERT INTO kwfld VALUES(51,'ecol','ecology');
INSERT INTO kwfld VALUES(52,'art','art, aesthetics');
INSERT INTO kwfld VALUES(53,'genet','genetics');
INSERT INTO kwfld VALUES(54,'horse','horse-racing');
INSERT INTO kwfld VALUES(55,'embryo','embryology');
INSERT INTO kwfld VALUES(56,'geogr','geography');
INSERT INTO kwfld VALUES(57,'fish','fishing');
INSERT INTO kwfld VALUES(58,'gardn','gardening, horticulture');
INSERT INTO kwfld VALUES(59,'telec','telecommunications');
INSERT INTO kwfld VALUES(60,'mech','mechanical engineering');
INSERT INTO kwfld VALUES(61,'aviat','aviation');
INSERT INTO kwfld VALUES(62,'stat','statistics');
INSERT INTO kwfld VALUES(63,'agric','agriculture');
INSERT INTO kwfld VALUES(64,'print','printing');
INSERT INTO kwfld VALUES(65,'go','go (game)');
INSERT INTO kwfld VALUES(66,'hanaf','hanafuda');

COMMIT;
