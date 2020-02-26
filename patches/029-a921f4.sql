\set ON_ERROR_STOP
BEGIN;

-- Treat rdng and kanj "freq" tags as independent.  Formerly we allowed
--  paired tags but that feature was never used and dropping it allows
--  significant code simplications.
-- Cleanup: remove unneccessary views, add missing FK' to table "gloss".
-- Add columns "src" and "seq" to table xresolv.  This supports
--  updates to jelparse/xrslv functions which now produce unresolved
--  xrefs as intermediate step prior to resolving them.
-- Create missing views "vrslv" and helper "vrkrestr" used by
--  xresolv.py.
-- Add new columns 'vseq' and 'vsrc' to table xresolv to allow
--  for unambiguous unresolved xrefs.
-- Swap order of columns 'typ' and 'ord' in table xresolv is order
--  to more closely align with layout of table xref (xresolv.ord and
--  xref.xref serve simlar purposes.)
-- Add a decimal id column to view dbx.

\set dbversion  '''a921f4'''  -- Update version applied by this update.
\set require    '''7256aa'''  -- Database must be at this version in
                              --  order to apply this update.
\qecho Checking database version...
SELECT CASE WHEN (EXISTS (SELECT 1 FROM db WHERE id=x:require::INT)) THEN NULL
    ELSE (SELECT err('Database at wrong update level, need version '||:require)) END;
INSERT INTO db(id) VALUES(x:dbversion::INT);
UPDATE db SET active=FALSE WHERE id!=x:dbversion::INT;


-- Do the update...

CREATE OR REPLACE VIEW dbx AS (
    SELECT LPAD(TO_HEX(id),6,'0') AS id, active, ts, id AS idd
    FROM db
    ORDER BY ts DESC);

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

------------------------------------------------------------------------------
-- Add "vseq" and "vsrc" columns to the xresolv table.
-- We recreate the xresolv table here rather than simply altering the
-- the preexisting one because in addition to adding new "vsrc" and "vseq"
-- columns we are changing the position of the "ord" column and we can't
-- do that by just altering the table.  The position change is to make
-- the columns order align more closely with the xref table since "ord"
-- in xresolv corresponds loosely to the "xref" column in the xref table.

DROP INDEX xresolv_rdng, xresolv_kanj;
ALTER TABLE xresolv
      -- Drop constraints so the names can be reused on the new table...
    DROP CONSTRAINT xresolv_pkey,
    DROP CONSTRAINT xresolv_check,
    DROP CONSTRAINT xresolv_entr_fkey,
    DROP CONSTRAINT xresolv_typ_fkey;
ALTER TABLE xresolv RENAME TO xresolv_;
CREATE TABLE xresolv (
    entr INT NOT NULL,          -- Entry xref occurs in.
    sens SMALLINT NOT NULL,     -- Sense number xref occurs in.
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens)
        ON DELETE CASCADE ON UPDATE CASCADE,
    ord SMALLINT NOT NULL,      -- Order of xref in sense.
    typ SMALLINT NOT NULL       -- Type of xref (table kwxref).
      REFERENCES kwxref(id),
    rtxt VARCHAR(250),          -- Reading text of target given in xref.
    ktxt VARCHAR(250),          -- Kanji text of target given in xref.
    tsens SMALLINT,             -- Target sense number.
    vsrc SMALLINT,              -- Target corpus restriction.
    vseq BIGINT,                -- Target sequence number.
    notes VARCHAR(250),         -- Notes.
    prio BOOLEAN DEFAULT FALSE, -- True if this is a Tanaka corpus exemplar.
    PRIMARY KEY (entr,sens,ord,typ),
    CHECK (rtxt NOTNULL OR ktxt NOTNULL));
INSERT INTO xresolv (
    SELECT entr,sens,ord,typ,rtxt,ktxt,tsens,NULL,NULL,notes,prio FROM xresolv_);
CREATE INDEX xresolv_rdng ON xresolv(rtxt);
CREATE INDEX xresolv_kanj ON xresolv(ktxt);
DROP TABLE xresolv_;

------------------------------------------------------------------------------
--  The following two new views are used by python/xresolv.py.

CREATE OR REPLACE VIEW vrkrestr AS (
    SELECT e.id,e.src,e.stat,e.unap,
           r.rdng,r.txt AS rtxt,rk.kanj,rk.txt AS ktxt,
           (SELECT COUNT(*) FROM sens s WHERE s.entr=e.id) AS nsens
    FROM entr e
    JOIN rdng r ON r.entr=e.id
    LEFT JOIN
        (SELECT r.entr,r.rdng,k.kanj,k.txt
        FROM rdng r
        LEFT JOIN kanj k ON k.entr=r.entr
        LEFT JOIN restr j ON j.entr=r.entr AND j.rdng=r.rdng AND j.kanj=k.kanj
        WHERE j.rdng IS NULL) AS rk ON rk.entr=r.entr AND rk.rdng=r.rdng);

CREATE OR REPLACE VIEW vrslv AS (
    -- Query for xresolv with both 'rtxt' and 'ktxt'
    SELECT v.seq, v.src, v.stat, v.unap, v.entr, v.sens, v.typ, v.ord,
           v.rtxt, v.ktxt, v.tsens, v.notes, v.prio,
           c.src AS tsrc, c.stat AS tstat, c.unap AS tunap,
           count(*) AS nentr, min(c.id) AS targ,
           c.rdng, c.kanj, FALSE AS nokanji,
           max(c.nsens) AS nsens
    FROM (SELECT z.*,seq,src,stat,unap
          FROM xresolv z JOIN entr e ON e.id=z.entr
          WHERE ktxt IS NOT NULL AND rtxt IS NOT NULL)
          AS v
    LEFT JOIN vrkrestr c ON v.rtxt=c.rtxt AND v.ktxt=c.ktxt AND v.entr!=c.id
    GROUP BY v.seq,v.src,v.stat,v.unap,v.entr,v.sens,v.typ,v.ord,v.rtxt,v.ktxt,
             v.tsens,v.notes,v.prio, c.src,c.stat,c.unap,c.rdng,c.kanj
    UNION

    -- Query for xresolv with only rtxt
    SELECT v.seq, v.src, v.stat, v.unap, v.entr, v.sens, v.typ, v.ord,
           v.rtxt, v.ktxt, v.tsens, v.notes, v.prio,
           c.src AS tsrc, c.stat AS tstat, c.unap AS tunap,
           count(*) AS nentr, min(c.id) AS targ,
           c.rdng, NULL AS kanj, nokanji, max(c.nsens) AS nsens
    FROM
       (SELECT z.*,seq,src,stat,unap
        FROM xresolv z JOIN entr e ON e.id=z.entr
        WHERE ktxt IS NULL AND rtxt IS NOT NULL)
        AS v
    LEFT JOIN
       (SELECT e.id,e.src,e.stat,e.unap,r.txt as rtxt,r.rdng,
                 -- The "not exists..." clause below is true if there
                 -- are no kanj table rows for the entry.
               (NOT EXISTS (SELECT 1 FROM kanj k WHERE k.entr=e.id))
                 -- This cause is true if this reading is tagged <nokanji>.
                 OR j.rdng IS NOT NULL AS nokanji,
               (SELECT count(*) FROM sens s WHERE s.entr=e.id) AS nsens
        FROM entr e JOIN rdng r ON r.entr=e.id
        LEFT JOIN re_nokanji j ON j.id=e.id AND j.rdng=r.rdng)
        AS c ON (v.rtxt=c.rtxt AND v.entr!=c.id)
    GROUP BY v.seq,v.src,v.stat,v.unap,v.entr,v.sens,v.typ,v.ord,v.rtxt,v.ktxt,
             v.tsens,v.notes,v.prio, c.src,c.stat,c.unap,c.rdng,c.nokanji
    UNION

    -- Query for xresolv with only ktxt
    SELECT v.seq, v.src, v.stat, v.unap, v.entr, v.sens, v.typ, v.ord,
           v.rtxt, v.ktxt, v.tsens, v.notes, v.prio,
           c.src AS tsrc, c.stat AS tstat, c.unap AS tunap,
           count(*) AS nentr, min(c.id) AS targ,
           NULL AS rdng, c.kanj, NULL AS nokanji, max(c.nsens) AS nsens
    FROM
       (SELECT z.*,seq,src,stat,unap FROM xresolv z JOIN entr e ON e.id=z.entr
        WHERE rtxt IS NULL AND ktxt IS NOT NULL)
        AS v
    LEFT JOIN
       (SELECT e.id,e.src,e.stat,e.unap,k.txt as ktxt,k.kanj,
               (SELECT count(*) FROM sens s WHERE s.entr=e.id) AS nsens
        FROM entr e JOIN kanj k ON k.entr=e.id)
        AS c ON (v.ktxt=c.ktxt AND v.entr!=c.id)
    GROUP BY v.seq,v.src,v.stat,v.unap,v.entr,v.sens,v.typ,v.ord,v.rtxt,v.ktxt,
             v.tsens,v.notes,v.prio, c.src,c.stat,c.unap,c.kanj);

COMMIT;
