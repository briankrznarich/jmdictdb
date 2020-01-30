--
-- PostgreSQL database dump
--

-- Dumped from database version 10.10 (Ubuntu 10.10-0ubuntu0.18.04.1)
-- Dumped by pg_dump version 10.10 (Ubuntu 10.10-0ubuntu0.18.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: imp; Type: SCHEMA; Schema: -; Owner: jmdictdb
--

CREATE SCHEMA imp;


ALTER SCHEMA imp OWNER TO jmdictdb;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


--
-- Name: delentr(integer); Type: FUNCTION; Schema: public; Owner: jmdictdb
--

CREATE FUNCTION public.delentr(entrid integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
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
    $$;


ALTER FUNCTION public.delentr(entrid integer) OWNER TO jmdictdb;

--
-- Name: dupentr(integer); Type: FUNCTION; Schema: public; Owner: jmdictdb
--

CREATE FUNCTION public.dupentr(entrid integer) RETURNS integer
    LANGUAGE plpgsql
    AS $$
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
    $$;


ALTER FUNCTION public.dupentr(entrid integer) OWNER TO jmdictdb;

--
-- Name: entr_seqdef(); Type: FUNCTION; Schema: public; Owner: jmdictdb
--

CREATE FUNCTION public.entr_seqdef() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
    $$;


ALTER FUNCTION public.entr_seqdef() OWNER TO jmdictdb;

--
-- Name: err(text); Type: FUNCTION; Schema: public; Owner: jmdictdb
--

CREATE FUNCTION public.err(msg text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
    BEGIN RAISE '%', msg; END;
    $$;


ALTER FUNCTION public.err(msg text) OWNER TO jmdictdb;

--
-- Name: get_edroot(integer); Type: FUNCTION; Schema: public; Owner: jmdictdb
--

CREATE FUNCTION public.get_edroot(eid integer) RETURNS SETOF integer
    LANGUAGE plpgsql
    AS $$
    -- Starting at entry 'eid', follow the chain of 'dfrm' foreign
    -- keys until a entr row is found that has a NULL 'dfrm' value,
    -- and return that row (which may be the row with id of 'eid').
    -- If there is no row with an id of 'eid', or if there is a cycle
    -- in the dfrm references such that none of entries have a NULL
    -- dfrm, no rows are returned.
    BEGIN
        RETURN QUERY
            WITH RECURSIVE wt(id,dfrm) AS (
                SELECT id,dfrm FROM entr WHERE id=eid
                UNION
                SELECT entr.id,entr.dfrm
                FROM wt, entr WHERE wt.dfrm=entr.id)
            SELECT id FROM wt WHERE dfrm IS NULL;
        RETURN;
    END; $$;


ALTER FUNCTION public.get_edroot(eid integer) OWNER TO jmdictdb;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: entr; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.entr (
    id integer NOT NULL,
    src smallint NOT NULL,
    stat smallint NOT NULL,
    seq bigint NOT NULL,
    dfrm integer,
    unap boolean NOT NULL,
    srcnote character varying(255),
    notes text,
    CONSTRAINT entr_seq_check CHECK ((seq > 0))
);


ALTER TABLE public.entr OWNER TO jmdictdb;

--
-- Name: get_subtree(integer); Type: FUNCTION; Schema: public; Owner: jmdictdb
--

CREATE FUNCTION public.get_subtree(eid integer) RETURNS SETOF public.entr
    LANGUAGE plpgsql
    AS $$
    -- Return the set of entr rows that reference the row with id
    -- 'eid' via 'dfrm', and all the row that reference those rows
    -- and so on.  This function will terminate even if there are
    -- 'dfrm' cycles.
    BEGIN
        RETURN QUERY
            WITH RECURSIVE wt(id) AS (
                SELECT id FROM entr WHERE id=eid
                UNION
                SELECT entr.id
                FROM wt, entr WHERE wt.id=entr.dfrm)
            SELECT entr.*
            FROM wt
            JOIN entr ON entr.id=wt.id;
        RETURN;
    END; $$;


ALTER FUNCTION public.get_subtree(eid integer) OWNER TO jmdictdb;

--
-- Name: kwsrc_updseq(); Type: FUNCTION; Schema: public; Owner: jmdictdb
--

CREATE FUNCTION public.kwsrc_updseq() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
    $$;


ALTER FUNCTION public.kwsrc_updseq() OWNER TO jmdictdb;

--
-- Name: syncseq(); Type: FUNCTION; Schema: public; Owner: jmdictdb
--

CREATE FUNCTION public.syncseq() RETURNS void
    LANGUAGE plpgsql
    AS $$
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
    $$;


ALTER FUNCTION public.syncseq() OWNER TO jmdictdb;

--
-- Name: chr; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.chr (
    entr integer NOT NULL,
    chr character(1) NOT NULL,
    bushu smallint,
    strokes smallint,
    freq smallint,
    grade smallint,
    jlpt smallint,
    radname character varying(50)
);


ALTER TABLE imp.chr OWNER TO jmdictdb;

--
-- Name: cinf; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.cinf (
    entr integer NOT NULL,
    kw smallint NOT NULL,
    value character varying(50) NOT NULL,
    mctype character varying(50) DEFAULT ''::character varying NOT NULL
);


ALTER TABLE imp.cinf OWNER TO jmdictdb;

--
-- Name: dial; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.dial (
    entr integer NOT NULL,
    sens integer NOT NULL,
    ord smallint NOT NULL,
    kw smallint DEFAULT 1 NOT NULL
);


ALTER TABLE imp.dial OWNER TO jmdictdb;

--
-- Name: entr; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.entr (
    id integer NOT NULL,
    src smallint NOT NULL,
    stat smallint NOT NULL,
    seq bigint NOT NULL,
    dfrm integer,
    unap boolean NOT NULL,
    srcnote character varying(255),
    notes text,
    CONSTRAINT entr_seq_check CHECK ((seq > 0))
);


ALTER TABLE imp.entr OWNER TO jmdictdb;

--
-- Name: entr_id_seq; Type: SEQUENCE; Schema: imp; Owner: jmdictdb
--

CREATE SEQUENCE imp.entr_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE imp.entr_id_seq OWNER TO jmdictdb;

--
-- Name: entr_id_seq; Type: SEQUENCE OWNED BY; Schema: imp; Owner: jmdictdb
--

ALTER SEQUENCE imp.entr_id_seq OWNED BY imp.entr.id;


--
-- Name: fld; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.fld (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    ord smallint NOT NULL,
    kw smallint NOT NULL
);


ALTER TABLE imp.fld OWNER TO jmdictdb;

--
-- Name: freq; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.freq (
    entr integer NOT NULL,
    rdng smallint,
    kanj smallint,
    kw smallint NOT NULL,
    value integer,
    CONSTRAINT freq_check CHECK (((rdng IS NOT NULL) <> (kanj IS NOT NULL)))
);


ALTER TABLE imp.freq OWNER TO jmdictdb;

--
-- Name: gloss; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.gloss (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    gloss smallint NOT NULL,
    lang smallint DEFAULT 1 NOT NULL,
    ginf smallint DEFAULT 1 NOT NULL,
    txt character varying(2048) NOT NULL,
    CONSTRAINT gloss_gloss_check CHECK ((gloss > 0))
);


ALTER TABLE imp.gloss OWNER TO jmdictdb;

--
-- Name: grp; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.grp (
    entr integer NOT NULL,
    kw integer NOT NULL,
    ord integer NOT NULL,
    notes character varying(250)
);


ALTER TABLE imp.grp OWNER TO jmdictdb;

--
-- Name: hist; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.hist (
    entr integer NOT NULL,
    hist smallint NOT NULL,
    stat smallint NOT NULL,
    unap boolean NOT NULL,
    dt timestamp without time zone DEFAULT now() NOT NULL,
    userid character varying(20),
    name character varying(60),
    email character varying(120),
    diff text,
    refs text,
    notes text,
    CONSTRAINT hist_hist_check CHECK ((hist > 0))
);


ALTER TABLE imp.hist OWNER TO jmdictdb;

--
-- Name: kanj; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.kanj (
    entr integer NOT NULL,
    kanj smallint NOT NULL,
    txt character varying(2048) NOT NULL,
    CONSTRAINT kanj_kanj_check CHECK ((kanj > 0))
);


ALTER TABLE imp.kanj OWNER TO jmdictdb;

--
-- Name: kinf; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.kinf (
    entr integer NOT NULL,
    kanj smallint NOT NULL,
    ord smallint NOT NULL,
    kw smallint NOT NULL
);


ALTER TABLE imp.kinf OWNER TO jmdictdb;

--
-- Name: kresolv; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.kresolv (
    entr integer NOT NULL,
    kw smallint NOT NULL,
    value character varying(50) NOT NULL
);


ALTER TABLE imp.kresolv OWNER TO jmdictdb;

--
-- Name: kwsrc; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.kwsrc (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255),
    dt date,
    notes character varying(255),
    seq character varying(20) NOT NULL,
    sinc smallint,
    smin bigint,
    smax bigint,
    srct smallint NOT NULL
);


ALTER TABLE imp.kwsrc OWNER TO jmdictdb;

--
-- Name: lsrc; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.lsrc (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    ord smallint NOT NULL,
    lang smallint DEFAULT 1 NOT NULL,
    txt character varying(250) NOT NULL,
    part boolean DEFAULT false,
    wasei boolean DEFAULT false
);


ALTER TABLE imp.lsrc OWNER TO jmdictdb;

--
-- Name: misc; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.misc (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    ord smallint NOT NULL,
    kw smallint NOT NULL
);


ALTER TABLE imp.misc OWNER TO jmdictdb;

--
-- Name: pos; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.pos (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    ord smallint NOT NULL,
    kw smallint NOT NULL
);


ALTER TABLE imp.pos OWNER TO jmdictdb;

--
-- Name: rdng; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.rdng (
    entr integer NOT NULL,
    rdng smallint NOT NULL,
    txt character varying(2048) NOT NULL,
    CONSTRAINT rdng_rdng_check CHECK ((rdng > 0))
);


ALTER TABLE imp.rdng OWNER TO jmdictdb;

--
-- Name: restr; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.restr (
    entr integer NOT NULL,
    rdng smallint NOT NULL,
    kanj smallint NOT NULL
);


ALTER TABLE imp.restr OWNER TO jmdictdb;

--
-- Name: rinf; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.rinf (
    entr integer NOT NULL,
    rdng smallint NOT NULL,
    ord smallint NOT NULL,
    kw smallint NOT NULL
);


ALTER TABLE imp.rinf OWNER TO jmdictdb;

--
-- Name: sens; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.sens (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    notes text,
    CONSTRAINT sens_sens_check CHECK ((sens > 0))
);


ALTER TABLE imp.sens OWNER TO jmdictdb;

--
-- Name: stagk; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.stagk (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    kanj smallint NOT NULL
);


ALTER TABLE imp.stagk OWNER TO jmdictdb;

--
-- Name: stagr; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.stagr (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    rdng smallint NOT NULL
);


ALTER TABLE imp.stagr OWNER TO jmdictdb;

--
-- Name: xref; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.xref (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    xref smallint NOT NULL,
    typ smallint NOT NULL,
    xentr integer NOT NULL,
    xsens smallint NOT NULL,
    rdng smallint,
    kanj smallint,
    notes text,
    nosens boolean DEFAULT false NOT NULL,
    lowpri boolean DEFAULT false NOT NULL,
    CONSTRAINT xref_check CHECK ((xentr <> entr)),
    CONSTRAINT xref_check1 CHECK (((kanj IS NOT NULL) OR (rdng IS NOT NULL))),
    CONSTRAINT xref_xref_check CHECK ((xref > 0))
);


ALTER TABLE imp.xref OWNER TO jmdictdb;

--
-- Name: xresolv; Type: TABLE; Schema: imp; Owner: jmdictdb
--

CREATE TABLE imp.xresolv (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    typ smallint NOT NULL,
    ord smallint NOT NULL,
    rtxt character varying(250),
    ktxt character varying(250),
    tsens smallint,
    notes character varying(250),
    prio boolean DEFAULT false,
    CONSTRAINT xresolv_check CHECK (((rtxt IS NOT NULL) OR (ktxt IS NOT NULL)))
);


ALTER TABLE imp.xresolv OWNER TO jmdictdb;

--
-- Name: chr; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.chr (
    entr integer NOT NULL,
    chr character(1) NOT NULL,
    bushu smallint,
    strokes smallint,
    freq smallint,
    grade smallint,
    jlpt smallint,
    radname character varying(50)
);


ALTER TABLE public.chr OWNER TO jmdictdb;

--
-- Name: cinf; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.cinf (
    entr integer NOT NULL,
    kw smallint NOT NULL,
    value character varying(50) NOT NULL,
    mctype character varying(50) DEFAULT ''::character varying NOT NULL
);


ALTER TABLE public.cinf OWNER TO jmdictdb;

--
-- Name: conj; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.conj (
    id smallint NOT NULL,
    name character varying(50)
);


ALTER TABLE public.conj OWNER TO jmdictdb;

--
-- Name: conjo; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.conjo (
    pos smallint NOT NULL,
    conj smallint NOT NULL,
    neg boolean DEFAULT false NOT NULL,
    fml boolean DEFAULT false NOT NULL,
    onum smallint DEFAULT 1 NOT NULL,
    stem smallint DEFAULT 1,
    okuri character varying(50) NOT NULL,
    euphr character varying(50) DEFAULT NULL::character varying,
    euphk character varying(50) DEFAULT NULL::character varying,
    pos2 smallint
);


ALTER TABLE public.conjo OWNER TO jmdictdb;

--
-- Name: conjo_notes; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.conjo_notes (
    pos smallint NOT NULL,
    conj smallint NOT NULL,
    neg boolean NOT NULL,
    fml boolean NOT NULL,
    onum smallint NOT NULL,
    note smallint NOT NULL
);


ALTER TABLE public.conjo_notes OWNER TO jmdictdb;

--
-- Name: conotes; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.conotes (
    id integer NOT NULL,
    txt text NOT NULL
);


ALTER TABLE public.conotes OWNER TO jmdictdb;

--
-- Name: db; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.db (
    id integer NOT NULL,
    active boolean DEFAULT true,
    ts timestamp without time zone DEFAULT now()
);


ALTER TABLE public.db OWNER TO jmdictdb;

--
-- Name: dbx; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.dbx AS
 SELECT lpad(to_hex(db.id), 6, '0'::text) AS id,
    db.active,
    db.ts
   FROM public.db
  ORDER BY db.ts DESC;


ALTER TABLE public.dbx OWNER TO jmdictdb;

--
-- Name: dial; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.dial (
    entr integer NOT NULL,
    sens integer NOT NULL,
    ord smallint NOT NULL,
    kw smallint DEFAULT 1 NOT NULL
);


ALTER TABLE public.dial OWNER TO jmdictdb;

--
-- Name: entr_id_seq; Type: SEQUENCE; Schema: public; Owner: jmdictdb
--

CREATE SEQUENCE public.entr_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.entr_id_seq OWNER TO jmdictdb;

--
-- Name: entr_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jmdictdb
--

ALTER SEQUENCE public.entr_id_seq OWNED BY public.entr.id;


--
-- Name: entrsnd; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.entrsnd (
    entr integer NOT NULL,
    ord smallint NOT NULL,
    snd integer NOT NULL
);


ALTER TABLE public.entrsnd OWNER TO jmdictdb;

--
-- Name: gloss; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.gloss (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    gloss smallint NOT NULL,
    lang smallint DEFAULT 1 NOT NULL,
    ginf smallint DEFAULT 1 NOT NULL,
    txt character varying(2048) NOT NULL,
    CONSTRAINT gloss_gloss_check CHECK ((gloss > 0))
);


ALTER TABLE public.gloss OWNER TO jmdictdb;

--
-- Name: kanj; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kanj (
    entr integer NOT NULL,
    kanj smallint NOT NULL,
    txt character varying(2048) NOT NULL,
    CONSTRAINT kanj_kanj_check CHECK ((kanj > 0))
);


ALTER TABLE public.kanj OWNER TO jmdictdb;

--
-- Name: rdng; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.rdng (
    entr integer NOT NULL,
    rdng smallint NOT NULL,
    txt character varying(2048) NOT NULL,
    CONSTRAINT rdng_rdng_check CHECK ((rdng > 0))
);


ALTER TABLE public.rdng OWNER TO jmdictdb;

--
-- Name: hdwds; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.hdwds AS
 SELECT e.id,
    e.src,
    e.stat,
    e.seq,
    e.dfrm,
    e.unap,
    e.srcnote,
    e.notes,
    r.txt AS rtxt,
    k.txt AS ktxt
   FROM ((public.entr e
     LEFT JOIN public.rdng r ON ((r.entr = e.id)))
     LEFT JOIN public.kanj k ON ((k.entr = e.id)))
  WHERE (((r.rdng = 1) OR (r.rdng IS NULL)) AND ((k.kanj = 1) OR (k.kanj IS NULL)));


ALTER TABLE public.hdwds OWNER TO jmdictdb;

--
-- Name: sens; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.sens (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    notes text,
    CONSTRAINT sens_sens_check CHECK ((sens > 0))
);


ALTER TABLE public.sens OWNER TO jmdictdb;

--
-- Name: ssum; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.ssum AS
 SELECT s.entr,
    s.sens,
    ( SELECT array_to_string(array_agg(sg.txt), '; '::text) AS array_to_string
           FROM ( SELECT g.txt
                   FROM public.gloss g
                  WHERE ((g.sens = s.sens) AND (g.entr = s.entr))
                  ORDER BY g.gloss) sg
          ORDER BY s.entr, s.sens) AS gloss,
    s.notes
   FROM public.sens s;


ALTER TABLE public.ssum OWNER TO jmdictdb;

--
-- Name: essum; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.essum AS
 SELECT e.id,
    e.seq,
    e.src,
    e.stat,
    s.sens,
    h.rtxt AS rdng,
    h.ktxt AS kanj,
    s.gloss,
    ( SELECT count(*) AS count
           FROM public.sens
          WHERE (sens.entr = e.id)) AS nsens
   FROM ((public.entr e
     JOIN public.hdwds h ON ((h.id = e.id)))
     JOIN public.ssum s ON ((s.entr = e.id)));


ALTER TABLE public.essum OWNER TO jmdictdb;

--
-- Name: freq; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.freq (
    entr integer NOT NULL,
    rdng smallint,
    kanj smallint,
    kw smallint NOT NULL,
    value integer,
    CONSTRAINT freq_check CHECK (((rdng IS NOT NULL) <> (kanj IS NOT NULL)))
);


ALTER TABLE public.freq OWNER TO jmdictdb;

--
-- Name: is_p; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.is_p AS
 SELECT e.id,
    e.src,
    e.stat,
    e.seq,
    e.dfrm,
    e.unap,
    e.srcnote,
    e.notes,
    (EXISTS ( SELECT f.entr,
            f.rdng,
            f.kanj,
            f.kw,
            f.value
           FROM public.freq f
          WHERE ((f.entr = e.id) AND (((f.kw = ANY (ARRAY[1, 2, 7])) AND (f.value = 1)) OR (f.kw = 4))))) AS p
   FROM public.entr e;


ALTER TABLE public.is_p OWNER TO jmdictdb;

--
-- Name: esum; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.esum AS
 SELECT e.id,
    e.seq,
    e.stat,
    e.src,
    e.dfrm,
    e.unap,
    e.notes,
    e.srcnote,
    h.rtxt AS rdng,
    h.ktxt AS kanj,
    ( SELECT array_to_string(array_agg(ss.gtxt), ' / '::text) AS array_to_string
           FROM ( SELECT ( SELECT array_to_string(array_agg(sg.txt), '; '::text) AS array_to_string
                           FROM ( SELECT g.txt
                                   FROM public.gloss g
                                  WHERE ((g.sens = s.sens) AND (g.entr = s.entr))
                                  ORDER BY g.gloss) sg
                          ORDER BY s.entr, s.sens) AS gtxt
                   FROM public.sens s
                  WHERE (s.entr = e.id)
                  ORDER BY s.sens) ss) AS gloss,
    ( SELECT count(*) AS count
           FROM public.sens
          WHERE (sens.entr = e.id)) AS nsens,
    ( SELECT is_p.p
           FROM public.is_p
          WHERE (is_p.id = e.id)) AS p
   FROM (public.entr e
     JOIN public.hdwds h ON ((h.id = e.id)));


ALTER TABLE public.esum OWNER TO jmdictdb;

--
-- Name: fld; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.fld (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    ord smallint NOT NULL,
    kw smallint NOT NULL
);


ALTER TABLE public.fld OWNER TO jmdictdb;

--
-- Name: grp; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.grp (
    entr integer NOT NULL,
    kw integer NOT NULL,
    ord integer NOT NULL,
    notes character varying(250)
);


ALTER TABLE public.grp OWNER TO jmdictdb;

--
-- Name: hist; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.hist (
    entr integer NOT NULL,
    hist smallint NOT NULL,
    stat smallint NOT NULL,
    unap boolean NOT NULL,
    dt timestamp without time zone DEFAULT now() NOT NULL,
    userid character varying(20),
    name character varying(60),
    email character varying(120),
    diff text,
    refs text,
    notes text,
    CONSTRAINT hist_hist_check CHECK ((hist > 0))
);


ALTER TABLE public.hist OWNER TO jmdictdb;

--
-- Name: item_cnts; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.item_cnts AS
 SELECT e.id,
    e.seq,
    ( SELECT count(*) AS count
           FROM public.rdng r
          WHERE (r.entr = e.id)) AS nrdng,
    ( SELECT count(*) AS count
           FROM public.kanj k
          WHERE (k.entr = e.id)) AS nkanj,
    ( SELECT count(*) AS count
           FROM public.sens s
          WHERE (s.entr = e.id)) AS nsens
   FROM public.entr e;


ALTER TABLE public.item_cnts OWNER TO jmdictdb;

--
-- Name: kinf; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kinf (
    entr integer NOT NULL,
    kanj smallint NOT NULL,
    ord smallint NOT NULL,
    kw smallint NOT NULL
);


ALTER TABLE public.kinf OWNER TO jmdictdb;

--
-- Name: kresolv; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kresolv (
    entr integer NOT NULL,
    kw smallint NOT NULL,
    value character varying(50) NOT NULL
);


ALTER TABLE public.kresolv OWNER TO jmdictdb;

--
-- Name: kwcinf; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwcinf (
    id smallint NOT NULL,
    kw character varying(50) NOT NULL,
    descr character varying(250)
);


ALTER TABLE public.kwcinf OWNER TO jmdictdb;

--
-- Name: kwdial; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwdial (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255)
);


ALTER TABLE public.kwdial OWNER TO jmdictdb;

--
-- Name: kwfld; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwfld (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255)
);


ALTER TABLE public.kwfld OWNER TO jmdictdb;

--
-- Name: kwfreq; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwfreq (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255)
);


ALTER TABLE public.kwfreq OWNER TO jmdictdb;

--
-- Name: kwginf; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwginf (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255)
);


ALTER TABLE public.kwginf OWNER TO jmdictdb;

--
-- Name: kwgrp; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwgrp (
    id integer NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255)
);


ALTER TABLE public.kwgrp OWNER TO jmdictdb;

--
-- Name: kwgrp_id_seq; Type: SEQUENCE; Schema: public; Owner: jmdictdb
--

CREATE SEQUENCE public.kwgrp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.kwgrp_id_seq OWNER TO jmdictdb;

--
-- Name: kwgrp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jmdictdb
--

ALTER SEQUENCE public.kwgrp_id_seq OWNED BY public.kwgrp.id;


--
-- Name: kwkinf; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwkinf (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255)
);


ALTER TABLE public.kwkinf OWNER TO jmdictdb;

--
-- Name: kwlang; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwlang (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255)
);


ALTER TABLE public.kwlang OWNER TO jmdictdb;

--
-- Name: kwmisc; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwmisc (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255)
);


ALTER TABLE public.kwmisc OWNER TO jmdictdb;

--
-- Name: kwpos; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwpos (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255)
);


ALTER TABLE public.kwpos OWNER TO jmdictdb;

--
-- Name: kwrinf; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwrinf (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255)
);


ALTER TABLE public.kwrinf OWNER TO jmdictdb;

--
-- Name: kwsrc; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwsrc (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255),
    dt date,
    notes character varying(255),
    seq character varying(20) NOT NULL,
    sinc smallint,
    smin bigint,
    smax bigint,
    srct smallint NOT NULL
);


ALTER TABLE public.kwsrc OWNER TO jmdictdb;

--
-- Name: kwsrct; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwsrct (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255)
);


ALTER TABLE public.kwsrct OWNER TO jmdictdb;

--
-- Name: kwstat; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwstat (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255)
);


ALTER TABLE public.kwstat OWNER TO jmdictdb;

--
-- Name: kwxref; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.kwxref (
    id smallint NOT NULL,
    kw character varying(20) NOT NULL,
    descr character varying(255)
);


ALTER TABLE public.kwxref OWNER TO jmdictdb;

--
-- Name: lsrc; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.lsrc (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    ord smallint NOT NULL,
    lang smallint DEFAULT 1 NOT NULL,
    txt character varying(250) NOT NULL,
    part boolean DEFAULT false,
    wasei boolean DEFAULT false
);


ALTER TABLE public.lsrc OWNER TO jmdictdb;

--
-- Name: misc; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.misc (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    ord smallint NOT NULL,
    kw smallint NOT NULL
);


ALTER TABLE public.misc OWNER TO jmdictdb;

--
-- Name: pos; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.pos (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    ord smallint NOT NULL,
    kw smallint NOT NULL
);


ALTER TABLE public.pos OWNER TO jmdictdb;

--
-- Name: rad; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.rad (
    num smallint NOT NULL,
    var smallint NOT NULL,
    rchr character(1),
    chr character(1),
    strokes smallint,
    loc character(1),
    name character varying(50),
    examples character varying(20),
    CONSTRAINT rad_loc_check CHECK (((loc IS NULL) OR (loc = ANY (ARRAY['O'::bpchar, 'T'::bpchar, 'B'::bpchar, 'R'::bpchar, 'L'::bpchar, 'E'::bpchar, 'V'::bpchar]))))
);


ALTER TABLE public.rad OWNER TO jmdictdb;

--
-- Name: rdngsnd; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.rdngsnd (
    entr integer NOT NULL,
    rdng integer NOT NULL,
    ord smallint NOT NULL,
    snd integer NOT NULL
);


ALTER TABLE public.rdngsnd OWNER TO jmdictdb;

--
-- Name: restr; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.restr (
    entr integer NOT NULL,
    rdng smallint NOT NULL,
    kanj smallint NOT NULL
);


ALTER TABLE public.restr OWNER TO jmdictdb;

--
-- Name: re_nokanji; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.re_nokanji AS
 SELECT e.id,
    e.seq,
    r.rdng,
    r.txt
   FROM ((public.entr e
     JOIN public.rdng r ON ((r.entr = e.id)))
     JOIN public.restr z ON (((z.entr = r.entr) AND (z.rdng = r.rdng))))
  GROUP BY e.id, e.seq, r.rdng, r.txt
 HAVING (count(z.kanj) = ( SELECT count(*) AS count
           FROM public.kanj k
          WHERE (k.entr = e.id)));


ALTER TABLE public.re_nokanji OWNER TO jmdictdb;

--
-- Name: rinf; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.rinf (
    entr integer NOT NULL,
    rdng smallint NOT NULL,
    ord smallint NOT NULL,
    kw smallint NOT NULL
);


ALTER TABLE public.rinf OWNER TO jmdictdb;

--
-- Name: rk_valid; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.rk_valid AS
 SELECT r.entr,
    r.rdng,
    r.txt AS rtxt,
    k.kanj,
    k.txt AS ktxt
   FROM (public.rdng r
     JOIN public.kanj k ON ((k.entr = r.entr)))
  WHERE (NOT (EXISTS ( SELECT z.entr,
            z.rdng,
            z.kanj
           FROM public.restr z
          WHERE ((z.entr = r.entr) AND (z.kanj = k.kanj) AND (z.rdng = r.rdng)))));


ALTER TABLE public.rk_valid OWNER TO jmdictdb;

--
-- Name: rk_validity; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.rk_validity AS
 SELECT e.id,
    e.seq,
    r.rdng,
    r.txt AS rtxt,
    k.kanj,
    k.txt AS ktxt,
        CASE
            WHEN (z.kanj IS NOT NULL) THEN 'X'::text
            ELSE NULL::text
        END AS valid
   FROM (((public.entr e
     LEFT JOIN public.rdng r ON ((r.entr = e.id)))
     LEFT JOIN public.kanj k ON ((k.entr = e.id)))
     LEFT JOIN public.restr z ON (((z.entr = e.id) AND (r.rdng = z.rdng) AND (k.kanj = z.kanj))));


ALTER TABLE public.rk_validity OWNER TO jmdictdb;

--
-- Name: seq_jmdict; Type: SEQUENCE; Schema: public; Owner: jmdictdb
--

CREATE SEQUENCE public.seq_jmdict
    START WITH 1000000
    INCREMENT BY 10
    MINVALUE 1000000
    MAXVALUE 8999999
    CACHE 1;


ALTER TABLE public.seq_jmdict OWNER TO jmdictdb;

--
-- Name: seq_jmnedict; Type: SEQUENCE; Schema: public; Owner: jmdictdb
--

CREATE SEQUENCE public.seq_jmnedict
    START WITH 1000000
    INCREMENT BY 10
    MINVALUE 1000000
    MAXVALUE 8999999
    CACHE 1;


ALTER TABLE public.seq_jmnedict OWNER TO jmdictdb;

--
-- Name: seq_test; Type: SEQUENCE; Schema: public; Owner: jmdictdb
--

CREATE SEQUENCE public.seq_test
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seq_test OWNER TO jmdictdb;

--
-- Name: stagk; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.stagk (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    kanj smallint NOT NULL
);


ALTER TABLE public.stagk OWNER TO jmdictdb;

--
-- Name: sk_valid; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.sk_valid AS
 SELECT s.entr,
    s.sens,
    k.kanj,
    k.txt AS ktxt
   FROM (public.sens s
     JOIN public.kanj k ON ((k.entr = s.entr)))
  WHERE (NOT (EXISTS ( SELECT z.entr,
            z.sens,
            z.kanj
           FROM public.stagk z
          WHERE ((z.entr = s.entr) AND (z.sens = s.sens) AND (z.kanj = k.kanj)))));


ALTER TABLE public.sk_valid OWNER TO jmdictdb;

--
-- Name: snd; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.snd (
    id integer NOT NULL,
    file smallint NOT NULL,
    strt integer DEFAULT 0 NOT NULL,
    leng integer DEFAULT 0 NOT NULL,
    trns text,
    notes character varying(255)
);


ALTER TABLE public.snd OWNER TO jmdictdb;

--
-- Name: snd_id_seq; Type: SEQUENCE; Schema: public; Owner: jmdictdb
--

CREATE SEQUENCE public.snd_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.snd_id_seq OWNER TO jmdictdb;

--
-- Name: snd_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jmdictdb
--

ALTER SEQUENCE public.snd_id_seq OWNED BY public.snd.id;


--
-- Name: sndfile; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.sndfile (
    id integer NOT NULL,
    vol integer NOT NULL,
    title character varying(50),
    loc character varying(500),
    type smallint,
    notes text
);


ALTER TABLE public.sndfile OWNER TO jmdictdb;

--
-- Name: sndfile_id_seq; Type: SEQUENCE; Schema: public; Owner: jmdictdb
--

CREATE SEQUENCE public.sndfile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sndfile_id_seq OWNER TO jmdictdb;

--
-- Name: sndfile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jmdictdb
--

ALTER SEQUENCE public.sndfile_id_seq OWNED BY public.sndfile.id;


--
-- Name: sndvol; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.sndvol (
    id integer NOT NULL,
    title character varying(50),
    loc character varying(500),
    type smallint NOT NULL,
    idstr character varying(100),
    corp integer,
    notes text
);


ALTER TABLE public.sndvol OWNER TO jmdictdb;

--
-- Name: sndvol_id_seq; Type: SEQUENCE; Schema: public; Owner: jmdictdb
--

CREATE SEQUENCE public.sndvol_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sndvol_id_seq OWNER TO jmdictdb;

--
-- Name: sndvol_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jmdictdb
--

ALTER SEQUENCE public.sndvol_id_seq OWNED BY public.sndvol.id;


--
-- Name: stagr; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.stagr (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    rdng smallint NOT NULL
);


ALTER TABLE public.stagr OWNER TO jmdictdb;

--
-- Name: sr_valid; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.sr_valid AS
 SELECT s.entr,
    s.sens,
    r.rdng,
    r.txt AS rtxt
   FROM (public.sens s
     JOIN public.rdng r ON ((r.entr = s.entr)))
  WHERE (NOT (EXISTS ( SELECT z.entr,
            z.sens,
            z.rdng
           FROM public.stagr z
          WHERE ((z.entr = s.entr) AND (z.sens = s.sens) AND (z.rdng = r.rdng)))));


ALTER TABLE public.sr_valid OWNER TO jmdictdb;

--
-- Name: testsrc; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.testsrc (
    filename text,
    method text,
    hash text
);


ALTER TABLE public.testsrc OWNER TO jmdictdb;

--
-- Name: vconj; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.vconj AS
 SELECT conjo.pos,
    kwpos.kw AS ptxt,
    conj.id AS conj,
    conj.name AS ctxt,
    conjo.neg,
    conjo.fml
   FROM ((public.conj
     JOIN public.conjo ON ((conj.id = conjo.conj)))
     JOIN public.kwpos ON ((kwpos.id = conjo.pos)))
  ORDER BY conjo.pos, conjo.conj, conjo.neg, conjo.fml;


ALTER TABLE public.vconj OWNER TO jmdictdb;

--
-- Name: vconotes; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.vconotes AS
 SELECT DISTINCT k.id AS pos,
    k.kw AS ptxt,
    m.id,
    m.txt
   FROM (((public.kwpos k
     JOIN public.conjo c ON ((c.pos = k.id)))
     JOIN public.conjo_notes n ON ((n.pos = c.pos)))
     JOIN public.conotes m ON ((m.id = n.note)))
  ORDER BY m.id;


ALTER TABLE public.vconotes OWNER TO jmdictdb;

--
-- Name: vcopos; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.vcopos AS
 SELECT p.id,
    p.kw,
    p.descr
   FROM (public.kwpos p
     JOIN ( SELECT DISTINCT conjo.pos
           FROM public.conjo) c ON ((c.pos = p.id)));


ALTER TABLE public.vcopos OWNER TO jmdictdb;

--
-- Name: vinfl; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.vinfl AS
 SELECT u.id,
    u.seq,
    u.src,
    u.unap,
    u.pos,
    u.ptxt,
    u.knum,
    u.ktxt,
    u.rnum,
    u.rtxt,
    u.conj,
    u.ctxt,
    u.neg,
    u.fml,
    ((
        CASE
            WHEN u.neg THEN 'neg'::text
            ELSE 'aff'::text
        END || '-'::text) ||
        CASE
            WHEN u.fml THEN 'polite'::text
            ELSE 'plain'::text
        END) AS t,
    u.onum,
    (
        CASE
            WHEN ((u.ktxt)::text ~ '[^あ-ん].$'::text) THEN COALESCE(("left"((u.ktxt)::text, ((length((u.ktxt)::text) - u.stem) - 1)) || (u.euphk)::text), "left"((u.ktxt)::text, (length((u.ktxt)::text) - u.stem)))
            ELSE COALESCE(("left"((u.ktxt)::text, ((length((u.ktxt)::text) - u.stem) - 1)) || (u.euphr)::text), "left"((u.ktxt)::text, (length((u.ktxt)::text) - u.stem)))
        END || (u.okuri)::text) AS kitxt,
    (COALESCE(("left"((u.rtxt)::text, ((length((u.rtxt)::text) - u.stem) - 1)) || (u.euphr)::text), "left"((u.rtxt)::text, (length((u.rtxt)::text) - u.stem))) || (u.okuri)::text) AS ritxt,
    ( SELECT array_agg(n.note ORDER BY n.note) AS array_agg
           FROM public.conjo_notes n
          WHERE ((u.pos = n.pos) AND (u.conj = n.conj) AND (u.neg = n.neg) AND (u.fml = n.fml) AND (u.onum = n.onum))) AS notes
   FROM ( SELECT DISTINCT entr.id,
            entr.seq,
            entr.src,
            entr.unap,
            kanj.txt AS ktxt,
            rdng.txt AS rtxt,
            pos.kw AS pos,
            kwpos.kw AS ptxt,
            conj.id AS conj,
            conj.name AS ctxt,
            conjo.onum,
            conjo.okuri,
            conjo.neg,
            conjo.fml,
            kanj.kanj AS knum,
            rdng.rdng AS rnum,
            conjo.stem,
            conjo.euphr,
            conjo.euphk
           FROM (((((((public.entr
             JOIN public.sens ON ((entr.id = sens.entr)))
             JOIN public.pos ON (((pos.entr = sens.entr) AND (pos.sens = sens.sens))))
             JOIN public.kwpos ON ((kwpos.id = pos.kw)))
             JOIN public.conjo ON ((conjo.pos = pos.kw)))
             JOIN public.conj ON ((conj.id = conjo.conj)))
             LEFT JOIN public.kanj ON ((entr.id = kanj.entr)))
             LEFT JOIN public.rdng ON ((entr.id = rdng.entr)))
          WHERE ((conjo.okuri IS NOT NULL) AND (NOT (EXISTS ( SELECT 1
                   FROM public.stagr
                  WHERE ((stagr.entr = entr.id) AND (stagr.sens = sens.sens) AND (stagr.rdng = rdng.rdng))))) AND (NOT (EXISTS ( SELECT 1
                   FROM public.stagk
                  WHERE ((stagk.entr = entr.id) AND (stagk.sens = sens.sens) AND (stagk.kanj = kanj.kanj))))) AND (NOT (EXISTS ( SELECT 1
                   FROM public.restr
                  WHERE ((restr.entr = entr.id) AND (restr.rdng = rdng.rdng) AND (restr.kanj = kanj.kanj))))))) u
  ORDER BY u.id, u.pos, u.knum, u.rnum, u.conj, u.neg, u.fml, u.onum;


ALTER TABLE public.vinfl OWNER TO jmdictdb;

--
-- Name: vinflxt_; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.vinflxt_ AS
 SELECT vinfl.id,
    vinfl.seq,
    vinfl.src,
    vinfl.unap,
    vinfl.pos,
    vinfl.ptxt,
    vinfl.knum,
    vinfl.ktxt,
    vinfl.rnum,
    vinfl.rtxt,
    vinfl.conj,
    vinfl.ctxt,
    vinfl.t,
    string_agg(((((((COALESCE(vinfl.kitxt, ''::text) ||
        CASE
            WHEN (vinfl.kitxt IS NOT NULL) THEN '【'::text
            ELSE ''::text
        END) || COALESCE(vinfl.ritxt, ''::text)) ||
        CASE
            WHEN (vinfl.kitxt IS NOT NULL) THEN '】'::text
            ELSE ''::text
        END) ||
        CASE
            WHEN (vinfl.notes IS NOT NULL) THEN ' ['::text
            ELSE ''::text
        END) || COALESCE(array_to_string(vinfl.notes, ','::text), ''::text)) ||
        CASE
            WHEN (vinfl.notes IS NOT NULL) THEN ']'::text
            ELSE ''::text
        END), ',
'::text ORDER BY vinfl.onum) AS word
   FROM public.vinfl
  GROUP BY vinfl.id, vinfl.seq, vinfl.src, vinfl.unap, vinfl.pos, vinfl.ptxt, vinfl.knum, vinfl.ktxt, vinfl.rnum, vinfl.rtxt, vinfl.conj, vinfl.ctxt, vinfl.t
  ORDER BY vinfl.id, vinfl.pos, vinfl.ptxt, vinfl.knum, vinfl.rnum, vinfl.conj;


ALTER TABLE public.vinflxt_ OWNER TO jmdictdb;

--
-- Name: vinflxt; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.vinflxt AS
 SELECT vinflxt_.id,
    vinflxt_.seq,
    vinflxt_.src,
    vinflxt_.unap,
    vinflxt_.pos,
    vinflxt_.ptxt,
    vinflxt_.knum,
    vinflxt_.ktxt,
    vinflxt_.rnum,
    vinflxt_.rtxt,
    vinflxt_.conj,
    vinflxt_.ctxt,
    min(
        CASE vinflxt_.t
            WHEN 'aff-plain'::text THEN vinflxt_.word
            ELSE NULL::text
        END) AS w0,
    min(
        CASE vinflxt_.t
            WHEN 'aff-polite'::text THEN vinflxt_.word
            ELSE NULL::text
        END) AS w1,
    min(
        CASE vinflxt_.t
            WHEN 'neg-plain'::text THEN vinflxt_.word
            ELSE NULL::text
        END) AS w2,
    min(
        CASE vinflxt_.t
            WHEN 'neg-polite'::text THEN vinflxt_.word
            ELSE NULL::text
        END) AS w3
   FROM public.vinflxt_
  GROUP BY vinflxt_.id, vinflxt_.seq, vinflxt_.src, vinflxt_.unap, vinflxt_.pos, vinflxt_.ptxt, vinflxt_.knum, vinflxt_.ktxt, vinflxt_.rnum, vinflxt_.rtxt, vinflxt_.conj, vinflxt_.ctxt
  ORDER BY vinflxt_.id, vinflxt_.pos, vinflxt_.knum, vinflxt_.rnum, vinflxt_.conj;


ALTER TABLE public.vinflxt OWNER TO jmdictdb;

--
-- Name: vrkrestr; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.vrkrestr AS
 SELECT e.id,
    e.src,
    e.stat,
    e.unap,
    r.rdng,
    r.txt AS rtxt,
    rk.kanj,
    rk.txt AS ktxt,
    ( SELECT count(*) AS count
           FROM public.sens s
          WHERE (s.entr = e.id)) AS nsens
   FROM ((public.entr e
     JOIN public.rdng r ON ((r.entr = e.id)))
     LEFT JOIN ( SELECT r_1.entr,
            r_1.rdng,
            k.kanj,
            k.txt
           FROM ((public.rdng r_1
             LEFT JOIN public.kanj k ON ((k.entr = r_1.entr)))
             LEFT JOIN public.restr j ON (((j.entr = r_1.entr) AND (j.rdng = r_1.rdng) AND (j.kanj = k.kanj))))
          WHERE (j.rdng IS NULL)) rk ON (((rk.entr = r.entr) AND (rk.rdng = r.rdng))));


ALTER TABLE public.vrkrestr OWNER TO jmdictdb;

--
-- Name: xresolv; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.xresolv (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    typ smallint NOT NULL,
    ord smallint NOT NULL,
    rtxt character varying(250),
    ktxt character varying(250),
    tsens smallint,
    notes character varying(250),
    prio boolean DEFAULT false,
    CONSTRAINT xresolv_check CHECK (((rtxt IS NOT NULL) OR (ktxt IS NOT NULL)))
);


ALTER TABLE public.xresolv OWNER TO jmdictdb;

--
-- Name: vrslv; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.vrslv AS
 SELECT v.seq,
    v.src,
    v.stat,
    v.unap,
    v.entr,
    v.sens,
    v.typ,
    v.ord,
    v.rtxt,
    v.ktxt,
    v.tsens,
    v.notes,
    v.prio,
    c.src AS tsrc,
    c.stat AS tstat,
    c.unap AS tunap,
    count(*) AS nentr,
    min(c.id) AS targ,
    c.rdng,
    c.kanj,
    false AS nokanji,
    max(c.nsens) AS nsens
   FROM (( SELECT z.entr,
            z.sens,
            z.typ,
            z.ord,
            z.rtxt,
            z.ktxt,
            z.tsens,
            z.notes,
            z.prio,
            e.seq,
            e.src,
            e.stat,
            e.unap
           FROM (public.xresolv z
             JOIN public.entr e ON ((e.id = z.entr)))
          WHERE ((z.ktxt IS NOT NULL) AND (z.rtxt IS NOT NULL))) v
     LEFT JOIN public.vrkrestr c ON ((((v.rtxt)::text = (c.rtxt)::text) AND ((v.ktxt)::text = (c.ktxt)::text) AND (v.entr <> c.id))))
  GROUP BY v.seq, v.src, v.stat, v.unap, v.entr, v.sens, v.typ, v.ord, v.rtxt, v.ktxt, v.tsens, v.notes, v.prio, c.src, c.stat, c.unap, c.rdng, c.kanj
UNION
 SELECT v.seq,
    v.src,
    v.stat,
    v.unap,
    v.entr,
    v.sens,
    v.typ,
    v.ord,
    v.rtxt,
    v.ktxt,
    v.tsens,
    v.notes,
    v.prio,
    c.src AS tsrc,
    c.stat AS tstat,
    c.unap AS tunap,
    count(*) AS nentr,
    min(c.id) AS targ,
    c.rdng,
    NULL::smallint AS kanj,
    c.nokanji,
    max(c.nsens) AS nsens
   FROM (( SELECT z.entr,
            z.sens,
            z.typ,
            z.ord,
            z.rtxt,
            z.ktxt,
            z.tsens,
            z.notes,
            z.prio,
            e.seq,
            e.src,
            e.stat,
            e.unap
           FROM (public.xresolv z
             JOIN public.entr e ON ((e.id = z.entr)))
          WHERE ((z.ktxt IS NULL) AND (z.rtxt IS NOT NULL))) v
     LEFT JOIN ( SELECT e.id,
            e.src,
            e.stat,
            e.unap,
            r.txt AS rtxt,
            r.rdng,
            ((NOT (EXISTS ( SELECT 1
                   FROM public.kanj k
                  WHERE (k.entr = e.id)))) OR (j.rdng IS NOT NULL)) AS nokanji,
            ( SELECT count(*) AS count
                   FROM public.sens s
                  WHERE (s.entr = e.id)) AS nsens
           FROM ((public.entr e
             JOIN public.rdng r ON ((r.entr = e.id)))
             LEFT JOIN public.re_nokanji j ON (((j.id = e.id) AND (j.rdng = r.rdng))))) c ON ((((v.rtxt)::text = (c.rtxt)::text) AND (v.entr <> c.id))))
  GROUP BY v.seq, v.src, v.stat, v.unap, v.entr, v.sens, v.typ, v.ord, v.rtxt, v.ktxt, v.tsens, v.notes, v.prio, c.src, c.stat, c.unap, c.rdng, c.nokanji
UNION
 SELECT v.seq,
    v.src,
    v.stat,
    v.unap,
    v.entr,
    v.sens,
    v.typ,
    v.ord,
    v.rtxt,
    v.ktxt,
    v.tsens,
    v.notes,
    v.prio,
    c.src AS tsrc,
    c.stat AS tstat,
    c.unap AS tunap,
    count(*) AS nentr,
    min(c.id) AS targ,
    NULL::smallint AS rdng,
    c.kanj,
    NULL::boolean AS nokanji,
    max(c.nsens) AS nsens
   FROM (( SELECT z.entr,
            z.sens,
            z.typ,
            z.ord,
            z.rtxt,
            z.ktxt,
            z.tsens,
            z.notes,
            z.prio,
            e.seq,
            e.src,
            e.stat,
            e.unap
           FROM (public.xresolv z
             JOIN public.entr e ON ((e.id = z.entr)))
          WHERE ((z.rtxt IS NULL) AND (z.ktxt IS NOT NULL))) v
     LEFT JOIN ( SELECT e.id,
            e.src,
            e.stat,
            e.unap,
            k.txt AS ktxt,
            k.kanj,
            ( SELECT count(*) AS count
                   FROM public.sens s
                  WHERE (s.entr = e.id)) AS nsens
           FROM (public.entr e
             JOIN public.kanj k ON ((k.entr = e.id)))) c ON ((((v.ktxt)::text = (c.ktxt)::text) AND (v.entr <> c.id))))
  GROUP BY v.seq, v.src, v.stat, v.unap, v.entr, v.sens, v.typ, v.ord, v.rtxt, v.ktxt, v.tsens, v.notes, v.prio, c.src, c.stat, c.unap, c.kanj;


ALTER TABLE public.vrslv OWNER TO jmdictdb;

--
-- Name: vsnd; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.vsnd AS
 SELECT snd.id,
    snd.strt,
    snd.leng,
    sndfile.loc AS sfile,
    sndvol.loc AS sdir,
    (sndvol.type = 2) AS iscd,
    sndvol.id AS sdid,
    snd.trns
   FROM ((public.sndvol
     JOIN public.sndfile ON ((sndvol.id = sndfile.vol)))
     JOIN public.snd ON ((sndfile.id = snd.file)));


ALTER TABLE public.vsnd OWNER TO jmdictdb;

--
-- Name: xref; Type: TABLE; Schema: public; Owner: jmdictdb
--

CREATE TABLE public.xref (
    entr integer NOT NULL,
    sens smallint NOT NULL,
    xref smallint NOT NULL,
    typ smallint NOT NULL,
    xentr integer NOT NULL,
    xsens smallint NOT NULL,
    rdng smallint,
    kanj smallint,
    notes text,
    nosens boolean DEFAULT false NOT NULL,
    lowpri boolean DEFAULT false NOT NULL,
    CONSTRAINT xref_check CHECK ((xentr <> entr)),
    CONSTRAINT xref_check1 CHECK (((kanj IS NOT NULL) OR (rdng IS NOT NULL))),
    CONSTRAINT xref_xref_check CHECK ((xref > 0))
);


ALTER TABLE public.xref OWNER TO jmdictdb;

--
-- Name: xrefhw; Type: VIEW; Schema: public; Owner: jmdictdb
--

CREATE VIEW public.xrefhw AS
 SELECT r.entr,
    rm.sens,
    r.txt AS rtxt,
    k.kanj,
    k.txt AS ktxt
   FROM (((( SELECT sr_valid.entr,
            sr_valid.sens,
            min(sr_valid.rdng) AS rdng
           FROM public.sr_valid
          GROUP BY sr_valid.entr, sr_valid.sens) rm
     JOIN public.rdng r ON (((r.entr = rm.entr) AND (r.rdng = rm.rdng))))
     LEFT JOIN ( SELECT sk_valid.entr,
            sk_valid.sens,
            min(sk_valid.kanj) AS kanj
           FROM public.sk_valid
          GROUP BY sk_valid.entr, sk_valid.sens) km ON (((km.entr = r.entr) AND (km.sens = rm.sens))))
     LEFT JOIN public.kanj k ON (((k.entr = km.entr) AND (k.kanj = km.kanj))));


ALTER TABLE public.xrefhw OWNER TO jmdictdb;

--
-- Name: entr id; Type: DEFAULT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.entr ALTER COLUMN id SET DEFAULT nextval('imp.entr_id_seq'::regclass);


--
-- Name: entr id; Type: DEFAULT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.entr ALTER COLUMN id SET DEFAULT nextval('public.entr_id_seq'::regclass);


--
-- Name: kwgrp id; Type: DEFAULT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwgrp ALTER COLUMN id SET DEFAULT nextval('public.kwgrp_id_seq'::regclass);


--
-- Name: snd id; Type: DEFAULT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.snd ALTER COLUMN id SET DEFAULT nextval('public.snd_id_seq'::regclass);


--
-- Name: sndfile id; Type: DEFAULT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.sndfile ALTER COLUMN id SET DEFAULT nextval('public.sndfile_id_seq'::regclass);


--
-- Name: sndvol id; Type: DEFAULT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.sndvol ALTER COLUMN id SET DEFAULT nextval('public.sndvol_id_seq'::regclass);


--
-- Data for Name: chr; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.chr (entr, chr, bushu, strokes, freq, grade, jlpt, radname) FROM stdin;
\.


--
-- Data for Name: cinf; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.cinf (entr, kw, value, mctype) FROM stdin;
\.


--
-- Data for Name: dial; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.dial (entr, sens, ord, kw) FROM stdin;
\.


--
-- Data for Name: entr; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.entr (id, src, stat, seq, dfrm, unap, srcnote, notes) FROM stdin;
\.


--
-- Data for Name: fld; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.fld (entr, sens, ord, kw) FROM stdin;
\.


--
-- Data for Name: freq; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.freq (entr, rdng, kanj, kw, value) FROM stdin;
\.


--
-- Data for Name: gloss; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.gloss (entr, sens, gloss, lang, ginf, txt) FROM stdin;
\.


--
-- Data for Name: grp; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.grp (entr, kw, ord, notes) FROM stdin;
\.


--
-- Data for Name: hist; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.hist (entr, hist, stat, unap, dt, userid, name, email, diff, refs, notes) FROM stdin;
\.


--
-- Data for Name: kanj; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.kanj (entr, kanj, txt) FROM stdin;
\.


--
-- Data for Name: kinf; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.kinf (entr, kanj, ord, kw) FROM stdin;
\.


--
-- Data for Name: kresolv; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.kresolv (entr, kw, value) FROM stdin;
\.


--
-- Data for Name: kwsrc; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.kwsrc (id, kw, descr, dt, notes, seq, sinc, smin, smax, srct) FROM stdin;
\.


--
-- Data for Name: lsrc; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.lsrc (entr, sens, ord, lang, txt, part, wasei) FROM stdin;
\.


--
-- Data for Name: misc; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.misc (entr, sens, ord, kw) FROM stdin;
\.


--
-- Data for Name: pos; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.pos (entr, sens, ord, kw) FROM stdin;
\.


--
-- Data for Name: rdng; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.rdng (entr, rdng, txt) FROM stdin;
\.


--
-- Data for Name: restr; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.restr (entr, rdng, kanj) FROM stdin;
\.


--
-- Data for Name: rinf; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.rinf (entr, rdng, ord, kw) FROM stdin;
\.


--
-- Data for Name: sens; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.sens (entr, sens, notes) FROM stdin;
\.


--
-- Data for Name: stagk; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.stagk (entr, sens, kanj) FROM stdin;
\.


--
-- Data for Name: stagr; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.stagr (entr, sens, rdng) FROM stdin;
\.


--
-- Data for Name: xref; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.xref (entr, sens, xref, typ, xentr, xsens, rdng, kanj, notes, nosens, lowpri) FROM stdin;
\.


--
-- Data for Name: xresolv; Type: TABLE DATA; Schema: imp; Owner: jmdictdb
--

COPY imp.xresolv (entr, sens, typ, ord, rtxt, ktxt, tsens, notes, prio) FROM stdin;
\.


--
-- Data for Name: chr; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.chr (entr, chr, bushu, strokes, freq, grade, jlpt, radname) FROM stdin;
\.


--
-- Data for Name: cinf; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.cinf (entr, kw, value, mctype) FROM stdin;
\.


--
-- Data for Name: conj; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.conj (id, name) FROM stdin;
1	Non-past
2	Past (~ta)
3	Conjunctive (~te)
4	Provisional (~eba)
5	Potential
6	Passive
7	Causative
8	Causative-Passive 
9	Volitional
10	Imperative
11	Conditional (~tara)
12	Alternative (~tari)
13	Continuative (~i)
\.


--
-- Data for Name: conjo; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.conjo (pos, conj, neg, fml, onum, stem, okuri, euphr, euphk, pos2) FROM stdin;
1	1	f	f	1	1	い	\N	\N	\N
1	1	f	t	1	1	いです	\N	\N	\N
1	1	t	f	1	1	くない	\N	\N	\N
1	1	t	t	1	1	くないです	\N	\N	\N
1	1	t	t	2	1	くありません	\N	\N	\N
1	2	f	f	1	1	かった	\N	\N	\N
1	2	f	t	1	1	かったです	\N	\N	\N
1	2	t	f	1	1	くなかった	\N	\N	\N
1	2	t	t	1	1	くなかったです	\N	\N	\N
1	2	t	t	2	1	くありませんでした	\N	\N	\N
1	3	f	f	1	1	くて	\N	\N	\N
1	3	t	f	1	1	くなくて	\N	\N	\N
1	4	f	f	1	1	ければ	\N	\N	\N
1	4	t	f	1	1	くなければ	\N	\N	\N
1	7	f	f	1	1	くさせる	\N	\N	\N
1	9	f	f	1	1	かろう	\N	\N	\N
1	9	f	t	1	1	いでしょう	\N	\N	\N
1	11	f	f	1	1	かったら	\N	\N	\N
1	11	t	f	1	1	くなかったら	\N	\N	\N
1	12	f	f	1	1	かったり	\N	\N	\N
2	1	f	f	1	0	だ	\N	\N	\N
7	1	f	f	1	1	い	\N	\N	\N
7	1	f	t	1	1	いです	\N	\N	\N
7	1	t	f	1	1	くない	よ	\N	\N
7	1	t	t	1	1	くないです	よ	\N	\N
7	1	t	t	2	1	くありません	よ	\N	\N
7	2	f	f	1	1	かった	よ	\N	\N
7	2	f	t	1	1	かったです	よ	\N	\N
7	2	t	f	1	1	くなかった	よ	\N	\N
7	2	t	t	1	1	くなかったです	よ	\N	\N
7	2	t	t	2	1	くありませんでした	よ	\N	\N
7	3	f	f	1	1	くて	よ	\N	\N
7	3	t	f	1	1	くなくて	よ	\N	\N
7	4	f	f	1	1	ければ	よ	\N	\N
7	4	t	f	1	1	くなければ	よ	\N	\N
7	7	f	f	1	1	くさせる	よ	\N	\N
7	9	f	f	1	1	かろう	よ	\N	\N
7	9	f	t	1	1	いでしょう	\N	\N	\N
7	11	f	f	1	1	かったら	よ	\N	\N
7	11	t	f	1	1	くなかったら	よ	\N	\N
7	12	f	f	1	1	かったり	よ	\N	\N
15	1	f	f	1	1	だ	\N	\N	\N
15	1	f	t	1	1	です	\N	\N	\N
15	1	t	f	1	1	ではない	\N	\N	\N
15	1	t	t	1	1	ではありません	\N	\N	\N
15	1	t	t	2	1	ではないです	\N	\N	\N
15	2	f	f	1	1	だった	\N	\N	\N
15	2	f	t	1	1	でした	\N	\N	\N
15	2	t	f	1	1	ではなかった	\N	\N	\N
15	2	t	t	1	1	ではありませんでした	\N	\N	\N
15	3	f	f	1	1	で	\N	\N	\N
15	3	f	t	1	1	でありまして	\N	\N	\N
15	3	t	f	1	1	ではなくて	\N	\N	\N
15	4	f	f	1	1	なら	\N	\N	\N
15	4	f	f	2	1	ならば	\N	\N	\N
15	4	f	f	3	1	であれば	\N	\N	\N
15	9	f	f	1	1	だろう	\N	\N	\N
15	9	f	t	1	1	でしょう	\N	\N	\N
15	10	f	f	1	1	であれ	\N	\N	\N
15	11	f	f	1	1	だったら	\N	\N	\N
15	11	f	t	1	1	でしたら	\N	\N	\N
15	11	t	f	1	1	ではなかったら	\N	\N	\N
15	11	t	t	1	1	ではありませんでしたら	\N	\N	\N
15	12	f	f	1	1	だったり	\N	\N	\N
17	1	f	f	1	0	だ	\N	\N	\N
28	1	f	f	1	1	る	\N	\N	\N
28	1	f	t	1	1	ます	\N	\N	\N
28	1	t	f	1	1	ない	\N	\N	\N
28	1	t	t	1	1	ました	\N	\N	\N
28	2	f	f	1	1	た	\N	\N	\N
28	2	f	t	1	1	ました	\N	\N	\N
28	2	t	f	1	1	なかった	\N	\N	\N
28	2	t	t	1	1	ませんでした	\N	\N	\N
28	3	f	f	1	1	て	\N	\N	\N
28	3	f	t	1	1	まして	\N	\N	\N
28	3	t	f	1	1	なくて	\N	\N	\N
28	3	t	f	2	1	ないで	\N	\N	\N
28	3	t	t	1	1	ませんで	\N	\N	\N
28	4	f	f	1	1	れば	\N	\N	\N
28	4	f	t	1	1	ますなら	\N	\N	\N
28	4	f	t	2	1	ますならば	\N	\N	\N
28	4	t	f	1	1	なければ	\N	\N	\N
28	4	t	t	1	1	ませんなら	\N	\N	\N
28	4	t	t	2	1	ませんならば	\N	\N	\N
28	5	f	f	1	1	られる	\N	\N	\N
28	5	f	f	2	1	れる	\N	\N	\N
28	5	f	t	1	1	られます	\N	\N	\N
28	5	f	t	2	1	れます	\N	\N	\N
28	5	t	f	1	1	られない	\N	\N	\N
28	5	t	f	2	1	れない	\N	\N	\N
28	5	t	t	1	1	られません	\N	\N	\N
28	5	t	t	2	1	れません	\N	\N	\N
28	6	f	f	1	1	られる	\N	\N	\N
28	6	f	t	1	1	られます	\N	\N	\N
28	6	t	f	1	1	られない	\N	\N	\N
28	6	t	t	1	1	られません	\N	\N	\N
28	7	f	f	1	1	させる	\N	\N	\N
28	7	f	f	2	1	さす	\N	\N	\N
28	7	f	t	1	1	させます	\N	\N	\N
28	7	f	t	2	1	さします	\N	\N	\N
28	7	t	f	1	1	させない	\N	\N	\N
28	7	t	f	2	1	ささない	\N	\N	\N
28	7	t	t	1	1	させません	\N	\N	\N
28	7	t	t	2	1	さしません	\N	\N	\N
28	8	f	f	1	1	させられる	\N	\N	\N
28	8	f	t	1	1	させられます	\N	\N	\N
28	8	t	f	1	1	させられない	\N	\N	\N
28	8	t	t	1	1	させられません	\N	\N	\N
28	9	f	f	1	1	よう	\N	\N	\N
28	9	f	t	1	1	ましょう	\N	\N	\N
28	9	t	f	1	1	まい	\N	\N	\N
28	9	t	t	1	1	ますまい	\N	\N	\N
28	10	f	f	1	1	ろ	\N	\N	\N
28	10	f	t	1	1	なさい	\N	\N	\N
28	10	t	f	1	1	るな	\N	\N	\N
28	10	t	t	1	1	なさるな	\N	\N	\N
28	11	f	f	1	1	たら	\N	\N	\N
28	11	f	t	1	1	ましたら	\N	\N	\N
28	11	t	f	1	1	なかったら	\N	\N	\N
28	11	t	t	1	1	ませんでしたら	\N	\N	\N
28	12	f	f	1	1	たり	\N	\N	\N
28	12	f	t	1	1	ましたり	\N	\N	\N
28	12	t	f	1	1	なかったり	\N	\N	\N
28	12	t	t	1	1	ませんでしたり	\N	\N	\N
28	13	f	f	1	1		\N	\N	\N
29	1	f	f	1	1	る	\N	\N	\N
29	1	f	t	1	1	ます	\N	\N	\N
29	1	t	f	1	1	ない	\N	\N	\N
29	1	t	t	1	1	ました	\N	\N	\N
29	2	f	f	1	1	た	\N	\N	\N
29	2	f	t	1	1	ました	\N	\N	\N
29	2	t	f	1	1	なかった	\N	\N	\N
29	2	t	t	1	1	ませんでした	\N	\N	\N
29	3	f	f	1	1	て	\N	\N	\N
29	3	f	t	1	1	まして	\N	\N	\N
29	3	t	f	1	1	なくて	\N	\N	\N
29	3	t	f	2	1	ないで	\N	\N	\N
29	3	t	t	1	1	ませんで	\N	\N	\N
29	4	f	f	1	1	れば	\N	\N	\N
29	4	f	t	1	1	ますなら	\N	\N	\N
29	4	f	t	2	1	ますならば	\N	\N	\N
29	4	t	f	1	1	なければ	\N	\N	\N
29	4	t	t	1	1	ませんなら	\N	\N	\N
29	4	t	t	2	1	ませんならば	\N	\N	\N
29	5	f	f	1	1	られる	\N	\N	\N
29	5	f	f	2	1	れる	\N	\N	\N
29	5	f	t	1	1	られます	\N	\N	\N
29	5	f	t	2	1	れます	\N	\N	\N
29	5	t	f	1	1	られない	\N	\N	\N
29	5	t	f	2	1	れない	\N	\N	\N
29	5	t	t	1	1	られません	\N	\N	\N
29	5	t	t	2	1	れません	\N	\N	\N
29	6	f	f	1	1	られる	\N	\N	\N
29	6	f	t	1	1	られます	\N	\N	\N
29	6	t	f	1	1	られない	\N	\N	\N
29	6	t	t	1	1	られません	\N	\N	\N
29	7	f	f	1	1	させる	\N	\N	\N
29	7	f	f	2	1	さす	\N	\N	\N
29	7	f	t	1	1	させます	\N	\N	\N
29	7	f	t	2	1	さします	\N	\N	\N
29	7	t	f	1	1	させない	\N	\N	\N
29	7	t	f	2	1	ささない	\N	\N	\N
29	7	t	t	1	1	させません	\N	\N	\N
29	7	t	t	2	1	さしません	\N	\N	\N
29	8	f	f	1	1	させられる	\N	\N	\N
29	8	f	t	1	1	させられます	\N	\N	\N
29	8	t	f	1	1	させられない	\N	\N	\N
29	8	t	t	1	1	させられません	\N	\N	\N
29	9	f	f	1	1	よう	\N	\N	\N
29	9	f	t	1	1	ましょう	\N	\N	\N
29	9	t	f	1	1	まい	\N	\N	\N
29	9	t	t	1	1	ますまい	\N	\N	\N
29	10	f	f	1	1		\N	\N	\N
29	10	f	t	1	1	なさい	\N	\N	\N
29	10	t	f	1	1	るな	\N	\N	\N
29	10	t	t	1	1	なさるな	\N	\N	\N
29	11	f	f	1	1	たら	\N	\N	\N
29	11	f	t	1	1	ましたら	\N	\N	\N
29	11	t	f	1	1	なかったら	\N	\N	\N
29	11	t	t	1	1	ませんでしたら	\N	\N	\N
29	12	f	f	1	1	たり	\N	\N	\N
29	12	f	t	1	1	ましたり	\N	\N	\N
29	12	t	f	1	1	なかったり	\N	\N	\N
29	12	t	t	1	1	ませんでしたり	\N	\N	\N
29	13	f	f	1	1		\N	\N	\N
30	1	f	f	1	1	る	\N	\N	\N
30	1	f	t	1	1	います	\N	\N	\N
30	1	t	f	1	1	らない	\N	\N	\N
30	1	t	t	1	1	いません	\N	\N	\N
30	2	f	f	1	1	った	\N	\N	\N
30	2	f	t	1	1	いました	\N	\N	\N
30	2	t	f	1	1	らなかった	\N	\N	\N
30	2	t	t	1	1	いませんでした	\N	\N	\N
30	3	f	f	1	1	って	\N	\N	\N
30	3	f	t	1	1	いまして	\N	\N	\N
30	3	t	f	1	1	らなくて	\N	\N	\N
30	3	t	f	2	1	らないで	\N	\N	\N
30	3	t	t	1	1	いませんで	\N	\N	\N
30	4	f	f	1	1	れば	\N	\N	\N
30	4	f	t	1	1	いますなら	\N	\N	\N
30	4	f	t	2	1	いますならば	\N	\N	\N
30	4	t	f	1	1	らなければ	\N	\N	\N
30	4	t	t	1	1	いませんなら	\N	\N	\N
30	4	t	t	2	1	いませんならば	\N	\N	\N
30	5	f	f	1	1	れる	\N	\N	\N
30	5	f	t	1	1	れます	\N	\N	\N
30	5	t	f	1	1	れない	\N	\N	\N
30	5	t	t	1	1	れません	\N	\N	\N
30	6	f	f	1	1	られる	\N	\N	\N
30	6	f	t	1	1	られます	\N	\N	\N
30	6	t	f	1	1	られない	\N	\N	\N
30	6	t	t	1	1	られません	\N	\N	\N
30	7	f	f	1	1	らせる	\N	\N	\N
30	7	f	f	2	1	らす	\N	\N	\N
30	7	f	t	1	1	らせます	\N	\N	\N
30	7	f	t	2	1	らします	\N	\N	\N
30	7	t	f	1	1	らせない	\N	\N	\N
30	7	t	f	2	1	らさない	\N	\N	\N
30	7	t	t	1	1	らせません	\N	\N	\N
30	7	t	t	2	1	らしません	\N	\N	\N
30	8	f	f	1	1	らせられる	\N	\N	\N
30	8	f	f	2	1	らされる	\N	\N	\N
30	8	f	t	1	1	らせられます	\N	\N	\N
30	8	f	t	2	1	らされます	\N	\N	\N
30	8	t	f	1	1	らせられない	\N	\N	\N
30	8	t	f	2	1	らされない	\N	\N	\N
30	8	t	t	1	1	らせられません	\N	\N	\N
30	8	t	t	2	1	らされません	\N	\N	\N
30	9	f	f	1	1	ろう	\N	\N	\N
30	9	f	t	1	1	いましょう	\N	\N	\N
30	9	t	f	1	1	るまい	\N	\N	\N
30	9	t	t	1	1	いませんまい	\N	\N	\N
30	10	f	f	1	1	い	\N	\N	\N
30	10	f	t	1	1	いなさい	\N	\N	\N
30	10	t	f	1	1	るな	\N	\N	\N
30	10	t	t	1	1	いなさるな	\N	\N	\N
30	11	f	f	1	1	ったら	\N	\N	\N
30	11	f	t	1	1	いましたら	\N	\N	\N
30	11	t	f	1	1	らなかったら	\N	\N	\N
30	11	t	t	1	1	いませんでしたら	\N	\N	\N
30	12	f	f	1	1	ったり	\N	\N	\N
30	12	f	t	1	1	いましたり	\N	\N	\N
30	12	t	f	1	1	らなかったり	\N	\N	\N
30	12	t	t	1	1	いませんでしたり	\N	\N	\N
30	13	f	f	1	1	い	\N	\N	\N
31	1	f	f	1	1	ぶ	\N	\N	\N
31	1	f	t	1	1	びます	\N	\N	\N
31	1	t	f	1	1	ばない	\N	\N	\N
31	1	t	t	1	1	びません	\N	\N	\N
31	2	f	f	1	1	んだ	\N	\N	\N
31	2	f	t	1	1	びました	\N	\N	\N
31	2	t	f	1	1	ばなかった	\N	\N	\N
31	2	t	t	1	1	びませんでした	\N	\N	\N
31	3	f	f	1	1	んで	\N	\N	\N
31	3	f	t	1	1	びまして	\N	\N	\N
31	3	t	f	1	1	ばなくて	\N	\N	\N
31	3	t	f	2	1	ばないで	\N	\N	\N
31	3	t	t	1	1	びませんで	\N	\N	\N
31	4	f	f	1	1	べば	\N	\N	\N
31	4	f	t	1	1	びますなら	\N	\N	\N
31	4	f	t	2	1	びますならば	\N	\N	\N
31	4	t	f	1	1	ばなければ	\N	\N	\N
31	4	t	t	1	1	びませんなら	\N	\N	\N
31	4	t	t	2	1	びませんならば	\N	\N	\N
31	5	f	f	1	1	べる	\N	\N	\N
31	5	f	t	1	1	べます	\N	\N	\N
31	5	t	f	1	1	べない	\N	\N	\N
31	5	t	t	1	1	べません	\N	\N	\N
31	6	f	f	1	1	ばれる	\N	\N	\N
31	6	f	t	1	1	ばれます	\N	\N	\N
31	6	t	f	1	1	ばれない	\N	\N	\N
31	6	t	t	1	1	ばれません	\N	\N	\N
31	7	f	f	1	1	ばせる	\N	\N	\N
31	7	f	f	2	1	ばす	\N	\N	\N
31	7	f	t	1	1	ばせます	\N	\N	\N
31	7	f	t	2	1	ばします	\N	\N	\N
31	7	t	f	1	1	ばせない	\N	\N	\N
31	7	t	f	2	1	ばさない	\N	\N	\N
31	7	t	t	1	1	ばせません	\N	\N	\N
31	7	t	t	2	1	ばしません	\N	\N	\N
31	8	f	f	1	1	ばせられる	\N	\N	\N
31	8	f	f	2	1	ばされる	\N	\N	\N
31	8	f	t	1	1	ばせられます	\N	\N	\N
31	8	f	t	2	1	ばされます	\N	\N	\N
31	8	t	f	1	1	ばせられない	\N	\N	\N
31	8	t	f	2	1	ばされない	\N	\N	\N
31	8	t	t	1	1	ばせられません	\N	\N	\N
31	8	t	t	2	1	ばされません	\N	\N	\N
31	9	f	f	1	1	ぼう	\N	\N	\N
31	9	f	t	1	1	びましょう	\N	\N	\N
31	9	t	f	1	1	ぶまい	\N	\N	\N
31	9	t	t	1	1	びませんまい	\N	\N	\N
31	10	f	f	1	1	べ	\N	\N	\N
31	10	f	t	1	1	びなさい	\N	\N	\N
31	10	t	f	1	1	ぶな	\N	\N	\N
31	10	t	t	1	1	びなさるな	\N	\N	\N
31	11	f	f	1	1	んだら	\N	\N	\N
31	11	f	t	1	1	びましたら	\N	\N	\N
31	11	t	f	1	1	ばなかったら	\N	\N	\N
31	11	t	t	1	1	びませんでしたら	\N	\N	\N
31	12	f	f	1	1	んだり	\N	\N	\N
31	12	f	t	1	1	びましたり	\N	\N	\N
31	12	t	f	1	1	ばなかったり	\N	\N	\N
31	12	t	t	1	1	びませんでしたり	\N	\N	\N
31	13	f	f	1	1	び	\N	\N	\N
32	1	f	f	1	1	ぐ	\N	\N	\N
32	1	f	t	1	1	ぎます	\N	\N	\N
32	1	t	f	1	1	がない	\N	\N	\N
32	1	t	t	1	1	ぎません	\N	\N	\N
32	2	f	f	1	1	いだ	\N	\N	\N
32	2	f	t	1	1	ぎました	\N	\N	\N
32	2	t	f	1	1	がなかった	\N	\N	\N
32	2	t	t	1	1	ぎませんでした	\N	\N	\N
32	3	f	f	1	1	いで	\N	\N	\N
32	3	f	t	1	1	ぎまして	\N	\N	\N
32	3	t	f	1	1	がなくて	\N	\N	\N
32	3	t	f	2	1	がないで	\N	\N	\N
32	3	t	t	1	1	ぎませんで	\N	\N	\N
32	4	f	f	1	1	げば	\N	\N	\N
32	4	f	t	1	1	ぎますなら	\N	\N	\N
32	4	f	t	2	1	ぎますならば	\N	\N	\N
32	4	t	f	1	1	がなければ	\N	\N	\N
32	4	t	t	1	1	ぎませんなら	\N	\N	\N
32	4	t	t	2	1	ぎませんならば	\N	\N	\N
32	5	f	f	1	1	げる	\N	\N	\N
32	5	f	t	1	1	げます	\N	\N	\N
32	5	t	f	1	1	げない	\N	\N	\N
32	5	t	t	1	1	げません	\N	\N	\N
32	6	f	f	1	1	がれる	\N	\N	\N
32	6	f	t	1	1	がれます	\N	\N	\N
32	6	t	f	1	1	がれない	\N	\N	\N
32	6	t	t	1	1	がれません	\N	\N	\N
32	7	f	f	1	1	がせる	\N	\N	\N
32	7	f	f	2	1	がす	\N	\N	\N
32	7	f	t	1	1	がせます	\N	\N	\N
32	7	f	t	2	1	がします	\N	\N	\N
32	7	t	f	1	1	がせない	\N	\N	\N
32	7	t	f	2	1	がさない	\N	\N	\N
32	7	t	t	1	1	がせません	\N	\N	\N
32	7	t	t	2	1	がしません	\N	\N	\N
32	8	f	f	1	1	がせられる	\N	\N	\N
32	8	f	f	2	1	がされる	\N	\N	\N
32	8	f	t	1	1	がせられます	\N	\N	\N
32	8	f	t	2	1	がされます	\N	\N	\N
32	8	t	f	1	1	がせられない	\N	\N	\N
32	8	t	f	2	1	がされない	\N	\N	\N
32	8	t	t	1	1	がせられません	\N	\N	\N
32	8	t	t	2	1	がされません	\N	\N	\N
32	9	f	f	1	1	ごう	\N	\N	\N
32	9	f	t	1	1	ぎましょう	\N	\N	\N
32	9	t	f	1	1	ぐまい	\N	\N	\N
32	9	t	t	1	1	ぎませんまい	\N	\N	\N
32	10	f	f	1	1	げ	\N	\N	\N
32	10	f	t	1	1	ぎなさい	\N	\N	\N
32	10	t	f	1	1	ぐな	\N	\N	\N
32	10	t	t	1	1	ぎなさるな	\N	\N	\N
32	11	f	f	1	1	いだら	\N	\N	\N
32	11	f	t	1	1	ぎましたら	\N	\N	\N
32	11	t	f	1	1	がなかったら	\N	\N	\N
32	11	t	t	1	1	ぎませんでしたら	\N	\N	\N
32	12	f	f	1	1	いだり	\N	\N	\N
32	12	f	t	1	1	ぎましたり	\N	\N	\N
32	12	t	f	1	1	がなかったり	\N	\N	\N
32	12	t	t	1	1	ぎませんでしたり	\N	\N	\N
32	13	f	f	1	1	ぎ	\N	\N	\N
33	1	f	f	1	1	く	\N	\N	\N
33	1	f	t	1	1	きます	\N	\N	\N
33	1	t	f	1	1	かない	\N	\N	\N
33	1	t	t	1	1	きません	\N	\N	\N
33	2	f	f	1	1	いた	\N	\N	\N
33	2	f	t	1	1	きました	\N	\N	\N
33	2	t	f	1	1	かなかった	\N	\N	\N
33	2	t	t	1	1	きませんでした	\N	\N	\N
33	3	f	f	1	1	いて	\N	\N	\N
33	3	f	t	1	1	きまして	\N	\N	\N
33	3	t	f	1	1	かなくて	\N	\N	\N
33	3	t	f	2	1	かないで	\N	\N	\N
33	3	t	t	1	1	きませんで	\N	\N	\N
33	4	f	f	1	1	けば	\N	\N	\N
33	4	f	t	1	1	きますなら	\N	\N	\N
33	4	f	t	2	1	きますならば	\N	\N	\N
33	4	t	f	1	1	かなければ	\N	\N	\N
33	4	t	t	1	1	きませんなら	\N	\N	\N
33	4	t	t	2	1	きませんならば	\N	\N	\N
33	5	f	f	1	1	ける	\N	\N	\N
33	5	f	t	1	1	けます	\N	\N	\N
33	5	t	f	1	1	けない	\N	\N	\N
33	5	t	t	1	1	けません	\N	\N	\N
33	6	f	f	1	1	かれる	\N	\N	\N
33	6	f	t	1	1	かれます	\N	\N	\N
33	6	t	f	1	1	かれない	\N	\N	\N
33	6	t	t	1	1	かれません	\N	\N	\N
33	7	f	f	1	1	かせる	\N	\N	\N
33	7	f	f	2	1	かす	\N	\N	\N
33	7	f	t	1	1	かせます	\N	\N	\N
33	7	f	t	2	1	かします	\N	\N	\N
33	7	t	f	1	1	かせない	\N	\N	\N
33	7	t	f	2	1	かさない	\N	\N	\N
33	7	t	t	1	1	かせません	\N	\N	\N
33	7	t	t	2	1	かしません	\N	\N	\N
33	8	f	f	1	1	かせられる	\N	\N	\N
33	8	f	f	2	1	かされる	\N	\N	\N
33	8	f	t	1	1	かせられます	\N	\N	\N
33	8	f	t	2	1	かされます	\N	\N	\N
33	8	t	f	1	1	かせられない	\N	\N	\N
33	8	t	f	2	1	かされない	\N	\N	\N
33	8	t	t	1	1	かせられません	\N	\N	\N
33	8	t	t	2	1	かされません	\N	\N	\N
33	9	f	f	1	1	こう	\N	\N	\N
33	9	f	t	1	1	きましょう	\N	\N	\N
33	9	t	f	1	1	くまい	\N	\N	\N
33	9	t	t	1	1	きませんまい	\N	\N	\N
33	10	f	f	1	1	け	\N	\N	\N
33	10	f	t	1	1	きなさい	\N	\N	\N
33	10	t	f	1	1	くな	\N	\N	\N
33	10	t	t	1	1	きなさるな	\N	\N	\N
33	11	f	f	1	1	いたら	\N	\N	\N
33	11	f	t	1	1	きましたら	\N	\N	\N
33	11	t	f	1	1	かなかったら	\N	\N	\N
33	11	t	t	1	1	きませんでしたら	\N	\N	\N
33	12	f	f	1	1	いたり	\N	\N	\N
33	12	f	t	1	1	きましたり	\N	\N	\N
33	12	t	f	1	1	かなかったり	\N	\N	\N
33	12	t	t	1	1	きませんでしたり	\N	\N	\N
33	13	f	f	1	1	き	\N	\N	\N
34	1	f	f	1	1	く	\N	\N	\N
34	1	f	t	1	1	きます	\N	\N	\N
34	1	t	f	1	1	かない	\N	\N	\N
34	1	t	t	1	1	きません	\N	\N	\N
34	2	f	f	1	1	った	\N	\N	\N
34	2	f	t	1	1	きました	\N	\N	\N
34	2	t	f	1	1	かなかった	\N	\N	\N
34	2	t	t	1	1	きませんでした	\N	\N	\N
34	3	f	f	1	1	って	\N	\N	\N
34	3	f	t	1	1	きまして	\N	\N	\N
34	3	t	f	1	1	かなくて	\N	\N	\N
34	3	t	f	2	1	かないで	\N	\N	\N
34	3	t	t	1	1	きませんで	\N	\N	\N
34	4	f	f	1	1	けば	\N	\N	\N
34	4	f	t	1	1	きますなら	\N	\N	\N
34	4	f	t	2	1	きますならば	\N	\N	\N
34	4	t	f	1	1	かなければ	\N	\N	\N
34	4	t	t	1	1	きませんなら	\N	\N	\N
34	4	t	t	2	1	きませんならば	\N	\N	\N
34	5	f	f	1	1	ける	\N	\N	\N
34	5	f	t	1	1	けます	\N	\N	\N
34	5	t	f	1	1	けない	\N	\N	\N
34	5	t	t	1	1	けません	\N	\N	\N
34	6	f	f	1	1	かれる	\N	\N	\N
34	6	f	t	1	1	かれます	\N	\N	\N
34	6	t	f	1	1	かれない	\N	\N	\N
34	6	t	t	1	1	かれません	\N	\N	\N
34	7	f	f	1	1	かせる	\N	\N	\N
34	7	f	f	2	1	かす	\N	\N	\N
34	7	f	t	1	1	かせます	\N	\N	\N
34	7	f	t	2	1	かします	\N	\N	\N
34	7	t	f	1	1	かせない	\N	\N	\N
34	7	t	f	2	1	かさない	\N	\N	\N
34	7	t	t	1	1	かせません	\N	\N	\N
34	7	t	t	2	1	かしません	\N	\N	\N
34	8	f	f	1	1	かせられる	\N	\N	\N
34	8	f	f	2	1	かされる	\N	\N	\N
34	8	f	t	1	1	かせられます	\N	\N	\N
34	8	f	t	2	1	かされます	\N	\N	\N
34	8	t	f	1	1	かせられない	\N	\N	\N
34	8	t	f	2	1	かされない	\N	\N	\N
34	8	t	t	1	1	かせられません	\N	\N	\N
34	8	t	t	2	1	かされません	\N	\N	\N
34	9	f	f	1	1	こう	\N	\N	\N
34	9	f	t	1	1	きましょう	\N	\N	\N
34	9	t	f	1	1	くまい	\N	\N	\N
34	9	t	t	1	1	きませんまい	\N	\N	\N
34	10	f	f	1	1	け	\N	\N	\N
34	10	f	t	1	1	きなさい	\N	\N	\N
34	10	t	f	1	1	くな	\N	\N	\N
34	10	t	t	1	1	きなさるな	\N	\N	\N
34	11	f	f	1	1	ったら	\N	\N	\N
34	11	f	t	1	1	きましたら	\N	\N	\N
34	11	t	f	1	1	かなかったら	\N	\N	\N
34	11	t	t	1	1	きませんでしたら	\N	\N	\N
34	12	f	f	1	1	ったり	\N	\N	\N
34	12	f	t	1	1	きましたり	\N	\N	\N
34	12	t	f	1	1	かなかったり	\N	\N	\N
34	12	t	t	1	1	きませんでしたり	\N	\N	\N
34	13	f	f	1	1	き	\N	\N	\N
35	1	f	f	1	1	む	\N	\N	\N
35	1	f	t	1	1	みます	\N	\N	\N
35	1	t	f	1	1	まない	\N	\N	\N
35	1	t	t	1	1	みません	\N	\N	\N
35	2	f	f	1	1	んだ	\N	\N	\N
35	2	f	t	1	1	みました	\N	\N	\N
35	2	t	f	1	1	まなかった	\N	\N	\N
35	2	t	t	1	1	みませんでした	\N	\N	\N
35	3	f	f	1	1	んで	\N	\N	\N
35	3	f	t	1	1	みまして	\N	\N	\N
35	3	t	f	1	1	まなくて	\N	\N	\N
35	3	t	f	2	1	まないで	\N	\N	\N
35	3	t	t	1	1	みませんで	\N	\N	\N
35	4	f	f	1	1	めば	\N	\N	\N
35	4	f	t	1	1	みますなら	\N	\N	\N
35	4	f	t	2	1	みますならば	\N	\N	\N
35	4	t	f	1	1	まなければ	\N	\N	\N
35	4	t	t	1	1	みませんなら	\N	\N	\N
35	4	t	t	2	1	みませんならば	\N	\N	\N
35	5	f	f	1	1	める	\N	\N	\N
35	5	f	t	1	1	めます	\N	\N	\N
35	5	t	f	1	1	めない	\N	\N	\N
35	5	t	t	1	1	めません	\N	\N	\N
35	6	f	f	1	1	まれる	\N	\N	\N
35	6	f	t	1	1	まれます	\N	\N	\N
35	6	t	f	1	1	まれない	\N	\N	\N
35	6	t	t	1	1	まれません	\N	\N	\N
35	7	f	f	1	1	ませる	\N	\N	\N
35	7	f	f	2	1	ます	\N	\N	\N
35	7	f	t	1	1	ませます	\N	\N	\N
35	7	f	t	2	1	まします	\N	\N	\N
35	7	t	f	1	1	ませない	\N	\N	\N
35	7	t	f	2	1	まさない	\N	\N	\N
35	7	t	t	1	1	ませません	\N	\N	\N
35	7	t	t	2	1	ましません	\N	\N	\N
35	8	f	f	1	1	ませられる	\N	\N	\N
35	8	f	f	2	1	まされる	\N	\N	\N
35	8	f	t	1	1	ませられます	\N	\N	\N
35	8	f	t	2	1	まされます	\N	\N	\N
35	8	t	f	1	1	ませられない	\N	\N	\N
35	8	t	f	2	1	まされない	\N	\N	\N
35	8	t	t	1	1	ませられません	\N	\N	\N
35	8	t	t	2	1	まされません	\N	\N	\N
35	9	f	f	1	1	もう	\N	\N	\N
35	9	f	t	1	1	みましょう	\N	\N	\N
35	9	t	f	1	1	むまい	\N	\N	\N
35	9	t	t	1	1	みませんまい	\N	\N	\N
35	10	f	f	1	1	め	\N	\N	\N
35	10	f	t	1	1	みなさい	\N	\N	\N
35	10	t	f	1	1	むな	\N	\N	\N
35	10	t	t	1	1	みなさるな	\N	\N	\N
35	11	f	f	1	1	んだら	\N	\N	\N
35	11	f	t	1	1	みましたら	\N	\N	\N
35	11	t	f	1	1	まなかったら	\N	\N	\N
35	11	t	t	1	1	みませんでしたら	\N	\N	\N
35	12	f	f	1	1	んだり	\N	\N	\N
35	12	f	t	1	1	みましたり	\N	\N	\N
35	12	t	f	1	1	まなかったり	\N	\N	\N
35	12	t	t	1	1	みませんでしたり	\N	\N	\N
35	13	f	f	1	1	み	\N	\N	\N
36	1	f	f	1	1	ぬ	\N	\N	\N
36	1	f	t	1	1	にます	\N	\N	\N
36	1	t	f	1	1	なない	\N	\N	\N
36	1	t	t	1	1	にません	\N	\N	\N
36	2	f	f	1	1	んだ	\N	\N	\N
36	2	f	t	1	1	にました	\N	\N	\N
36	2	t	f	1	1	ななかった	\N	\N	\N
36	2	t	t	1	1	にませんでした	\N	\N	\N
36	3	f	f	1	1	んで	\N	\N	\N
36	3	f	t	1	1	にまして	\N	\N	\N
36	3	t	f	1	1	ななくて	\N	\N	\N
36	3	t	f	2	1	なないで	\N	\N	\N
36	3	t	t	1	1	にませんで	\N	\N	\N
36	4	f	f	1	1	ねば	\N	\N	\N
36	4	f	t	1	1	にますなら	\N	\N	\N
36	4	f	t	2	1	にますならば	\N	\N	\N
36	4	t	f	1	1	ななければ	\N	\N	\N
36	4	t	t	1	1	にませんなら	\N	\N	\N
36	4	t	t	2	1	にませんならば	\N	\N	\N
36	5	f	f	1	1	ねる	\N	\N	\N
36	5	f	t	1	1	ねます	\N	\N	\N
36	5	t	f	1	1	ねない	\N	\N	\N
36	5	t	t	1	1	ねません	\N	\N	\N
36	6	f	f	1	1	なれる	\N	\N	\N
36	6	f	t	1	1	なれます	\N	\N	\N
36	6	t	f	1	1	なれない	\N	\N	\N
36	6	t	t	1	1	なれません	\N	\N	\N
36	7	f	f	1	1	なせる	\N	\N	\N
36	7	f	f	2	1	なす	\N	\N	\N
36	7	f	t	1	1	なせます	\N	\N	\N
36	7	f	t	2	1	なします	\N	\N	\N
36	7	t	f	1	1	なせない	\N	\N	\N
36	7	t	f	2	1	なさない	\N	\N	\N
36	7	t	t	1	1	なせません	\N	\N	\N
36	7	t	t	2	1	なしません	\N	\N	\N
36	8	f	f	1	1	なせられる	\N	\N	\N
36	8	f	f	2	1	なされる	\N	\N	\N
36	8	f	t	1	1	なせられます	\N	\N	\N
36	8	f	t	2	1	なされます	\N	\N	\N
36	8	t	f	1	1	なせられない	\N	\N	\N
36	8	t	f	2	1	なされない	\N	\N	\N
36	8	t	t	1	1	なせられません	\N	\N	\N
36	8	t	t	2	1	なされません	\N	\N	\N
36	9	f	f	1	1	のう	\N	\N	\N
36	9	f	t	1	1	にましょう	\N	\N	\N
36	9	t	f	1	1	ぬまい	\N	\N	\N
36	9	t	t	1	1	にませんまい	\N	\N	\N
36	10	f	f	1	1	ね	\N	\N	\N
36	10	f	t	1	1	になさい	\N	\N	\N
36	10	t	f	1	1	ぬな	\N	\N	\N
36	10	t	t	1	1	になさるな	\N	\N	\N
36	11	f	f	1	1	んだら	\N	\N	\N
36	11	f	t	1	1	にましたら	\N	\N	\N
36	11	t	f	1	1	ななかったら	\N	\N	\N
36	11	t	t	1	1	にませんでしたら	\N	\N	\N
36	12	f	f	1	1	んだり	\N	\N	\N
36	12	f	t	1	1	にましたり	\N	\N	\N
36	12	t	f	1	1	ななかったり	\N	\N	\N
36	12	t	t	1	1	にませんでしたり	\N	\N	\N
36	13	f	f	1	1	に	\N	\N	\N
37	1	f	f	1	1	る	\N	\N	\N
37	1	f	t	1	1	ります	\N	\N	\N
37	1	t	f	1	1	らない	\N	\N	\N
37	1	t	t	1	1	りません	\N	\N	\N
37	2	f	f	1	1	った	\N	\N	\N
37	2	f	t	1	1	りました	\N	\N	\N
37	2	t	f	1	1	らなかった	\N	\N	\N
37	2	t	t	1	1	りませんでした	\N	\N	\N
37	3	f	f	1	1	って	\N	\N	\N
37	3	f	t	1	1	りまして	\N	\N	\N
37	3	t	f	1	1	らなくて	\N	\N	\N
37	3	t	f	2	1	らないで	\N	\N	\N
37	3	t	t	1	1	りませんで	\N	\N	\N
37	4	f	f	1	1	れば	\N	\N	\N
37	4	f	t	1	1	りますなら	\N	\N	\N
37	4	f	t	2	1	りますならば	\N	\N	\N
37	4	t	f	1	1	らなければ	\N	\N	\N
37	4	t	t	1	1	りませんなら	\N	\N	\N
37	4	t	t	2	1	りませんならば	\N	\N	\N
37	5	f	f	1	1	れる	\N	\N	\N
37	5	f	t	1	1	れます	\N	\N	\N
37	5	t	f	1	1	れない	\N	\N	\N
37	5	t	t	1	1	れません	\N	\N	\N
37	6	f	f	1	1	られる	\N	\N	\N
37	6	f	t	1	1	られます	\N	\N	\N
37	6	t	f	1	1	られない	\N	\N	\N
37	6	t	t	1	1	られません	\N	\N	\N
37	7	f	f	1	1	らせる	\N	\N	\N
37	7	f	f	2	1	らす	\N	\N	\N
37	7	f	t	1	1	らせます	\N	\N	\N
37	7	f	t	2	1	らします	\N	\N	\N
37	7	t	f	1	1	らせない	\N	\N	\N
37	7	t	f	2	1	らさない	\N	\N	\N
37	7	t	t	1	1	らせません	\N	\N	\N
37	7	t	t	2	1	らしません	\N	\N	\N
37	8	f	f	1	1	らせられる	\N	\N	\N
37	8	f	f	2	1	らされる	\N	\N	\N
37	8	f	t	1	1	らせられます	\N	\N	\N
37	8	f	t	2	1	らされます	\N	\N	\N
37	8	t	f	1	1	らせられない	\N	\N	\N
37	8	t	f	2	1	らされない	\N	\N	\N
37	8	t	t	1	1	らせられません	\N	\N	\N
37	8	t	t	2	1	らされません	\N	\N	\N
37	9	f	f	1	1	ろう	\N	\N	\N
37	9	f	t	1	1	りましょう	\N	\N	\N
37	9	t	f	1	1	るまい	\N	\N	\N
37	9	t	t	1	1	りませんまい	\N	\N	\N
37	10	f	f	1	1	れ	\N	\N	\N
37	10	f	t	1	1	りなさい	\N	\N	\N
37	10	t	f	1	1	るな	\N	\N	\N
37	10	t	t	1	1	りなさるな	\N	\N	\N
37	11	f	f	1	1	ったら	\N	\N	\N
37	11	f	t	1	1	りましたら	\N	\N	\N
37	11	t	f	1	1	らなかったら	\N	\N	\N
37	11	t	t	1	1	りませんでしたら	\N	\N	\N
37	12	f	f	1	1	ったり	\N	\N	\N
37	12	f	t	1	1	りましたり	\N	\N	\N
37	12	t	f	1	1	らなかったり	\N	\N	\N
37	12	t	t	1	1	りませんでしたり	\N	\N	\N
37	13	f	f	1	1	り	\N	\N	\N
38	1	f	f	1	1	る	\N	\N	\N
38	1	f	t	1	1	ります	\N	\N	\N
38	1	t	f	1	2	ない	\N	\N	\N
38	1	t	t	1	1	りません	\N	\N	\N
38	2	f	f	1	1	った	\N	\N	\N
38	2	f	t	1	1	りました	\N	\N	\N
38	2	t	f	1	2	なかった	\N	\N	\N
38	2	t	t	1	1	りませんでした	\N	\N	\N
38	3	f	f	1	1	って	\N	\N	\N
38	3	f	t	1	1	りまして	\N	\N	\N
38	3	t	f	1	2	なくて	\N	\N	\N
38	3	t	f	2	2	ないで	\N	\N	\N
38	3	t	t	1	1	りませんで	\N	\N	\N
38	4	f	f	1	1	れば	\N	\N	\N
38	4	f	t	1	1	りますなら	\N	\N	\N
38	4	f	t	2	1	りますならば	\N	\N	\N
38	4	t	f	1	2	なければ	\N	\N	\N
38	4	t	t	1	1	りませんなら	\N	\N	\N
38	4	t	t	2	1	りませんならば	\N	\N	\N
38	5	f	f	1	1	れる	\N	\N	\N
38	5	f	t	1	1	れます	\N	\N	\N
38	5	t	f	1	1	れない	\N	\N	\N
38	5	t	t	1	1	れません	\N	\N	\N
38	6	f	f	1	1	られる	\N	\N	\N
38	6	f	t	1	1	られます	\N	\N	\N
38	6	t	f	1	1	られない	\N	\N	\N
38	6	t	t	1	1	られません	\N	\N	\N
38	7	f	f	1	1	らせる	\N	\N	\N
38	7	f	f	2	1	らす	\N	\N	\N
38	7	f	t	1	1	らせます	\N	\N	\N
38	7	f	t	2	1	らします	\N	\N	\N
38	7	t	f	1	1	らせない	\N	\N	\N
38	7	t	f	2	1	らさない	\N	\N	\N
38	7	t	t	1	1	らせません	\N	\N	\N
38	7	t	t	2	1	らしません	\N	\N	\N
38	8	f	f	1	1	らせられる	\N	\N	\N
38	8	f	f	2	1	らされる	\N	\N	\N
38	8	f	t	1	1	らせられます	\N	\N	\N
38	8	f	t	2	1	らされます	\N	\N	\N
38	8	t	f	1	1	らせられない	\N	\N	\N
38	8	t	f	2	1	らされない	\N	\N	\N
38	8	t	t	1	1	らせられません	\N	\N	\N
38	8	t	t	2	1	らされません	\N	\N	\N
38	9	f	f	1	1	ろう	\N	\N	\N
38	9	f	t	1	1	りましょう	\N	\N	\N
38	9	t	f	1	1	るまい	\N	\N	\N
38	9	t	t	1	1	りませんまい	\N	\N	\N
38	10	f	f	1	1	れ	\N	\N	\N
38	10	f	t	1	1	りなさい	\N	\N	\N
38	10	t	f	1	1	るな	\N	\N	\N
38	10	t	t	1	1	りなさるな	\N	\N	\N
38	11	f	f	1	1	ったら	\N	\N	\N
38	11	f	t	1	1	りましたら	\N	\N	\N
38	11	t	f	1	2	なかったら	\N	\N	\N
38	11	t	t	1	1	りませんでしたら	\N	\N	\N
38	12	f	f	1	1	ったり	\N	\N	\N
38	12	f	t	1	1	りましたり	\N	\N	\N
38	12	t	f	1	2	なかったり	\N	\N	\N
38	12	t	t	1	1	りませんでしたり	\N	\N	\N
38	13	f	f	1	1	り	\N	\N	\N
39	1	f	f	1	1	す	\N	\N	\N
39	1	f	t	1	1	します	\N	\N	\N
39	1	t	f	1	1	さない	\N	\N	\N
39	1	t	t	1	1	しません	\N	\N	\N
39	2	f	f	1	1	した	\N	\N	\N
39	2	f	t	1	1	しました	\N	\N	\N
39	2	t	f	1	1	さなかった	\N	\N	\N
39	2	t	t	1	1	しませんでした	\N	\N	\N
39	3	f	f	1	1	して	\N	\N	\N
39	3	f	t	1	1	しまして	\N	\N	\N
39	3	t	f	1	1	さなくて	\N	\N	\N
39	3	t	f	2	1	さないで	\N	\N	\N
39	3	t	t	1	1	しませんで	\N	\N	\N
39	4	f	f	1	1	せば	\N	\N	\N
39	4	f	t	1	1	しますなら	\N	\N	\N
39	4	f	t	2	1	しますならば	\N	\N	\N
39	4	t	f	1	1	さなければ	\N	\N	\N
39	4	t	t	1	1	しませんなら	\N	\N	\N
39	4	t	t	2	1	しませんならば	\N	\N	\N
39	5	f	f	1	1	せる	\N	\N	\N
39	5	f	t	1	1	せます	\N	\N	\N
39	5	t	f	1	1	せない	\N	\N	\N
39	5	t	t	1	1	せません	\N	\N	\N
39	6	f	f	1	1	される	\N	\N	\N
39	6	f	t	1	1	されます	\N	\N	\N
39	6	t	f	1	1	されない	\N	\N	\N
39	6	t	t	1	1	されません	\N	\N	\N
39	7	f	f	1	1	させる	\N	\N	\N
39	7	f	f	2	1	さす	\N	\N	\N
39	7	f	t	1	1	させます	\N	\N	\N
39	7	f	t	2	1	さします	\N	\N	\N
39	7	t	f	1	1	させない	\N	\N	\N
39	7	t	f	2	1	ささない	\N	\N	\N
39	7	t	t	1	1	させません	\N	\N	\N
39	7	t	t	2	1	さしません	\N	\N	\N
39	8	f	f	1	1	させられる	\N	\N	\N
39	8	f	t	1	1	させられます	\N	\N	\N
39	8	t	f	1	1	させられない	\N	\N	\N
39	8	t	t	1	1	させられません	\N	\N	\N
39	9	f	f	1	1	そう	\N	\N	\N
39	9	f	t	1	1	しましょう	\N	\N	\N
39	9	t	f	1	1	すまい	\N	\N	\N
39	9	t	t	1	1	しませんまい	\N	\N	\N
39	10	f	f	1	1	せ	\N	\N	\N
39	10	f	t	1	1	しなさい	\N	\N	\N
39	10	t	f	1	1	すな	\N	\N	\N
39	10	t	t	1	1	しなさるな	\N	\N	\N
39	11	f	f	1	1	したら	\N	\N	\N
39	11	f	t	1	1	しましたら	\N	\N	\N
39	11	t	f	1	1	さなかったら	\N	\N	\N
39	11	t	t	1	1	しませんでしたら	\N	\N	\N
39	12	f	f	1	1	したり	\N	\N	\N
39	12	f	t	1	1	しましたり	\N	\N	\N
39	12	t	f	1	1	さなかったり	\N	\N	\N
39	12	t	t	1	1	しませんでしたり	\N	\N	\N
39	13	f	f	1	1	し	\N	\N	\N
40	1	f	f	1	1	つ	\N	\N	\N
40	1	f	t	1	1	ちます	\N	\N	\N
40	1	t	f	1	1	たない	\N	\N	\N
40	1	t	t	1	1	ちません	\N	\N	\N
40	2	f	f	1	1	った	\N	\N	\N
40	2	f	t	1	1	ちました	\N	\N	\N
40	2	t	f	1	1	たなかった	\N	\N	\N
40	2	t	t	1	1	ちませんでした	\N	\N	\N
40	3	f	f	1	1	って	\N	\N	\N
40	3	f	t	1	1	ちまして	\N	\N	\N
40	3	t	f	1	1	たなくて	\N	\N	\N
40	3	t	f	2	1	たないで	\N	\N	\N
40	3	t	t	1	1	ちませんで	\N	\N	\N
40	4	f	f	1	1	てば	\N	\N	\N
40	4	f	t	1	1	ちますなら	\N	\N	\N
40	4	f	t	2	1	ちますならば	\N	\N	\N
40	4	t	f	1	1	たなければ	\N	\N	\N
40	4	t	t	1	1	ちませんなら	\N	\N	\N
40	4	t	t	2	1	ちませんならば	\N	\N	\N
40	5	f	f	1	1	てる	\N	\N	\N
40	5	f	t	1	1	てます	\N	\N	\N
40	5	t	f	1	1	てない	\N	\N	\N
40	5	t	t	1	1	てません	\N	\N	\N
40	6	f	f	1	1	たれる	\N	\N	\N
40	6	f	t	1	1	たれます	\N	\N	\N
40	6	t	f	1	1	たれない	\N	\N	\N
40	6	t	t	1	1	たれません	\N	\N	\N
40	7	f	f	1	1	たせる	\N	\N	\N
40	7	f	f	2	1	たす	\N	\N	\N
40	7	f	t	1	1	たせます	\N	\N	\N
40	7	f	t	2	1	たします	\N	\N	\N
40	7	t	f	1	1	たせない	\N	\N	\N
40	7	t	f	2	1	たさない	\N	\N	\N
40	7	t	t	1	1	たせません	\N	\N	\N
40	7	t	t	2	1	たしません	\N	\N	\N
40	8	f	f	1	1	たせられる	\N	\N	\N
40	8	f	f	2	1	たされる	\N	\N	\N
40	8	f	t	1	1	たせられます	\N	\N	\N
40	8	f	t	2	1	たされます	\N	\N	\N
40	8	t	f	1	1	たせられない	\N	\N	\N
40	8	t	f	2	1	たされない	\N	\N	\N
40	8	t	t	1	1	たせられません	\N	\N	\N
40	8	t	t	2	1	たされません	\N	\N	\N
40	9	f	f	1	1	とう	\N	\N	\N
40	9	f	t	1	1	ちましょう	\N	\N	\N
40	9	t	f	1	1	つまい	\N	\N	\N
40	9	t	t	1	1	ちませんまい	\N	\N	\N
40	10	f	f	1	1	て	\N	\N	\N
40	10	f	t	1	1	ちなさい	\N	\N	\N
40	10	t	f	1	1	つな	\N	\N	\N
40	10	t	t	1	1	ちなさるな	\N	\N	\N
40	11	f	f	1	1	ったら	\N	\N	\N
40	11	f	t	1	1	ちまったら	\N	\N	\N
40	11	t	f	1	1	たなかったら	\N	\N	\N
40	11	t	t	1	1	ちませんでしたら	\N	\N	\N
40	12	f	f	1	1	ったり	\N	\N	\N
40	12	f	t	1	1	ちましたり	\N	\N	\N
40	12	t	f	1	1	たなかったり	\N	\N	\N
40	12	t	t	1	1	ちませんでしたり	\N	\N	\N
40	13	f	f	1	1	ち	\N	\N	\N
41	1	f	f	1	1	う	\N	\N	\N
41	1	f	t	1	1	います	\N	\N	\N
41	1	t	f	1	1	わない	\N	\N	\N
41	1	t	t	1	1	いません	\N	\N	\N
41	2	f	f	1	1	った	\N	\N	\N
41	2	f	t	1	1	いました	\N	\N	\N
41	2	t	f	1	1	わなかった	\N	\N	\N
41	2	t	t	1	1	いませんでした	\N	\N	\N
41	3	f	f	1	1	って	\N	\N	\N
41	3	f	t	1	1	いまして	\N	\N	\N
41	3	t	f	1	1	わなくて	\N	\N	\N
41	3	t	f	2	1	わないで	\N	\N	\N
41	3	t	t	1	1	いませんで	\N	\N	\N
41	4	f	f	1	1	えば	\N	\N	\N
41	4	f	t	1	1	いますなら	\N	\N	\N
41	4	f	t	2	1	いますならば	\N	\N	\N
41	4	t	f	1	1	わなければ	\N	\N	\N
41	4	t	t	1	1	いませんなら	\N	\N	\N
41	4	t	t	2	1	いませんならば	\N	\N	\N
41	5	f	f	1	1	える	\N	\N	\N
41	5	f	t	1	1	えます	\N	\N	\N
41	5	t	f	1	1	えない	\N	\N	\N
41	5	t	t	1	1	えません	\N	\N	\N
41	6	f	f	1	1	われる	\N	\N	\N
41	6	f	t	1	1	われます	\N	\N	\N
41	6	t	f	1	1	われない	\N	\N	\N
41	6	t	t	1	1	われません	\N	\N	\N
41	7	f	f	1	1	わせる	\N	\N	\N
41	7	f	f	2	1	わす	\N	\N	\N
41	7	f	t	1	1	わせます	\N	\N	\N
41	7	f	t	2	1	わします	\N	\N	\N
41	7	t	f	1	1	わせない	\N	\N	\N
41	7	t	f	2	1	わさない	\N	\N	\N
41	7	t	t	1	1	わせません	\N	\N	\N
41	7	t	t	2	1	わしません	\N	\N	\N
41	8	f	f	1	1	わせられる	\N	\N	\N
41	8	f	f	2	1	わされる	\N	\N	\N
41	8	f	t	1	1	わせられます	\N	\N	\N
41	8	f	t	2	1	わされます	\N	\N	\N
41	8	t	f	1	1	わせられない	\N	\N	\N
41	8	t	f	2	1	わされない	\N	\N	\N
41	8	t	t	1	1	わせられません	\N	\N	\N
41	8	t	t	2	1	わされません	\N	\N	\N
41	9	f	f	1	1	おう	\N	\N	\N
41	9	f	t	1	1	いましょう	\N	\N	\N
41	9	t	f	1	1	うまい	\N	\N	\N
41	9	t	t	1	1	いませんまい	\N	\N	\N
41	10	f	f	1	1	え	\N	\N	\N
41	10	f	t	1	1	いなさい	\N	\N	\N
41	10	t	f	1	1	うな	\N	\N	\N
41	10	t	t	1	1	いなさるな	\N	\N	\N
41	11	f	f	1	1	ったら	\N	\N	\N
41	11	f	t	1	1	いましたら	\N	\N	\N
41	11	t	f	1	1	わかったら	\N	\N	\N
41	11	t	t	1	1	いませんでしたら	\N	\N	\N
41	12	f	f	1	1	ったり	\N	\N	\N
41	12	f	t	1	1	いましたり	\N	\N	\N
41	12	t	f	1	1	わなかったり	\N	\N	\N
41	12	t	t	1	1	いませんでしたり	\N	\N	\N
41	13	f	f	1	1	い	\N	\N	\N
42	1	f	f	1	1	う	\N	\N	\N
42	1	f	t	1	1	います	\N	\N	\N
42	1	t	f	1	1	わない	\N	\N	\N
42	1	t	t	1	1	いません	\N	\N	\N
42	2	f	f	1	1	うた	\N	\N	\N
42	2	f	t	1	1	いました	\N	\N	\N
42	2	t	f	1	1	わなかった	\N	\N	\N
42	2	t	t	1	1	いませんでした	\N	\N	\N
42	3	f	f	1	1	うて	\N	\N	\N
42	3	f	t	1	1	いまして	\N	\N	\N
42	3	t	f	1	1	わなくて	\N	\N	\N
42	3	t	f	2	1	わないで	\N	\N	\N
42	3	t	t	1	1	いませんで	\N	\N	\N
42	4	f	f	1	1	えば	\N	\N	\N
42	4	f	t	1	1	いますなら	\N	\N	\N
42	4	f	t	2	1	いますならば	\N	\N	\N
42	4	t	f	1	1	わなければ	\N	\N	\N
42	4	t	t	1	1	いませんなら	\N	\N	\N
42	4	t	t	2	1	いませんならば	\N	\N	\N
42	5	f	f	1	1	える	\N	\N	\N
42	5	f	t	1	1	えます	\N	\N	\N
42	5	t	f	1	1	えない	\N	\N	\N
42	5	t	t	1	1	えません	\N	\N	\N
42	6	f	f	1	1	われる	\N	\N	\N
42	6	f	t	1	1	われます	\N	\N	\N
42	6	t	f	1	1	われない	\N	\N	\N
42	6	t	t	1	1	われません	\N	\N	\N
42	7	f	f	1	1	わせる	\N	\N	\N
42	7	f	f	2	1	わす	\N	\N	\N
42	7	f	t	1	1	わせます	\N	\N	\N
42	7	f	t	2	1	わします	\N	\N	\N
42	7	t	f	1	1	わせない	\N	\N	\N
42	7	t	f	2	1	わさない	\N	\N	\N
42	7	t	t	1	1	わせません	\N	\N	\N
42	7	t	t	2	1	わしません	\N	\N	\N
42	8	f	f	1	1	わせられる	\N	\N	\N
42	8	f	f	2	1	わされる	\N	\N	\N
42	8	f	t	1	1	わせられます	\N	\N	\N
42	8	f	t	2	1	わされます	\N	\N	\N
42	8	t	f	1	1	わせられない	\N	\N	\N
42	8	t	f	2	1	わされない	\N	\N	\N
42	8	t	t	1	1	わせられません	\N	\N	\N
42	8	t	t	2	1	わされません	\N	\N	\N
42	9	f	f	1	1	おう	\N	\N	\N
42	9	f	t	1	1	いましょう	\N	\N	\N
42	9	t	f	1	1	うまい	\N	\N	\N
42	9	t	t	1	1	いませんまい	\N	\N	\N
42	10	f	f	1	1	え	\N	\N	\N
42	10	f	t	1	1	いなさい	\N	\N	\N
42	10	t	f	1	1	うな	\N	\N	\N
42	10	t	t	1	1	いなさるな	\N	\N	\N
42	11	f	f	1	1	うたら	\N	\N	\N
42	11	f	t	1	1	いましたら	\N	\N	\N
42	11	t	f	1	1	わなかったら	\N	\N	\N
42	11	t	t	1	1	いませんでしたら	\N	\N	\N
42	12	f	f	1	1	うたり	\N	\N	\N
42	12	f	t	1	1	いましたり	\N	\N	\N
42	12	t	f	1	1	わなかったり	\N	\N	\N
42	12	t	t	1	1	いませんでしたり	\N	\N	\N
42	13	f	f	1	1	い	\N	\N	\N
45	1	f	f	1	1	る	く	\N	\N
45	1	f	t	1	1	ます	き	\N	\N
45	1	t	f	1	1	ない	こ	\N	\N
45	1	t	t	1	1	ません	き	\N	\N
45	2	f	f	1	1	た	き	\N	\N
45	2	f	t	1	1	ました	き	\N	\N
45	2	t	f	1	1	なかった	こ	\N	\N
45	2	t	t	1	1	ませんでした	き	\N	\N
45	3	f	f	1	1	て	き	\N	\N
45	3	f	t	1	1	まして	き	\N	\N
45	3	t	f	1	1	なくて	こ	\N	\N
45	3	t	f	2	1	ないで	こ	\N	\N
45	3	t	t	1	1	ませんで	き	\N	\N
45	4	f	f	1	1	れば	く	\N	\N
45	4	f	t	1	1	ますなら	く	\N	\N
45	4	f	t	2	1	ますならば	く	\N	\N
45	4	t	f	1	1	なければ	く	\N	\N
45	4	t	t	1	1	ませんなら	く	\N	\N
45	4	t	t	2	1	ませんならば	く	\N	\N
45	5	f	f	1	1	られる	こ	\N	\N
45	5	f	f	2	1	れる	こ	\N	\N
45	5	f	t	1	1	られます	こ	\N	\N
45	5	f	t	2	1	れます	こ	\N	\N
45	5	t	f	1	1	られない	こ	\N	\N
45	5	t	f	2	1	れない	こ	\N	\N
45	5	t	t	1	1	られません	こ	\N	\N
45	5	t	t	2	1	れません	こ	\N	\N
45	6	f	f	1	1	られる	こ	\N	\N
45	6	f	t	1	1	られます	こ	\N	\N
45	6	t	f	1	1	られない	こ	\N	\N
45	6	t	t	1	1	られません	こ	\N	\N
45	7	f	f	1	1	させる	こ	\N	\N
45	7	f	f	2	1	さす	こ	\N	\N
45	7	f	t	1	1	させます	こ	\N	\N
45	7	f	t	2	1	さします	こ	\N	\N
45	7	t	f	1	1	させない	こ	\N	\N
45	7	t	f	2	1	ささない	こ	\N	\N
45	7	t	t	1	1	させません	こ	\N	\N
45	7	t	t	2	1	さしません	こ	\N	\N
45	8	f	f	1	1	させられる	こ	\N	\N
45	8	f	t	1	1	させられます	こ	\N	\N
45	8	t	f	1	1	させられない	こ	\N	\N
45	8	t	t	1	1	させられません	こ	\N	\N
45	9	f	f	1	1	よう	こ	\N	\N
45	9	f	t	1	1	ましょう	き	\N	\N
45	9	t	f	1	1	まい	こ	\N	\N
45	9	t	t	1	1	ますまい	き	\N	\N
45	10	f	f	1	1	い	こ	\N	\N
45	10	f	t	1	1	なさい	こ	\N	\N
45	10	t	f	1	1	るな	く	\N	\N
45	10	t	t	1	1	なさるな	こ	\N	\N
45	11	f	f	1	1	たら	き	\N	\N
45	11	f	t	1	1	ましたら	き	\N	\N
45	11	t	f	1	1	なかったら	こ	\N	\N
45	11	t	t	1	1	ませんでしたら	き	\N	\N
45	12	f	f	1	1	たり	き	\N	\N
45	12	f	t	1	1	ましたり	き	\N	\N
45	12	t	f	1	1	なかったり	こ	\N	\N
45	12	t	t	1	1	ませんでしたり	き	\N	\N
45	13	f	f	1	1		き	\N	\N
46	1	f	f	1	0	する	\N	\N	\N
47	1	f	f	1	1	る	す	\N	\N
47	1	f	t	1	1	ます	し	\N	\N
47	1	t	f	1	1	ない	さ	\N	\N
47	1	t	t	1	1	ません	し	\N	\N
47	2	f	f	1	1	た	し	\N	\N
47	2	f	t	1	1	ました	し	\N	\N
47	2	t	f	1	1	なかった	さ	\N	\N
47	2	t	t	1	1	ませんでした	し	\N	\N
47	3	f	f	1	1	て	し	\N	\N
47	3	f	t	1	1	まして	し	\N	\N
47	3	t	f	1	1	なくて	さ	\N	\N
47	3	t	f	2	1	ないで	し	\N	\N
47	3	t	t	1	1	ませんで	し	\N	\N
47	4	f	f	1	1	れば	す	\N	\N
47	4	f	t	1	1	ますなら	し	\N	\N
47	4	f	t	2	1	ますなれば	し	\N	\N
47	4	t	f	1	1	なければ	さ	\N	\N
47	4	t	t	1	1	ませんなら	し	\N	\N
47	4	t	t	2	1	ませんならば	し	\N	\N
47	5	f	f	1	1	る	しえ	\N	\N
47	5	f	f	2	1	る	しう	\N	\N
47	5	f	t	1	1	ます	しえ	\N	\N
47	5	t	f	1	1	ない	しえ	\N	\N
47	5	t	t	1	1	ません	しえ	\N	\N
47	6	f	f	1	1	れる	さ	\N	\N
47	6	f	t	1	1	れます	さ	\N	\N
47	6	t	f	1	1	れない	さ	\N	\N
47	6	t	t	1	1	れません	さ	\N	\N
47	7	f	f	1	1	せる	さ	\N	\N
47	7	f	f	2	1	す	さ	\N	\N
47	7	f	t	1	1	せます	さ	\N	\N
47	7	f	t	2	1	します	さ	\N	\N
47	7	t	f	1	1	せない	さ	\N	\N
47	7	t	f	2	1	さない	さ	\N	\N
47	7	t	t	1	1	せません	さ	\N	\N
47	7	t	t	2	1	しません	さ	\N	\N
47	8	f	f	1	1	せられる	さ	\N	\N
47	8	f	t	1	1	せられます	さ	\N	\N
47	8	t	f	1	1	せられない	さ	\N	\N
47	8	t	t	1	1	せられません	さ	\N	\N
47	9	f	f	1	1	よう	し	\N	\N
47	9	f	t	1	1	ましょう	し	\N	\N
47	9	t	f	1	1	るまい	す	\N	\N
47	9	t	t	1	1	ますまい	し	\N	\N
47	10	f	f	1	1	ろ	し	\N	\N
47	10	f	f	2	1	よ	せ	\N	\N
47	10	f	t	1	1	なさい	し	\N	\N
47	10	t	f	1	1	るな	す	\N	\N
47	10	t	t	1	1	なさるな	し	\N	\N
47	11	f	f	1	1	たら	し	\N	\N
47	11	f	t	1	1	ましたら	し	\N	\N
47	11	t	f	1	1	なかったら	さ	\N	\N
47	11	t	t	1	1	ませんでしたら	し	\N	\N
47	12	f	f	1	1	たり	し	\N	\N
47	12	f	t	1	1	ましたり	し	\N	\N
47	12	t	f	1	1	なかったり	さ	\N	\N
47	12	t	t	1	1	ませんでしたり	し	\N	\N
47	13	f	f	1	1		し	\N	\N
48	1	f	f	1	1	る	す	\N	\N
48	1	f	t	1	1	ます	し	\N	\N
48	1	t	f	1	1	ない	し	\N	\N
48	1	t	t	1	1	ません	し	\N	\N
48	2	f	f	1	1	た	し	\N	\N
48	2	f	t	1	1	ました	し	\N	\N
48	2	t	f	1	1	なかった	し	\N	\N
48	2	t	t	1	1	ませんでした	し	\N	\N
48	3	f	f	1	1	て	し	\N	\N
48	3	f	t	1	1	まして	し	\N	\N
48	3	t	f	1	1	なくて	し	\N	\N
48	3	t	f	2	1	ないで	し	\N	\N
48	3	t	t	1	1	ませんで	し	\N	\N
48	4	f	f	1	1	れば	す	\N	\N
48	4	f	t	1	1	ますなら	し	\N	\N
48	4	f	t	2	1	ますなれば	し	\N	\N
48	4	t	f	1	1	なければ	し	\N	\N
48	4	t	t	1	1	ませんなら	し	\N	\N
48	4	t	t	2	1	ませんならば	し	\N	\N
48	5	f	f	1	1	る	でき	出来	\N
48	5	f	t	1	1	ます	でき	出来	\N
48	5	t	f	1	1	ない	でき	出来	\N
48	5	t	t	1	1	ません	でき	出来	\N
48	6	f	f	1	1	れる	さ	\N	\N
48	6	f	t	1	1	れます	さ	\N	\N
48	6	t	f	1	1	れない	さ	\N	\N
48	6	t	t	1	1	れません	さ	\N	\N
48	7	f	f	1	1	せる	さ	\N	\N
48	7	f	f	2	1	す	さ	\N	\N
48	7	f	t	1	1	せます	さ	\N	\N
48	7	f	t	2	1	します	さ	\N	\N
48	7	t	f	1	1	せない	さ	\N	\N
48	7	t	f	2	1	さない	さ	\N	\N
48	7	t	t	1	1	せません	さ	\N	\N
48	7	t	t	2	1	しません	さ	\N	\N
48	8	f	f	1	1	せられる	さ	\N	\N
48	8	f	t	1	1	せられます	さ	\N	\N
48	8	t	f	1	1	せられない	さ	\N	\N
48	8	t	t	1	1	せられません	さ	\N	\N
48	9	f	f	1	1	よう	し	\N	\N
48	9	f	t	1	1	ましょう	し	\N	\N
48	9	t	f	1	1	るまい	す	\N	\N
48	9	t	t	1	1	ますまい	し	\N	\N
48	10	f	f	1	1	ろ	し	\N	\N
48	10	f	f	2	1	よ	せ	\N	\N
48	10	f	t	1	1	なさい	し	\N	\N
48	10	t	f	1	1	るな	す	\N	\N
48	10	t	t	1	1	なさるな	し	\N	\N
48	11	f	f	1	1	たら	し	\N	\N
48	11	f	t	1	1	ましたら	し	\N	\N
48	11	t	f	1	1	なかったら	し	\N	\N
48	11	t	t	1	1	ませんでしたら	し	\N	\N
48	12	f	f	1	1	たり	し	\N	\N
48	12	f	t	1	1	ましたり	し	\N	\N
48	12	t	f	1	1	なかったり	し	\N	\N
48	12	t	t	1	1	ませんでしたり	し	\N	\N
48	13	f	f	1	1		し	\N	\N
\.


--
-- Data for Name: conjo_notes; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.conjo_notes (pos, conj, neg, fml, onum, note) FROM stdin;
2	1	f	f	1	7
15	1	t	f	1	3
15	1	t	t	1	3
15	1	t	t	2	3
15	2	t	f	1	3
15	2	t	t	1	3
15	3	t	f	1	3
15	4	f	f	1	2
15	11	t	f	1	3
15	11	t	t	1	3
17	1	f	f	1	7
28	5	f	f	2	6
28	5	f	t	2	6
28	5	t	f	2	6
28	5	t	t	2	6
28	9	t	f	1	5
28	9	t	t	1	5
29	5	f	f	2	6
29	5	f	t	2	6
29	5	t	f	2	6
29	5	t	t	2	6
29	9	t	f	1	5
29	9	t	t	1	5
29	10	f	f	1	1
30	1	f	t	1	1
30	1	t	t	1	1
30	2	f	t	1	1
30	2	t	t	1	1
30	3	f	t	1	1
30	3	t	t	1	1
30	4	f	t	1	1
30	4	f	t	2	1
30	4	t	t	1	1
30	4	t	t	2	1
30	9	f	t	1	1
30	9	t	f	1	5
30	9	t	t	1	5
30	10	f	f	1	1
30	10	f	t	1	1
30	10	t	t	1	1
30	11	f	t	1	1
30	11	t	t	1	1
30	12	f	t	1	1
30	13	f	f	1	1
31	9	t	f	1	5
31	9	t	t	1	5
32	9	t	f	1	5
32	9	t	t	1	5
33	9	t	f	1	5
33	9	t	t	1	5
34	2	f	f	1	1
34	3	f	f	1	1
34	9	t	f	1	5
34	9	t	t	1	5
34	11	f	f	1	1
34	12	f	f	1	1
35	9	t	f	1	5
35	9	t	t	1	5
36	9	t	f	1	5
36	9	t	t	1	5
37	9	t	f	1	5
37	9	t	t	1	5
38	1	t	f	1	1
38	2	t	f	1	1
38	3	t	f	1	1
38	3	t	f	2	1
38	9	t	f	1	5
38	9	t	t	1	5
38	11	t	f	1	1
38	12	t	f	1	1
39	9	t	f	1	5
39	9	t	t	1	5
40	9	t	f	1	5
40	9	t	t	1	5
41	9	t	f	1	5
41	9	t	t	1	5
42	2	f	f	1	1
42	3	f	f	1	1
42	9	t	f	1	5
42	9	t	t	1	5
42	11	f	f	1	1
42	12	f	f	1	1
45	5	f	f	2	6
45	5	f	t	2	6
45	5	t	f	2	6
45	5	t	t	2	6
45	9	t	f	1	5
45	9	t	t	1	5
45	10	f	f	1	1
46	1	f	f	1	8
47	5	f	f	1	1
47	5	f	t	1	1
47	5	t	f	1	1
47	5	t	t	1	1
47	6	f	f	1	1
47	6	f	t	1	1
47	6	t	f	1	1
47	6	t	t	1	1
47	7	f	f	1	1
47	7	f	f	2	1
47	7	f	t	1	1
47	7	f	t	2	1
47	7	t	f	1	1
47	7	t	f	2	1
47	7	t	t	1	1
47	7	t	t	2	1
47	8	f	f	1	1
47	8	f	t	1	1
47	8	t	f	1	1
47	8	t	t	1	1
47	9	t	f	1	5
47	9	t	t	1	5
47	10	f	f	2	1
48	5	f	f	1	1
48	5	f	t	1	1
48	5	t	f	1	1
48	5	t	t	1	1
48	6	f	f	1	1
48	6	f	t	1	1
48	6	t	f	1	1
48	6	t	t	1	1
48	7	f	f	1	1
48	7	f	f	2	1
48	7	f	t	1	1
48	7	f	t	2	1
48	7	t	f	1	1
48	7	t	f	2	1
48	7	t	t	1	1
48	7	t	t	2	1
48	8	f	f	1	1
48	8	f	t	1	1
48	8	t	f	1	1
48	8	t	t	1	1
48	9	t	f	1	5
48	9	t	t	1	5
48	10	f	f	2	1
\.


--
-- Data for Name: conotes; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.conotes (id, txt) FROM stdin;
1	Irregular conjugation.  Note that this not the same as the definition\n of "irregular verb" commonly found in textbooks (typically する and\n 来る).  It denotes okurigana that is different than other words of\n the same class.  Thus the past tense of 行く (行った) is an irregular\n conjugation because other く (v5k) verbs use いた as the okurigana for\n this conjugation.  します is not an irregular conjugation because if\n we take する to behave as a v1 verb the okurigana is the same as other\n v1 verbs despite the sound change of the stem (す) part of the verb\n to し.
2	na-adjectives and nouns are usually used with the なら nara conditional, instead of with であれば de areba. なら is a contracted and more common form of ならば.
3	では is often contracted to じゃ in colloquial speech.
4	The (first) non-abbreviated form is obtained by applying sequentially the causative, then passive conjugations.
5	The -まい negative form is literary and rather rare.
6	The ら is sometimes dropped from -られる, etc. in the potential form in conversational Japanese, but it is not regarded as grammatically correct.
7	'n' and 'adj-na' words when used as predicates are followed by the\n copula <a href="entr.py?svc=jmdict&sid=&q=2089020.jmdict">だ</a> which is what is conjugated (<a href="conj.py?svc=jmdict&sid=&q=2089020.jmdict">conjugations</a>).
8	'vs' words are followed by <a href=entr.py?svc=jmdict&sid=&q=1157170.jmdict>する</a> which is what is conjugated (<a href=conj.py?svc=jmdict&sid=&q=1157170.jmdict>conjugations</a>).
\.


--
-- Data for Name: db; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.db (id, active, ts) FROM stdin;
8607617	t	2019-05-14 10:46:08.849884
\.


--
-- Data for Name: dial; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.dial (entr, sens, ord, kw) FROM stdin;
4	1	1	2
\.


--
-- Data for Name: entr; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.entr (id, src, stat, seq, dfrm, unap, srcnote, notes) FROM stdin;
1	1	2	1000090	\N	f	\N	\N
2	1	2	1000290	\N	f	\N	\N
3	1	2	1000420	\N	f	\N	\N
4	1	2	1000480	\N	f	\N	\N
5	1	2	1000490	\N	f	\N	\N
6	1	2	1000520	\N	f	\N	\N
7	1	2	1000580	\N	f	\N	\N
8	1	2	1000730	\N	f	\N	\N
9	1	2	1000920	\N	f	\N	\N
10	1	2	1000930	\N	f	\N	\N
11	1	2	1000940	\N	f	\N	\N
12	1	2	1002320	\N	f	\N	\N
13	1	2	1002480	\N	f	\N	\N
14	1	2	1004020	\N	f	\N	\N
15	1	2	1005250	\N	f	\N	\N
16	1	2	1005930	\N	f	\N	\N
17	1	2	1006830	\N	f	\N	\N
18	1	2	1011770	\N	f	\N	\N
19	1	2	1013970	\N	f	\N	\N
20	1	2	1013980	\N	f	\N	\N
21	1	2	1017940	\N	f	\N	\N
22	1	2	1017950	\N	f	\N	\N
23	1	2	1019420	\N	f	\N	\N
24	1	2	1028520	\N	f	\N	\N
25	1	2	1055420	\N	f	\N	\N
26	1	2	1075210	\N	f	\N	\N
27	1	2	1077760	\N	f	\N	\N
28	1	2	1079110	\N	f	\N	\N
29	1	2	1087930	\N	f	\N	\N
30	1	2	1097870	\N	f	\N	\N
31	1	2	1098650	\N	f	\N	\N
32	1	2	1099200	\N	f	\N	\N
33	1	2	1106120	\N	f	\N	\N
34	1	2	1140360	\N	f	\N	\N
35	1	2	1198180	\N	f	\N	\N
36	1	2	1208850	\N	f	\N	\N
37	1	2	1214540	\N	f	\N	\N
38	1	2	1214560	\N	f	\N	\N
39	1	2	1316860	\N	f	\N	\N
40	1	2	1324440	\N	f	\N	\N
41	1	2	1329750	\N	f	\N	\N
42	1	2	1348750	\N	f	\N	\N
43	1	2	1379360	\N	f	\N	\N
44	1	2	1398850	\N	f	\N	\N
45	1	2	1401950	\N	f	\N	\N
46	1	2	1414950	\N	f	\N	\N
47	1	2	1416050	\N	f	\N	\N
48	1	2	1456930	\N	f	\N	\N
49	1	2	1516925	\N	f	\N	\N
50	1	2	1517910	\N	f	\N	\N
51	1	2	1528300	\N	f	\N	\N
52	1	2	1542640	\N	f	\N	\N
53	1	2	1578780	\N	f	\N	\N
54	1	2	1582580	\N	f	\N	\N
55	1	2	1582920	\N	f	\N	\N
56	1	2	1593470	\N	f	\N	\N
57	1	2	1593475	\N	f	\N	\N
58	1	2	1603990	\N	f	\N	\N
59	1	2	1604310	\N	f	\N	\N
60	1	2	1612710	\N	f	\N	\N
61	1	2	1629230	\N	f	\N	\N
62	1	2	1778610	\N	f	\N	\N
63	1	2	1920240	\N	f	\N	\N
64	1	2	1920245	\N	f	\N	\N
65	1	2	2013840	\N	f	\N	\N
66	1	2	2038530	\N	f	\N	\N
67	1	2	2107800	\N	f	\N	\N
68	1	2	2148610	\N	f	\N	\N
69	1	2	2159530	\N	f	\N	\N
70	1	2	2194060	\N	f	\N	\N
71	1	2	2195100	\N	f	\N	\N
72	1	2	2209290	\N	f	\N	\N
73	1	2	2231000	\N	f	\N	\N
74	1	2	2234570	\N	f	\N	\N
75	1	2	2404900	\N	f	\N	\N
76	1	2	2518550	\N	f	\N	\N
77	1	2	2636250	\N	f	\N	\N
78	1	2	2833860	\N	f	\N	\N
104	1	2	2833900	\N	f		
105	1	2	2833900	104	t		
106	1	2	2833900	105	t		
107	1	4	2833900	104	t		
109	1	6	2833900	\N	f		
115	2	2	5655279	\N	f		
116	1	2	1526080	\N	f		
120	1	4	2833910	\N	f		
121	1	6	2833920	\N	f		
\.


--
-- Data for Name: entrsnd; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.entrsnd (entr, ord, snd) FROM stdin;
\.


--
-- Data for Name: fld; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.fld (entr, sens, ord, kw) FROM stdin;
21	1	1	22
30	2	1	2
30	2	2	7
32	1	1	13
34	3	1	3
44	1	1	7
\.


--
-- Data for Name: freq; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.freq (entr, rdng, kanj, kw, value) FROM stdin;
3	1	\N	4	1
3	\N	1	4	1
6	1	\N	1	1
7	1	\N	1	1
7	\N	1	1	1
8	1	\N	1	1
8	\N	1	1	1
9	1	\N	4	1
10	1	\N	1	1
11	1	\N	1	1
12	1	\N	1	1
12	\N	1	1	1
16	1	\N	4	1
16	2	\N	1	1
16	\N	1	4	1
16	\N	2	1	1
17	1	\N	4	1
17	\N	1	4	1
18	1	\N	1	1
18	\N	1	1	1
18	\N	2	1	1
19	1	\N	2	1
19	1	\N	1	1
20	1	\N	2	1
20	1	\N	1	1
23	1	\N	2	1
23	1	\N	1	1
27	3	\N	2	1
28	1	\N	2	1
30	1	\N	2	1
30	1	\N	1	1
34	1	\N	2	1
35	1	\N	1	1
35	1	\N	7	2
35	1	\N	5	26
35	\N	1	1	1
35	\N	1	7	2
35	\N	1	5	26
35	\N	2	1	1
35	\N	3	1	1
35	\N	3	7	2
35	\N	3	5	34
36	1	\N	7	2
36	1	\N	5	41
36	\N	1	7	2
36	\N	1	5	41
37	1	\N	1	1
37	1	\N	7	1
37	1	\N	5	6
37	\N	1	1	1
37	\N	1	7	1
37	\N	1	5	6
38	1	\N	1	1
38	1	\N	7	1
38	1	\N	5	14
38	\N	1	1	1
38	\N	1	7	1
38	\N	1	5	14
38	\N	2	1	1
40	1	\N	1	1
40	\N	1	1	1
40	\N	2	1	1
42	1	\N	1	1
42	1	\N	7	2
42	1	\N	5	45
42	\N	1	1	1
42	\N	1	7	2
42	\N	1	5	45
43	1	\N	7	1
43	1	\N	5	19
43	\N	1	7	1
43	\N	1	5	19
46	1	\N	1	1
46	1	\N	7	2
46	1	\N	5	35
46	\N	1	1	1
46	\N	1	7	2
46	\N	1	5	35
47	1	\N	4	1
47	2	\N	4	1
47	\N	1	4	1
48	1	\N	7	2
48	1	\N	5	30
48	\N	1	7	2
48	\N	1	5	30
49	1	\N	1	1
49	\N	1	1	1
51	1	\N	7	1
51	1	\N	5	17
51	\N	1	7	1
51	\N	1	5	17
52	1	\N	7	1
52	1	\N	5	18
52	2	\N	1	1
52	2	\N	7	1
52	2	\N	5	21
52	\N	1	7	1
52	\N	1	5	18
52	\N	2	1	1
52	\N	2	7	1
52	\N	2	5	21
53	1	\N	1	1
53	1	\N	7	1
53	1	\N	5	16
53	2	\N	1	1
53	\N	1	1	1
53	\N	1	7	1
53	\N	1	5	16
54	1	\N	1	1
54	\N	1	1	1
55	1	\N	1	1
55	\N	1	1	1
56	1	\N	7	1
56	1	\N	5	14
56	\N	1	7	1
56	\N	1	5	14
58	1	\N	1	1
58	1	\N	7	1
58	1	\N	5	2
58	\N	1	1	1
58	\N	1	7	1
58	\N	1	5	2
59	1	\N	7	1
59	1	\N	5	18
59	\N	1	7	1
59	\N	1	5	18
60	1	\N	1	1
60	\N	1	1	1
63	1	\N	7	1
63	1	\N	5	5
63	\N	1	7	1
63	\N	1	5	5
73	1	\N	1	1
73	\N	1	1	1
116	\N	1	1	1
116	\N	1	7	1
116	\N	1	5	23
116	1	\N	1	1
116	1	\N	7	1
116	1	\N	5	23
\.


--
-- Data for Name: gloss; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.gloss (entr, sens, gloss, lang, ginf, txt) FROM stdin;
1	1	1	1	1	circle (sometimes used for zero)
1	2	1	1	1	'correct' (when marking)
1	3	1	1	1	symbol used as a placeholder (either because a number of other words could be used in that position, or because of censorship)
1	4	1	1	1	period
1	4	2	1	1	full stop
1	5	1	1	1	maru mark
1	5	2	1	1	semivoiced sound
1	5	3	1	1	p-sound
2	1	1	1	1	Jouetsu line express Shinkansen
3	1	1	1	1	that (someone or something distant from both speaker and listener, or situation unfamiliar to both speaker and listener)
4	1	1	1	1	fool
4	1	2	1	1	oaf
4	1	3	1	1	airhead
4	2	1	1	4	type of fast-paced humorous singing mimicking the chanting of a Buddhist sutra, usually with lyrics satirizing current events
5	1	1	1	1	land-locked variety of red-spotted masu trout (Oncorhynchus masou ishikawae)
5	1	2	1	1	amago
6	1	1	1	1	oh
6	1	2	1	1	ah
7	1	1	1	1	that (indicating something distant from both speaker and listener (in space, time or psychologically), or something understood without naming it directly)
7	2	1	1	1	that person
7	3	1	1	1	over there
7	4	1	1	1	down there (i.e. one's genitals)
7	5	1	1	1	period
7	5	2	1	1	menses
7	6	1	1	1	hey
7	6	2	1	1	huh?
7	6	3	1	1	eh?
7	7	1	1	1	that (something mentioned before which is distant psychologically or in terms of time)
8	1	1	1	1	wrong
8	1	2	1	1	not good
8	1	3	1	1	of no use
8	2	1	1	1	hopeless
8	2	2	1	1	past hope
8	3	1	1	1	must not do
9	1	1	1	1	come
9	1	2	1	1	go
9	1	3	1	1	stay
9	2	1	1	1	welcome
10	1	1	1	1	welcome (in shops, etc.)
11	1	1	1	1	to come
11	1	2	1	1	to go
11	1	3	1	1	to be (somewhere)
11	2	1	1	1	to be (doing)
12	1	1	1	1	grandfather
12	2	1	1	1	male senior-citizen
13	1	1	1	1	tomboy
14	1	1	1	1	fast (asleep)
14	1	2	1	1	snoring or grumbling sound
15	1	1	1	1	relieved
15	1	2	1	1	refreshed
15	2	1	1	1	easy-going
15	2	2	1	1	laid-back
15	2	3	1	1	frank
15	2	4	1	1	candid
16	1	1	1	1	potato (Solanum tuberosum)
17	1	1	1	1	that (something or someone distant from the speaker, close to the listener; actions of the listener, or ideas expressed or understood by the listener)
17	1	2	1	1	the
17	2	1	1	1	um...
17	2	2	1	1	er...
17	2	3	1	1	uh...
18	1	1	1	1	idiot
18	1	2	1	1	fool
18	1	3	1	1	touched in the head (from)
18	1	4	1	1	out of it (from)
18	1	5	1	1	space case
18	2	1	1	1	funny man (of a comedy duo)
18	2	2	1	1	(in comedy) silly or stupid line
18	3	1	1	1	Alzheimer's (impol)
19	1	1	1	1	ice
19	2	1	1	1	ice cream
19	2	2	1	1	icecream
20	1	1	1	1	ice cream
20	1	2	1	1	icecream
21	1	1	1	1	aftercare
21	1	2	1	1	care for patients after discharge from hospital
21	2	1	1	1	after-sales service
22	1	1	1	1	after-sales service
22	1	2	1	1	warranty service
23	1	1	1	1	part-time job
23	1	2	1	1	side job
23	2	1	1	1	part-time worker
23	3	1	1	1	albite
24	1	1	1	1	science fiction
24	1	2	1	1	sci-fi
24	1	3	1	1	SF
25	1	1	1	1	science fiction
25	1	2	1	1	sci-fi
26	1	1	1	1	007 (James Bond's code in the books and films)
26	1	2	1	1	double-oh-seven
27	1	1	1	1	typhoid fever
27	1	2	1	1	typhus
28	1	1	1	1	tissue paper
28	1	2	1	1	tissue
28	1	3	1	1	facial tissue
28	1	4	1	1	facial tissues
29	1	1	1	1	doorman
30	1	1	1	1	work (esp. part time or casual)
30	2	1	1	1	byte
30	2	2	1	1	octet
30	3	1	1	1	bite
30	4	1	1	1	cutting tool
30	4	2	1	1	bit
31	1	1	1	1	battered child (syndrome)
32	1	1	1	1	batting practice facility
32	1	2	1	1	batting practice center
32	1	3	1	1	batting cage
33	1	1	1	1	piroshki (Russian pierogi; meat and eggs, etc. baked in bread)
34	1	1	1	1	lamp
34	1	2	1	1	light
34	2	1	1	1	ramp
34	3	1	1	1	rump
35	1	1	1	1	to meet
35	1	2	1	1	to encounter
35	1	3	1	1	to see
35	2	1	1	1	to have an accident
35	2	2	1	1	to have a bad experience
36	1	1	1	1	skipjack tuna (Katsuwonus pelamis)
36	1	2	1	1	oceanic bonito
36	1	3	1	1	victorfish
37	1	1	1	1	can
37	1	2	1	1	tin
37	2	1	1	1	canned food
38	1	1	1	1	canned food
38	1	2	1	1	tinned food
38	2	1	1	1	confining someone (e.g. so they can concentrate on work)
38	3	1	1	1	being stuck in a confined space
39	1	1	1	1	jig (tool)
40	1	1	1	1	wakame (species of edible brown seaweed, Undaria pinnatifida)
41	1	1	1	1	examination hell
41	1	2	1	1	ordeal of entrance examinations
42	1	1	1	1	lowercase letter
42	2	1	1	1	small letter
43	1	1	1	1	live broadcast (radio, TV)
43	1	2	1	1	live coverage
44	1	1	1	1	duality
45	1	1	1	1	kanji "grass radical" (radical 140)
45	2	1	1	1	grass crown
46	1	1	1	1	uppercase letter
46	1	2	1	1	capital letter
46	2	1	1	1	large character
46	2	2	1	1	large writing
46	3	1	1	1	the (kanji) character "dai" meaning "big"
46	4	1	1	1	huge character "dai" formed by fires lit on the side of a mountain in Kyoto on August 16 each year
47	1	1	1	1	mince (minced meat or fish)
47	2	1	1	1	seared skipjack tuna
47	3	1	1	1	robbery
47	3	2	1	1	extortion
47	4	1	1	1	hard-packed dirt (clay, gravel, etc.) floor
47	4	2	1	1	concrete floor
47	5	1	1	1	whipping
47	5	2	1	1	lashing
47	5	3	1	1	bashing
47	5	4	1	1	beating
47	5	5	1	1	flaming
48	1	1	1	1	penetration
48	1	2	1	1	digging into something
48	2	1	1	1	(in comedy) straight man
48	2	2	1	1	retort
48	2	3	1	1	quip
48	3	1	1	1	sex
48	3	2	1	1	intercourse
49	1	1	1	1	direction
49	1	2	1	1	way
49	2	1	1	1	person
49	2	2	1	1	lady
49	2	3	1	1	gentleman
49	3	1	1	1	method of
49	3	2	1	1	manner of
49	3	3	1	1	way of
49	4	1	1	1	care of ...
49	5	1	1	1	person in charge of ...
49	6	1	1	1	side (e.g. "on my mother's side")
50	1	1	1	1	backhanded compliment
50	1	2	1	1	making fun of someone via excessive praise
51	1	1	1	1	close adhesion
51	1	2	1	1	sticking firmly to
51	1	3	1	1	being glued to
51	2	1	1	1	relating closely to
51	2	2	1	1	having relevance to
51	3	1	1	1	contact printing
52	1	1	1	1	evening
52	2	1	1	1	last night
52	2	2	1	1	yesterday evening
53	1	1	1	1	autumn colours
53	1	2	1	1	fall colors
53	1	3	1	1	leaves changing color (colour)
53	2	1	1	1	leaves turning red
53	2	2	1	1	red leaves
53	3	1	1	1	leaves turning yellow
53	3	2	1	1	yellow leaves
53	4	1	1	1	(Japanese) maple (Acer japonicum)
53	5	1	1	1	venison
53	6	1	1	1	layered colors in garments, resembling autumn colors
54	1	1	1	1	pumpkin (Cucurbita sp.)
54	1	2	1	1	squash
55	1	1	1	1	this (something or someone close to the speaker (including the speaker), or ideas expressed by the speaker)
56	1	1	1	1	seasonal change of clothing
56	1	2	1	1	changing (one's) dress for the season
56	2	1	1	1	renovation
56	2	2	1	1	facelift
56	2	3	1	1	changing appearance
57	1	1	1	1	changing one's clothes
57	2	1	1	1	lady court attendant
58	1	1	1	1	town
58	1	2	1	1	block
58	1	3	1	1	neighbourhood
58	1	4	1	1	neighborhood
58	2	1	1	1	downtown
58	2	2	1	1	main street
58	3	1	1	1	street
58	3	2	1	1	road
58	4	1	1	1	109.09 m
58	5	1	1	1	0.99 hectares
59	1	1	1	1	manzai
59	1	2	1	1	comic dialogue
59	1	3	1	4	two-person comedy act (usu. presented as a fast-paced dialogue, occ. presented as a skit)
60	1	1	1	1	tissue paper
60	1	2	1	1	toilet paper
61	1	1	1	1	undershirt
62	1	1	1	1	mock Buddhist sutra
62	1	2	1	4	type of fast-paced humorous singing mimicking the chanting of a Buddhist sutra, usually with lyrics satirizing current events
62	1	3	1	1	ahodarakyō
63	1	1	1	1	which
63	1	2	1	1	what (way)
64	1	1	1	1	what kind
64	1	2	1	1	what sort
65	1	1	1	1	tomfoolery
65	1	2	1	1	monkey business
66	1	1	1	1	Nuclear and Industrial Safety Agency
66	1	2	1	1	NISA
67	1	1	1	1	social networking service
67	1	2	1	1	SNS
68	1	1	1	1	Japanese maple (Acer palmatum)
69	1	1	1	1	high-definition digital versatile disc (HD DVD, high-definition DVD)
70	1	1	1	1	potato (Solanum tuberosum)
71	1	1	1	1	lamp
72	1	1	1	1	battered child syndrome
73	1	1	1	1	grandfather (may be used after name as honorific)
73	2	1	1	1	male senior-citizen (may be used after name as honorific)
74	1	1	1	1	close coverage (of an event, celebrity, etc.)
74	1	2	1	1	close reporting
74	1	3	1	1	total coverage
75	1	1	1	1	grandfather (may be used after name as honorific)
75	2	1	1	1	male senior-citizen (may be used after name as honorific)
76	1	1	1	1	Asia-Pacific War (starting with the Manchurian Incident in 1931 and ending with the Japanese surrender in 1945)
76	1	2	1	1	Pacific War
77	1	1	1	1	sea-run variety of red-spotted masu trout (subspecies of cherry salmon, Oncorhynchus masou ishikawae)
77	1	2	1	1	red-spotted masu salmon
78	1	1	1	1	layered colors in garments, resembling autumn colors
104	1	1	1	1	test entry
105	1	1	1	1	test entry
106	1	1	1	1	test entry
107	1	1	1	1	test entry
109	1	1	1	1	test entry
115	1	1	1	1	Panji
116	1	1	1	1	all
116	1	2	1	1	everything
120	1	1	1	1	deleted entry
121	1	1	1	1	rejected entry
\.


--
-- Data for Name: grp; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.grp (entr, kw, ord, notes) FROM stdin;
\.


--
-- Data for Name: hist; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.hist (entr, hist, stat, unap, dt, userid, name, email, diff, refs, notes) FROM stdin;
104	1	2	f	2020-01-26 21:56:59	smg			\N		
105	1	2	f	2020-01-26 21:56:59	smg			\N		
105	2	2	t	2020-01-26 21:59:28	smg					edit #1
106	1	2	f	2020-01-26 21:56:59	smg			\N		
106	2	2	t	2020-01-26 21:59:28	smg					edit #1
106	3	2	t	2020-01-26 21:59:44	smg					edit #2
107	1	2	f	2020-01-26 21:56:59	smg			\N		
107	2	4	t	2020-01-26 22:00:22	smg					for delete
109	1	2	f	2020-01-26 21:56:59	smg			\N		
109	2	2	t	2020-01-26 22:01:48	smg					for reject
109	3	6	f	2020-01-26 22:02:24	smg					reject
115	1	2	f	2020-01-27 02:02:11	smg			\N		
116	1	2	f	2020-01-27 23:53:16	smg			\N		
120	1	2	t	2020-01-30 01:55:29	smg			\N		
120	2	4	f	2020-01-30 01:55:54	smg					
121	1	6	f	2020-01-30 01:56:52	smg			\N		
\.


--
-- Data for Name: kanj; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kanj (entr, kanj, txt) FROM stdin;
1	1	○
1	2	〇
3	1	彼の
4	1	阿呆陀羅
5	1	甘子
5	2	天魚
5	3	雨子
7	1	彼
8	1	行けない
12	1	お祖父さん
12	2	お爺さん
12	3	御爺さん
12	4	御祖父さん
13	1	お転婆
13	2	御転婆
16	1	じゃが芋
16	2	ジャガ芋
17	1	其の
18	1	惚け
18	2	呆け
24	1	ＳＦ
27	1	窒扶斯
35	1	会う
35	2	逢う
35	3	遭う
35	4	遇う
36	1	鰹
36	2	松魚
36	3	堅魚
37	1	缶
37	2	罐
37	3	鑵
38	1	缶詰
38	2	缶詰め
38	3	罐詰め
38	4	罐詰
39	1	治具
39	2	冶具
40	1	若布
40	2	和布
40	3	稚海藻
40	4	裙蔕菜
41	1	受験地獄
42	1	小文字
43	1	生中継
44	1	双対
45	1	草冠
45	2	艸
46	1	大文字
47	1	叩き
47	2	敲き
47	3	三和土
48	1	突っ込み
48	2	突っこみ
48	3	突込み
49	1	方
50	1	褒め殺し
50	2	ほめ殺し
50	3	誉め殺し
51	1	密着
52	1	夕べ
52	2	昨夜
53	1	紅葉
53	2	黄葉
54	1	南瓜
55	1	此の
55	2	斯の
56	1	衣替え
56	2	更衣
56	3	衣更え
57	1	更衣
58	1	町
58	2	街
59	1	漫才
59	2	万才
60	1	ちり紙
60	2	塵紙
62	1	あほだら経
62	2	阿呆陀羅経
63	1	何の
64	1	何の
65	1	馬鹿な真似
66	1	原子力安全保安院
66	2	原子力安全・保安院
68	1	以呂波紅葉
69	1	ＨＤＤＶＤ
69	2	ＨＤ・ＤＶＤ
70	1	ジャガタラ芋
70	2	ジャガタラ薯
71	1	洋灯
71	2	洋燈
72	1	被虐待児症候群
73	1	爺さん
73	2	祖父さん
74	1	密着取材
75	1	爺ちゃん
75	2	祖父ちゃん
76	1	アジア太平洋戦争
76	2	アジア・太平洋戦争
77	1	皐月鱒
78	1	紅葉襲
104	1	亜亜
105	1	亜亜
106	1	亜亜
107	1	亜亜
109	1	亜亜
115	1	万事
116	1	万事
\.


--
-- Data for Name: kinf; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kinf (entr, kanj, ord, kw) FROM stdin;
27	1	1	5
37	1	1	5
37	2	1	5
37	2	2	3
37	3	1	5
37	3	2	3
38	3	1	3
38	4	1	3
39	1	1	5
39	2	1	5
39	2	2	1
59	2	1	3
\.


--
-- Data for Name: kresolv; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kresolv (entr, kw, value) FROM stdin;
\.


--
-- Data for Name: kwcinf; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwcinf (id, kw, descr) FROM stdin;
1	nelson_c	"Modern Reader's Japanese-English Character Dictionary", edited by Andrew Nelson (now published as the "Classic" Nelson).
2	nelson_n	"The New Nelson Japanese-English Character Dictionary", edited by John Haig.
3	halpern_njecd	"New Japanese-English Character Dictionary", edited by Jack Halpern.
4	halpern_kkld	"Kanji Learners Dictionary" (Kodansha) edited by Jack Halpern.
5	heisig	"Remembering The  Kanji"  by  James Heisig.
6	gakken	"A  New Dictionary of Kanji Usage" (Gakken).
7	oneill_names	"Japanese Names", by P.G. O'Neill.
8	oneill_kk	"Essential Kanji" by P.G. O'Neill.
9	moro	"Daikanwajiten" compiled by Morohashi.
10	henshall	"A Guide To Remembering Japanese Characters" by Kenneth G.  Henshall.
11	sh_kk	"Kanji and Kana" by Spahn and Hadamitzky.
12	sakade	"A Guide To Reading and Writing Japanese" edited by Florence Sakade.
13	tutt_cards	Tuttle Kanji Cards, compiled by Alexander Kask.
14	crowley	"The Kanji Way to Japanese Language Power" by Dale Crowley.
15	kanji_in_ctx	"Kanji in Context" by Nishiguchi and Kono.
16	busy_people	"Japanese For Busy People" vols I-III, published by the AJLT. The codes are the volume.chapter.
17	kodansha_comp	The "Kodansha Compact Kanji Guide".
18	skip	Halpern's SKIP (System  of  Kanji  Indexing  by  Patterns) code.
19	sh_desc	Descriptor codes for The Kanji Dictionary (Tuttle 1996) by Spahn and Hadamitzky.
20	four_corner	"Four Corner" code for the kanji invented by Wang Chen in 1928.
21	deroo	Codes developed by the late Father Joseph De Roo, and published in  his book "2001 Kanji" (Bojinsha).
22	misclass	A possible misclassification of the kanji according to one of the code types.
23	pinyin	Modern PinYin romanization of the Chinese reading.
24	strokes	Stroke miscount or alternate count.
25	jis208	JIS X 0208-1997 - kuten coding (nn-nn).
26	jis212	JIS X 0212-1990 - kuten coding (nn-nn).
27	jis213	JIS X 0213-2000 - kuten coding (p-nn-nn).
28	henshall3	"A Guide To Reading and Writing Japanese" 3rd edition, edited by Henshall, Seeley and De Groot.
29	korean_h	Korean reading of the kanji in hangul.
30	korean_r	Romanized form of the Korean reading of the kanji.
31	jf_cards	Japanese Kanji Flashcards, by Max Hodges and Tomoko Okazaki.
32	nelson_rad	Radical number given in nelson_c.
33	skip_mis	SKIP code misclassification.
34	s_h	"The Kanji Dictionary" by Spahn and Hadamitzky.
35	maniette	Codes from Yves Maniette's "Les Kanjis dans la tete" French adaptation of Heisig.
36	halpern_kkd	"Kodansha Kanji Dictionary", (2nd Ed. of the NJECD) edited by Jack Halpern.
37	halpern_kkld_2ed	"Kanji Learners Dictionary" (Kodansha), 2nd edition (2013) edited by Jack Halpern.
38	heisig6	"Remembering The Kanji, Sixth Ed." by  James Heisig.
39	vietnam	Vietnamese reading.
40	sh_kk2	"Kanji and Kana" by Spahn and Hadamitzky (2011 edition).
101	gahoh	Filename of Quicktime animation.
\.


--
-- Data for Name: kwdial; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwdial (id, kw, descr) FROM stdin;
1	std	Tokyo-ben (std)
2	ksb	Kansai-ben
3	ktb	Kantou-ben
4	kyb	Kyoto-ben
5	osb	Osaka-ben
6	tsb	Tosa-ben
7	thb	Touhoku-ben
8	tsug	Tsugaru-ben
9	kyu	Kyuushuu-ben
10	rkb	Ryuukyuu-ben
11	nab	Nagano-ben
12	hob	Hokkaido-ben
\.


--
-- Data for Name: kwfld; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwfld (id, kw, descr) FROM stdin;
1	Buddh	Buddhist term
2	comp	computer terminology
3	food	food term
4	geom	geometry term
5	ling	linguistics terminology
6	MA	martial arts term
7	math	mathematics
8	mil	military
9	physics	physics terminology
10	chem	chemistry term
11	archit	architecture term
12	astron	astronomy, etc. term
13	baseb	baseball term
14	biol	biology term
15	bot	botany term
16	bus	business term
17	econ	economics term
18	engr	engineering term
19	finc	finance term
20	geol	geology, etc. term
21	law	law, etc. term
22	med	medicine, etc. term
23	music	music term
24	Shinto	Shinto term
25	sports	sports term
26	sumo	sumo term
27	zool	zoology term
28	anat	anatomical term
29	mahj	mahjong term
30	shogi	shogi term
\.


--
-- Data for Name: kwfreq; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwfreq (id, kw, descr) FROM stdin;
1	ichi	Ranking from Ichimango goi bunruishuu, 1-2.
2	gai	Common loanwords based on wordfreq file, 1-2
4	spec	Ranking assigned by JMdict editors, 1-2 
5	nf	Ranking in wordfreq file, 1-48
6	gA	Google counts (by Kale Stutzman, 2007-01-14)
7	news	Ranking in wordfreq file, 1-2
\.


--
-- Data for Name: kwginf; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwginf (id, kw, descr) FROM stdin;
1	equ	equivalent
2	lit	literaly
3	fig	figuratively
4	expl	explanatory
\.


--
-- Data for Name: kwgrp; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwgrp (id, kw, descr) FROM stdin;
\.


--
-- Data for Name: kwkinf; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwkinf (id, kw, descr) FROM stdin;
1	iK	word containing irregular kanji usage
2	io	irregular okurigana usage
3	oK	word containing out-dated kanji
4	ik	word containing irregular kana usage
5	ateji	ateji (phonetic) reading
\.


--
-- Data for Name: kwlang; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwlang (id, kw, descr) FROM stdin;
1	eng	English
2	abk	Abkhazian
3	ace	Achinese
4	ach	Acoli
5	ada	Adangme
6	ady	Adyghe; Adygei
7	afa	Afro-Asiatic (Other)
8	afh	Afrihili
9	afr	Afrikaans
10	ain	Ainu
11	aka	Akan
12	akk	Akkadian
13	alb	Albanian
14	ale	Aleut
15	alg	Algonquian languages
16	alt	Southern Altai
17	amh	Amharic
18	ang	English, Old (ca.450-1100)
19	anp	Angika
20	apa	Apache languages
21	ara	Arabic
22	arc	Official Aramaic (700-300 BCE); Imperial Aramaic (700-300 BCE)
23	arg	Aragonese
24	arm	Armenian
25	arn	Mapudungun; Mapuche
26	arp	Arapaho
27	art	Artificial (Other)
28	arw	Arawak
29	asm	Assamese
30	ast	Asturian; Bable; Leonese; Asturleonese
31	ath	Athapascan languages
32	aus	Australian languages
33	ava	Avaric
34	ave	Avestan
35	awa	Awadhi
36	aym	Aymara
37	aze	Azerbaijani
38	bad	Banda languages
39	bai	Bamileke languages
40	bak	Bashkir
41	bal	Baluchi
42	bam	Bambara
43	ban	Balinese
44	baq	Basque
45	bas	Basa
46	bat	Baltic (Other)
47	bej	Beja; Bedawiyet
48	bel	Belarusian
49	bem	Bemba
50	ben	Bengali
51	ber	Berber (Other)
52	bho	Bhojpuri
53	bih	Bihari
54	bik	Bikol
55	bin	Bini; Edo
56	bis	Bislama
57	bla	Siksika
58	bnt	Bantu (Other)
59	bos	Bosnian
60	bra	Braj
61	bre	Breton
62	btk	Batak languages
63	bua	Buriat
64	bug	Buginese
65	bul	Bulgarian
66	bur	Burmese
67	byn	Blin; Bilin
68	cad	Caddo
69	cai	Central American Indian (Other)
70	car	Galibi Carib
71	cat	Catalan; Valencian
72	cau	Caucasian (Other)
73	ceb	Cebuano
74	cel	Celtic (Other)
75	cha	Chamorro
76	chb	Chibcha
77	che	Chechen
78	chg	Chagatai
79	chi	Chinese
80	chk	Chuukese
81	chm	Mari
82	chn	Chinook jargon
83	cho	Choctaw
84	chp	Chipewyan; Dene Suline
85	chr	Cherokee
86	chu	Church Slavic; Old Slavonic; Church Slavonic; Old Bulgarian; Old Church Slavonic
87	chv	Chuvash
88	chy	Cheyenne
89	cmc	Chamic languages
90	cop	Coptic
91	cor	Cornish
92	cos	Corsican
93	cpe	Creoles and pidgins, English based (Other)
94	cpf	Creoles and pidgins, French-based (Other)
95	cpp	Creoles and pidgins, Portuguese-based (Other)
96	cre	Cree
97	crh	Crimean Tatar; Crimean Turkish
98	crp	Creoles and pidgins (Other)
99	csb	Kashubian
100	cus	Cushitic (Other)
101	cze	Czech
102	dak	Dakota
103	dan	Danish
104	dar	Dargwa
105	day	Land Dayak languages
106	del	Delaware
107	den	Slave (Athapascan)
108	dgr	Dogrib
109	din	Dinka
110	div	Divehi; Dhivehi; Maldivian
111	doi	Dogri
112	dra	Dravidian (Other)
113	dsb	Lower Sorbian
114	dua	Duala
115	dum	Dutch, Middle (ca.1050-1350)
116	dut	Dutch; Flemish
117	dyu	Dyula
118	dzo	Dzongkha
119	efi	Efik
120	egy	Egyptian (Ancient)
121	eka	Ekajuk
122	elx	Elamite
124	enm	English, Middle (1100-1500)
125	epo	Esperanto
126	est	Estonian
127	ewe	Ewe
128	ewo	Ewondo
129	fan	Fang
130	fao	Faroese
131	fat	Fanti
132	fij	Fijian
133	fil	Filipino; Pilipino
134	fin	Finnish
135	fiu	Finno-Ugrian (Other)
136	fon	Fon
137	fre	French
138	frm	French, Middle (ca.1400-1600)
139	fro	French, Old (842-ca.1400)
140	frr	Northern Frisian
141	frs	Eastern Frisian
142	fry	Western Frisian
143	ful	Fulah
144	fur	Friulian
145	gaa	Ga
146	gay	Gayo
147	gba	Gbaya
148	gem	Germanic (Other)
149	geo	Georgian
150	ger	German
151	gez	Geez
152	gil	Gilbertese
153	gla	Gaelic; Scottish Gaelic
154	gle	Irish
155	glg	Galician
156	glv	Manx
157	gmh	German, Middle High (ca.1050-1500)
158	goh	German, Old High (ca.750-1050)
159	gon	Gondi
160	gor	Gorontalo
161	got	Gothic
162	grb	Grebo
163	grc	Greek, Ancient (to 1453)
164	gre	Greek, Modern (1453-)
165	grn	Guarani
166	gsw	Swiss German; Alemannic; Alsatian
167	guj	Gujarati
168	gwi	Gwich'in
169	hai	Haida
170	hat	Haitian; Haitian Creole
171	hau	Hausa
172	haw	Hawaiian
173	heb	Hebrew
174	her	Herero
175	hil	Hiligaynon
176	him	Himachali
177	hin	Hindi
178	hit	Hittite
179	hmn	Hmong
180	hmo	Hiri Motu
181	hsb	Upper Sorbian
182	hun	Hungarian
183	hup	Hupa
184	iba	Iban
185	ibo	Igbo
186	ice	Icelandic
187	ido	Ido
188	iii	Sichuan Yi; Nuosu
189	ijo	Ijo languages
190	iku	Inuktitut
191	ile	Interlingue; Occidental
192	ilo	Iloko
193	ina	Interlingua (International Auxiliary Language Association)
194	inc	Indic (Other)
195	ind	Indonesian
196	ine	Indo-European (Other)
197	inh	Ingush
198	ipk	Inupiaq
199	ira	Iranian (Other)
200	iro	Iroquoian languages
201	ita	Italian
202	jav	Javanese
203	jbo	Lojban
204	jpn	Japanese
205	jpr	Judeo-Persian
206	jrb	Judeo-Arabic
207	kaa	Kara-Kalpak
208	kab	Kabyle
209	kac	Kachin; Jingpho
210	kal	Kalaallisut; Greenlandic
211	kam	Kamba
212	kan	Kannada
213	kar	Karen languages
214	kas	Kashmiri
215	kau	Kanuri
216	kaw	Kawi
217	kaz	Kazakh
218	kbd	Kabardian
219	kha	Khasi
220	khi	Khoisan (Other)
221	khm	Central Khmer
222	kho	Khotanese
223	kik	Kikuyu; Gikuyu
224	kin	Kinyarwanda
225	kir	Kirghiz; Kyrgyz
226	kmb	Kimbundu
227	kok	Konkani
228	kom	Komi
229	kon	Kongo
230	kor	Korean
231	kos	Kosraean
232	kpe	Kpelle
233	krc	Karachay-Balkar
234	krl	Karelian
235	kro	Kru languages
236	kru	Kurukh
237	kua	Kuanyama; Kwanyama
238	kum	Kumyk
239	kur	Kurdish
240	kut	Kutenai
241	lad	Ladino
242	lah	Lahnda
243	lam	Lamba
244	lao	Lao
245	lat	Latin
246	lav	Latvian
247	lez	Lezghian
248	lim	Limburgan; Limburger; Limburgish
249	lin	Lingala
250	lit	Lithuanian
251	lol	Mongo
252	loz	Lozi
253	ltz	Luxembourgish; Letzeburgesch
254	lua	Luba-Lulua
255	lub	Luba-Katanga
256	lug	Ganda
257	lui	Luiseno
258	lun	Lunda
259	luo	Luo (Kenya and Tanzania)
260	lus	Lushai
261	mac	Macedonian
262	mad	Madurese
263	mag	Magahi
264	mah	Marshallese
265	mai	Maithili
266	mak	Makasar
267	mal	Malayalam
268	man	Mandingo
269	mao	Maori
270	map	Austronesian (Other)
271	mar	Marathi
272	mas	Masai
273	may	Malay
274	mdf	Moksha
275	mdr	Mandar
276	men	Mende
277	mga	Irish, Middle (900-1200)
278	mic	Mi'kmaq; Micmac
279	min	Minangkabau
280	mis	Uncoded languages
281	mkh	Mon-Khmer (Other)
282	mlg	Malagasy
283	mlt	Maltese
284	mnc	Manchu
285	mni	Manipuri
286	mno	Manobo languages
287	moh	Mohawk
288	mol	Moldavian
289	mon	Mongolian
290	mos	Mossi
291	mul	Multiple languages
292	mun	Munda languages
293	mus	Creek
294	mwl	Mirandese
295	mwr	Marwari
296	myn	Mayan languages
297	myv	Erzya
298	nah	Nahuatl languages
299	nai	North American Indian
300	nap	Neapolitan
301	nau	Nauru
302	nav	Navajo; Navaho
303	nbl	Ndebele, South; South Ndebele
304	nde	Ndebele, North; North Ndebele
305	ndo	Ndonga
306	nds	Low German; Low Saxon; German, Low; Saxon, Low
307	nep	Nepali
308	new	Nepal Bhasa; Newari
309	nia	Nias
310	nic	Niger-Kordofanian (Other)
311	niu	Niuean
312	nno	Norwegian Nynorsk; Nynorsk, Norwegian
313	nob	Bokmål, Norwegian; Norwegian Bokmål
314	nog	Nogai
315	non	Norse, Old
316	nor	Norwegian
317	nqo	N'Ko
318	nso	Pedi; Sepedi; Northern Sotho
319	nub	Nubian languages
320	nwc	Classical Newari; Old Newari; Classical Nepal Bhasa
321	nya	Chichewa; Chewa; Nyanja
322	nym	Nyamwezi
323	nyn	Nyankole
324	nyo	Nyoro
325	nzi	Nzima
326	oci	Occitan (post 1500); Provençal
327	oji	Ojibwa
328	ori	Oriya
329	orm	Oromo
330	osa	Osage
331	oss	Ossetian; Ossetic
332	ota	Turkish, Ottoman (1500-1928)
333	oto	Otomian languages
334	paa	Papuan (Other)
335	pag	Pangasinan
336	pal	Pahlavi
337	pam	Pampanga; Kapampangan
338	pan	Panjabi; Punjabi
339	pap	Papiamento
340	pau	Palauan
341	peo	Persian, Old (ca.600-400 B.C.)
342	per	Persian
343	phi	Philippine (Other)
344	phn	Phoenician
345	pli	Pali
346	pol	Polish
347	pon	Pohnpeian
348	por	Portuguese
349	pra	Prakrit languages
350	pro	Provençal, Old (to 1500)
351	pus	Pushto; Pashto
353	que	Quechua
354	raj	Rajasthani
355	rap	Rapanui
356	rar	Rarotongan; Cook Islands Maori
357	roa	Romance (Other)
358	roh	Romansh
359	rom	Romany
360	rum	Romanian
361	run	Rundi
362	rup	Aromanian; Arumanian; Macedo-Romanian
363	rus	Russian
364	sad	Sandawe
365	sag	Sango
366	sah	Yakut
367	sai	South American Indian (Other)
368	sal	Salishan languages
369	sam	Samaritan Aramaic
370	san	Sanskrit
371	sas	Sasak
372	sat	Santali
373	scc	Serbian
374	scn	Sicilian
375	sco	Scots
376	scr	Croatian
377	sel	Selkup
378	sem	Semitic (Other)
379	sga	Irish, Old (to 900)
380	sgn	Sign Languages
381	shn	Shan
382	sid	Sidamo
383	sin	Sinhala; Sinhalese
384	sio	Siouan languages
385	sit	Sino-Tibetan (Other)
386	sla	Slavic (Other)
387	slo	Slovak
388	slv	Slovenian
389	sma	Southern Sami
390	sme	Northern Sami
391	smi	Sami languages (Other)
392	smj	Lule Sami
393	smn	Inari Sami
394	smo	Samoan
395	sms	Skolt Sami
396	sna	Shona
397	snd	Sindhi
398	snk	Soninke
399	sog	Sogdian
400	som	Somali
401	son	Songhai languages
402	sot	Sotho, Southern
403	spa	Spanish; Castilian
404	srd	Sardinian
405	srn	Sranan Tongo
406	srr	Serer
407	ssa	Nilo-Saharan (Other)
408	ssw	Swati
409	suk	Sukuma
410	sun	Sundanese
411	sus	Susu
412	sux	Sumerian
413	swa	Swahili
414	swe	Swedish
415	syc	Classical Syriac
416	syr	Syriac
417	tah	Tahitian
418	tai	Tai (Other)
419	tam	Tamil
420	tat	Tatar
421	tel	Telugu
422	tem	Timne
423	ter	Tereno
424	tet	Tetum
425	tgk	Tajik
426	tgl	Tagalog
427	tha	Thai
428	tib	Tibetan
429	tig	Tigre
430	tir	Tigrinya
431	tiv	Tiv
432	tkl	Tokelau
433	tlh	Klingon; tlhIngan-Hol
434	tli	Tlingit
435	tmh	Tamashek
436	tog	Tonga (Nyasa)
437	ton	Tonga (Tonga Islands)
438	tpi	Tok Pisin
439	tsi	Tsimshian
440	tsn	Tswana
441	tso	Tsonga
442	tuk	Turkmen
443	tum	Tumbuka
444	tup	Tupi languages
445	tur	Turkish
446	tut	Altaic (Other)
447	tvl	Tuvalu
448	twi	Twi
449	tyv	Tuvinian
450	udm	Udmurt
451	uga	Ugaritic
452	uig	Uighur; Uyghur
453	ukr	Ukrainian
454	umb	Umbundu
455	und	Undetermined
456	urd	Urdu
457	uzb	Uzbek
458	vai	Vai
459	ven	Venda
460	vie	Vietnamese
461	vol	Volapük
462	vot	Votic
463	wak	Wakashan languages
464	wal	Walamo
465	war	Waray
466	was	Washo
467	wel	Welsh
468	wen	Sorbian languages
469	wln	Walloon
470	wol	Wolof
471	xal	Kalmyk; Oirat
472	xho	Xhosa
473	yao	Yao
474	yap	Yapese
475	yid	Yiddish
476	yor	Yoruba
477	ypk	Yupik languages
478	zap	Zapotec
479	zbl	Blissymbols; Blissymbolics; Bliss
480	zen	Zenaga
481	zha	Zhuang; Chuang
482	znd	Zande languages
483	zul	Zulu
484	zun	Zuni
485	zxx	No linguistic content
486	zza	Zaza; Dimili; Dimli; Kirdki; Kirmanjki; Zazaki
\.


--
-- Data for Name: kwmisc; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwmisc (id, kw, descr) FROM stdin;
1	X	rude or X-rated term (not displayed in educational software)
2	abbr	abbreviation
3	arch	archaism
4	chn	children's language
5	col	colloquialism
6	derog	derogatory
7	eK	exclusively kanji
8	fam	familiar language
9	fem	female term, language, or name
11	hon	honorific or respectful (sonkeigo) language
12	hum	humble (kenjougo) language
13	id	idiomatic expression
14	m-sl	manga slang
15	male	male term, language, or name
17	obs	obsolete term
18	obsc	obscure term
19	pol	polite (teineigo) language
20	rare	rare
21	sl	slang
22	uk	word usually written using kana alone
24	vulg	vulgar expression or word
25	sens	sensitive
26	poet	poetical term
27	on-mim	onomatopoeic or mimetic word
28	joc	jocular, humorous term
81	proverb	proverb
82	aphorism	aphorism (pithy saying)
83	quote	quotation
84	yoji	yojijukugo
181	surname	family or surname
182	place	place name
183	unclass	unclassified name
184	company	company name
185	product	product name
188	person	full name of a particular person
189	given	given name or forename, gender not specified
190	station	railway station
191	organization	organization name
192	work	work of art, literature, music, etc. name
\.


--
-- Data for Name: kwpos; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwpos (id, kw, descr) FROM stdin;
1	adj-i	adjective (keiyoushi)
2	adj-na	adjectival nouns or quasi-adjectives (keiyodoshi)
3	adj-no	nouns which may take the genitive case particle `no'
4	adj-pn	pre-noun adjectival (rentaishi)
5	adj-t	`taru' adjective
6	adv	adverb (fukushi)
7	adj-ix	adjective (keiyoushi) - yoi/ii class
8	adv-to	adverb taking the `to' particle
9	aux	auxiliary
10	aux-adj	auxiliary adjective
11	aux-v	auxiliary verb
12	conj	conjunction
13	exp	Expressions (phrases, clauses, etc.)
14	int	interjection (kandoushi)
15	cop-da	copula
17	n	noun (common) (futsuumeishi)
18	n-adv	adverbial noun (fukushitekimeishi)
19	n-suf	noun, used as a suffix
20	n-pref	noun, used as a prefix
21	n-t	noun (temporal) (jisoumeishi)
24	num	numeric
25	pref	prefix
26	prt	particle
27	suf	suffix
28	v1	Ichidan verb
29	v1-s	Ichidan verb - kureru special class
30	v5aru	Godan verb - -aru special class
31	v5b	Godan verb with `bu' ending
32	v5g	Godan verb with `gu' ending
33	v5k	Godan verb with `ku' ending
34	v5k-s	Godan verb - Iku/Yuku special class
35	v5m	Godan verb with `mu' ending
36	v5n	Godan verb with `nu' ending
37	v5r	Godan verb with `ru' ending
38	v5r-i	Godan verb with `ru' ending (irregular verb)
39	v5s	Godan verb with `su' ending
40	v5t	Godan verb with `tsu' ending
41	v5u	Godan verb with `u' ending
42	v5u-s	Godan verb with `u' ending (special class)
43	v5uru	Godan verb - Uru old class verb (old form of Eru)
44	vi	intransitive verb
45	vk	Kuru verb - special class
46	vs	noun or participle which takes the aux. verb suru
47	vs-s	suru verb - special class
48	vs-i	suru verb - irregular
49	vz	Ichidan verb - zuru verb (alternative form of -jiru verbs)
50	vt	transitive verb
51	ctr	counter
52	vn	irregular nu verb
53	v4r	Yodan verb with `ru' ending (archaic)
56	adj-f	noun or verb acting prenominally
58	vr	irregular ru verb, plain form ends with -ri
59	v2a-s	Nidan verb with 'u' ending (archaic)
60	v4h	Yodan verb with `hu/fu' ending (archaic)
61	pn	pronoun
62	vs-c	su verb - precursor to the modern suru
63	adj-kari	`kari' adjective (archaic)
64	adj-ku	`ku' adjective (archaic)
65	adj-shiku	`shiku' adjective (archaic)
66	adj-nari	archaic/formal form of na-adjective
67	n-pr	proper noun
68	v-unspec	verb unspecified
69	v4k	Yodan verb with `ku' ending (archaic)
70	v4g	Yodan verb with `gu' ending (archaic)
71	v4s	Yodan verb with `su' ending (archaic)
72	v4t	Yodan verb with `tsu' ending (archaic)
73	v4n	Yodan verb with `nu' ending (archaic)
74	v4b	Yodan verb with `bu' ending (archaic)
75	v4m	Yodan verb with `mu' ending (archaic)
76	v2k-k	Nidan verb (upper class) with `ku' ending (archaic)
77	v2g-k	Nidan verb (upper class) with `gu' ending (archaic)
78	v2t-k	Nidan verb (upper class) with `tsu' ending (archaic)
79	v2d-k	Nidan verb (upper class) with `dzu' ending (archaic)
80	v2h-k	Nidan verb (upper class) with `hu/fu' ending (archaic)
81	v2b-k	Nidan verb (upper class) with `bu' ending (archaic)
82	v2m-k	Nidan verb (upper class) with `mu' ending (archaic)
83	v2y-k	Nidan verb (upper class) with `yu' ending (archaic)
84	v2r-k	Nidan verb (upper class) with `ru' ending (archaic)
85	v2k-s	Nidan verb (lower class) with `ku' ending (archaic)
86	v2g-s	Nidan verb (lower class) with `gu' ending (archaic)
87	v2s-s	Nidan verb (lower class) with `su' ending (archaic)
88	v2z-s	Nidan verb (lower class) with `zu' ending (archaic)
89	v2t-s	Nidan verb (lower class) with `tsu' ending (archaic)
90	v2d-s	Nidan verb (lower class) with `dzu' ending (archaic)
91	v2n-s	Nidan verb (lower class) with `nu' ending (archaic)
92	v2h-s	Nidan verb (lower class) with `hu/fu' ending (archaic)
93	v2b-s	Nidan verb (lower class) with `bu' ending (archaic)
94	v2m-s	Nidan verb (lower class) with `mu' ending (archaic)
95	v2y-s	Nidan verb (lower class) with `yu' ending (archaic)
96	v2r-s	Nidan verb (lower class) with `ru' ending (archaic)
97	v2w-s	Nidan verb (lower class) with `u' ending and `we' conjugation (archaic)
98	unc	unclassified
\.


--
-- Data for Name: kwrinf; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwrinf (id, kw, descr) FROM stdin;
1	gikun	gikun (meaning as reading) or jukujikun (special kanji reading)
2	ok	out-dated or obsolete kana usage
3	ik	word containing irregular kana usage
4	uK	word usually written using kanji alone
21	oik	old or irregular kana form
103	name	reading used only in names (nanori)
104	rad	reading used as name of radical
105	jouyou	approved reading for jouyou kanji
106	kun	kun-yomi
128	on	on-yomi
129	kan	on-yomi, kan
130	go	on-yomi, go
131	tou	on-yomi, tou
132	kanyou	on-yomi, kan\\'you
\.


--
-- Data for Name: kwsrc; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwsrc (id, kw, descr, dt, notes, seq, sinc, smin, smax, srct) FROM stdin;
99	test	Corpus for testing and experimentation	\N	\N	seq_test	\N	\N	\N	1
1	jmdict	\N	\N	\N	seq_jmdict	10	1000000	8999999	1
2	jmnedict	\N	\N	\N	seq_jmnedict	10	1000000	8999999	2
\.


--
-- Data for Name: kwsrct; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwsrct (id, kw, descr) FROM stdin;
1	jmdict	Words dictionary (http://www.edrdg.org/jmdict/edict_doc.html)
2	jmnedict	Names dictionary (http://www.csse.monash.edu.au/~jwb/enamdict_doc.html)
3	examples	Example sentences (http://www.edrdg.org/wiki/index.php/Tanaka_Corpus)
4	kanjidic	Kanji dictionary (http://www.csse.monash.edu.au/~jwb/kanjidic.html)
\.


--
-- Data for Name: kwstat; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwstat (id, kw, descr) FROM stdin;
2	A	Active
4	D	Deleted
6	R	Rejected
\.


--
-- Data for Name: kwxref; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.kwxref (id, kw, descr) FROM stdin;
1	syn	Synonym
2	ant	Antonym
3	see	See also
4	cf	cf.
5	ex	Usage example
6	uses	Uses
7	pref	Preferred
8	kvar	Kanji variant
9	vtvi	Transitive-intransitive verb pair
\.


--
-- Data for Name: lsrc; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.lsrc (entr, sens, ord, lang, txt, part, wasei) FROM stdin;
13	1	1	116	ontembaar	f	f
19	1	1	1	ice	f	f
19	1	2	150	Eis	f	f
21	2	1	1	after care	f	t
22	1	1	1	after service	f	t
23	1	1	150	Arbeit	f	f
27	1	1	150	Typhus	f	f
27	1	2	116		f	f
30	1	1	150	Arbeit	f	f
32	1	1	1	batting center	f	t
33	1	1	363	pirozhki	f	f
34	1	1	1		f	f
34	1	2	116		f	f
37	1	1	116	kan	f	f
37	1	2	1	can	f	f
54	1	1	348	Cambodia abóbora	f	f
61	1	1	403	medias	t	f
61	1	2	348	meias	t	f
61	1	3	1	shirt	t	f
\.


--
-- Data for Name: misc; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.misc (entr, sens, ord, kw) FROM stdin;
3	1	1	22
4	1	1	22
4	2	1	2
5	1	1	22
6	1	1	9
7	1	1	22
7	3	1	3
7	4	1	5
7	5	1	5
7	6	1	22
7	7	1	22
8	1	1	22
8	2	1	22
8	3	1	22
9	1	1	11
11	1	1	11
11	2	1	11
12	1	1	22
12	2	1	22
13	1	1	22
14	1	1	27
15	1	1	27
15	2	1	27
16	1	1	22
17	1	1	22
18	1	1	22
18	2	1	22
19	2	1	2
27	1	1	22
30	1	1	2
35	2	1	22
36	1	1	22
37	2	1	2
39	1	1	22
40	1	1	22
47	3	1	21
48	2	1	22
48	3	1	13
49	2	1	11
53	5	1	5
54	1	1	22
55	1	1	22
57	2	1	3
63	1	1	22
68	1	1	22
70	1	1	22
73	1	1	22
73	2	1	22
75	1	1	8
75	1	2	22
75	2	1	22
77	1	1	22
115	1	1	181
\.


--
-- Data for Name: pos; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.pos (entr, sens, ord, kw) FROM stdin;
1	1	1	17
1	2	1	17
1	3	1	17
1	4	1	17
1	5	1	17
2	1	1	17
3	1	1	4
4	1	1	17
4	2	1	17
5	1	1	17
6	1	1	14
7	1	1	17
7	2	1	17
7	3	1	17
7	4	1	17
7	5	1	17
7	6	1	14
7	7	1	17
8	1	1	13
8	2	1	13
8	3	1	13
9	1	1	14
9	2	1	14
10	1	1	13
11	1	1	30
11	1	2	44
11	2	1	30
11	2	2	11
12	1	1	17
12	2	1	17
13	1	1	2
13	1	2	17
14	1	1	6
14	1	2	8
15	1	1	6
15	1	2	8
15	1	3	46
15	2	1	6
15	2	2	8
15	2	3	46
16	1	1	17
17	1	1	4
17	2	1	14
18	1	1	17
18	1	2	27
18	2	1	17
18	2	2	27
18	3	1	17
18	3	2	27
19	1	1	17
19	2	1	17
20	1	1	17
21	1	1	17
21	2	1	17
22	1	1	17
23	1	1	17
23	1	2	46
23	2	1	17
23	3	1	17
24	1	1	17
25	1	1	17
26	1	1	17
27	1	1	17
28	1	1	17
29	1	1	17
30	1	1	17
30	1	2	46
30	2	1	17
30	3	1	17
30	4	1	17
31	1	1	17
32	1	1	17
33	1	1	17
34	1	1	17
34	2	1	17
34	3	1	17
35	1	1	41
35	1	2	44
35	2	1	41
35	2	2	44
36	1	1	17
37	1	1	17
37	2	1	17
38	1	1	17
38	1	2	3
38	2	1	17
38	3	1	17
39	1	1	17
40	1	1	17
41	1	1	17
42	1	1	17
42	2	1	17
43	1	1	17
43	1	2	46
44	1	1	17
45	1	1	17
45	2	1	17
46	1	1	17
46	2	1	17
46	3	1	17
46	4	1	17
47	1	1	17
47	2	1	17
47	3	1	17
47	4	1	17
47	5	1	17
48	1	1	17
48	2	1	17
48	3	1	17
49	1	1	17
49	2	1	17
49	3	1	17
49	3	2	19
49	4	1	19
49	5	1	19
49	6	1	19
50	1	1	17
51	1	1	17
51	1	2	46
51	2	1	17
51	2	2	46
51	3	1	17
51	3	2	46
52	1	1	18
52	1	2	21
52	2	1	18
52	2	2	21
53	1	1	17
53	1	2	46
53	2	1	17
53	2	2	46
53	3	1	17
53	3	2	46
53	4	1	17
53	5	1	17
53	6	1	17
54	1	1	17
55	1	1	4
56	1	1	17
56	1	2	46
56	2	1	17
56	2	2	46
57	1	1	17
57	1	2	46
57	2	1	17
58	1	1	17
58	2	1	17
58	3	1	17
58	4	1	17
58	5	1	17
59	1	1	17
60	1	1	17
61	1	1	17
62	1	1	17
63	1	1	4
64	1	1	56
65	1	1	17
66	1	1	17
67	1	1	17
68	1	1	17
69	1	1	17
70	1	1	17
71	1	1	17
72	1	1	17
73	1	1	17
73	2	1	17
74	1	1	17
74	1	2	46
75	1	1	17
75	2	1	17
76	1	1	17
77	1	1	17
78	1	1	17
104	1	1	17
105	1	1	17
106	1	1	17
107	1	1	17
109	1	1	17
116	1	1	17
120	1	1	17
121	1	1	17
\.


--
-- Data for Name: rad; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.rad (num, var, rchr, chr, strokes, loc, name, examples) FROM stdin;
1	1	⼀	一	1	O	いち	丁七万丈三
2	1	⼁	丨	1	O	ぼう	中丰串
3	1	⼂	丶	1	O	てん	丸丹主丼
4	1	⼃	丿	1	O	の	乂乃
4	2	\N	\N	1	T	の	久乍乎
5	1	⼄	乙	1	O	おつ	乞乾
5	2	⺃	乚	1	V	れ	乳
6	1	⼅	亅	1	O	はねぼう	了予
7	1	⼆	二	2	O	に	于五井些
8	1	⼇	亠	2	O	なべぶた	交亥京亮
9	1	⼈	人	2	O	ひと	从
9	2	⺅	亻	2	L	にんへん	仁仕他仙休
9	3	\N	𠆢	2	T	ひとやね	今介令会
10	1	⼉	儿	2	O	にんにょう、ひとあし	兄兆先光兒
11	1	⼊	入	2	O	いる	\N
12	1	⼋	八	2	O	はちがしら	公共兵具典
12	2	\N	ハ	2	V	はち	\N
12	3	\N	丷	2	T	はちがしら	\N
13	1	⼌	冂	2	O	まきがまえ	冉冊再冎冏
14	1	⼍	冖	2	O	わかんむり	冗冠冢冤冥
15	1	⼎	冫	2	O	にすい	冬冰冶冷凍
16	1	⼏	几	2	O	つくえ	凡凭凱凳
16	2	⺇	\N	\N	E	かざがまえ	凰
17	1	⼐	凵	2	O	かんにょう、うけばこ	凶凸凹出函
18	1	⼑	刀	2	O	かたな	刃分切初券
18	2	⺉	刂	2	R	りっとう	刈刊刑列判
19	1	⼒	力	2	O	ちから	功劣助努励
20	1	⼓	勹	2	O	つつみがまえ	勺勻勾包匈
21	1	⼔	匕	2	O	さじのひ	北北匙
22	1	⼕	匚	2	O	はこがまえ	匠匡匣匪匱
23	1	⼖	匸	2	O	かくしがまえ	匹医匼匿區
24	1	⼗	十	2	O	じゅう	千午南
24	2	\N	\N	2	L	じゅうへん	協博
25	1	⼘	卜	2	O	ぼくのと	卞卦
25	2	⺊	\N	2	\N	ぼくのと	占卡卣
26	1	⼙	卩	2	O	ふしづくり	卯印即却
26	2	⺋	\N	2	V	ふしづくり	危
27	1	⼚	厂	2	O	がんだれ	厄厖厘厚原
28	1	⼛	厶	2	O	む	厷去厽叀參
29	1	⼜	又	2	O	また	叉友双取受
30	1	⼝	口	3	O	くち	史名君吟味
31	1	⼞	囗	3	O	くにがまえ	囚因困國園
32	1	⼟	土	3	O	つち	報在堂圭尭
32	2	\N	\N	3	L	つちへん	地均坊城域
33	1	⼠	士	3	O	さむらい	壬壯壺壻壽
34	1	⼡	夂	3	O	ふゆがしら	夅夆処粂
34	2	\N	\N	3	B	なつあし	変
35	1	⼢	夊	3	O	すいにょう、ふゆがしら	夋复夎夏夔
36	1	⼣	夕	3	O	た、ゆうべ	外夘多夜夢
37	1	⼤	大	3	O	だい、おおきい	天太夫契奔
38	1	⼥	女	3	O	おんな	妻
38	2	\N	\N	3	L	おんなへん	好妊妹姓
39	1	⼦	子	3	O	こ	字孝孟
39	2	\N	\N	3	L	こへん	孔孫
40	1	⼧	宀	3	O	うかんむり	宅宇宗官定
41	1	⼨	寸	3	O	すん	寺尋
41	2	\N	\N	3	R	すんづくり	封射對
42	1	⼩	小	3	O	ちいさい、しょう	少尖尗尠
42	2	⺌	\N	3	T	なおがしら	当尚
42	3	⺍	\N	3	T	つ	営
43	1	⼪	尢	3	O	(だいの)まげあし	尣尤尨尬就
44	1	⼫	尸	3	O	かばね、しかばね	尺尻尾局屈
45	1	⼬	屮	3	O	てつ	屯屰
46	1	⼭	山	3	O	やま	岳島岡
46	2	\N	\N	3	L	やまへん	屹岐峰
46	3	\N	\N	3	T	やまかんむり	岸崩岩嵐
47	1	⼮	巛	3	O	まがりがわ	巡巢
47	2	\N	川	3	V	さんぼんがわ	順
48	1	⼯	工	3	O	たくみ	左巨巫差
48	2	\N	\N	3	L	たくみへん	巧巩
49	1	⼰	己	3	O	おのれ	改巻
49	2	\N	巳	3	V	み	巴巵巷巸巽
50	1	⼱	巾	3	O	はば	市布帆帝帥
51	1	⼲	干	3	O	ほす	平幵幷幹
52	1	⼳	幺	3	O	いとがしら	幻幼幽幾
53	1	⼴	广	3	O	まだれ	床底店府度
54	1	⼵	廴	3	O	えんにょう、いんにゅう	延廷建廻
55	1	⼶	廾	3	O	にじゅうあし	弁异弃弄弊
56	1	⼷	弋	3	O	しきがまえ	弌弍弎式弑
57	1	⼸	弓	3	O	ゆみ	弟
57	2	\N	\N	3	L	ゆみへん	引弦弱張
58	1	⼹	彐	3	O	けいがしら、いのかしら	\N
58	2	⺕	\N	3	V	けいがしら	\N
58	3	⺔	彑	4	V	けいがしら	彔彖彘彙彝
59	1	⼺	彡	3	O	さんづくり	形彥彩彬彭
60	1	⼻	彳	3	O	ぎょうにんべん	役往待律徐
61	1	⼼	心	4	O	こころ	必志忘忠
61	2	⺖	忄	3	L	りっしんべん	忙快怖怪悟
61	3	\N	\N	\N	B	したごころ	恭
62	1	⼽	戈	4	O	かのほこ	戊戎成我戒
63	1	\N	戶	4	O	とびらのと	\N
63	2	⼾	戸	4	E	とびらのと	房所扁扇扉
64	1	⼿	手	4	O	て	拜拳掌掣擧
64	2	⺘	扌	3	L	てへん	打批技抱押
65	1	⽀	支	4	R	しんよう、じゅうまた	攱攲攳
66	1	⽁	攴	4	O	ぼくづくり、とまた	敲
66	2	⺙	攵	3	R	のぶん	改放政故
67	1	⽂	文	4	V	ぶん、ぶんにょう	斈斌斐斑斕
68	1	⽃	斗	4	O	とます	料斛斜斟斡
69	1	⽄	斤	4	O	おの	斥斧斬新斷
70	1	⽅	方	4	O	かた	於施旁旅族
71	1	⽆	无	4	O	むにょう	\N
71	2	⺛	旡	4	R	すでのつくり	既旤
72	1	⽇	日	4	V	ひ	旦旱明星春
73	1	⽈	曰	4	V	ひらび	晉曷書曹曾
74	1	⽉	月	4	V	つき	朏朖期朦朧
75	1	⽊	木	4	O	き	末本森
75	2	\N	\N	4	L	きへん	杉林
76	1	⽋	欠	4	O	あくび	次欣欲歌歡
77	1	⽌	止	4	O	とめる	步武歪歲
77	2	\N	\N	4	L	とめへん	此
78	1	⽍	歹	4	O	がつへん	死殉殊殘殲
78	2	⺞	歺	4	\N	\N	\N
79	1	⽎	殳	4	O	るまた、ほこづくり	段殷殺殿毀
80	1	⽏	毋	4	O	はは、なかれ	毐毒
80	2	\N	毌	4	V	はは、なかれ	\N
80	3	\N	母	5	O	はは、なかれ	每毑毓
81	1	⽐	比	4	O	くらべる、ひ	毕毖毘毚
82	1	⽑	毛	4	O	け	毫毬毯毳氈
83	1	⽒	氏	4	O	うじ	氐民氒氓
84	1	⽓	气	4	O	きがまえ	氛氜氣氤氳
85	1	⽔	水	4	O	みず	汞泉淼漿潁
85	2	⺡	氵	3	L	さんずい	河泣洋海湖
85	3	⺢	氺	5	B	したみず	求泰滕
86	1	⽕	火	4	O	ひ	炎炙
86	2	\N	\N	4	L	ひへん	灼炊炒
86	3	⺣	灬	4	B	れっか	黒烈烹焦然煮
87	1	⽖	爪	4	O	つめ	爬
87	2	⺤	爫	4	T	のつ	爯
87	3	⺥	\N	4	T	つめかんむり	爭爰爲
88	1	⽗	父	4	O	ちち	爸爹爺
89	1	⽘	爻	4	O	めめ	爼爾
90	1	⽙	爿	4	O	しょうへん	牀牁牂牃牆
90	2	⺦	丬	3	\N	\N	\N
91	1	⽚	片	4	O	かた	版牋牌牒牘
92	1	⽛	牙	4	O	きば	牚
93	1	⽜	牛	4	O	うし	犀
93	2	\N	牜	4	L	うしへん	牧物牲特
94	1	⽝	犬	4	O	いぬ	狀猋猒獸獻
94	2	⺨	犭	3	L	けものへん	犯狂狗狩狼
95	1	⽞	玄	5	O	げん	玅玆率玈
96	1	⽟	玉	5	O	たま	瑩瑬瑿璧璽
96	2	⺩	⺩	4	L	たまへん	珍珠現球理
97	1	⽠	瓜	5	O	うり	瓝瓞瓠瓢瓣
98	1	⽡	瓦	5	O	かわら	瓮瓷甄甑甕
99	1	⽢	甘	5	O	あまい	甙甚甜甝甞
100	1	⽣	生	5	O	うまれる	甡產甥甦甧
101	1	⽤	用	5	O	もちいる	甩甫甬甭甯
102	1	⽥	田	5	O	た	男界留畦番
103	1	⽦	疋	5	O	ひきへん	疌疐疑
103	2	⺪	\N	\N	L	ひき	疎疏
104	1	⽧	疒	5	O	やまいだれ	疼疾病痛痴
105	1	⽨	癶	5	O	はつがしら	癷癸癹登發
106	1	⽩	白	5	O	しろ	的皆皇皎皓
107	1	⽪	皮	5	O	けがわ	皰皴皸皺皻
108	1	⽫	皿	5	O	さら	盂盆盒盛盟
109	1	⽬	目	5	O	め	盲看眺眼睛
110	1	⽭	矛	5	O	ほこ	矜矝矞矠矡
111	1	⽮	矢	5	O	や	矣
111	2	\N	\N	5	L	やへん	知矩短矮
112	1	⽯	石	5	O	いし	磨碁磐磊砦
112	2	\N	\N	5	L	いしへん	砂砥砲硬磁
113	1	⽰	示	5	O	しめす	祟票祭禁禦
113	2	⺭	礻	4	L	ねへん、しめすへん	礼社祈祝神
113	3	⺬	\N	5	L	しめすへん	禮禳祛禛祚
114	1	⽱	禸	5	O	ぐうのあし	禹禺离禼禽
115	1	⽲	禾	5	O	のぎ	秦秂秊穌穎
115	2	\N	\N	5	O	のぎへん	秋税稔稻稼
116	1	⽳	穴	5	O	あな	\N
116	2	\N	\N	5	T	あなかんむり	究空穿突窃
117	1	⽴	立	5	O	たつ	章童
117	2	\N	\N	5	T	たつへん	站竝竣
118	1	⽵	竹	6	O	たけ	\N
118	2	⺮	\N	6	T	たけかんむり	竿笏箒算箱
119	1	⽶	米	6	O	こめ	粟
119	2	\N	\N	6	L	こめへん	粒粗精糊
120	1	⽷	糸	6	O	いと	系紊素索紫
120	2	\N	\N	6	L	いおへん	紅納紙細組
120	3	⺯	糹	\N	\N	\N	\N
120	4	⺰	纟	\N	\N	\N	\N
121	1	⽸	缶	6	O	ほとぎ	缸缺罅罎罐
122	1	⽹	网	6	O	あみがしら	羀
122	2	⺫	罒	5	T	よんかしら	罠罪置罰署
122	3	⺳	\N	4	T	よんかしら	罕
123	1	⽺	羊	6	O	ひつじ	群
123	2	⺷	\N	6	T	ひつじかんむり	着美義
123	3	⺶	\N	6	L	ひつじへん	羯
124	1	⽻	羽	6	O	はね	\N
124	2	\N	\N	6	V	はね	翁翌習翔翼
125	1	⽼	老	6	O	おい	耄耆耋
125	2	⺹	耂	4	T	おいかんむり、おいがしら	考者耇
126	1	⽽	而	6	O	しかして	耍耎耏耐耑
127	1	⽾	耒	6	O	らいすき	\N
127	2	\N	\N	6	L	らいへん	耕耗
127	3	\N	\N	6	L	すきへん	耘耙耡
128	1	⽿	耳	6	O	みみ	聲聽
128	2	\N	\N	6	L	みみへん	耽聘聰
129	1	⾀	聿	6	O	ふでづくり	肂肄肅肆肇
130	1	⾁	肉	6	O	にく	胔胾腐臠臡
130	2	\N	⺼	4	V	にくずき	肌肝肥育
130	3	⺼	\N	4	V	つき	\N
131	1	⾂	臣	6	L	しん	臤臥臦臧臨
132	1	⾃	自	6	O	みずから	臫臬臭臮臱
133	1	⾄	至	6	O	いたる	致臸臹臺臻
134	1	⾅	臼	6	O	うす	臾舁舂與興
135	1	⾆	舌	6	O	した	舍
135	2	\N	\N	6	L	したへん	舐舒舔舕
136	1	⾇	舛	6	O	まい	\N
136	2	\N	\N	6	B	まいあし	舜舞
137	1	⾈	舟	6	O	ふね	\N
137	2	\N	\N	6	L	ふねへん	航舫般船艘
138	1	⾉	艮	6	O	ねづくり、うしとら	艱
139	1	⾊	色	6	O	いろ	\N
139	2	\N	\N	6	R	いろづくり	艴艵艷
140	1	⾋	艸	6	O	くさ	芔芻茻
140	2	⺾	艹	3	T	くさかんむり、そうこう	花茶草菓華
140	3	⺿	\N	4	T	くさかんむり、そうこう	菥薘藟
141	1	⾌	虍	6	O	とらかんむり	虎虐處虞號
142	1	⾍	虫	6	O	むし	蜜蟲
142	2	\N	\N	6	L	むしへん	蛇蛙蝶
143	1	⾎	血	6	O	ち	衆
143	2	\N	\N	6	L	ちへん	衄衅衉衊
144	1	⾏	行	6	O	ぎょう	\N
144	2	\N	\N	\N	E	ぎょうがまえ	衒術街衝衞
145	1	⾐	衣	6	O	ころも	表袋裔裝
145	2	⻂	衤	5	L	ころもへん	袂袖裸裾襟
145	3	\N	\N	\N	V	ころも	衰
146	1	⾑	襾	6	O	にし	覃覈
146	2	⻃	覀	6	T	にし	覆覇覉
146	3	⻄	西	6	O	にし	\N
147	1	⾒	見	7	O	みる	規視覚覍覕
147	2	⻅	见	4	\N	\N	\N
148	1	⾓	角	7	O	つの	觜
148	2	\N	\N	7	L	つのへん	觝解觴觸
149	1	⾔	言	7	O	ことば	詈誓謦警譬
149	2	\N	訁	7	L	ごんべん	訓記設詩話
149	3	⻈	讠	\N	\N	\N	\N
150	1	⾕	谷	7	O	たに	谿豁
150	2	\N	\N	7	L	たにへん	谺谻谽
151	1	⾖	豆	7	O	まめ	豈豎豐
151	2	\N	\N	7	L	まめへん	豉豌
152	1	⾗	豕	7	O	いのこ	豚象豢豪
152	2	\N	\N	7	L	いのこへん	豬
153	1	⾘	豸	7	O	むじな	豹豺貂貌貎
154	1	⾙	貝	7	O	かい	負貧貨
154	2	\N	\N	7	V	かいへん	財販
154	3	⻉	贝	4	\N	\N	\N
155	1	⾚	赤	7	O	あか	\N
155	2	\N	\N	7	L	あかへん	赦赧赫赬赭
156	1	⾛	走	7	O	はしる	\N
156	2	\N	\N	7	E	そうにょう	赴起超越趨
157	1	⾜	足	7	O	あし	\N
157	2	⻊	\N	7	L	あしへん	距跨跪路跳
158	1	⾝	身	7	O	み	\N
158	2	\N	\N	7	L	みへん	躬躱躴躺軀
159	1	⾞	車	7	O	かるま	軍
159	2	\N	\N	7	L	かるまへん	軌軒輕輸
159	3	⻋	车	\N	\N	\N	\N
160	1	⾟	辛	7	O	からい	辜辟辭
160	2	\N	\N	\N	L	からい	辡辣
161	1	⾠	辰	7	O	しんのたつ	辱農辴
162	1	⾡	辵	7	O	しんにょう、しんにゅう	\N
162	2	⻌	辶	3	E	しんにょう、しんにゅう	近返述進道
162	3	⻍	\N	4	E	しんにょう、しんにゅう	蓮逗逢
162	4	⻎	\N	\N	E	\N	迆迋迶
163	1	⾢	邑	7	O	むら	邫郒郶
163	2	⻏	阝	3	R	おおざと	部那邦邸郁郊
164	1	⾣	酉	7	O	ひよみのとり	酋酒
164	2	\N	\N	7	L	とりへん	配酸醉
165	1	⾤	釆	7	O	のごめ	\N
165	2	\N	\N	7	L	のごめへん	釉釋
166	1	⾥	里	7	O	さと	重量釐
166	2	\N	\N	7	L	さとへん	野
167	1	⾦	金	8	O	かね	釜鏖鏨鑾鑿
167	2	\N	釒	8	L	かねへん	銀銅鋼錫鐵
167	3	⻐	钅	\N	\N	\N	\N
168	1	⾧	長	8	O	ながい	\N
168	2	⻒	镸	8	L	ながい	镺镻镼镽镾
168	3	⻓	长	4	\N	\N	\N
169	1	⾨	門	8	O	もん、もんがまえ	閂閉開閏間
169	2	⻔	门	\N	\N	\N	\N
170	1	⾩	阜	8	O	ぎふのふ	\N
170	2	⻖	阝	3	L	こざとへん	防降陰陽階
171	1	⾪	隶	8	O	れいづくり	逮隸
172	1	⾫	隹	8	O	ふるとり	隻隼雀雄雌
173	1	⾬	雨	8	O	あめ	靉
173	2	⻗	\N	8	T	あめかんむり	雪雲零雷電
174	1	⾭	靑	8	O	あお	靜
174	2	⻘	青	8	V	あお	靖靘靚靛
175	1	⾮	非	8	O	あらず	靟靠靡
176	1	⾯	面	9	O	めん	靤靦靧靨
177	1	⾰	革	9	O	かわ	\N
177	2	\N	\N	9	L	かわへん	勒靴鞋鞍鞭
178	1	⾱	韋	9	V	なめしがわ	韌韍韓韙韜
178	2	⻙	韦	4	\N	\N	\N
179	1	⾲	韭	9	O	にら	韮韰韱韲
180	1	\N	\N	9	O	おと	韴韸
180	2	⾳	音	9	V	おと	韶韻響
181	1	⾴	頁	9	O	おうがい	頂頃頭顏類
181	2	⻚	页	6	\N	\N	\N
182	1	⾵	風	9	O	かぜ	颯飄飆
182	2	\N	\N	9	L	かぜ	颱颶
182	3	⻛	风	4	\N	\N	\N
183	1	⾶	飛	9	O	とぶ	飜飝
183	2	⻜	飞	\N	\N	\N	\N
184	1	⾷	食	9	O	しょく	養餐餮饕饗
184	2	⻟	飠	8	L	しょくへん	飢飯飽飾
184	3	⻞	\N	\N	L	しょくへん	餃
184	4	⻠	饣	\N	\N	\N	\N
185	1	⾸	首	9	O	くび	馗馘
186	1	⾹	香	9	O	においこう	馛馞馥馨馩
187	1	⾺	馬	10	O	うま	\N
187	2	\N	\N	10	L	うまへん	駐駿騎驅驛
187	3	⻢	马	3	\N	\N	\N
188	1	⾻	骨	10	O	ほね	\N
188	2	\N	\N	10	L	ほねへん	骰骸髀髓體
189	1	⾼	高	10	O	たかい	髚髜髝髞
190	1	⾽	髟	10	O	かみかんむり	髦髮髯鬆鬚
191	1	⾾	鬥	10	O	とうがまえ	鬧鬨鬩鬪鬮
192	1	⾿	鬯	10	O	ちょう	鬱
193	1	⿀	鬲	10	O	かく	鬳鬴鬵鬷鬻
194	1	⿁	鬼	10	O	おに	魂魏
194	2	\N	\N	10	E	きにょう	魁魃魅
195	1	⿂	魚	11	O	うお	魯
195	2	\N	\N	11	L	うおへん	鮫鮭鯉鯨
195	3	⻥	鱼	8	\N	\N	\N
196	1	⿃	鳥	11	O	とり	鷲
196	2	\N	\N	11	R	とり	鳩鳴鵝鷗
196	3	⻦	鸟	5	\N	\N	\N
197	1	⿄	鹵	11	O	ろ	鹶鹷鹹鹺鹽
198	1	⿅	鹿	11	O	しか	麋麒麓麗麟
199	1	⿆	麥	11	O	ばく	麨
199	2	⻨	麦	7	O	ばく	麺
199	3	\N	\N	7	E	ばくにょう	麩麪麭麰麴
200	1	⿇	\N	11	O	あさ	\N
200	2	\N	麻	11	\N	\N	\N
200	3	\N	\N	11	\N	あさかんむり	麼麾黀黂
200	4	\N	\N	11	\N	あさかんむり	麿麽黁
201	1	⿈	黃	12	O	きいろ	黌
201	2	⻩	黄	11	O	きいろ	黆黇黉黋
202	1	⿉	黍	12	O	きび	黎黏黐
203	1	⿊	黑	12	O	くろい	墨黔默黛黠
203	2	\N	黒	10	V	くろい	墨黔默黛黠
204	1	⿋	黹	12	O	ふつ	黺黻黼
205	1	⿌	黽	13	O	べん	鼀鼆鼇鼈鼉
205	2	⻪	黾	8	\N	\N	\N
206	1	⿍	鼎	13	O	かなえ	鼏鼐鼑鼒
207	1	⿎	鼓	13	O	つずみ	鼕鼖鼗鼘鼙
208	1	⿏	鼠	13	O	ねずみ	鼦鼹
208	2	\N	\N	13	E	ねずみにょう	鼨鼬鼯
209	1	⿐	\N	14	O	はな	\N
209	2	\N	鼻	14	O	\N	\N
209	3	\N	\N	14	L	はなへん	鼾鼿齁齅齉
210	1	⿑	齊	14	O	せい	齋齌齍齎齏
210	2	⻫	斉	8	V	せい	\N
210	3	⻬	齐	6	\N	\N	\N
211	1	⿒	齒	15	O	は	\N
211	2	\N	\N	15	L	はへん	齟齡齧齬齲
211	3	⻭	歯	12	V	は	\N
211	4	\N	\N	12	L	はへん	\N
211	5	⻮	齿	8	\N	\N	\N
212	1	⿓	龍	16	O	たつ	龏龐龑龔龕
212	2	⻯	竜	10	O	たつ	\N
212	3	⻰	龙	5	\N	\N	\N
213	1	⿔	龜	16	O	かめ	龞
213	2	⻲	亀	\N	O	かめ	\N
213	3	⻳	龟	\N	\N	\N	\N
214	1	⿕	龠	17	O	やく	龡龢龣龤龥
\.


--
-- Data for Name: rdng; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.rdng (entr, rdng, txt) FROM stdin;
1	1	まる
2	1	あさひ
3	1	あの
3	2	かの
4	1	あほんだら
4	2	あほだら
5	1	あまご
5	2	アマゴ
6	1	あら
7	1	あれ
7	2	あ
8	1	いけない
9	1	いらっしゃい
9	2	いらしゃい
10	1	いらっしゃいませ
10	2	いらしゃいませ
10	3	いっらしゃいませ
11	1	いらっしゃる
12	1	おじいさん
13	1	おてんば
14	1	ぐうぐう
15	1	さばさば
16	1	じゃがいも
16	2	ジャガいも
16	3	ジャガイモ
17	1	その
18	1	ぼけ
18	2	ボケ
19	1	アイス
20	1	アイスクリーム
21	1	アフターケア
21	2	アフター・ケア
22	1	アフターサービス
22	2	アフター・サービス
23	1	アルバイト
24	1	エスエフ
25	1	サイエンスフィクション
25	2	サイエンス・フィクション
26	1	ゼロゼロセブン
26	2	ゼロ・ゼロ・セブン
27	1	ちふす
27	2	ちぶす
27	3	チフス
27	4	チブス
28	1	ティッシュペーパー
28	2	ティッシュ・ペーパー
29	1	ドアマン
29	2	ドア・マン
30	1	バイト
31	1	バタードチャイルド
31	2	バタード・チャイルド
32	1	バッティングセンター
32	2	バッテイングセンター
32	3	バッティング・センター
32	4	バッテイング・センター
33	1	ピロシキ
33	2	ビロシキ
34	1	ランプ
35	1	あう
36	1	かつお
36	2	しょうぎょ
36	3	カツオ
37	1	かん
37	2	カン
38	1	かんづめ
39	1	じぐ
39	2	ジグ
40	1	わかめ
40	2	ワカメ
41	1	じゅけんじごく
42	1	こもじ
43	1	なまちゅうけい
44	1	そうつい
45	1	くさかんむり
45	2	そうこう
46	1	おおもじ
46	2	だいもんじ
47	1	たたき
47	2	タタキ
48	1	つっこみ
48	2	ツッコミ
49	1	かた
50	1	ほめごろし
51	1	みっちゃく
52	1	ゆうべ
52	2	さくや
52	3	ゆんべ
53	1	こうよう
53	2	もみじ
54	1	かぼちゃ
54	2	ぼうぶら
54	3	なんか
54	4	カボチャ
55	1	この
56	1	ころもがえ
57	1	こうい
58	1	まち
58	2	ちょう
59	1	まんざい
60	1	ちりがみ
60	2	ちりし
61	1	メリヤスシャツ
61	2	メリヤス・シャツ
62	1	あほだらきょう
63	1	どの
64	1	なんの
65	1	ばかなまね
66	1	げんしりょくあんぜんほあんいん
67	1	ソーシャルネットワーキングサービス
67	2	ソーシャル・ネットワーキング・サービス
68	1	いろはもみじ
68	2	イロハモミジ
69	1	エッチディーディーブイディー
70	1	ジャガタラいも
70	2	ジャガタライモ
71	1	ようとう
71	2	ランプ
72	1	ひぎゃくたいじしょうこうぐん
73	1	じいさん
74	1	みっちゃくしゅざい
75	1	じいちゃん
76	1	アジアたいへいようせんそう
77	1	さつきます
77	2	サツキマス
78	1	もみじがさね
104	1	ああ
105	1	ああ
106	1	ああ
107	1	ああ
109	1	ああ
115	1	ぱんじ
116	1	ばんじ
120	1	あゑあ
121	1	あゑい
\.


--
-- Data for Name: rdngsnd; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.rdngsnd (entr, rdng, ord, snd) FROM stdin;
\.


--
-- Data for Name: restr; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.restr (entr, rdng, kanj) FROM stdin;
5	2	1
5	2	2
5	2	3
16	1	2
16	2	1
16	3	1
16	3	2
18	2	1
18	2	2
27	3	1
27	4	1
36	2	1
36	2	3
36	3	1
36	3	2
36	3	3
37	2	1
37	2	2
37	2	3
39	2	1
39	2	2
40	2	1
40	2	2
40	2	3
40	2	4
45	1	2
47	2	1
47	2	2
47	2	3
48	2	1
48	2	2
48	2	3
52	2	1
52	3	1
54	4	1
58	2	2
68	2	1
70	2	1
70	2	2
77	2	1
\.


--
-- Data for Name: rinf; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.rinf (entr, rdng, ord, kw) FROM stdin;
7	2	1	2
9	2	1	3
10	2	1	3
10	3	1	3
33	2	1	3
54	3	1	2
71	2	1	1
\.


--
-- Data for Name: sens; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.sens (entr, sens, notes) FROM stdin;
1	1	\N
1	2	\N
1	3	\N
1	4	\N
1	5	\N
2	1	\N
3	1	\N
4	1	\N
4	2	\N
5	1	\N
6	1	\N
7	1	\N
7	2	used to refer to one's equals or inferiors
7	3	\N
7	4	\N
7	5	\N
7	6	expression of surprise, suspicion, etc.
7	7	\N
8	1	\N
8	2	\N
8	3	\N
9	1	used as a polite imperative
9	2	\N
10	1	\N
11	1	sometimes erroneously written 居らっしゃる
11	2	after a -te form, or the particle "de"
12	1	usu. お祖父さん
12	2	usu. お爺さん
13	1	\N
14	1	\N
15	1	\N
15	2	\N
16	1	\N
17	1	\N
17	2	\N
18	1	\N
18	2	\N
18	3	\N
19	1	\N
19	2	\N
20	1	\N
21	1	\N
21	2	\N
22	1	\N
23	1	\N
23	2	\N
23	3	\N
24	1	\N
25	1	\N
26	1	\N
27	1	\N
28	1	\N
29	1	\N
30	1	\N
30	2	\N
30	3	\N
30	4	\N
31	1	\N
32	1	\N
33	1	\N
34	1	\N
34	2	\N
34	3	\N
35	1	逢う is often used for close friends, etc. and may be associated with drama or pathos; 遭う may have an undesirable nuance
35	2	esp. 遭う when in kanji
36	1	\N
37	1	\N
37	2	\N
38	1	\N
38	2	usu. 缶詰にする
38	3	usu. 缶詰になる
39	1	\N
40	1	\N
41	1	\N
42	1	\N
42	2	\N
43	1	\N
44	1	\N
45	1	e.g. top of 艾
45	2	\N
46	1	\N
46	2	\N
46	3	\N
46	4	\N
47	1	\N
47	2	\N
47	3	\N
47	4	usu. 三和土 (gikun)
47	5	\N
48	1	\N
48	2	\N
48	3	\N
49	1	also ほう
49	2	\N
49	3	\N
49	4	\N
49	5	also がた
49	6	also がた
50	1	\N
51	1	\N
51	2	\N
51	3	\N
52	1	\N
52	2	usu. 昨夜
53	1	\N
53	2	\N
53	3	\N
53	4	\N
53	5	\N
53	6	\N
54	1	ぼうぶら is primarily Kansai dialect
55	1	\N
56	1	reading is gikun for 更衣
56	2	\N
57	1	\N
57	2	\N
58	1	esp. 町
58	2	\N
58	3	\N
58	4	\N
58	5	\N
59	1	\N
60	1	\N
61	1	\N
62	1	pun on あほだら and 陀羅尼経
63	1	\N
64	1	\N
65	1	\N
66	1	\N
67	1	\N
68	1	\N
69	1	\N
70	1	\N
71	1	\N
72	1	\N
73	1	usu. 祖父さん
73	2	usu. 爺さん
74	1	\N
75	1	usu. 祖父ちゃん
75	2	usu. 爺ちゃん
76	1	\N
77	1	\N
78	1	\N
104	1	\N
105	1	\N
106	1	\N
107	1	\N
109	1	\N
115	1	\N
116	1	\N
120	1	\N
121	1	\N
\.


--
-- Data for Name: snd; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.snd (id, file, strt, leng, trns, notes) FROM stdin;
\.


--
-- Data for Name: sndfile; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.sndfile (id, vol, title, loc, type, notes) FROM stdin;
\.


--
-- Data for Name: sndvol; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.sndvol (id, title, loc, type, idstr, corp, notes) FROM stdin;
\.


--
-- Data for Name: stagk; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.stagk (entr, sens, kanj) FROM stdin;
47	1	3
47	2	3
47	3	3
47	5	2
47	5	3
52	1	2
53	2	2
53	3	1
58	2	1
58	4	2
58	5	2
\.


--
-- Data for Name: stagr; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.stagr (entr, sens, rdng) FROM stdin;
4	2	1
7	4	2
7	5	2
46	1	2
46	3	1
46	4	1
47	1	1
47	5	1
53	2	2
53	3	2
53	4	1
53	5	1
58	4	1
58	5	1
\.


--
-- Data for Name: xref; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.xref (entr, sens, xref, typ, xentr, xsens, rdng, kanj, notes, nosens, lowpri) FROM stdin;
3	1	1	3	63	1	1	1	\N	f	f
3	1	2	3	55	1	\N	1	\N	f	f
3	1	3	3	17	1	\N	1	\N	f	f
3	1	4	3	7	1	1	1	\N	f	f
4	2	1	3	62	1	\N	1	\N	f	f
5	1	1	3	77	1	\N	1	\N	f	f
9	1	1	3	11	1	1	\N	\N	f	f
9	2	1	3	10	1	1	\N	\N	f	f
12	1	1	3	73	1	\N	2	\N	t	f
16	1	1	3	70	1	\N	1	\N	f	f
17	1	1	3	63	1	1	1	\N	f	f
17	1	2	3	55	1	\N	1	\N	f	f
17	1	4	3	3	1	\N	1	\N	f	f
18	2	1	3	59	1	\N	1	\N	f	f
18	2	2	3	48	2	1	1	\N	f	f
19	2	1	3	20	1	1	\N	\N	f	f
21	2	1	3	22	1	1	\N	\N	f	f
22	1	1	3	21	2	1	\N	\N	f	f
25	1	1	3	24	1	\N	1	\N	f	f
28	1	1	3	60	1	\N	2	\N	f	f
30	1	1	3	23	1	1	\N	\N	f	f
31	1	1	3	72	1	\N	1	\N	f	f
34	1	1	3	71	1	2	1	\N	f	f
37	2	1	3	38	1	\N	1	\N	f	f
42	1	1	3	46	1	\N	1	\N	f	f
46	1	1	3	42	1	\N	1	\N	f	f
47	2	1	3	36	1	\N	1	\N	f	f
48	2	1	3	18	2	1	1	\N	f	f
53	4	1	3	68	1	\N	1	\N	f	f
53	6	1	3	78	1	\N	1	\N	f	f
55	1	1	3	63	1	1	1	\N	f	f
55	1	3	3	17	1	\N	1	\N	f	f
55	1	4	3	3	1	\N	1	\N	f	f
56	1	1	3	57	1	1	1	\N	f	f
62	1	1	3	4	1	2	\N	\N	f	f
63	1	1	3	55	1	\N	1	\N	f	f
63	1	2	3	17	1	\N	1	\N	f	f
63	1	3	3	3	1	\N	1	\N	f	f
70	1	1	3	16	1	\N	2	\N	f	f
73	1	1	3	12	1	\N	1	\N	f	f
73	2	1	3	75	2	\N	1	\N	f	f
75	1	1	3	73	1	\N	2	\N	f	f
75	2	1	3	73	2	\N	1	\N	f	f
77	1	1	3	5	1	\N	1	\N	f	f
78	1	1	3	53	6	\N	1	\N	f	f
\.


--
-- Data for Name: xresolv; Type: TABLE DATA; Schema: public; Owner: jmdictdb
--

COPY public.xresolv (entr, sens, typ, ord, rtxt, ktxt, tsens, notes, prio) FROM stdin;
1	1	3	1	まる	丸	1	\N	\N
1	2	3	1	にじゅうまる	二重丸	\N	\N	\N
1	3	3	1	〇〇・まるまる	\N	1	\N	\N
1	4	3	1	\N	句点	\N	\N	\N
1	5	3	1	\N	半濁点	\N	\N	\N
7	1	3	1	\N	何れ	1	\N	\N
7	1	3	2	\N	此れ	1	\N	\N
7	1	3	3	\N	其れ	1	\N	\N
17	1	3	3	\N	其れ	1	\N	\N
23	3	3	1	\N	曹長石	\N	\N	\N
55	1	3	2	\N	此れ	1	\N	\N
59	1	3	1	まんざい	万歳	\N	\N	\N
76	1	3	1	\N	十五年戦争	\N	\N	\N
76	1	3	2	\N	太平洋戦争	\N	\N	\N
\.


--
-- Name: entr_id_seq; Type: SEQUENCE SET; Schema: imp; Owner: jmdictdb
--

SELECT pg_catalog.setval('imp.entr_id_seq', 1, false);


--
-- Name: entr_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jmdictdb
--

SELECT pg_catalog.setval('public.entr_id_seq', 121, true);


--
-- Name: kwgrp_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jmdictdb
--

SELECT pg_catalog.setval('public.kwgrp_id_seq', 1, false);


--
-- Name: seq_jmdict; Type: SEQUENCE SET; Schema: public; Owner: jmdictdb
--

SELECT pg_catalog.setval('public.seq_jmdict', 2833920, true);


--
-- Name: seq_jmnedict; Type: SEQUENCE SET; Schema: public; Owner: jmdictdb
--

SELECT pg_catalog.setval('public.seq_jmnedict', 1000030, true);


--
-- Name: seq_test; Type: SEQUENCE SET; Schema: public; Owner: jmdictdb
--

SELECT pg_catalog.setval('public.seq_test', 13, true);


--
-- Name: snd_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jmdictdb
--

SELECT pg_catalog.setval('public.snd_id_seq', 1, false);


--
-- Name: sndfile_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jmdictdb
--

SELECT pg_catalog.setval('public.sndfile_id_seq', 1, false);


--
-- Name: sndvol_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jmdictdb
--

SELECT pg_catalog.setval('public.sndvol_id_seq', 1, false);


--
-- Name: chr chr_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.chr
    ADD CONSTRAINT chr_pkey PRIMARY KEY (entr);


--
-- Name: cinf cinf_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.cinf
    ADD CONSTRAINT cinf_pkey PRIMARY KEY (entr, kw, value, mctype);


--
-- Name: dial dial_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.dial
    ADD CONSTRAINT dial_pkey PRIMARY KEY (entr, sens, kw);


--
-- Name: entr entr_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.entr
    ADD CONSTRAINT entr_pkey PRIMARY KEY (id);


--
-- Name: fld fld_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.fld
    ADD CONSTRAINT fld_pkey PRIMARY KEY (entr, sens, kw);


--
-- Name: freq freq_entr_kanj_kw_value_key; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.freq
    ADD CONSTRAINT freq_entr_kanj_kw_value_key UNIQUE (entr, kanj, kw, value);


--
-- Name: freq freq_entr_rdng_kw_value_key; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.freq
    ADD CONSTRAINT freq_entr_rdng_kw_value_key UNIQUE (entr, rdng, kw, value);


--
-- Name: gloss gloss_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.gloss
    ADD CONSTRAINT gloss_pkey PRIMARY KEY (entr, sens, gloss);


--
-- Name: grp grp_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.grp
    ADD CONSTRAINT grp_pkey PRIMARY KEY (entr, kw);


--
-- Name: hist hist_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.hist
    ADD CONSTRAINT hist_pkey PRIMARY KEY (entr, hist);


--
-- Name: kanj kanj_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.kanj
    ADD CONSTRAINT kanj_pkey PRIMARY KEY (entr, kanj);


--
-- Name: kinf kinf_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.kinf
    ADD CONSTRAINT kinf_pkey PRIMARY KEY (entr, kanj, kw);


--
-- Name: kresolv kresolv_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.kresolv
    ADD CONSTRAINT kresolv_pkey PRIMARY KEY (entr, kw, value);


--
-- Name: kwsrc kwsrc_kw_key; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.kwsrc
    ADD CONSTRAINT kwsrc_kw_key UNIQUE (kw);


--
-- Name: kwsrc kwsrc_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.kwsrc
    ADD CONSTRAINT kwsrc_pkey PRIMARY KEY (id);


--
-- Name: lsrc lsrc_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.lsrc
    ADD CONSTRAINT lsrc_pkey PRIMARY KEY (entr, sens, lang, txt);


--
-- Name: misc misc_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.misc
    ADD CONSTRAINT misc_pkey PRIMARY KEY (entr, sens, kw);


--
-- Name: pos pos_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.pos
    ADD CONSTRAINT pos_pkey PRIMARY KEY (entr, sens, kw);


--
-- Name: rdng rdng_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.rdng
    ADD CONSTRAINT rdng_pkey PRIMARY KEY (entr, rdng);


--
-- Name: restr restr_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.restr
    ADD CONSTRAINT restr_pkey PRIMARY KEY (entr, rdng, kanj);


--
-- Name: rinf rinf_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.rinf
    ADD CONSTRAINT rinf_pkey PRIMARY KEY (entr, rdng, kw);


--
-- Name: sens sens_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.sens
    ADD CONSTRAINT sens_pkey PRIMARY KEY (entr, sens);


--
-- Name: stagk stagk_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.stagk
    ADD CONSTRAINT stagk_pkey PRIMARY KEY (entr, sens, kanj);


--
-- Name: stagr stagr_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.stagr
    ADD CONSTRAINT stagr_pkey PRIMARY KEY (entr, sens, rdng);


--
-- Name: xref xref_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.xref
    ADD CONSTRAINT xref_pkey PRIMARY KEY (entr, sens, xref, xentr, xsens);


--
-- Name: xresolv xresolv_pkey; Type: CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.xresolv
    ADD CONSTRAINT xresolv_pkey PRIMARY KEY (entr, sens, typ, ord);


--
-- Name: chr chr_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.chr
    ADD CONSTRAINT chr_pkey PRIMARY KEY (entr);


--
-- Name: cinf cinf_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.cinf
    ADD CONSTRAINT cinf_pkey PRIMARY KEY (entr, kw, value, mctype);


--
-- Name: conj conj_name_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.conj
    ADD CONSTRAINT conj_name_key UNIQUE (name);


--
-- Name: conj conj_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.conj
    ADD CONSTRAINT conj_pkey PRIMARY KEY (id);


--
-- Name: conjo_notes conjo_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.conjo_notes
    ADD CONSTRAINT conjo_notes_pkey PRIMARY KEY (pos, conj, neg, fml, onum, note);


--
-- Name: conjo conjo_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.conjo
    ADD CONSTRAINT conjo_pkey PRIMARY KEY (pos, conj, neg, fml, onum);


--
-- Name: conotes conotes_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.conotes
    ADD CONSTRAINT conotes_pkey PRIMARY KEY (id);


--
-- Name: db db_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.db
    ADD CONSTRAINT db_pkey PRIMARY KEY (id);


--
-- Name: dial dial_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.dial
    ADD CONSTRAINT dial_pkey PRIMARY KEY (entr, sens, kw);


--
-- Name: entr entr_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.entr
    ADD CONSTRAINT entr_pkey PRIMARY KEY (id);


--
-- Name: entrsnd entrsnd_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.entrsnd
    ADD CONSTRAINT entrsnd_pkey PRIMARY KEY (entr, snd);


--
-- Name: fld fld_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.fld
    ADD CONSTRAINT fld_pkey PRIMARY KEY (entr, sens, kw);


--
-- Name: freq freq_entr_kanj_kw_value_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.freq
    ADD CONSTRAINT freq_entr_kanj_kw_value_key UNIQUE (entr, kanj, kw, value);


--
-- Name: freq freq_entr_rdng_kw_value_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.freq
    ADD CONSTRAINT freq_entr_rdng_kw_value_key UNIQUE (entr, rdng, kw, value);


--
-- Name: gloss gloss_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.gloss
    ADD CONSTRAINT gloss_pkey PRIMARY KEY (entr, sens, gloss);


--
-- Name: grp grp_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.grp
    ADD CONSTRAINT grp_pkey PRIMARY KEY (entr, kw);


--
-- Name: hist hist_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.hist
    ADD CONSTRAINT hist_pkey PRIMARY KEY (entr, hist);


--
-- Name: kanj kanj_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kanj
    ADD CONSTRAINT kanj_pkey PRIMARY KEY (entr, kanj);


--
-- Name: kinf kinf_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kinf
    ADD CONSTRAINT kinf_pkey PRIMARY KEY (entr, kanj, kw);


--
-- Name: kresolv kresolv_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kresolv
    ADD CONSTRAINT kresolv_pkey PRIMARY KEY (entr, kw, value);


--
-- Name: kwcinf kwcinf_kw_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwcinf
    ADD CONSTRAINT kwcinf_kw_key UNIQUE (kw);


--
-- Name: kwcinf kwcinf_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwcinf
    ADD CONSTRAINT kwcinf_pkey PRIMARY KEY (id);


--
-- Name: kwdial kwdial_kw_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwdial
    ADD CONSTRAINT kwdial_kw_key UNIQUE (kw);


--
-- Name: kwdial kwdial_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwdial
    ADD CONSTRAINT kwdial_pkey PRIMARY KEY (id);


--
-- Name: kwfld kwfld_kw_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwfld
    ADD CONSTRAINT kwfld_kw_key UNIQUE (kw);


--
-- Name: kwfld kwfld_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwfld
    ADD CONSTRAINT kwfld_pkey PRIMARY KEY (id);


--
-- Name: kwfreq kwfreq_kw_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwfreq
    ADD CONSTRAINT kwfreq_kw_key UNIQUE (kw);


--
-- Name: kwfreq kwfreq_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwfreq
    ADD CONSTRAINT kwfreq_pkey PRIMARY KEY (id);


--
-- Name: kwginf kwginf_kw_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwginf
    ADD CONSTRAINT kwginf_kw_key UNIQUE (kw);


--
-- Name: kwginf kwginf_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwginf
    ADD CONSTRAINT kwginf_pkey PRIMARY KEY (id);


--
-- Name: kwgrp kwgrp_kw_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwgrp
    ADD CONSTRAINT kwgrp_kw_key UNIQUE (kw);


--
-- Name: kwgrp kwgrp_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwgrp
    ADD CONSTRAINT kwgrp_pkey PRIMARY KEY (id);


--
-- Name: kwkinf kwkinf_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwkinf
    ADD CONSTRAINT kwkinf_pkey PRIMARY KEY (id);


--
-- Name: kwlang kwlang_kw_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwlang
    ADD CONSTRAINT kwlang_kw_key UNIQUE (kw);


--
-- Name: kwlang kwlang_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwlang
    ADD CONSTRAINT kwlang_pkey PRIMARY KEY (id);


--
-- Name: kwmisc kwmisc_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwmisc
    ADD CONSTRAINT kwmisc_pkey PRIMARY KEY (id);


--
-- Name: kwpos kwpos_kw_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwpos
    ADD CONSTRAINT kwpos_kw_key UNIQUE (kw);


--
-- Name: kwpos kwpos_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwpos
    ADD CONSTRAINT kwpos_pkey PRIMARY KEY (id);


--
-- Name: kwrinf kwrinf_kw_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwrinf
    ADD CONSTRAINT kwrinf_kw_key UNIQUE (kw);


--
-- Name: kwrinf kwrinf_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwrinf
    ADD CONSTRAINT kwrinf_pkey PRIMARY KEY (id);


--
-- Name: kwsrc kwsrc_kw_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwsrc
    ADD CONSTRAINT kwsrc_kw_key UNIQUE (kw);


--
-- Name: kwsrc kwsrc_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwsrc
    ADD CONSTRAINT kwsrc_pkey PRIMARY KEY (id);


--
-- Name: kwsrct kwsrct_kw_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwsrct
    ADD CONSTRAINT kwsrct_kw_key UNIQUE (kw);


--
-- Name: kwsrct kwsrct_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwsrct
    ADD CONSTRAINT kwsrct_pkey PRIMARY KEY (id);


--
-- Name: kwstat kwstat_kw_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwstat
    ADD CONSTRAINT kwstat_kw_key UNIQUE (kw);


--
-- Name: kwstat kwstat_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwstat
    ADD CONSTRAINT kwstat_pkey PRIMARY KEY (id);


--
-- Name: kwxref kwxref_kw_key; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwxref
    ADD CONSTRAINT kwxref_kw_key UNIQUE (kw);


--
-- Name: kwxref kwxref_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwxref
    ADD CONSTRAINT kwxref_pkey PRIMARY KEY (id);


--
-- Name: lsrc lsrc_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.lsrc
    ADD CONSTRAINT lsrc_pkey PRIMARY KEY (entr, sens, lang, txt);


--
-- Name: misc misc_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.misc
    ADD CONSTRAINT misc_pkey PRIMARY KEY (entr, sens, kw);


--
-- Name: pos pos_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.pos
    ADD CONSTRAINT pos_pkey PRIMARY KEY (entr, sens, kw);


--
-- Name: rad rad_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.rad
    ADD CONSTRAINT rad_pkey PRIMARY KEY (num, var);


--
-- Name: rdng rdng_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.rdng
    ADD CONSTRAINT rdng_pkey PRIMARY KEY (entr, rdng);


--
-- Name: rdngsnd rdngsnd_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.rdngsnd
    ADD CONSTRAINT rdngsnd_pkey PRIMARY KEY (entr, rdng, snd);


--
-- Name: restr restr_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.restr
    ADD CONSTRAINT restr_pkey PRIMARY KEY (entr, rdng, kanj);


--
-- Name: rinf rinf_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.rinf
    ADD CONSTRAINT rinf_pkey PRIMARY KEY (entr, rdng, kw);


--
-- Name: sens sens_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.sens
    ADD CONSTRAINT sens_pkey PRIMARY KEY (entr, sens);


--
-- Name: snd snd_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.snd
    ADD CONSTRAINT snd_pkey PRIMARY KEY (id);


--
-- Name: sndfile sndfile_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.sndfile
    ADD CONSTRAINT sndfile_pkey PRIMARY KEY (id);


--
-- Name: sndvol sndvol_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.sndvol
    ADD CONSTRAINT sndvol_pkey PRIMARY KEY (id);


--
-- Name: stagk stagk_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.stagk
    ADD CONSTRAINT stagk_pkey PRIMARY KEY (entr, sens, kanj);


--
-- Name: stagr stagr_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.stagr
    ADD CONSTRAINT stagr_pkey PRIMARY KEY (entr, sens, rdng);


--
-- Name: xref xref_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.xref
    ADD CONSTRAINT xref_pkey PRIMARY KEY (entr, sens, xref, xentr, xsens);


--
-- Name: xresolv xresolv_pkey; Type: CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.xresolv
    ADD CONSTRAINT xresolv_pkey PRIMARY KEY (entr, sens, typ, ord);


--
-- Name: chr_chr_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE UNIQUE INDEX chr_chr_idx ON imp.chr USING btree (chr);


--
-- Name: cinf_kw; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX cinf_kw ON imp.cinf USING btree (kw);


--
-- Name: cinf_val; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX cinf_val ON imp.cinf USING btree (value);


--
-- Name: entr_dfrm_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX entr_dfrm_idx ON imp.entr USING btree (dfrm) WHERE (dfrm IS NOT NULL);


--
-- Name: entr_seq_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX entr_seq_idx ON imp.entr USING btree (seq);


--
-- Name: entr_stat_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX entr_stat_idx ON imp.entr USING btree (stat) WHERE (stat <> 2);


--
-- Name: entr_unap_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX entr_unap_idx ON imp.entr USING btree (unap) WHERE unap;


--
-- Name: gloss_entr_sens_lang_txt_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE UNIQUE INDEX gloss_entr_sens_lang_txt_idx ON imp.gloss USING btree (entr, sens, lang, txt);


--
-- Name: gloss_lower_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX gloss_lower_idx ON imp.gloss USING btree (lower((txt)::text) varchar_pattern_ops);


--
-- Name: gloss_lower_idx1; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX gloss_lower_idx1 ON imp.gloss USING btree (lower((txt)::text));


--
-- Name: gloss_txt_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX gloss_txt_idx ON imp.gloss USING btree (txt);


--
-- Name: grp_kw; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX grp_kw ON imp.grp USING btree (kw);


--
-- Name: hist_dt_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX hist_dt_idx ON imp.hist USING btree (dt);


--
-- Name: hist_email_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX hist_email_idx ON imp.hist USING btree (email);


--
-- Name: hist_userid_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX hist_userid_idx ON imp.hist USING btree (userid);


--
-- Name: kanj_entr_txt_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE UNIQUE INDEX kanj_entr_txt_idx ON imp.kanj USING btree (entr, txt);


--
-- Name: kanj_txt_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX kanj_txt_idx ON imp.kanj USING btree (txt);


--
-- Name: kanj_txt_idx1; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX kanj_txt_idx1 ON imp.kanj USING btree (txt varchar_pattern_ops);


--
-- Name: rdng_entr_txt_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE UNIQUE INDEX rdng_entr_txt_idx ON imp.rdng USING btree (entr, txt);


--
-- Name: rdng_txt_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX rdng_txt_idx ON imp.rdng USING btree (txt);


--
-- Name: rdng_txt_idx1; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX rdng_txt_idx1 ON imp.rdng USING btree (txt varchar_pattern_ops);


--
-- Name: xref_xentr_xsens_idx; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX xref_xentr_xsens_idx ON imp.xref USING btree (xentr, xsens);


--
-- Name: xresolv_kanj; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX xresolv_kanj ON imp.xresolv USING btree (ktxt);


--
-- Name: xresolv_rdng; Type: INDEX; Schema: imp; Owner: jmdictdb
--

CREATE INDEX xresolv_rdng ON imp.xresolv USING btree (rtxt);


--
-- Name: chr_chr_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE UNIQUE INDEX chr_chr_idx ON public.chr USING btree (chr);


--
-- Name: cinf_kw; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX cinf_kw ON public.cinf USING btree (kw);


--
-- Name: cinf_val; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX cinf_val ON public.cinf USING btree (value);


--
-- Name: entr_dfrm_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX entr_dfrm_idx ON public.entr USING btree (dfrm) WHERE (dfrm IS NOT NULL);


--
-- Name: entr_seq_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX entr_seq_idx ON public.entr USING btree (seq);


--
-- Name: entr_stat_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX entr_stat_idx ON public.entr USING btree (stat) WHERE (stat <> 2);


--
-- Name: entr_unap_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX entr_unap_idx ON public.entr USING btree (unap) WHERE unap;


--
-- Name: entrsnd_snd_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX entrsnd_snd_idx ON public.entrsnd USING btree (snd);


--
-- Name: gloss_entr_sens_lang_txt_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE UNIQUE INDEX gloss_entr_sens_lang_txt_idx ON public.gloss USING btree (entr, sens, lang, txt);


--
-- Name: gloss_lower_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX gloss_lower_idx ON public.gloss USING btree (lower((txt)::text) varchar_pattern_ops);


--
-- Name: gloss_lower_idx1; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX gloss_lower_idx1 ON public.gloss USING btree (lower((txt)::text));


--
-- Name: gloss_txt_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX gloss_txt_idx ON public.gloss USING btree (txt);


--
-- Name: grp_kw; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX grp_kw ON public.grp USING btree (kw);


--
-- Name: hist_dt_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX hist_dt_idx ON public.hist USING btree (dt);


--
-- Name: hist_email_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX hist_email_idx ON public.hist USING btree (email);


--
-- Name: hist_userid_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX hist_userid_idx ON public.hist USING btree (userid);


--
-- Name: kanj_entr_txt_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE UNIQUE INDEX kanj_entr_txt_idx ON public.kanj USING btree (entr, txt);


--
-- Name: kanj_txt_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX kanj_txt_idx ON public.kanj USING btree (txt);


--
-- Name: kanj_txt_idx1; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX kanj_txt_idx1 ON public.kanj USING btree (txt varchar_pattern_ops);


--
-- Name: rdng_entr_txt_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE UNIQUE INDEX rdng_entr_txt_idx ON public.rdng USING btree (entr, txt);


--
-- Name: rdng_txt_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX rdng_txt_idx ON public.rdng USING btree (txt);


--
-- Name: rdng_txt_idx1; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX rdng_txt_idx1 ON public.rdng USING btree (txt varchar_pattern_ops);


--
-- Name: rdngsnd_snd; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX rdngsnd_snd ON public.rdngsnd USING btree (snd);


--
-- Name: sndfile_vol_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX sndfile_vol_idx ON public.sndfile USING btree (vol);


--
-- Name: xref_xentr_xsens_idx; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX xref_xentr_xsens_idx ON public.xref USING btree (xentr, xsens);


--
-- Name: xresolv_kanj; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX xresolv_kanj ON public.xresolv USING btree (ktxt);


--
-- Name: xresolv_rdng; Type: INDEX; Schema: public; Owner: jmdictdb
--

CREATE INDEX xresolv_rdng ON public.xresolv USING btree (rtxt);


--
-- Name: entr entr_seqdef; Type: TRIGGER; Schema: public; Owner: jmdictdb
--

CREATE TRIGGER entr_seqdef BEFORE INSERT ON public.entr FOR EACH ROW EXECUTE PROCEDURE public.entr_seqdef();


--
-- Name: kwsrc kwsrc_updseq; Type: TRIGGER; Schema: public; Owner: jmdictdb
--

CREATE TRIGGER kwsrc_updseq AFTER INSERT OR DELETE OR UPDATE ON public.kwsrc FOR EACH ROW EXECUTE PROCEDURE public.kwsrc_updseq();


--
-- Name: chr chr_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.chr
    ADD CONSTRAINT chr_entr_fkey FOREIGN KEY (entr) REFERENCES imp.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: cinf cinf_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.cinf
    ADD CONSTRAINT cinf_entr_fkey FOREIGN KEY (entr) REFERENCES imp.chr(entr) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: cinf cinf_kw_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.cinf
    ADD CONSTRAINT cinf_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwcinf(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: dial dial_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.dial
    ADD CONSTRAINT dial_entr_fkey FOREIGN KEY (entr, sens) REFERENCES imp.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: dial dial_kw_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.dial
    ADD CONSTRAINT dial_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwdial(id);


--
-- Name: entr entr_dfrm_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.entr
    ADD CONSTRAINT entr_dfrm_fkey FOREIGN KEY (dfrm) REFERENCES imp.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: entr entr_src_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.entr
    ADD CONSTRAINT entr_src_fkey FOREIGN KEY (src) REFERENCES imp.kwsrc(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: entr entr_stat_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.entr
    ADD CONSTRAINT entr_stat_fkey FOREIGN KEY (stat) REFERENCES public.kwstat(id);


--
-- Name: fld fld_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.fld
    ADD CONSTRAINT fld_entr_fkey FOREIGN KEY (entr, sens) REFERENCES imp.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: fld fld_kw_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.fld
    ADD CONSTRAINT fld_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwfld(id);


--
-- Name: freq freq_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.freq
    ADD CONSTRAINT freq_entr_fkey FOREIGN KEY (entr, rdng) REFERENCES imp.rdng(entr, rdng) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: freq freq_entr_fkey1; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.freq
    ADD CONSTRAINT freq_entr_fkey1 FOREIGN KEY (entr, kanj) REFERENCES imp.kanj(entr, kanj) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: freq freq_kw_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.freq
    ADD CONSTRAINT freq_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwfreq(id);


--
-- Name: gloss gloss_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.gloss
    ADD CONSTRAINT gloss_entr_fkey FOREIGN KEY (entr, sens) REFERENCES imp.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: gloss gloss_ginf_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.gloss
    ADD CONSTRAINT gloss_ginf_fkey FOREIGN KEY (ginf) REFERENCES public.kwginf(id);


--
-- Name: gloss gloss_lang_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.gloss
    ADD CONSTRAINT gloss_lang_fkey FOREIGN KEY (lang) REFERENCES public.kwlang(id);


--
-- Name: grp grp_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.grp
    ADD CONSTRAINT grp_entr_fkey FOREIGN KEY (entr) REFERENCES imp.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: grp grp_kw_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.grp
    ADD CONSTRAINT grp_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwgrp(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: hist hist_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.hist
    ADD CONSTRAINT hist_entr_fkey FOREIGN KEY (entr) REFERENCES imp.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: hist hist_stat_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.hist
    ADD CONSTRAINT hist_stat_fkey FOREIGN KEY (stat) REFERENCES public.kwstat(id);


--
-- Name: kanj kanj_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.kanj
    ADD CONSTRAINT kanj_entr_fkey FOREIGN KEY (entr) REFERENCES imp.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: kinf kinf_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.kinf
    ADD CONSTRAINT kinf_entr_fkey FOREIGN KEY (entr, kanj) REFERENCES imp.kanj(entr, kanj) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: kinf kinf_kw_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.kinf
    ADD CONSTRAINT kinf_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwkinf(id);


--
-- Name: kresolv kresolv_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.kresolv
    ADD CONSTRAINT kresolv_entr_fkey FOREIGN KEY (entr) REFERENCES imp.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: kwsrc kwsrc_srct_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.kwsrc
    ADD CONSTRAINT kwsrc_srct_fkey FOREIGN KEY (srct) REFERENCES public.kwsrct(id);


--
-- Name: lsrc lsrc_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.lsrc
    ADD CONSTRAINT lsrc_entr_fkey FOREIGN KEY (entr, sens) REFERENCES imp.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: lsrc lsrc_lang_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.lsrc
    ADD CONSTRAINT lsrc_lang_fkey FOREIGN KEY (lang) REFERENCES public.kwlang(id);


--
-- Name: misc misc_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.misc
    ADD CONSTRAINT misc_entr_fkey FOREIGN KEY (entr, sens) REFERENCES imp.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: misc misc_kw_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.misc
    ADD CONSTRAINT misc_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwmisc(id);


--
-- Name: pos pos_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.pos
    ADD CONSTRAINT pos_entr_fkey FOREIGN KEY (entr, sens) REFERENCES imp.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: pos pos_kw_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.pos
    ADD CONSTRAINT pos_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwpos(id);


--
-- Name: rdng rdng_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.rdng
    ADD CONSTRAINT rdng_entr_fkey FOREIGN KEY (entr) REFERENCES imp.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: restr restr_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.restr
    ADD CONSTRAINT restr_entr_fkey FOREIGN KEY (entr, rdng) REFERENCES imp.rdng(entr, rdng) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: restr restr_entr_fkey1; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.restr
    ADD CONSTRAINT restr_entr_fkey1 FOREIGN KEY (entr, kanj) REFERENCES imp.kanj(entr, kanj) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: rinf rinf_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.rinf
    ADD CONSTRAINT rinf_entr_fkey FOREIGN KEY (entr, rdng) REFERENCES imp.rdng(entr, rdng) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: rinf rinf_kw_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.rinf
    ADD CONSTRAINT rinf_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwrinf(id);


--
-- Name: sens sens_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.sens
    ADD CONSTRAINT sens_entr_fkey FOREIGN KEY (entr) REFERENCES imp.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: stagk stagk_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.stagk
    ADD CONSTRAINT stagk_entr_fkey FOREIGN KEY (entr, sens) REFERENCES imp.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: stagk stagk_entr_fkey1; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.stagk
    ADD CONSTRAINT stagk_entr_fkey1 FOREIGN KEY (entr, kanj) REFERENCES imp.kanj(entr, kanj) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: stagr stagr_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.stagr
    ADD CONSTRAINT stagr_entr_fkey FOREIGN KEY (entr, sens) REFERENCES imp.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: stagr stagr_entr_fkey1; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.stagr
    ADD CONSTRAINT stagr_entr_fkey1 FOREIGN KEY (entr, rdng) REFERENCES imp.rdng(entr, rdng) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: xref xref_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.xref
    ADD CONSTRAINT xref_entr_fkey FOREIGN KEY (entr, sens) REFERENCES imp.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: xref xref_kanj_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.xref
    ADD CONSTRAINT xref_kanj_fkey FOREIGN KEY (xentr, kanj) REFERENCES imp.kanj(entr, kanj) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: xref xref_rdng_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.xref
    ADD CONSTRAINT xref_rdng_fkey FOREIGN KEY (xentr, rdng) REFERENCES imp.rdng(entr, rdng) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: xref xref_typ_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.xref
    ADD CONSTRAINT xref_typ_fkey FOREIGN KEY (typ) REFERENCES public.kwxref(id);


--
-- Name: xref xref_xentr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.xref
    ADD CONSTRAINT xref_xentr_fkey FOREIGN KEY (xentr, xsens) REFERENCES imp.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: xresolv xresolv_entr_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.xresolv
    ADD CONSTRAINT xresolv_entr_fkey FOREIGN KEY (entr, sens) REFERENCES imp.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: xresolv xresolv_typ_fkey; Type: FK CONSTRAINT; Schema: imp; Owner: jmdictdb
--

ALTER TABLE ONLY imp.xresolv
    ADD CONSTRAINT xresolv_typ_fkey FOREIGN KEY (typ) REFERENCES public.kwxref(id);


--
-- Name: chr chr_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.chr
    ADD CONSTRAINT chr_entr_fkey FOREIGN KEY (entr) REFERENCES public.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: cinf cinf_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.cinf
    ADD CONSTRAINT cinf_entr_fkey FOREIGN KEY (entr) REFERENCES public.chr(entr) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: cinf cinf_kw_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.cinf
    ADD CONSTRAINT cinf_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwcinf(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: conjo conjo_conj_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.conjo
    ADD CONSTRAINT conjo_conj_fkey FOREIGN KEY (conj) REFERENCES public.conj(id) ON UPDATE CASCADE;


--
-- Name: conjo_notes conjo_notes_note_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.conjo_notes
    ADD CONSTRAINT conjo_notes_note_fkey FOREIGN KEY (note) REFERENCES public.conotes(id) ON UPDATE CASCADE;


--
-- Name: conjo_notes conjo_notes_pos_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.conjo_notes
    ADD CONSTRAINT conjo_notes_pos_fkey FOREIGN KEY (pos, conj, neg, fml, onum) REFERENCES public.conjo(pos, conj, neg, fml, onum) ON UPDATE CASCADE;


--
-- Name: conjo conjo_pos2_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.conjo
    ADD CONSTRAINT conjo_pos2_fkey FOREIGN KEY (pos2) REFERENCES public.kwpos(id) ON UPDATE CASCADE;


--
-- Name: conjo conjo_pos_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.conjo
    ADD CONSTRAINT conjo_pos_fkey FOREIGN KEY (pos) REFERENCES public.kwpos(id) ON UPDATE CASCADE;


--
-- Name: dial dial_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.dial
    ADD CONSTRAINT dial_entr_fkey FOREIGN KEY (entr, sens) REFERENCES public.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: dial dial_kw_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.dial
    ADD CONSTRAINT dial_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwdial(id);


--
-- Name: entr entr_dfrm_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.entr
    ADD CONSTRAINT entr_dfrm_fkey FOREIGN KEY (dfrm) REFERENCES public.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: entr entr_src_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.entr
    ADD CONSTRAINT entr_src_fkey FOREIGN KEY (src) REFERENCES public.kwsrc(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: entr entr_stat_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.entr
    ADD CONSTRAINT entr_stat_fkey FOREIGN KEY (stat) REFERENCES public.kwstat(id);


--
-- Name: entrsnd entrsnd_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.entrsnd
    ADD CONSTRAINT entrsnd_entr_fkey FOREIGN KEY (entr) REFERENCES public.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: entrsnd entrsnd_snd_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.entrsnd
    ADD CONSTRAINT entrsnd_snd_fkey FOREIGN KEY (snd) REFERENCES public.snd(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: fld fld_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.fld
    ADD CONSTRAINT fld_entr_fkey FOREIGN KEY (entr, sens) REFERENCES public.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: fld fld_kw_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.fld
    ADD CONSTRAINT fld_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwfld(id);


--
-- Name: freq freq_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.freq
    ADD CONSTRAINT freq_entr_fkey FOREIGN KEY (entr, rdng) REFERENCES public.rdng(entr, rdng) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: freq freq_entr_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.freq
    ADD CONSTRAINT freq_entr_fkey1 FOREIGN KEY (entr, kanj) REFERENCES public.kanj(entr, kanj) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: freq freq_kw_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.freq
    ADD CONSTRAINT freq_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwfreq(id);


--
-- Name: gloss gloss_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.gloss
    ADD CONSTRAINT gloss_entr_fkey FOREIGN KEY (entr, sens) REFERENCES public.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: gloss gloss_ginf_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.gloss
    ADD CONSTRAINT gloss_ginf_fkey FOREIGN KEY (ginf) REFERENCES public.kwginf(id);


--
-- Name: gloss gloss_lang_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.gloss
    ADD CONSTRAINT gloss_lang_fkey FOREIGN KEY (lang) REFERENCES public.kwlang(id);


--
-- Name: grp grp_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.grp
    ADD CONSTRAINT grp_entr_fkey FOREIGN KEY (entr) REFERENCES public.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: grp grp_kw_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.grp
    ADD CONSTRAINT grp_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwgrp(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: hist hist_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.hist
    ADD CONSTRAINT hist_entr_fkey FOREIGN KEY (entr) REFERENCES public.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: hist hist_stat_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.hist
    ADD CONSTRAINT hist_stat_fkey FOREIGN KEY (stat) REFERENCES public.kwstat(id);


--
-- Name: kanj kanj_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kanj
    ADD CONSTRAINT kanj_entr_fkey FOREIGN KEY (entr) REFERENCES public.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: kinf kinf_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kinf
    ADD CONSTRAINT kinf_entr_fkey FOREIGN KEY (entr, kanj) REFERENCES public.kanj(entr, kanj) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: kinf kinf_kw_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kinf
    ADD CONSTRAINT kinf_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwkinf(id);


--
-- Name: kresolv kresolv_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kresolv
    ADD CONSTRAINT kresolv_entr_fkey FOREIGN KEY (entr) REFERENCES public.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: kwsrc kwsrc_srct_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.kwsrc
    ADD CONSTRAINT kwsrc_srct_fkey FOREIGN KEY (srct) REFERENCES public.kwsrct(id);


--
-- Name: lsrc lsrc_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.lsrc
    ADD CONSTRAINT lsrc_entr_fkey FOREIGN KEY (entr, sens) REFERENCES public.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: lsrc lsrc_lang_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.lsrc
    ADD CONSTRAINT lsrc_lang_fkey FOREIGN KEY (lang) REFERENCES public.kwlang(id);


--
-- Name: misc misc_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.misc
    ADD CONSTRAINT misc_entr_fkey FOREIGN KEY (entr, sens) REFERENCES public.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: misc misc_kw_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.misc
    ADD CONSTRAINT misc_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwmisc(id);


--
-- Name: pos pos_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.pos
    ADD CONSTRAINT pos_entr_fkey FOREIGN KEY (entr, sens) REFERENCES public.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: pos pos_kw_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.pos
    ADD CONSTRAINT pos_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwpos(id);


--
-- Name: rdng rdng_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.rdng
    ADD CONSTRAINT rdng_entr_fkey FOREIGN KEY (entr) REFERENCES public.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: rdngsnd rdngsnd_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.rdngsnd
    ADD CONSTRAINT rdngsnd_entr_fkey FOREIGN KEY (entr, rdng) REFERENCES public.rdng(entr, rdng) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: rdngsnd rdngsnd_snd_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.rdngsnd
    ADD CONSTRAINT rdngsnd_snd_fkey FOREIGN KEY (snd) REFERENCES public.snd(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: restr restr_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.restr
    ADD CONSTRAINT restr_entr_fkey FOREIGN KEY (entr, rdng) REFERENCES public.rdng(entr, rdng) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: restr restr_entr_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.restr
    ADD CONSTRAINT restr_entr_fkey1 FOREIGN KEY (entr, kanj) REFERENCES public.kanj(entr, kanj) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: rinf rinf_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.rinf
    ADD CONSTRAINT rinf_entr_fkey FOREIGN KEY (entr, rdng) REFERENCES public.rdng(entr, rdng) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: rinf rinf_kw_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.rinf
    ADD CONSTRAINT rinf_kw_fkey FOREIGN KEY (kw) REFERENCES public.kwrinf(id);


--
-- Name: sens sens_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.sens
    ADD CONSTRAINT sens_entr_fkey FOREIGN KEY (entr) REFERENCES public.entr(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: snd snd_file_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.snd
    ADD CONSTRAINT snd_file_fkey FOREIGN KEY (file) REFERENCES public.sndfile(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: sndfile sndfile_vol_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.sndfile
    ADD CONSTRAINT sndfile_vol_fkey FOREIGN KEY (vol) REFERENCES public.sndvol(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: sndvol sndvol_corp_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.sndvol
    ADD CONSTRAINT sndvol_corp_fkey FOREIGN KEY (corp) REFERENCES public.kwsrc(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: stagk stagk_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.stagk
    ADD CONSTRAINT stagk_entr_fkey FOREIGN KEY (entr, sens) REFERENCES public.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: stagk stagk_entr_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.stagk
    ADD CONSTRAINT stagk_entr_fkey1 FOREIGN KEY (entr, kanj) REFERENCES public.kanj(entr, kanj) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: stagr stagr_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.stagr
    ADD CONSTRAINT stagr_entr_fkey FOREIGN KEY (entr, sens) REFERENCES public.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: stagr stagr_entr_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.stagr
    ADD CONSTRAINT stagr_entr_fkey1 FOREIGN KEY (entr, rdng) REFERENCES public.rdng(entr, rdng) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: xref xref_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.xref
    ADD CONSTRAINT xref_entr_fkey FOREIGN KEY (entr, sens) REFERENCES public.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: xref xref_kanj_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.xref
    ADD CONSTRAINT xref_kanj_fkey FOREIGN KEY (xentr, kanj) REFERENCES public.kanj(entr, kanj) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: xref xref_rdng_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.xref
    ADD CONSTRAINT xref_rdng_fkey FOREIGN KEY (xentr, rdng) REFERENCES public.rdng(entr, rdng) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: xref xref_typ_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.xref
    ADD CONSTRAINT xref_typ_fkey FOREIGN KEY (typ) REFERENCES public.kwxref(id);


--
-- Name: xref xref_xentr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.xref
    ADD CONSTRAINT xref_xentr_fkey FOREIGN KEY (xentr, xsens) REFERENCES public.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: xresolv xresolv_entr_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.xresolv
    ADD CONSTRAINT xresolv_entr_fkey FOREIGN KEY (entr, sens) REFERENCES public.sens(entr, sens) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: xresolv xresolv_typ_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jmdictdb
--

ALTER TABLE ONLY public.xresolv
    ADD CONSTRAINT xresolv_typ_fkey FOREIGN KEY (typ) REFERENCES public.kwxref(id);


--
-- Name: TABLE vcopos; Type: ACL; Schema: public; Owner: jmdictdb
--

GRANT SELECT ON TABLE public.vcopos TO jmdictdbv;


--
-- PostgreSQL database dump complete
--

