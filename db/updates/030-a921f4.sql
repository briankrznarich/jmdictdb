\set ON_ERROR_STOP
BEGIN;

-- Treat rdng and kanj "freq" tags as independent (db-835781)
-- Also some cleanup: remove unneccessary views, add missing FK'
--  to table "gloss".
-- Create missing views "vrslv" and helper "vrkrestr" used by
--  xresolv.py.

\set dbversion  '''a921f4'''  -- Update version applied by this update.
\set require    '''835781'''  -- Database must be at this version in
                              --  order to apply this update.

\qecho Checking database version...
SELECT CASE WHEN (EXISTS (SELECT 1 FROM db WHERE id=x:require::INT)) THEN NULL
    ELSE (SELECT err('Database at wrong update level, need version '||:require)) END;
INSERT INTO db(id) VALUES(x:dbversion::INT);
UPDATE db SET active=FALSE WHERE id!=x:dbversion::INT;


-- Do the update...

-- Add "vseq" and "vsrc" columns to the xresolv table.
-- We recreate the xresolv table here rather than simply altering the
-- the preexisting one because in addition to adding new "vsrc" and "vseq"
-- columns we are changing the position of the "ord" column and we can't
-- do that by just altering the table.  The position change is to make
-- the columns order align more closely with the xref table since "ord"
-- in xresolv corresponds loosely to the "xref" column in the xref table.

DROP VIEW IF EXISTS vrslv;      -- Dependency of view xresolv.
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

-- Recreate the dropped 'vrslv' view.

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
