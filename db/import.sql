\set ON_ERROR_STOP

-- This script will migrate entry data that has beeb imported into
-- schema "imp", into the "public" schema where they become accessible
-- to the JMdictDB system.
--
-- The import entries all have assigned corpora (that is, each entry
-- has an entr.src value referencing a row by id number in imp.kwsrc).
-- Those corpora need to be merged into the already existing corpora
-- in public.kwsrc.  We do this by adding a new column to imp.kwsrc
-- 'newid' and setting its values to id numbers that will be used in
-- public.kwsrc.
-- When a imp.kwsrc.newid value does not match any id numbers in
-- public.kwsrc the entire imp.kwsrc row is copied into the public.-
-- kwsrc table and given an 'id' value of 'newid'.
-- When there is a matching id number in public.kwsrc, the entries
-- belonging to the imp.kwsrc corpus will be reassigned the public.-
-- kwsrc corpus.
-- In both cases when entries are copied to the public schema, their
-- entr.src values are replaced with the value from 'newid'.
-- Note that when a corpus is mapped to an already existing row in
-- in public.kwsrc, none of the other information in the imp.kwsrc
-- row is carried over or even checked; it is the user's responsibility
-- to to make sure that the new corpus assignment is compatible (has
-- the same corpus type ('srct') value, for example.)
--
-- Before running this script we expect that the user has:
--   * Imported the incoming data into the imp schema tables.  Note
--       that  before this can be done (in order to avoid failed
--       'dfrm' foreign key references), the user must also drop the
--       "entr_dfrm_fkey" constraint on the imp.entr table.
--   * Added a new column to the imp.kwsrc table, e.g.:
--       ALTER TABLE imp.kwsrc
--         ADD COLUMN IF NOT EXISTS newid INT;
--   * Set the value of imp.kwsrc.newid to either of:
--     * A value matching an 'id' value in public.kwsrc.
--       In this case entries belonging to the imp.kwsrc corpora will
--       be reassigned to the matching public.kwsrc corpus.
--     * A value not matching any 'id' value in public.kwsrc.
--       In this case the imp.kwsrc row will be copied into the public.-
--       kwdsrc and the copied entries belonging to the imp.kwsrc
--       corpora will be reassigned to it.

BEGIN;

-- Add the imp.kwsrc rows that don't have matching (by id) rows in the
-- public.kwsrc table.

INSERT INTO public.kwsrc
    (SELECT newid, kw, descr, dt, notes, seq, sinc, smin, smax, srct
     FROM imp.kwsrc WHERE newid NOT IN (SELECT id FROM public.kwsrc));

-- Load the imported entr table and it's children into the public
-- schema tables.  The imported entr rows are expected to start with
-- id=1.  We adjust the id's before inserting them to values that are
-- greater then the largest id already in public.entr.  The foreign
-- key references to entr.id in the children tables are adjusted the
-- same way.  We also change the value of 'entr.src' to '.newid' from
-- the imp.kwsrc table during the load which assigns them to the public
-- corpus corresponding to the one they belonged to in "imp".

  -- Set the value of script variable 'maxid' to the value of the
  -- largest entr.id in use in the main public.entr table.
SELECT COALESCE(MAX(id),0) AS maxid FROM public.entr \gset

  -- Check that the target rows of any imported rows that have non-
  -- NULL 'dfrm' values are also present in the imported rows.  Other-
  -- wise the 'dfrm' would end up NULL and the information about some
  -- entries parents silently lost.
SELECT err('Missing ''dfrm'' target: '|| dfrmlist)
    FROM (SELECT dfrmlist
          -- The string_agg() function will return 1 row (of NULL) when
          -- its base query returns 0 rows; hence the enclosing query to
          -- eliminate that row.
        FROM (SELECT string_agg (i.dfrm::TEXT, ',') AS dfrmlist
              FROM imp.entr i
              LEFT JOIN imp.entr t ON i.dfrm=t.idx
              WHERE t.id IS NULL) AS x) AS y WHERE dfrmlist IS NOT NULL;

  -- Move the entr rows from the imp schema to the public one. assigning
  -- new 'id' and 'src' values en route.
INSERT INTO public.entr
                    (SELECT e.id+:maxid,s.newid,stat,
                            e.seq,NULL,unap,srcnote,e.notes,e.idx
                     FROM imp.entr e JOIN imp.kwsrc s ON s.id=e.src);

  -- Update the 'dfrm' values (set to NULL above) to the equivalent id's
  -- of the correct rows now in the public.entr table.
UPDATE public.entr SET dfrm=m.id
    FROM (SELECT p.id,i.idx FROM imp.entr i JOIN public.entr p ON i.dfrm=p.idx) AS m
    WHERE public.entr.idx=m.idx;
ALTER TABLE entr ADD FOREIGN KEY

INSERT INTO rdng    (SELECT entr+:maxid,rdng,txt                     FROM imp.rdng);
INSERT INTO kanj    (SELECT entr+:maxid,kanj,txt                     FROM imp.kanj);
INSERT INTO sens    (SELECT entr+:maxid,sens,notes                   FROM imp.sens);
INSERT INTO gloss   (SELECT entr+:maxid,sens,gloss,lang,ginf,txt     FROM imp.gloss);
INSERT INTO hist    (SELECT entr+:maxid,hist,stat,unap,dt,userid,name,email,diff,refs,notes FROM imp.hist);
INSERT INTO dial    (SELECT entr+:maxid,sens,ord,kw                  FROM imp.dial);
INSERT INTO fld     (SELECT entr+:maxid,sens,ord,kw                  FROM imp.fld);
INSERT INTO freq    (SELECT entr+:maxid,rdng,kanj,kw,value           FROM imp.freq);
INSERT INTO kinf    (SELECT entr+:maxid,kanj,ord,kw                  FROM imp.kinf);
INSERT INTO lsrc    (SELECT entr+:maxid,sens,ord,lang,txt,part,wasei FROM imp.lsrc);
INSERT INTO misc    (SELECT entr+:maxid,sens,ord,kw                  FROM imp.misc);
INSERT INTO pos     (SELECT entr+:maxid,sens,ord,kw                  FROM imp.pos);
INSERT INTO rinf    (SELECT entr+:maxid,rdng,ord,kw                  FROM imp.rinf);
INSERT INTO restr   (SELECT entr+:maxid,rdng,kanj                    FROM imp.restr);
INSERT INTO stagr   (SELECT entr+:maxid,sens,rdng                    FROM imp.stagr);
INSERT INTO stagk   (SELECT entr+:maxid,sens,kanj                    FROM imp.stagk);
INSERT INTO xresolv (SELECT entr+:maxid,sens,ord,typ,rtxt,ktxt,tsens,vsrc,vseq,notes,prio FROM imp.xresolv);
INSERT INTO chr     (SELECT entr+:maxid,chr,bushu,strokes,freq,grade,jlpt FROM imp.chr);
INSERT INTO cinf    (SELECT entr+:maxid,kw,value,mctype              FROM imp.cinf);
INSERT INTO kresolv (SELECT entr+:maxid,kw,value                     FROM imp.kresolv);

  -- Update the sequences which is necessary after any bulk load.
  -- Changes to sequences are not transactional so no point in doing
  -- before the commit.
SELECT setval('entr_id_seq',  (SELECT max(id) FROM entr));

  -- Since we create the schema anew for each import no need to keep
  -- it around.
--DROP SCHEMA imp CASCADE;
COMMIT;
