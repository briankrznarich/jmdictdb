-- Copyright (c) 2006-2019 Stuart McGraw
-- SPDX-License-Identifier: GPL-2.0-or-later

-- Create the views needed by JMdictDB.
-- This script is normally executed by schema.sql.

\set ON_ERROR_STOP
BEGIN;

-------------------------------------------------------------
-- The first kanji and reading in an entry are significant
-- because jmdict xml and some other apps use them as
-- entry "headwords" that identify the entry.  (Unfortunately
-- they are not necessarily unique, especially for reading-
-- only words.)
-- This view provide's the first reading and (if there is
-- one) first kanji for each entry.
-------------------------------------------------------------
CREATE OR REPLACE VIEW hdwds AS (
    SELECT e.*,r.txt AS rtxt,k.txt AS ktxt
    FROM entr e
    LEFT JOIN rdng r ON r.entr=e.id
    LEFT JOIN kanj k ON k.entr=e.id
    WHERE (r.rdng=1 OR r.rdng IS NULL)
      AND (k.kanj=1 OR k.kanj IS NULL));

-------------------------------------------------------------
-- View "is_p" returns each row in table "entr" with an
-- additional boolean column, "p" that if true indicates
-- the entry meets the wwwjdic criteria for a "P" marking:
-- has a reading or a kanji with a freq tag of "ichi1",
-- "gai1", "news1" or "spec<anything>" as documented at
--   http://www.csse.monash.edu.au/~jwb/edict_doc.html#IREF05
-- (That ref specifies only "spec1" but per IS-149, "spec2"
-- is also included.)
-- See also views pkfreq and prfreq below.
-------------------------------------------------------------
CREATE OR REPLACE VIEW is_p AS (
    SELECT e.*,
        EXISTS (
            SELECT * FROM freq f
            WHERE f.entr=e.id
              -- ichi1, gai1, news1, or specX
              AND ((f.kw IN (1,2,7) AND f.value=1)
                OR f.kw=4)) AS p
    FROM entr e);

-----------------------------------------------------------
-- Summarize each entry (one per row) with readings, kanji,
-- and sense/gloss.  The rdng and kanj columns contain the
-- entry's single "headword" items (as given by view hdwds)
-- The sense column contain gloss strings in contatented
-- with ';', and grouped into senses concatenated with "/".
-----------------------------------------------------------
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

-----------------------------------------------------------
-- Provide a pseudo-sens table with an additional column
-- "txt" that contains an aggregation of all the glosses
-- for that sense concatenated into a single string with
-- each gloss delimited with the string "; ".
--
-- DEPRECATED: use vt_sens* in mkviews2 instead.  Note
--  that that view may need to be used in an outer join
--  unlike this view.
------------------------------------------------------------
CREATE OR REPLACE VIEW ssum AS (
    SELECT s.entr,s.sens,
       (SELECT ARRAY_TO_STRING(ARRAY_AGG(sg.txt), '; ')
        FROM (
            SELECT g.txt
            FROM gloss g
            WHERE g.sens=s.sens AND g.entr=s.entr
            ORDER BY g.gloss) AS sg
        ORDER BY entr,sens) AS gloss,
        s.notes
    FROM sens s);

-----------------------------------------------------------
-- Provide a pseudo-sens table with additional columns
-- "txt" (contains an aggregation of all the glosses
-- for that sense concatenated into a single string with
-- each gloss delimited with the string "; "), "rdng"
-- (similarly has concatenated readings of the entry
-- to which this sense belongs), "kanj" (similarly has
-- concatenated readings of the entry to which this sense
-- belongs).
------------------------------------------------------------

CREATE OR REPLACE VIEW essum AS (
    SELECT e.id, e.seq, e.src, e.stat,
            s.sens,
            h.rtxt as rdng,
            h.ktxt as kanj,
            s.gloss,
           (SELECT COUNT(*) FROM sens WHERE sens.entr=e.id) AS nsens
        FROM entr e
        JOIN hdwds h ON h.id=e.id
        JOIN ssum s ON s.entr=e.id);

---------------------------------------------------------
-- For every entry, give the number of associated reading,
-- kanji, and sense items.
----------------------------------------------------------
CREATE OR REPLACE VIEW item_cnts AS (
    SELECT
        e.id,e.seq,
        (SELECT COUNT(*) FROM rdng r WHERE r.entr=e.id) as nrdng,
        (SELECT COUNT(*) FROM kanj k WHERE k.entr=e.id) as nkanj,
        (SELECT COUNT(*) FROM sens s WHERE s.entr=e.id) as nsens
    FROM entr e);

------------------------------------------------------------
-- For every entry, give all the combinations of reading and
-- kanji, and an indicator whether of not that combination
-- is valid ('X' in column 'valid' means invalid).
------------------------------------------------------------
CREATE OR REPLACE VIEW rk_validity AS (
    SELECT e.id AS id,e.seq AS seq,
        r.rdng AS rdng,r.txt AS rtxt,k.kanj AS kanj,k.txt AS ktxt,
        CASE WHEN z.kanj IS NOT NULL THEN 'X' END AS valid
    FROM ((entr e
    LEFT JOIN rdng r ON r.entr=e.id)
    LEFT JOIN kanj k ON k.entr=e.id)
    LEFT JOIN restr z ON z.entr=e.id AND r.rdng=z.rdng AND k.kanj=z.kanj);

------------------------------------------------------------
-- List all readings that should be marked "re_nokanji"
-- in jmdict.xml.
------------------------------------------------------------
CREATE OR REPLACE VIEW re_nokanji AS (
    SELECT e.id,e.seq,r.rdng,r.txt
    FROM entr e
    JOIN rdng r ON r.entr=e.id
    JOIN restr z ON z.entr=r.entr AND z.rdng=r.rdng
    GROUP BY e.id,e.seq,r.rdng,r.txt
    HAVING COUNT(z.kanj)=(SELECT COUNT(*) FROM kanj k WHERE k.entr=e.id));

-------------------------------------------------------------
-- For every reading in every entry, provide only the valid
-- kanji as determined by restr if applicable, and taking
-- the jmdict's re_nokanji information into account.
-------------------------------------------------------------
CREATE OR REPLACE VIEW rk_valid AS (
    SELECT r.entr,r.rdng,r.txt as rtxt,k.kanj,k.txt as ktxt
    FROM rdng r
    JOIN kanj k ON k.entr=r.entr
    WHERE NOT EXISTS (
        SELECT * FROM restr z
        WHERE z.entr=r.entr AND z.kanj=k.kanj AND z.rdng=r.rdng));

CREATE OR REPLACE VIEW sr_valid AS (
    SELECT s.entr,s.sens,r.rdng,r.txt as rtxt
    FROM sens s
    JOIN rdng r ON r.entr=s.entr
    WHERE NOT EXISTS (
        SELECT * FROM stagr z
        WHERE z.entr=s.entr AND z.sens=s.sens AND z.rdng=r.rdng));

CREATE OR REPLACE VIEW sk_valid AS (
    SELECT s.entr,s.sens,k.kanj,k.txt as ktxt
    FROM sens s
    JOIN kanj k ON k.entr=s.entr
    WHERE NOT EXISTS (
        SELECT * FROM stagk z
        WHERE z.entr=s.entr AND z.sens=s.sens AND z.kanj=k.kanj));

CREATE OR REPLACE VIEW xrefhw AS (
    SELECT r.entr,rm.sens,r.txt as rtxt,k.kanj,k.txt as ktxt
    FROM (
        SELECT entr,sens,MIN(rdng) as rdng FROM sr_valid GROUP BY entr,sens)
        AS rm
    JOIN rdng r ON r.entr=rm.entr AND r.rdng=rm.rdng
    LEFT JOIN (
        SELECT entr,sens,MIN(kanj) as kanj FROM sk_valid GROUP BY entr,sens)
        AS km ON km.entr=r.entr AND km.sens=rm.sens
    LEFT JOIN kanj k ON k.entr=km.entr AND k.kanj=km.kanj);

CREATE OR REPLACE VIEW vsnd AS (
    SELECT snd.id, snd.strt, snd.leng,
        sndfile.loc AS sfile, sndvol.loc AS sdir,
        sndvol.type=2 AS iscd, sndvol.id AS sdid, snd.trns
    FROM sndvol
    JOIN sndfile ON sndvol.id = sndfile.vol
    JOIN snd ON sndfile.id = snd.file);

--============================================================================
--  The following two views are used by python/xresolv.py.
--============================================================================

  -- Support view for "vrslv" below.  Return reading and kanji information
  -- information for entries taking into account restr restrictions.
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

  ----------------------------------------------------------------------------
  -- This view is used by xresolv.py for finding entries that could
  -- possibly be the intended targets of unresolved xrefs in table
  -- "xresolv".
  -- It joins the rows in xresolve to entries based on a common reading
  -- text, kanji text, or both.  Because the joins vary depending on the
  -- join column there are three separate SELECTs, one for each case,
  -- UNIONed together.
  -- There may be multiple (or no) entries that have kanji or a reading
  -- matching an xresolv row so a particular xresolv row may result in
  -- 0 or multiple rows returned.  This view provides data in additional
  -- columns that is intended to allow for a reasonable guess at which
  -- entry is the intended target (or that no reasonable guess is justified)
  -- in the case of multiple matches.

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

--============================================================================
--  The following views are used in cgi/edsubmit.py for manipulating
--  a tree of edits to an entry.
--============================================================================
-- Get all edit paths and subpaths for every unapproved entry.
-- This view is a helper view for the more useful view, "edtrees",
-- below.  This view is based directly on the recursive CTE tree example
-- in the Postgresql docs:
--   https://www.postgresql.org/docs/10/queries-with.html#id-1.5.6.12.5.4
-- The aliases "g" and "sg" have been kept allow easier comparision to
-- the example.
--
-- If a JMdictDB edit tree (a tree of entries linked by their entr.dfrm
-- fields) like the following exists:
--   NULL=A.dfrm <-- B.dfrm <-.---- C.dfrm
--                             `.-- D.dfrm <-- E.dfrm
-- The 'path' values in the 'sg' working table in the CTE will be:
--   AB, ABC, ABD, ABDE, B, BC, BD, BDE, C, D, DE, E
-- (Values in the 'path' column are actually arrays and "ABC" above is an
-- abbreviation for ARRAY[A,B,C], where A, B and C are entry id numbers.)
-- We refer to A as the "root" entry, the entries C and E as (edit) "heads"
-- (or "leaf" entries), and the two sequences of entries from the root to
-- each head (ABC and ABDE) as "paths".
-- * If there is cyclic 'dfrm' path, it will be detected and not cause an
--   infinite loop but will not be returned in the result set.
-- * The first item in 'path' will always equal 'id' for that row.
-- * 'dfrm' will be NULL for each row that 'id'/'path[0]' is A.
-- * Any connected set of paths that has a row with a 'dfrm' value of NULL
--    can't contain any rows with 'cycle' equal True.
-- * The first item in 'path' is the "oldest" in that edit path, the right
--    most the newest.
-- Because we want only full-length paths (from root entry to leaf entry)
-- we'll select only those paths with 'dfrm'=NULL (ie, starting at a root
-- entry).  This will include incomplete paths (not all the way to a leaf
-- node) but those can be removed later.  It will exclude any sets of paths
-- that are cyclic but that exclusion can be justified on the grounds that
-- they are "broken" (the jmdictdb libraries should prevent them) and we
-- assume routine jmdictdb database maintenance will detect and remove
-- them.  The query will still terminate if 'dfrm' cycles exist.
------------------------------------------------------------------------------
CREATE OR REPLACE VIEW edbase AS (
    WITH RECURSIVE sg (id, dfrm, path, cycle) AS (
        SELECT g.id, g.dfrm, ARRAY[g.id], false
          FROM entr g LEFT JOIN entr h ON h.id=g.dfrm
          WHERE g.unap
        UNION ALL
        SELECT g.id, g.dfrm, g.id||path, g.id=ANY(path)
          FROM entr g, sg
          WHERE g.id = sg.dfrm AND NOT cycle)
    SELECT id, path AS path FROM sg WHERE dfrm IS NULL);

------------------------------------------------------------------------------
-- Return a set of edit paths: arrays where each element is an entry id
-- and the array represents a list of edits from a "root" entry to the
-- most recenty edited entry on an edit branch.
-- This view simply removes incomplete paths (those not starting from a
-- root entry or not ending at a head entry) from the paths returned by
-- the "edbase" helper view above.
-- The number of rows returned is the number of edit "heads".
-- There will be at least one row for every unapproved root entry (which
-- includes new entries with no following entries.)
-- Any approved entries present will be the first entry in the path and
-- there will be at least one unapproved entry following it.  (I.e.,
-- approved entries, unlike unapproved ones, will never appear alone, or
-- to put it in a different way, never with a path length of 1 and never
-- in any position in the path except the first.  (The latter condition
-- is guaranteed by the "entr_dfrm_check" constrain on the entr table.)
-- With the example tree in the "edbase" view comments, the result set of
-- this view would be:    id      path
--                         A     {A,B,C}
--                         A     {A,B,D,E}
-- where the letters are entry id numbers.
------------------------------------------------------------------------------
CREATE OR REPLACE VIEW edpath AS (
    SELECT id AS root, path FROM edbase e WHERE NOT EXISTS (
        SELECT 1 FROM edbase f
        WHERE e.id=f.id AND f.path@>e.path AND e.path!=f.path));

------------------------------------------------------------------------------
-- Like view "edpath" but with a separate row for each 'path' item; each
-- row is from table "entr" with an additional two columns: 'root', whose
-- value is the root entry of the edit path, and 'path', the path that 'id'
-- is an element of.
-- With the example tree in the "edbase" view comments, the result set of
-- this view would be:    id     root    path
--                         A       A     {A,B,C}
--                         A       A     {A,B,D,E}
--                         B       A     {A,B,C}
--                         B       A     {A,B,D,E}
--                         C       A     {A,B,C}
--                         D       A     {A,B,D,E}
--                         E       A     {A,B,D,E}
------------------------------------------------------------------------------
CREATE OR REPLACE VIEW edpaths AS (
    SELECT e1.id, e2.root, e2.path
        FROM
           (SELECT root, path, unnest(path) AS id
            FROM edpath
            WHERE array_length(path,1)>1) AS e1
        JOIN edpath e2 ON e1.root=e2.root);

------------------------------------------------------------------------------
-- This function will replicate an entry by duplicating it's
-- row in table entr and all child rows recursively (although
-- this function is not recursive.)
------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION dupentr(entrid int) RETURNS INT AS $$
    DECLARE
        _p0_ INT;
    BEGIN
        INSERT INTO entr(src,stat,seq,dfrm,unap,srcnotes,notes)
          (SELECT src,seq,3,notes FROM entr WHERE id=entrid);
        SELECT lastval() INTO _p0_;

        INSERT INTO hist(entr,hist,stat,unap,dt,userid,name,email,diff,refs,notes)
          (SELECT _p0_,hist,stat,unap,dt,userid,name,email,diff,refs,notes
           FROM hist WHERE hist.entr=entrid);

        INSERT INTO kanj(entr,kanj,txt)
          (SELECT _p0_,kanj,txt FROM kanj WHERE entr=entrid);
        INSERT INTO kinf(entr,kanj,ord,kw)
          (SELECT _p0_,kanj,kw FROM kinf WHERE entr=entrid);

        INSERT INTO rdng(entr,rdng,txt)
          (SELECT _p0_,rdng,txt FROM rdng WHERE entr=entrid);
        INSERT INTO rinf(entr,rdng,ord,kw)
          (SELECT _p0_,rdng,kw FROM rinf WHERE entr=entrid);
        INSERT INTO audio(entr,rdng,audio,fname,strt,leng)
          (SELECT _p0_,rdng,audio,fname,strt,leng FROM audio a WHERE a.entr=entrid);

        INSERT INTO sens(entr,sens,notes)
          (SELECT _p0_,sens,notes FROM sens WHERE entr=entrid);
        INSERT INTO pos(entr,sens,ord,kw)
          (SELECT _p0_,sens,kw FROM pos WHERE entr=entrid);
        INSERT INTO misc(entr,sens,ord,kw)
          (SELECT _p0_,sens,kw FROM misc WHERE entr=entrid);
        INSERT INTO fld(entr,sens,ord,kw)
          (SELECT _p0_,sens,kw FROM fld WHERE entr=entrid);
        INSERT INTO gloss(entr,sens,gloss,lang,ginf,txt,notes)
          (SELECT _p0_,sens,gloss,lang,txt,ginf,notes FROM gloss WHERE entr=entrid);
        INSERT INTO dial(entr,sens,ord,kw)
          (SELECT _p0_,kw FROM dial WHERE dial.entr=entrid);
        INSERT INTO lsrc(entr,sens,ord,lang,txt,part,wasei)
          (SELECT _p0_,kw FROM lsrc WHERE lang.entr=entrid);
        INSERT INTO xref(entr,sens,xref,typ,xentr,xsens,notes)
          (SELECT _p0_,sens,xref,typ,xentr,xsens,notes FROM xref WHERE entr=entrid);
        INSERT INTO xref(entr,sens,xref,typ,xentr,xsens,notes)
          (SELECT entr,sens,xref,typ,_p0_,xsens,notes FROM xref WHERE xentr=entrid);
        INSERT INTO xresolv(entr,sens,typ,ord,typ,rtxt,ktxt,tsens,notes,prio)
          (SELECT _p0_,sens,typ,ord,typ,rtxt,ktxt,tsens,notes,prio FROM xresolv WHERE entr=entrid);

        INSERT INTO freq(entr,kanj,kw,value)
          (SELECT _p0_,rdng,kanj,kw,value FROM freq WHERE entr=entrid);
        INSERT INTO restr(entr,rdng,kanj)
          (SELECT _p0_,rdng,kanj FROM restr WHERE entr=entrid);
        INSERT INTO stagr(entr,sens,rdng)
          (SELECT _p0_,sens,rdng FROM stagr WHERE entr=entrid);
        INSERT INTO stagk(entr,sens,kanj)
          (SELECT _p0_,sens,kanj FROM stagk WHERE entr=entrid);

        RETURN _p0_;
        END;
    $$ LANGUAGE plpgsql;

-------------------------------------------------------------
-- This function will delete an entry by deleting all related
-- rows in child tables other than hist, and setting the entr
-- row's status to "deleted, pending approval".
-------------------------------------------------------------
CREATE OR REPLACE FUNCTION delentr(entrid int) RETURNS void AS $$
    BEGIN
        -- We don't delete the entr row or history rows but
        -- we delete everything else.
        -- Because fk's use "on delete cascade" options we
        -- need only delete the top-level children to get
        -- rid of everything.
        UPDATE entr SET stat=5 WHERE entr=entrid;
        DELETE FROM kanj WHERE entr=entrid;
        DELETE FROM rdng WHERE entr=entrid;
        DELETE FROM sens WHERE entr=entrid;
        UPDATE entr SET stat=5 WHERE entr=entrid;
        END;
    $$ LANGUAGE plpgsql;

--============================================================================
--  The following views are used by cgi/conj.py for conjugating
--  database entry words.
--============================================================================

DROP VIEW IF EXISTS vconotes, vinflxt, vinflxt_, vinfl, vconj, vcpos CASCADE;

CREATE OR REPLACE VIEW vconj AS (
    SELECT conjo.pos, kwpos.kw AS ptxt, conj.id AS conj, conj.name AS ctxt, conjo.neg, conjo.fml
    FROM conj
    INNER JOIN conjo ON conj.id=conjo.conj
    INNER JOIN kwpos ON kwpos.id=conjo.pos
    ORDER BY conjo.pos, conjo.conj, conjo.neg, conjo.fml);
ALTER VIEW vconj OWNER TO jmdictdb;

CREATE OR REPLACE VIEW vinfl AS (
    SELECT u.id, seq, src, unap, pos, ptxt, knum, ktxt, rnum, rtxt, conj, ctxt, neg, fml,
        CASE WHEN neg THEN 'neg' ELSE 'aff' END || '-' ||
          CASE WHEN fml THEN 'polite' ELSE 'plain' END AS t, onum,
        CASE WHEN ktxt ~ '[^あ-ん].$'  -- True if final verb is kanji, false if it is hiragana
                                      --  (see IS-226, 2014-08-26).
            THEN COALESCE((LEFT(ktxt,LENGTH(ktxt)-stem-1)||euphk), LEFT(ktxt,LENGTH(ktxt)-stem))
            ELSE COALESCE((LEFT(ktxt,LENGTH(ktxt)-stem-1)||euphr), LEFT(ktxt,LENGTH(ktxt)-stem)) END
            || okuri AS kitxt,
        COALESCE((LEFT(rtxt,LENGTH(rtxt)-stem-1)||euphr), LEFT(rtxt,LENGTH(rtxt)-stem)) || okuri AS ritxt,
        (SELECT array_agg (note ORDER BY note) FROM conjo_notes n
            WHERE u.pos=n.pos AND u.conj=n.conj AND u.neg=n.neg
                AND u.fml=n.fml AND u.onum=n.onum) AS notes
    FROM (
        SELECT DISTINCT entr.id, seq, src, unap, kanj.txt AS ktxt, rdng.txt AS rtxt,
                        pos.kw AS pos, kwpos.kw AS ptxt, conj.id AS conj, conj.name AS ctxt,
                        onum, okuri, neg, fml,
                        kanj.kanj AS knum, rdng.rdng AS rnum, stem, euphr, euphk
        FROM entr
        JOIN sens ON entr.id=sens.entr
        JOIN pos ON pos.entr=sens.entr AND pos.sens=sens.sens
        JOIN kwpos ON kwpos.id=pos.kw
        JOIN conjo ON conjo.pos=pos.kw
        JOIN conj ON conj.id=conjo.conj
        LEFT JOIN kanj ON entr.id=kanj.entr
        LEFT JOIN rdng ON entr.id=rdng.entr
        WHERE conjo.okuri IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM stagr WHERE stagr.entr=entr.id AND stagr.sens=sens.sens AND stagr.rdng=rdng.rdng)
        AND NOT EXISTS (SELECT 1 FROM stagk WHERE stagk.entr=entr.id AND stagk.sens=sens.sens AND stagk.kanj=kanj.kanj)
        AND NOT EXISTS (SELECT 1 FROM restr WHERE restr.entr=entr.id AND restr.rdng=rdng.rdng AND restr.kanj=kanj.kanj)
        ) AS u)
    ORDER BY u.id,pos,knum,rnum,conj,neg,fml,onum;

-- Example:
--      SELECT * FROM vinfl
--      WHERE seq=.......
--      ORDER BY seq,knum,rnum,pos,conjid,t,onum;

-- The following view combines, for each conjugation row, multiple okurigana
-- and multiple notes into a single string so that each conjugation will have
-- only one row.  Note that the string inside the string_agg() function below
-- contains an embedded newline.  This file needs to be saved with Unix-style
-- ('\n') newlines (rather than Windows style ('\r\n') in order to prevent
-- the '\r' characters from appearing in the view results.

CREATE OR REPLACE VIEW vinflxt_ AS (
    SELECT id, seq, src, unap, pos, ptxt, knum, ktxt, rnum, rtxt, conj, ctxt, t, string_agg (
      COALESCE (kitxt,'') || (CASE WHEN kitxt IS NOT NULL THEN '【' ELSE '' END) ||
      COALESCE (ritxt,'') || (CASE WHEN kitxt IS NOT NULL THEN '】' ELSE '' END) ||
      (CASE WHEN notes IS NOT NULL THEN ' [' ELSE '' END) ||
      COALESCE (ARRAY_TO_STRING (notes, ','), '') ||
      (CASE WHEN notes IS NOT NULL THEN ']' ELSE '' END), ',
' ORDER BY onum) AS word
    FROM vinfl
    GROUP BY id, seq, src, unap, pos, ptxt, knum, ktxt, rnum, rtxt, conj, ctxt, t
    ORDER BY id, pos, ptxt, knum, rnum, conj);

CREATE OR REPLACE VIEW vinflxt AS (
    SELECT id, seq, src, unap, pos, ptxt, knum, ktxt, rnum, rtxt, conj, ctxt,
        MIN (CASE t WHEN 'aff-plain'  THEN word END) AS w0,
        MIN (CASE t WHEN 'aff-polite' THEN word END) AS w1,
        MIN (CASE t WHEN 'neg-plain'  THEN word END) AS w2,
        MIN (CASE t WHEN 'neg-polite' THEN word END) AS w3
        FROM vinflxt_
        GROUP BY id, seq, src, unap, pos, ptxt, knum, ktxt, rnum, rtxt, conj, ctxt
        ORDER BY id, pos, knum, rnum, conj);

CREATE OR REPLACE VIEW vconotes AS (
    SELECT DISTINCT k.id AS pos, k.kw AS ptxt, m.*
        FROM kwpos k
        JOIN conjo c ON c.pos=k.id
        JOIN conjo_notes n ON n.pos=c.pos
        JOIN conotes m ON m.id=n.note
        ORDER BY m.id);

-- See IS-226 (2014-06-12).  This view is used to present a pseudo-keyword
--  table that is loaded into the jdb.Kwds instance and provides a list
--  of conjugatable pos's in the same format as the kwpos table.
CREATE OR REPLACE VIEW vcopos AS (
    SELECT id,kw,descr FROM kwpos p JOIN (SELECT DISTINCT pos FROM conjo) AS c ON c.pos=p.id);
GRANT SELECT ON vcopos TO jmdictdbv;

COMMIT;
