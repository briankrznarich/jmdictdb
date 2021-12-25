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
        -- Each row represents a corpus to which zero or more entries
        -- belong.
    id SMALLINT PRIMARY KEY,
    kw VARCHAR(20) NOT NULL UNIQUE,
    descr VARCHAR(255),
    dt DATE,
        -- Available for recording a timestamp associated with the corpus.
    notes VARCHAR(255),
        -- Ad hoc nore regarding this corpus.
    seq VARCHAR(20) NOT NULL,
        -- Name of Postgresql sequence thar will supply entr.seq default
        -- values.  The sequence will be automatically created (by the
        -- kwsrc_updseq() trigger in mktables.sql) when a row in inserted
        -- in kwsrc.
    sinc SMALLINT,  -- Sequence INCREMENT value used when creating seq.
    smin BIGINT,    -- Sequence MINVALUE value used when creating seq.
    smax BIGINT,    -- Sequence MAXVALUE value used when creating seq.
    srct TEXT NOT NULL REFERENCES kwsrct(kw));
        -- Corpus type as defined in table "kwsrct".  This will be by
        -- default one of: 'jmdict', 'jmnedict', 'kanjidic', 'examples'.

CREATE TABLE entr (
    id SERIAL PRIMARY KEY,
        -- Arbitrary and unique integer to identify entries within
        -- the database.  We don't want to use seq as the PK because
        -- the database may include entries from non-JMdict sources
        -- (such as JMnedict) in the future and those source may not
        -- have seq numbers.
        -- All rows in other tables related to an entry will have a
        -- foreign key pointing to the entry's id value.
    src SMALLINT NOT NULL
      REFERENCES kwsrc(id) ON DELETE CASCADE ON UPDATE CASCADE,
        -- Indicates he corpus this entry belongs to.
    stat SMALLINT NOT NULL
      REFERENCES kwstat(id),
        -- Indicates the status of this entry.  Will be 2 (active),
        -- 4 (deleted) or 6 (rejected).
        -- "rejected”, etc.
    seq BIGINT NOT NULL CHECK(seq>0),
        -- Sequence number.  This number maps to the <ent_seq>
        -- element of the JMdict XML file, and is intended
        -- to be a stable identifier of a particular word.
    dfrm INT CHECK
      CONSTRAINT entr_dfrm_check CHECK (dfrm IS NULL OR unap)
      REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
        -- If not NULL is a reference to another entry that was the
        -- edit source for this entry.  The CHECK constraint prevents
        -- approved entries from being an edit of some other entry.
    unap BOOLEAN NOT NULL,
        -- If TRUE, this entry has not been approved by an editor yet.
    srcnote VARCHAR(255) NULL,
        -- Additional ad-hoc information about the source of this
        -- entry.
    notes TEXT,
        -- Arbitrary textual information about this entry.  Intended
        -- for display by applications.
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
        -- Contains the readings associated with each entry.  Maps to
        -- the JMdict XML element <re_ele>.
    entr INT NOT NULL
      REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    rdng SMALLINT NOT NULL CHECK (rdng>0),
        -- Disambiguates and orders multiple readings in an entry.
    PRIMARY KEY (entr,rdng),
    txt VARCHAR(2048) NOT NULL);
        -- Reading text.
CREATE INDEX ON rdng(txt);
CREATE UNIQUE INDEX ON rdng(entr,txt);
CREATE INDEX ON rdng(txt varchar_pattern_ops); --For fast LIKE 'xxx%'

CREATE TABLE kanj (
        -- Contains the kanji associated with each entry.  Maps to
        -- the JMdict XML element <ke_ele>.
    entr INT NOT NULL
      REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    kanj SMALLINT NOT NULL CHECK (kanj>0),
        -- Disambiguates and orders multiple kanji in an entry.
    PRIMARY KEY (entr,kanj),
    txt VARCHAR(2048) NOT NULL);
        -- Kanji text.
CREATE INDEX ON kanj(txt);
CREATE UNIQUE INDEX ON kanj(entr,txt);
CREATE INDEX ON kanj(txt varchar_pattern_ops); --For fast LIKE 'xxx%'

CREATE TABLE sens (
        -- Contains the sense items associated with each entry.
        -- Has no information of its own beyond a sense note but serves
        -- as an anchor for other tables to reference.
    entr INT NOT NULL
      REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    sens SMALLINT NOT NULL CHECK (sens>0),
        -- Disambiguates and orders multiple sense in an entry.
    PRIMARY KEY (entr,sens),
    notes TEXT);
        -- Sense note.  Corresponds to the <s_inf> element in JMdict.

CREATE TABLE gloss (
      -- Contain the gloss items associated with each sense.
    entr INT NOT NULL,
    sens SMALLINT NOT NULL,
    FOREIGN KEY (entr,sens)
      REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
    gloss SMALLINT NOT NULL CHECK (gloss>0),
        -- Disambiguates and orders multiple gloss in a sense.
    PRIMARY KEY (entr,sens,gloss),
    lang SMALLINT NOT NULL DEFAULT 1 REFERENCES kwlang(id),
        -- The language of the gloss.
    ginf SMALLINT NOT NULL DEFAULT 1 REFERENCES kwginf(id),
        -- Type of gloss (equivalent, literal, figurative, etc.)
    txt VARCHAR(2048) NOT NULL);
        -- Gloss text.
CREATE INDEX ON gloss(txt);
CREATE UNIQUE INDEX ON gloss(entr,sens,lang,txt);
CREATE INDEX ON gloss(lower(txt) varchar_pattern_ops); --For case-insensitive LIKE 'xxx%'
CREATE INDEX ON gloss(lower(txt)); 		    --For case-insensitive '='

CREATE TABLE xref (
        -- Models various types of cross-references between entries (or
        -- more accurately, between senses of entries.)  Maps approximately
        -- to JMdict XML elements <xref> and <ant>.
    entr INT NOT NULL,
    sens SMALLINT NOT NULL,
    FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens)
      ON DELETE CASCADE ON UPDATE CASCADE,
    xref SMALLINT NOT NULL CHECK (xref>0),
        -- Disambiguates and orders multiple xrefs in a sense.
    typ SMALLINT NOT NULL REFERENCES kwxref(id),
        -- The type of xref (synonym, antonym, etc).
    xentr INT NOT NULL CHECK (xentr!=entr),
    xsens SMALLINT NOT NULL,
        -- xentr,xsens identify the target entry and sense of the cross-
        -- reference.
    FOREIGN KEY (xentr,xsens) REFERENCES sens(entr,sens)
      ON DELETE CASCADE ON UPDATE CASCADE,
    rdng SMALLINT,
    CONSTRAINT xref_rdng_fkey FOREIGN KEY (xentr,rdng)
      REFERENCES rdng(entr,rdng) ON DELETE CASCADE ON UPDATE CASCADE,
        -- Identifies a particular reading in the target entry to use when
        -- displaying this cross-reference.
    kanj SMALLINT CHECK (kanj IS NOT NULL OR rdng IS NOT NULL),
    CONSTRAINT xref_kanj_fkey FOREIGN KEY (xentr,kanj)
      REFERENCES kanj(entr,kanj) ON DELETE CASCADE ON UPDATE CASCADE,
        -- Identifies a particular kanji in the target entry to use when
        -- displaying this cross-reference.
    notes TEXT,
       -- Ad hoc note associated with this cross-referernce.
    nosens BOOLEAN NOT NULL DEFAULT FALSE,
       -- Indicates that no specific sense should be considered the target
       -- of the cross-reference; that is the xref should be treated as if
       -- was to the entire target entry.  If 'nosens' is True, 'xsens'
       -- should always be 1 although this is not enforced by constraint.
    lowpri BOOLEAN NOT NULL DEFAULT FALSE,
       -- Low priority xref.  Used by Examples entries to denote xrefs that
       -- are not "priority" xrefs.
    PRIMARY KEY (entr,sens,xref,xentr,xsens));
CREATE INDEX ON xref(xentr,xsens);
    --## The following index is disabled because it is violated by Examples
    --## file xrefs.
--CREATE UNIQUE INDEX xref_entr_unq ON xref(entr,sens,typ,xentr,xsens);

CREATE TABLE hist (
        -- This table maintains a series of history records for each
        -- entry that document significant changes to the entry.
    entr INT NOT NULL
      REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    hist SMALLINT NOT NULL CHECK (hist>0),
        -- Disambiguates and orders multiple xrefs in a sense.
    stat SMALLINT NOT NULL REFERENCES kwstat(id),
        -- Status (entr.stat) of entry after the change this record
        -- documents was made.
    unap BOOLEAN NOT NULL,
        -- Approval status (entr.unap) of entry after this change was
        -- made.
    dt TIMESTAMP NOT NULL DEFAULT NOW(),
        -- Date and time this history record was added.
    userid VARCHAR(20),
        -- Userid of logged in editor (or NULL if not logged in).
    name VARCHAR(60),
        -- Name given on submission form.
    email VARCHAR(120),
        -- Email address given on submission form.
    diff TEXT,
        -- Unix-style 'diff' between the XML of the pre- and post-edit
        -- changes.
    refs TEXT,
        -- User provided text from the "References" field on the
        -- submission form.
    notes TEXT,
        -- User provided text from the "Comments" field on the
        -- submission form.
    eid INT,
        -- Id# of entry history item was first attached to.  
    PRIMARY KEY (entr,hist));
CREATE INDEX ON hist(dt);
CREATE INDEX ON hist(email);
CREATE INDEX ON hist(userid);

CREATE TABLE dial (
      -- Provides lists of dialects for senses.  This information
      -- corresponds to the JMdict XML <dial> element.
    entr INT NOT NULL,    -- The entry (entr.id) and
    sens INT NOT NULL,    --  sense (sens.sens) this tag appliers to.
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
      -- Order of this tag among other "dial" tags.
    ord SMALLINT NOT NULL,
      -- Identifies the specific dialect tag.
    kw SMALLINT NOT NULL DEFAULT 1 REFERENCES kwdial(id),
    PRIMARY KEY (entr,sens,kw));

CREATE TABLE fld (
      -- Provides lists of fields of application for senses.  This
      -- information corresponds to the JMdict XML <field> element.
    entr INT NOT NULL,          -- The entry (entr.id) and sense
    sens SMALLINT NOT NULL,     --  (sens.sens) this tag appliers to.
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
      -- Order of this tag among other "fld" tags.
    ord SMALLINT NOT NULL,
      -- Identifies the specific field tag.
    kw SMALLINT NOT NULL REFERENCES kwfld(id),
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
    FOREIGN KEY (entr,kanj) REFERENCES kanj(entr,kanj)
      ON DELETE CASCADE ON UPDATE CASCADE,
    ord SMALLINT NOT NULL,
        -- Order of this tag among other "lsrc" tags.
    kw SMALLINT NOT NULL
      REFERENCES kwkinf(id),
      PRIMARY KEY (entr,kanj,kw));

CREATE TABLE lsrc (
        -- Provides the foreign language word and language for each
        -- sense for imported words.  This information corresponds to
        -- the JMdict XML <lsource> element.
    entr INT NOT NULL,
    sens SMALLINT NOT NULL,
      FOREIGN KEY (entr,sens) REFERENCES sens(entr,sens) ON DELETE CASCADE ON UPDATE CASCADE,
    ord SMALLINT NOT NULL,
        -- Order of this tag among other "lsrc" tags.
    lang SMALLINT NOT NULL DEFAULT 1 REFERENCES kwlang(id),
        -- Language of the source word.
    txt VARCHAR(250) NOT NULL,
        -- Text of the source word.
    PRIMARY KEY (entr,sens,lang,txt),
    part BOOLEAN DEFAULT FALSE,
        -- Corresponds to <lsource> "ls_wasei" attribute in the JMdict XML.
    wasei BOOLEAN DEFAULT FALSE);
        -- Corresponds to <lsource> "ls_type" attribute in the JMdict XML.

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
        -- Similar to table "xref" but holds cross-references before
        -- they are resolved to a specific other entry and while they
        -- are identified only by reading and/or kanji texts.
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

CREATE TABLE chr (
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

CREATE TABLE cinf (
    entr INT NOT NULL
      REFERENCES chr(entr) ON DELETE CASCADE ON UPDATE CASCADE,
    kw SMALLINT NOT NULL
      REFERENCES kwcinf(id) ON DELETE CASCADE ON UPDATE CASCADE,
    value VARCHAR(50) NOT NULL,
    mctype VARCHAR(50) NOT NULL DEFAULT(''),
      PRIMARY KEY (entr,kw,value,mctype));
CREATE INDEX cinf_kw ON cinf(kw);
CREATE INDEX cinf_val ON cinf(value);

CREATE TABLE krslv (
    entr INT NOT NULL
      REFERENCES entr(id) ON DELETE CASCADE ON UPDATE CASCADE,
    kw SMALLINT NOT NULL,
    value VARCHAR(50) NOT NULL,
      PRIMARY KEY (entr,kw,value));
-- No FK constraint on 'kw' (to kwcinf) because it may have a value of
-- 0, meaning 'ucs', which we don't need or want to be a real cinf item.
