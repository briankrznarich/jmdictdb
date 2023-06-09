-- Copyright (c) 2006-2014,2018 Stuart McGraw
-- SPDX-License-Identifier: GPL-2.0-or-later

-- JMdict schema for Postgresql
-- This script is normally executed by schema.sql.

-- Objects for identifying database version.
---------------------------------------------------------------------------
-- Database version identifier; use a new number whenever a change is
-- made to the schema in pg/mktables.sql that will prevent the changed
-- version from working with not-yet-updated application software.
-- Should be a random 6-digit hexidecimal string.  One way to generate
-- is with:
--   python -c 'import random;print("%06.6x"%random.randint(0,16777215))'
-- If multiple version ids are needed, separate them with commas inside
-- the triple quotes, eg:
--   \set updateids '''8fac2c,e4aa1c'''
-- When changing updateids don't forget to change python/lib/dbver.py to
-- tell the JMdictDB API to expect the new version.

\set updateids '''cda09c'''

-- This is a function for the benefit of psql scripts that can be
-- conditionally called to generate an error in order to stop the
-- the script's execution.  See:
--   http://dba.stackexchange.com/questions/24518/how-to-conditionally-stop-a-psql-script-based-on-a-variable-value

CREATE OR REPLACE FUNCTION err(msg TEXT) RETURNS boolean AS $body$
    BEGIN RAISE '%', msg; END;
    $body$ LANGUAGE plpgsql;

-- Function to check that database has required updates active.
-- Parameter 'need' is a single text string containing a comma-separated
--  list of the update values.  Any that are not active updates in the
--  the "dbx" table will be reported as missing and an error raised.
-- We return SETOF VOID rather than simply VOID because the former returns
--  zero rows whereas the latter returns a single empty row; the former
--  is less noisy.  See:
--  https://www.depesz.com/2011/05/03/tips-n-tricks-return-nothing-from-plpgsql-function/
--   Example: SELECT vchk ('12b5e2,7256aa')

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

-- Database updates table.
-- Changes to the database made subsequent to initial database creation
-- will add additional rows to this table.  The 'id' numbers are chosen
-- randomly.  A new row with a new id number and 'active'=True is added
-- when there is a change to the database schema or static contents (eg
-- tag tables).  The 'active' value indicates that the update is current;
-- rows with active=False are historical information.
-- Usually, the update process will set earlier updates' 'active' values
-- to false.  However, if an update is not dependent on specific earlier
-- updates and does not impose a requirement on the JMdictDB code version
-- (for example, tag table content updates), the update process may leave
-- earlier rows set to active resulting in multiple updates that are active.
-- The update process uses the db table to determine if an update's
-- prerequisite updates have been applied, and the JMdictDB code uses it
-- to determine if the database is at an update version that it understands.
-- View 'dbx' shows the 'id' values in the hex number form used ouside
-- the database and is for convenience.

CREATE TABLE db (
    id INT PRIMARY KEY,
    active BOOLEAN DEFAULT TRUE,
    ts TIMESTAMP DEFAULT NOW());

-- Populate the "db" table using the current database update id number(s)
-- in psql variable ':updateids'.  It is a string containing the id number
-- as a six-digit hexadecimal number or multiple comma-separated hex numbers.
-- The sql below splits them into separate rows and converts them to decimal
-- before insertion.
INSERT INTO db(id) (SELECT (
  'x'||lpad(unnest(string_to_array(:updateids,',')),8,'0'))::BIT(32)::INT);

-- Presents table "db" with hexadecimal id numbers for convenience.
CREATE OR REPLACE VIEW dbx AS (
    SELECT LPAD(TO_HEX(id),6,'0') AS id, active, ts, id AS idd
    FROM db
    ORDER BY ts DESC);
---------------------------------------------------------------------------

-- Tables for static tag data.

CREATE TABLE kwdial (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL UNIQUE,
    descr VARCHAR(255),
    ents JSONB);

CREATE TABLE kwfreq (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL UNIQUE,
    descr VARCHAR(255));

CREATE TABLE kwfld (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL UNIQUE,
    descr VARCHAR(255),
    ents JSONB);

CREATE TABLE kwginf (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL UNIQUE,
    descr VARCHAR(255));

CREATE TABLE kwkinf (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL,
    descr VARCHAR(255),
    ents JSONB);

CREATE TABLE kwlang (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL UNIQUE,
    descr VARCHAR(255));

CREATE TABLE kwmisc (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL,
    descr VARCHAR(255),
    ents JSONB);

CREATE TABLE kwpos (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL UNIQUE,
    descr VARCHAR(255),
    ents JSONB);

CREATE TABLE kwrinf (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL UNIQUE,
    descr VARCHAR(255),
    ents JSONB);

CREATE TABLE kwstat (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL UNIQUE,
    descr VARCHAR(255));

CREATE TABLE kwxref (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL UNIQUE,
    descr VARCHAR(255));

CREATE TABLE kwgrp (
    id SERIAL PRIMARY KEY,
    kw VARCHAR(20) NOT NULL UNIQUE,
    descr VARCHAR(255));

CREATE TABLE kwcinf (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(50) NOT NULL UNIQUE,
    descr VARCHAR(250));

CREATE TABLE rad (
    num SMALLINT NOT NULL,	-- Radical (bushu) number.
    var SMALLINT NOT NULL,	-- Variant number.
      PRIMARY KEY (num,var),
    rchr CHAR(1),		-- Radical character from unicode blocks CJK radicals
                                --   2F00-2FDF and Radicals Supplement 2E80-2EFF.
    chr CHAR(1),		-- Radical character from outside radical blocks.
    strokes SMALLINT,		-- Number of strokes.
    loc	CHAR(1) 		-- Location code.
        CHECK(loc is NULL OR loc IN('O','T','B','R','L','E','V')),
    name VARCHAR(50),		-- Name of radical (japanese).
    examples VARCHAR(20));	-- Characters that include the radical.

CREATE TABLE kwsrct (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL UNIQUE,
    descr VARCHAR(255));

-- The tables that contain corpora entry data are defined in a
-- separate file since they created both by this file when creating
-- a new JMdictDB database, and by imptabs.sql when creating a
-- separate schema for use during bulk loading.

\ir entrobjs.sql

-- The following functions are used in the main database but are not
-- needed in the import schema and so are defined only here.

CREATE OR REPLACE FUNCTION kwsrc_updseq() RETURNS trigger AS $kwsrc_updseq$
    -- Create a sequence for entr.seq numbers whenever a new
    -- row is added to table 'kwsrc' (and delete it when row
    -- is deleted).  This allows every corpus to maintain its
    -- own sequence.  The sequence is *not* made default value
    -- of entr.seq (because there multiple sequences are used
    -- depending on entr.src); the API is responsible for choosing
    -- and using the correct sequence.

    DECLARE seqnm VARCHAR; newseq VARCHAR := ''; oldseq VARCHAR := '';
        partinc VARCHAR := ''; partmin VARCHAR := ''; partmax VARCHAR := '';
        usedcnt INT;
    BEGIN
        IF TG_OP != 'DELETE' THEN newseq=NEW.seq; END IF;
        IF TG_OP != 'INSERT' THEN oldseq=OLD.seq; END IF;
        IF oldseq != '' THEN
            -- 'kwsrc' row was deleted or updated.  Drop the deleted sequence
            -- if not used in any other rows.
            SELECT INTO usedcnt COUNT(*) FROM kwsrc WHERE seq=oldseq;
            IF usedcnt = 0 THEN
                EXECUTE 'DROP SEQUENCE IF EXISTS '||oldseq;
                END IF;
        ELSEIF newseq != '' THEN
            -- 'kwsrc' row was inserted or updated.  See if sequence 'newseq'
            -- already exists, and if so, do nothing.  If not, create it.
            IF NEW.sinc IS NOT NULL THEN
                partinc = ' INCREMENT ' || NEW.sinc;
                END IF;
            IF NEW.smin IS NOT NULL THEN
                partmin = ' MINVALUE ' || NEW.smin;
                END IF;
            IF NEW.smax IS NOT NULL THEN
                partmax = ' MAXVALUE ' || NEW.smax;
                END IF;
            IF NOT EXISTS (SELECT relname FROM pg_class WHERE relname=NEW.seq AND relkind='S') THEN
                EXECUTE 'CREATE SEQUENCE '||newseq||partinc||partmin||partmax||' NO CYCLE';
                END IF;
            END IF;
        RETURN NEW;
        END;
    $kwsrc_updseq$ LANGUAGE plpgsql;

CREATE TRIGGER kwsrc_updseq AFTER INSERT OR UPDATE OR DELETE ON kwsrc
    FOR EACH ROW EXECUTE PROCEDURE kwsrc_updseq();

CREATE OR REPLACE FUNCTION syncseq() RETURNS VOID AS $syncseq$
    -- Syncronises all the sequences specified in table 'kwsrc'
    -- (which are used for generation of corpus specific seq numbers.)
    DECLARE cur REFCURSOR; seqname VARCHAR; maxseq BIGINT;
    BEGIN
        -- The following cursor gets the max value of entr.seq for each corpus
        -- for entr.seq values within the range of the associated seq (where
        -- the range is what was given in kwsrc table .smin and .smax values.
        -- [Don't confuse kwsrc.seq (name of the Postgresq1 sequence that
        -- generates values used for entry seq numbers) with entr.seq (the
        -- entry sequence numbers themselves).]  Since the kwsrc.smin and
        -- .smax values can be changed after the sequence was created, and
        -- doing so may screwup the operation herein, don't do that!  It is
        -- also possible that multiple kwsrc's can share a common 'seq' value,
        -- but have different 'smin' and 'smax' values -- again, don't do that!
        -- The rather elaborate join below is done to make sure we get a row
        -- for every kwsrc.seq value, even if there are no entries that
        -- reference that kwsrc row.

        OPEN cur FOR
            SELECT ks.sqname, COALESCE(ke.mxseq,ks.smin,1)
            FROM
                (SELECT seq AS sqname, MIN(smin) AS smin
                FROM kwsrc
                GROUP BY seq) AS ks
            LEFT JOIN	-- Find the max entr.seq number in use, but ignoring
                        -- any that are autside the min/max bounds of the kwsrc's
                        -- sequence.
                (SELECT k.seq AS sqname, MAX(e.seq) AS mxseq
                FROM entr e
                JOIN kwsrc k ON k.id=e.src
                WHERE e.seq BETWEEN COALESCE(k.smin,1)
                    AND COALESCE(k.smax,9223372036854775807)
                GROUP BY k.seq,k.smin) AS ke
            ON ke.sqname=ks.sqname;
        LOOP
            FETCH cur INTO seqname, maxseq;
            EXIT WHEN NOT FOUND;
            EXECUTE 'SELECT setval(''' || seqname || ''', ' || maxseq || ')';
            END LOOP;
        END;
    $syncseq$ LANGUAGE plpgsql;

CREATE FUNCTION entr_seqdef() RETURNS trigger AS $entr_seqdef$
    -- This function is used as an "insert" trigger on table
    -- 'entr'.  It checks the 'seq' field value and if NULL,
    -- provides a default value from one of several sequences,
    -- with the sequence used determined by the value if the
    -- new row's 'src' field.  The name of the sequence to be
    -- used is given in the 'seq' column of table 'kwsrc'.

    DECLARE seqnm VARCHAR;
    BEGIN
        IF NEW.seq IS NOT NULL THEN
            RETURN NEW;
            END IF;
        SELECT seq INTO seqnm FROM kwsrc WHERE id=NEW.src;
        NEW.seq :=  NEXTVAL(seqnm);
        RETURN NEW;
        END;
    $entr_seqdef$ LANGUAGE plpgsql;

CREATE TRIGGER entr_seqdef BEFORE INSERT ON entr
    FOR EACH ROW EXECUTE PROCEDURE entr_seqdef();

-------------------------------
-- Tables for audio sound clips
-------------------------------

CREATE TABLE sndvol (	-- Audio media volume (directory, CD, etc)
    id SERIAL PRIMARY KEY,		-- Volume id.
    title VARCHAR(50),			-- Volume title (for display).
    loc VARCHAR(500),			-- Volume location (directory name or CD id).
    type SMALLINT NOT NULL,		-- Volume type, 1:file, 2:cd
    idstr VARCHAR(100),			-- If type==2, this is CD ID string.
    corp INT 				-- Corpus id (in table kwsrc).
      REFERENCES kwsrc(id) ON UPDATE CASCADE ON DELETE CASCADE,
    notes TEXT);			-- Ad hoc notes pertinent to this sound volume.
-- Anticipate this table will generally be too small to benefit from indexes.

CREATE TABLE sndfile (	-- Audio file, track, etc.
    id SERIAL PRIMARY KEY,		-- File id.
    vol INT NOT NULL 			-- Volume id (in table sndvol).
      REFERENCES sndvol(id) ON UPDATE CASCADE ON DELETE CASCADE,
    title VARCHAR(50),			-- File title (for display).
    loc VARCHAR(500),			-- File location in vol (filename or track number).
    type SMALLINT,			-- File type.
    notes TEXT);			-- Ad hoc notes pertinent to this sound file.
CREATE INDEX ON sndfile(vol);

CREATE TABLE snd (	-- Audio sound clip.
    id SERIAL PRIMARY KEY,		-- Sound id.
    file SMALLINT NOT NULL 		-- File id (in table sndfile).
      REFERENCES sndfile(id) ON UPDATE CASCADE ON DELETE CASCADE,
    strt INT NOT NULL DEFAULT(0),	-- Start of clip in file (10ms units).
    leng INT NOT NULL DEFAULT(0),	-- Length of clip in file (10ms units).
    trns TEXT,				-- Transcription of sound clip (typ. japanese).
    notes VARCHAR(255));		-- Ad hoc notes pertinent to this clip.

CREATE TABLE entrsnd (	-- Entry to sound clip map.
    entr INT NOT NULL		-- Entry id.
      REFERENCES entr(id) ON UPDATE CASCADE ON DELETE CASCADE,
    ord SMALLINT NOT NULL,	-- Order in entry.
    snd INT NOT NULL 		-- Sound id.
      REFERENCES snd(id) ON UPDATE CASCADE ON DELETE CASCADE,
      PRIMARY KEY (entr,snd));
CREATE INDEX ON entrsnd(snd);

CREATE TABLE rdngsnd (	-- Reading to sound clip map.
    entr INT NOT NULL,		-- Entry id.
    rdng INT NOT NULL,		-- Reading number.
      FOREIGN KEY(entr,rdng) REFERENCES rdng(entr,rdng) ON UPDATE CASCADE ON DELETE CASCADE,
    ord SMALLINT NOT NULL,	-- Order in reading.
    snd INT NOT NULL 		-- Sound id.
      REFERENCES snd(id) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (entr,rdng,snd));
CREATE INDEX rdngsnd_snd ON rdngsnd(snd);


-- The following tables are used for resolving textual xrefs to
-- actual entries and senses when loading data from external files.
-- See file pg/xresolv.sql for a description of the process.

---------------------------------------------
--  Verb/adjective/copula conjugation tables
---------------------------------------------

DROP TABLE IF EXISTS conjo_notes, conotes, conjo, conj CASCADE;

-- Notes for conj, conjo items.
CREATE TABLE conotes (
    id INT PRIMARY KEY,
    txt TEXT NOT NULL);

-- Verb and adjective inflection names.
CREATE TABLE conj (
    id SMALLINT PRIMARY KEY,
    name VARCHAR(50) UNIQUE);             -- Eg, "present", "past", "conditional", provisional", etc.

-- Okurigana used for for each verb inflection type.
CREATE TABLE conjo (
    pos SMALLINT NOT NULL                 -- Part-of-speech id from 'kwpos'.
      REFERENCES kwpos(id) ON UPDATE CASCADE,
    conj SMALLINT NOT NULL                -- Conjugation id from 'conj'.
      REFERENCES conj(id) ON UPDATE CASCADE,
    neg BOOLEAN NOT NULL DEFAULT FALSE,   -- Negative form.
    fml BOOLEAN NOT NULL DEFAULT FALSE,   -- Formal (aka distal) form.
    onum SMALLINT NOT NULL DEFAULT 1,     -- Okurigana variant id when more than one exists.
      PRIMARY KEY (pos,conj,neg,fml,onum),
    stem SMALLINT DEFAULT 1,              -- Number of chars to remove to get stem.
    okuri VARCHAR(50) NOT NULL,           -- Okurigana text.
    euphr VARCHAR(50) DEFAULT NULL,       -- Kana for euphonic change in stem (する and 来る).
    euphk VARCHAR(50) DEFAULT NULL,       -- Kanji for change in stem (used only for 為る-＞出来る).
    pos2 SMALLINT DEFAULT NULL            -- Part-of-speech (kwpos id) of word after conjugation.
      REFERENCES kwpos(id) ON UPDATE CASCADE);

-- Notes that apply to a particular conjugation.
CREATE TABLE conjo_notes (
    pos SMALLINT NOT NULL,  ---.
    conj SMALLINT NOT NULL, --  \
    neg BOOLEAN NOT NULL,   --   +--- Primary key of table 'conjo'.
    fml BOOLEAN NOT NULL,   --  /
    onum SMALLINT NOT NULL, ---'
      FOREIGN KEY (pos,conj,neg,fml,onum) REFERENCES conjo(pos,conj,neg,fml,onum) ON UPDATE CASCADE,
    note SMALLINT NOT NULL
      REFERENCES conotes(id) ON UPDATE CASCADE,
    PRIMARY KEY (pos,conj,neg,fml,onum,note));
