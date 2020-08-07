\set ON_ERROR_STOP

-- Migrate data that has been loaded into the import schema "imp"
-- into the main database tables in the public schema.
-- This procedure is NOT concurrency-friendly; the database should
-- be quiesent when this procedure is run.
-- Before running this script the data to import should be loaded:
--    SET search_path TO imp,public;
--    \ir data/jmnedict.pgi
-- or
--    PGOPTIONS=--search_path=imp,public psql -d ... -f data/jmnedict.pgi
-- If a source id is given on the command line with -v "src=<n>'
-- and a kwsrc row with that id exists in the public.kwsrc table,
-- that src id will be used for the entr rows migrated into the
-- public table.  If no such row exists in public.kwsrc, the
-- imported kwsrc row will added to public.kwsrc but with an
-- id from the command line.  If no command line src id value is
-- given, the imported kwsrc row will be added to public.kwsrc
-- with its id unchanged.

BEGIN;

-- Update the kwsrc table.  The imported data has its own kwsrc table
-- containing the src names found in the parsed xml, and like the other
-- data, with id numbers incrementing from 1.  We compare the imported
-- kwsrc records in imp.kwsrc with those already existing in the target
-- database, public.kwsrc.  If a imported kwsrc name (and 'srct' type)
-- matches an existing kwsrc name, the imported entries will be assigned
-- the existing kwsrc's id.  Imported kwsrc records whos name does not
-- match any name in public.kwsrc are added to public.kwsrc with a new
-- id number (since the existing one may conflict which ids already in
-- use in public.kwsrc) and entries are imported with the new kwsrc.id
-- number.

-- Add columns that will be used to map imported kwsrc.id's to new
-- values for eexistance in the public.kwsrc table.
ALTER TABLE imp.kwsrc
    ADD COLUMN IF NOT EXISTS newid INT,  -- replacement id number.
    ADD COLUMN IF NOT EXISTS isnew BOOL; -- a row not in public.kwsrc.

-- Set the two new columns added above.
UPDATE imp.kwsrc i SET newid=m.newid, isnew=m.isnew
    FROM (
        SELECT i.id, p.id IS NULL AS isnew,
            COALESCE (p.id,
               (SELECT MAX(id) FROM public.kwsrc WHERE kw!='test')
               + row_number() OVER (PARTITION BY p.id IS NULL), 1) AS newid
        FROM imp.kwsrc i
        LEFT JOIN public.kwsrc p ON p.kw=i.kw AND p.srct=i.srct) AS m
    WHERE m.id=i.id;

-- Add the imp.kwsrc rows identified as new to the public.kwsrc table.
INSERT INTO public.kwsrc(id,kw,seq,srct)
    SELECT newid, kw, 'seq_'||kw, srct FROM imp.kwsrc WHERE isnew;

  -- Load the imported entr table and it's children into the public
  -- schema tables.  The imported entr rows are expected to start with
  -- id=1.  We adjust the id's before inserting them to values that are
  -- greater then the largest id already in public.entr.  The foreign
  -- key references to entr.id in the children tables are adjusted the
  -- same way.  We also change the value of 'src' to ':src' during the
  -- load.  When loading the "entr" table we will also change the row's
  -- .src value to match a possibly changed id number for the corresponding
  -- row in public.kwsrc.

  -- Set the value of script variable 'maxid' to the value of the
  -- largest entr.id in use in the main public.entr table.
SELECT COALESCE(MAX(id),0) AS maxid FROM public.entr \gset

INSERT INTO public.entr
                    (SELECT e.id+:maxid,s.newid,stat,e.seq,dfrm,unap,srcnote,e.notes
                     FROM imp.entr e JOIN imp.kwsrc s ON s.id=e.src);
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

  -- The following will delete the contents of all imp.* tables due
  -- the the cascade delete rules on the foreign keys.
DELETE FROM imp.kwsrc;
COMMIT;
