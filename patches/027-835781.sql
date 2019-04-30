\set ON_ERROR_STOP
BEGIN;

-- Treat rdng and kanj "freq" tags as independent (db-835781)
-- Also some cleanup: remove unneccessary views, add missing FK'
--  to table "gloss".

\set dbversion  '''835781'''  -- Update version applied by this update.
\set require    '''1ef804'''  -- Database must be at this version in
                              --  order to apply this update.

\qecho Checking database version...
SELECT CASE WHEN (EXISTS (SELECT 1 FROM db WHERE id=x:require::INT)) THEN NULL
    ELSE (SELECT err('Database at wrong update level, need version '||:require)) END;
INSERT INTO db(id) VALUES(x:dbversion::INT);
UPDATE db SET active=FALSE WHERE id!=x:dbversion::INT;


-- Do the update...

DROP TABLE IF EXISTS freq_tmp;
CREATE TABLE freq_tmp AS SELECT * FROM freq;

DROP VIEW IF EXISTS pkfreq, prfreq, vt_entr, vt_entr3, esum, is_p;
DROP TABLE freq;
CREATE TABLE freq (
    entr INT NOT NULL,
    rdng SMALLINT NULL,
      FOREIGN KEY (entr,rdng) REFERENCES rdng(entr,rdng)
        ON DELETE CASCADE ON UPDATE CASCADE,
    kanj SMALLINT NULL,
      FOREIGN KEY (entr,kanj) REFERENCES kanj(entr,kanj)
        ON DELETE CASCADE ON UPDATE CASCADE,
    kw SMALLINT NOT NULL
      REFERENCES kwfreq(id),
    value INT,
        -- Make sure either rdng or kanj is present but not both.
      CHECK (rdng NOTNULL != (kanj NOTNULL)),
      -- Note that in an index NULLs are always considered not equal so that
      -- a single UNIQUE index on all 5 columns will still allow insertion
      -- of duplicate rows since either 'rdng' or 'kanj' will be NULL and
      -- thus always be considered different than any present rows.
      -- Also we want to allow multiple freq values with the same scale on
      -- the same rdng/kanj: eg both nf11 and nf21 on the same kanji.  Such
      -- values occur in JMdict entries as a result kanji-reading pairs where
      -- the pair may have a different value than just the reading or kanji
      -- by itself.
    UNIQUE (entr,kanj,kw,value),
    UNIQUE (entr,rdng,kw,value));

-- Recreate dropped dependent view.
CREATE OR REPLACE VIEW is_p AS (
    SELECT e.*,
        EXISTS (
            SELECT * FROM freq f
            WHERE f.entr=e.id
              -- ichi1, gai1, news1, or specX
              AND ((f.kw IN (1,2,7) AND f.value=1)
                OR f.kw=4)) AS p
    FROM entr e);

-- Recreate dropped dependent view.
CREATE OR REPLACE VIEW esum AS (
    SELECT e.id,e.seq,e.stat,e.src,e.dfrm,e.unap,e.notes,e.srcnote,
        h.rtxt AS rdng,
        h.ktxt AS kanj,
        (SELECT ARRAY_TO_STRING(ARRAY_AGG( ss.gtxt ), ' / ')
         FROM
            (SELECT
                (SELECT ARRAY_TO_STRING(ARRAY_AGG(sg.txt), '; ')
                FROM (
                    SELECT g.txt
                    FROM gloss g
                    WHERE g.sens=s.sens AND g.entr=s.entr
                    ORDER BY g.gloss) AS sg
                ORDER BY entr,sens) AS gtxt
            FROM sens s WHERE s.entr=e.id ORDER BY s.sens) AS ss) AS gloss,
        (SELECT COUNT(*) FROM sens WHERE sens.entr=e.id) AS nsens,
        (SELECT p FROM is_p WHERE is_p.id=e.id) AS p
    FROM entr e
    JOIN hdwds h on h.id=e.id);

INSERT INTO freq(entr,rdng,kanj,kw,value)
    (SELECT entr,rdng,NULL,kw,value FROM freq_tmp
     WHERE rdng IS NOT NULL GROUP BY entr,rdng,kw,value);
INSERT INTO freq(entr,rdng,kanj,kw,value)
    (SELECT entr,NULL,kanj,kw,value FROM freq_tmp
     WHERE kanj IS NOT NULL GROUP BY entr,kanj,kw,value);
DROP TABLE freq_tmp;

ALTER TABLE gloss ADD FOREIGN KEY (ginf) REFERENCES kwginf(id);

COMMIT;
