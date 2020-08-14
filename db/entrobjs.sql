-- This file defines the tables that contain corpora entry data.
-- It is included by both the main mktables.sql script that is
-- run when a new JMdictDB database is created and by imptabs.sql
-- which creates a copy of the tables in a separate schema for
-- use when importing bulk data.

-- NOTE: Remember to check if any corresponding changes are needed
-- to python/lib/objects.py when this file is updated.

-- Table kwsrc needs to be in this file because these objects are created
-- in both the "public" schema and the "imp" schema used when importing
-- bulk data.  Objects (like kwsrct) in mktables.sql are created only in
-- the public schema.

CREATE TABLE kwsrc (
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL UNIQUE,
    descr VARCHAR(255),
    dt DATE,
    notes VARCHAR(255),
    seq VARCHAR(20) NOT NULL,   -- Name of sequence to create for entr.seq default values.
    sinc SMALLINT,		-- Sequence INCREMENT value used when creating seq.
    smin BIGINT,		-- Sequence MINVALUE value used when creating seq.
    smax BIGINT,		-- Sequence MAXVALUE value used when creating seq.
    srct TEXT NOT NULL REFERENCES kwsrct(kw));

CREATE TABLE entr (
    id SERIAL PRIMARY KEY,
    src SMALLINT NOT NULL
      REFERENCES kwsrc(id) ON DELETE CASCADE ON UPDATE CASCADE,
    stat SMALLINT NOT NULL
      REFERENCES kwstat(id),
    seq BIGINT NOT NULL CHECK(seq>0),
    dfrm INT
      REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    unap BOOLEAN NOT NULL,
    srcnote VARCHAR(255) NULL,
    notes TEXT,
    idx INT);
CREATE INDEX ON entr(seq);
CREATE INDEX ON entr(stat) WHERE stat!=2;
CREATE INDEX ON entr(dfrm) WHERE dfrm IS NOT NULL;
CREATE INDEX ON entr(unap) WHERE unap;
  -- Following disallows two active (stat=2), approved (unap=False)
  -- with the same corpus (seq) and sequence number (seq) from 
  -- existing at the same time. (IS-213).
CREATE UNIQUE INDEX ON entr (src,seq) WHERE stat=2 AND NOT unap;

CREATE TABLE rdng (
    entr INT NOT NULL REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    rdng SMALLINT NOT NULL CHECK (rdng>0),
      PRIMARY KEY (entr,rdng),
    txt VARCHAR(2048) NOT NULL);
CREATE INDEX ON rdng(txt);
CREATE UNIQUE INDEX ON rdng(entr,txt);
CREATE INDEX ON rdng(txt varchar_pattern_ops); --For fast LIKE 'xxx%'

CREATE TABLE kanj (
    entr INT NOT NULL REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    kanj SMALLINT NOT NULL CHECK (kanj>0),
      PRIMARY KEY (entr,kanj),
    txt VARCHAR(2048) NOT NULL);
CREATE INDEX ON kanj(txt);
CREATE UNIQUE INDEX ON kanj(entr,txt);
CREATE INDEX ON kanj(txt varchar_pattern_ops); --For fast LIKE 'xxx%'

CREATE TABLE sens (
    entr INT NOT NULL REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    sens SMALLINT NOT NULL CHECK (sens>0),
      PRIMARY KEY (entr,sens),
    notes TEXT);

CREATE TABLE gloss (
    entr INT NOT NULL,
    sens SMALLINT NOT NULL,
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
    gloss SMALLINT NOT NULL CHECK (gloss>0),
      PRIMARY KEY (entr,sens,gloss),
    lang SMALLINT NOT NULL DEFAULT 1
      REFERENCES kwlang(id),
    ginf SMALLINT NOT NULL DEFAULT 1
      REFERENCES kwginf(id),
    txt VARCHAR(2048) NOT NULL);
CREATE INDEX ON gloss(txt);
CREATE UNIQUE INDEX ON gloss(entr,sens,lang,txt);
CREATE INDEX ON gloss(lower(txt) varchar_pattern_ops); --For case-insensitive LIKE 'xxx%'
CREATE INDEX ON gloss(lower(txt)); 		    --For case-insensitive '='

CREATE TABLE xref (
    entr INT NOT NULL,
    sens SMALLINT NOT NULL,
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
    xref SMALLINT NOT NULL CHECK (xref>0),
    typ SMALLINT NOT NULL
      REFERENCES kwxref(id),
    xentr INT NOT NULL CHECK (xentr!=entr),
    xsens SMALLINT NOT NULL,
      FOREIGN KEY (xentr,xsens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
    rdng SMALLINT,
      CONSTRAINT xref_rdng_fkey FOREIGN KEY (xentr,rdng) REFERENCES rdng(entr,rdng) ON DELETE CASCADE ON UPDATE CASCADE,
    kanj SMALLINT CHECK (kanj IS NOT NULL OR rdng IS NOT NULL),
      CONSTRAINT xref_kanj_fkey FOREIGN KEY (xentr,kanj) REFERENCES kanj(entr,kanj) ON DELETE CASCADE ON UPDATE CASCADE,
    notes TEXT,
    nosens BOOLEAN NOT NULL DEFAULT FALSE,  -- No specific target sense preferred.
    lowpri BOOLEAN NOT NULL DEFAULT FALSE,  -- Low priority xref.
      PRIMARY KEY (entr,sens,xref,xentr,xsens));
CREATE INDEX ON xref(xentr,xsens);
    --## The following index disabled because it is violated by Examples file xrefs.
    --CREATE UNIQUE INDEX xref_entr_unq ON xref(entr,sens,typ,xentr,xsens);

CREATE TABLE hist (
    entr INT NOT NULL
      REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    hist SMALLINT NOT NULL CHECK (hist>0),
    stat SMALLINT NOT NULL
      REFERENCES kwstat(id),
    unap BOOLEAN NOT NULL,
    dt TIMESTAMP NOT NULL DEFAULT NOW(),
    userid VARCHAR(20),
    name VARCHAR(60),
    email VARCHAR(120),
    diff TEXT,
    refs TEXT,
    notes TEXT,
      PRIMARY KEY (entr,hist));
CREATE INDEX ON hist(dt);
CREATE INDEX ON hist(email);
CREATE INDEX ON hist(userid);

CREATE TABLE dial (
    entr INT NOT NULL,
    sens INT NOT NULL,
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
    ord SMALLINT NOT NULL,
    kw SMALLINT NOT NULL DEFAULT 1
      REFERENCES kwdial(id),
      PRIMARY KEY (entr,sens,kw));

CREATE TABLE fld (
    entr INT NOT NULL,
    sens SMALLINT NOT NULL,
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
    ord SMALLINT NOT NULL,
    kw SMALLINT NOT NULL
      REFERENCES kwfld(id),
      PRIMARY KEY (entr,sens,kw));

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
      -- Also we want to allow multiple freq values with the same domain on
      -- the same rdng/kanj: eg both nf11 and nf21 on the same kanji.  Such
      -- values occur in JMdict entries as a result kanji-reading pairs where
      -- the pair may have a different value than just the reading or kanji
      -- by itself.
    UNIQUE (entr,kanj,kw,value),
    UNIQUE (entr,rdng,kw,value));

CREATE TABLE kinf (
    entr INT NOT NULL,
    kanj SMALLINT NOT NULL,
      FOREIGN KEY (entr,kanj) REFERENCES kanj(entr,kanj) ON DELETE CASCADE ON UPDATE CASCADE,
    ord SMALLINT NOT NULL,
    kw SMALLINT NOT NULL
      REFERENCES kwkinf(id),
      PRIMARY KEY (entr,kanj,kw));

CREATE TABLE lsrc (
    entr INT NOT NULL,
    sens SMALLINT NOT NULL,
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
    ord SMALLINT NOT NULL,
    lang SMALLINT NOT NULL DEFAULT 1
      REFERENCES kwlang(id),
    txt VARCHAR(250) NOT NULL,
      PRIMARY KEY (entr,sens,lang,txt),
    part BOOLEAN DEFAULT FALSE,
    wasei BOOLEAN DEFAULT FALSE);

CREATE TABLE misc (
    entr INT NOT NULL,
    sens SMALLINT NOT NULL,
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
    ord SMALLINT NOT NULL,
    kw SMALLINT NOT NULL
      REFERENCES kwmisc(id),
      PRIMARY KEY (entr,sens,kw));

CREATE TABLE pos (
    entr INT NOT NULL,
    sens SMALLINT NOT NULL,
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
    ord SMALLINT NOT NULL,
    kw SMALLINT  NOT NULL
      REFERENCES kwpos(id),
      PRIMARY KEY (entr,sens,kw));

CREATE TABLE rinf (
    entr INT NOT NULL,
    rdng SMALLINT NOT NULL,
      FOREIGN KEY (entr,rdng) REFERENCES rdng(entr,rdng) ON DELETE CASCADE ON UPDATE CASCADE,
    ord SMALLINT NOT NULL,
    kw SMALLINT NOT NULL
      REFERENCES kwrinf(id),
      PRIMARY KEY (entr,rdng,kw));

CREATE TABLE restr (
    entr INT NOT NULL,
    rdng SMALLINT NOT NULL,
      FOREIGN KEY (entr,rdng) REFERENCES rdng(entr,rdng) ON DELETE CASCADE ON UPDATE CASCADE,
    kanj SMALLINT NOT NULL,
      FOREIGN KEY (entr,kanj) REFERENCES kanj(entr,kanj) ON DELETE CASCADE ON UPDATE CASCADE,
      PRIMARY KEY (entr,rdng,kanj));

CREATE TABLE stagr (
    entr INT NOT NULL,
    sens SMALLINT NOT NULL,
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
    rdng SMALLINT NOT NULL,
      FOREIGN KEY (entr,rdng) REFERENCES rdng(entr,rdng) ON DELETE CASCADE ON UPDATE CASCADE,
      PRIMARY KEY (entr,sens,rdng));

CREATE TABLE stagk (
    entr INT NOT NULL,
    sens SMALLINT NOT NULL,
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
    kanj SMALLINT NOT NULL,
      FOREIGN KEY (entr,kanj) REFERENCES kanj(entr,kanj) ON DELETE CASCADE ON UPDATE CASCADE,
      PRIMARY KEY (entr,sens,kanj));

CREATE TABLE grp (
    entr INT NOT NULL REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    kw INT NOT NULL REFERENCES kwgrp(id)  ON DELETE CASCADE ON UPDATE CASCADE,
      PRIMARY KEY (entr,kw),
    ord INT NOT NULL,
    notes VARCHAR(250));
CREATE INDEX grp_kw ON grp(kw);

CREATE TABLE xresolv (
    entr INT NOT NULL,		-- Entry xref occurs in.
    sens SMALLINT NOT NULL,	-- Sense number xref occurs in.
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
    ord SMALLINT NOT NULL,	-- Order of xref in sense.
    typ SMALLINT NOT NULL 	-- Type of xref (table kwxref).
      REFERENCES kwxref(id),
    rtxt VARCHAR(250),		-- Reading text of target given in xref.
    ktxt VARCHAR(250),		-- Kanji text of target given in xref.
    tsens SMALLINT,		-- Target sense number.
    vsrc SMALLINT,              -- Target corpus restriction.
    vseq BIGINT,                -- Target sequence number.
    notes VARCHAR(250),		-- Notes.
    prio BOOLEAN DEFAULT FALSE,	-- True if this is a Tanaka corpus exemplar.
    PRIMARY KEY (entr,sens,typ,ord),
    CHECK (rtxt NOTNULL OR ktxt NOTNULL));
CREATE INDEX xresolv_rdng ON xresolv(rtxt);
CREATE INDEX xresolv_kanj ON xresolv(ktxt);

-------------------
--  Kanjidic tables
-------------------

CREATE TABLE chr(
    entr INT PRIMARY KEY	-- Defines readings and meanings, but not kanji.
      REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    chr CHAR(1) NOT NULL,	-- Defines kanji.
    bushu SMALLINT,		-- Radical number.
    strokes SMALLINT,
    freq SMALLINT,
    grade SMALLINT,
    jlpt SMALLINT,
    radname VARCHAR(50));
CREATE UNIQUE INDEX ON chr(entr,chr);  -- Only one chr item per entr.
-- XX ALTER TABLE chr ADD CONSTRAINT chr_rad_fkey FOREIGN KEY (bushu) REFERENCES rad(num);

CREATE TABLE cinf(
    entr INT NOT NULL
      REFERENCES chr(entr) ON DELETE CASCADE ON UPDATE CASCADE,
    kw SMALLINT NOT NULL
      REFERENCES kwcinf(id) ON DELETE CASCADE ON UPDATE CASCADE,
    value VARCHAR(50) NOT NULL,
    mctype VARCHAR(50) NOT NULL DEFAULT(''),
      PRIMARY KEY (entr,kw,value,mctype));
CREATE INDEX cinf_kw ON cinf(kw);
CREATE INDEX cinf_val ON cinf(value);

CREATE TABLE kresolv(
    entr INT NOT NULL
      REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    kw SMALLINT NOT NULL,
    value VARCHAR(50) NOT NULL,
      PRIMARY KEY (entr,kw,value));
-- No FK constraint on 'kw' (to kwcinf) because it may have a value of
-- 0, meaning 'ucs', which we don't need or want to be a real cinf item.
