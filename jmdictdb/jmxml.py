# Copyright (c) 2006-2012 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Functions for parsing XML descriptions of entries into
entry objects.
"""

import sys, os, copy, re, datetime
from collections import defaultdict
#import lxml.etree as ElementTree
import xml.etree.cElementTree as ElementTree
  # If debugging, get the dev libs rather than the installed ones.
if __name__ == '__main__':
    _=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
  # Use Python's logging for warning messages to facilitate testing.
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb

class ParseError (RuntimeError): pass
class InvalidError (RuntimeError): pass
class NotFoundError (RuntimeError): pass

def _ent_repl (mo):
        # This func is used in re.sub() calls below to replace all
        # but the standard xml entities with ordinary text strings.
        orig = mo.group(0)
        if orig in ('&lt;','&gt;','&amp;','&quot;'): return orig
        return orig[1:-1]

class JmdictFile:
    # Wrap a standard file object and preprocess the lines being
    # read (expectedly by an XML parser) for three purposes:
    #   1. Keep track of the file line number (for error messages).
    #   2. Since the XML parser doesn't seem to be able to extract
    #      the JMdict creation date comment (because it is outside
    #      of the root element), we do it here.
    #   3. Build a map of the jmdict entities defined in the DTD.
    #   4. Replace jmdict entities with fixed (i.e. non-entity)
    #      text strings of the same value (e.g., "&v5r;" -> "v5r")
    #      It is more convinient to work with the entity string
    #      values than their expanded text values.

    def __init__ (self, source):
        self.source = source;  self.lineno = 0
        self.name = None; self.created=None
    def read (self, bytes):  # 'bytes' argument ignored.
        s = self.source.readline();  self.lineno += 1
        if self.lineno == 1:
            if s[0] == '\uFEFF': s = s[1:]
        s = re.sub (r'&[a-zA-Z0-9-]+;', _ent_repl, s)
        if self.created is None and self.lineno < 400:
            pat = r'<!-- ([a-zA-Z]+) created: (\d{4})-(\d{2})-(\d{2}) -->'
            mo = re.search (pat, s)
            if mo:
                self.name = mo.group(1)
                self.created = datetime.date (*map(int, mo.group(2,3,4)))
        return s

class Jmparser (object):
    '''-----------------------------------------------------------------------
    A class for parsing a JMdict, JMnedict or JMex (a superset of
    the elements in the first two) formatted XML file into a list of
    objects.Entr instances.
    Methods:
    .parse_file() -- A generator that will incrementally parse a full
        XML file, returning an objects.Entr instance on each iteration.
    .parse_entry() -- Parses a string containing concatenated <entry>
        elements returning a list of objects.Entr instances.
    -----------------------------------------------------------------------'''
    def __init__ (self,
            kw,           # A jdb.Kwds object initialized with database
                          #  keywords, such as returned by jdb.dbOpen()
                          #  or jdb.Kwds(jdb.std_csv_dir()).
            xmltype,      # (str) Type of XML: "jmdict", "jmnedict", "jmex".
                          #  This determines the xml format and tags that
                          #  will be recognised by the parser and is used
                          #  as the corpus type when when generating the
                          #  kwsrc table data.
            srcids=True): # (bool) If true, all entries without an explicit
                          #  corpus (jmdict and jmnedict XML) will be
                          #  assigned an entr.src id number like (jmex)
                          #  entries that do have an explicit corpus.
                          #  If false, entries without an explicit corpus
                          #  will be assigned an entr.src value of None.
                          #  This is desirable in tests and other cases
                          #  where the caller will determine the proper
                          #  value.
        L('jmxml').debug("module: %s" % __file__)
        self.KW = kw
        if xmltype == 'jmex': self.XKW = self.KW
        else: self.XKW = make_enttab (self.KW, xmltype)
        self.seq = 0  #FIXME? sequence numbers are per-corpus so maintaining
          # a single stream of numbers here will do the wrong thing in the
          # presence of jmex XML which mixes multiple corpora.  On the other
          # hand jmex XML always contains embedded sequence numbers so it
          # should never need sequence number generation.
        self.corpora = {}
        self.srcids = srcids

    def parse_entry (self, txt):
        # Convert an XML text string into entry objects.
        # Parameters:
        #   txt -- (str) XML text defining one of more entry elements.
        # Returns: A list of entry objects.

        pat = '&[a-zA-Z0-9-]+;'
        if isinstance (txt, bytes): pat = pat.encode ('latin1')
        txt = re.sub (pat, _ent_repl, txt)
        xo = ElementTree.XML (txt)
        if xo is None:
            print ("No parse results")
            return []
        e = self.do_entr (xo, None)
        return [e]

    def parse_file (self,  # Parse a full JMdict/JMnedict XML file.
        inpf,           # (file) An open jmdict/jmnedict XML file.
        startseq=None,  # (int) Skip until an entry with this seq
                        #   number is seen, or None to start at first
                        #   entry.  See also parameters seqnum_init
                        #   and seqnum_incr below.
        elimit=None,    # (int) Maximum number of entries to process.
        xlang=None,     # (list) List of lang id's to limit extracted
                        #   glosses to.
        grpdefs=None,   # (dict) A mapping that contains grpdef (aka
                        #   "kwgrp") records indexed by id number and
                        #   name.  <group> elements will be looked
                        #   up in this dict.  If not supplied, it is
                        #   expected that <grpdef> elements will occur
                        #   in the XML that define corpora before they
                        #   are referenced by <group> elements.
        toptag=False,   # (bool) Make first item returned by iterator
                        #   a string giving the name of the top-level
                        #   element.
        seqnum_init=1,  # If an entry does not contain a <ent_seq> tag
        seqnum_incr=1): #   giving its sequence number, calculate a
                        #   seq number for it from the formula:
                        #     seqnum_init + (seqnum_incr * entrnum)
                        #   where entrnum is the ordinal position of
                        #   the entry in the file, starting at 0.  For
                        #   example, to get jmdict-like sequence numbers
                        #   use seqnum_init=1000000 and seqnum_incr=10.

        etiter = iter(ElementTree.iterparse( inpf, ("start","end")))
        event, root = next(etiter)
        if toptag: yield 'root', root.tag
        if grpdefs is None: grpdefs = {}
        elist=[];  count=0;  entrnum=0
        for event, elem in etiter:

            if elem.tag not in ['entry', 'grpdef']: continue

            if event == "start":
                lineno = getattr (inpf, 'lineno', None)
                if elem.tag == 'entry': entrnum += 1
                continue

              # At this point elem.tag must be either 'entry' or 'grpdef'
              #  and event is 'end'.
            if elem.tag == 'grpdef':
                grpdef = self.do_grpdef (elem)
                grpdefs[grpdef.id] = grpdefs[grpdef.kw] = grpdef
                yield "grpdef", grpdef
                continue

              # From this point on elem.tag is 'entr'...
            prevseq = self.seq
              # Old-style (pre 2014-10) jmnedict xml does not have "ent_seq"
              # elements so we will generate a synthetic seq_number based on
              # the ordinal position of the entry in the file ('entrnum').
            self.seq = seq = int (elem.findtext ('ent_seq')
                                  or ((entrnum-1) * seqnum_incr + seqnum_init))
            if prevseq and seq <= prevseq:
                self.warn (" (line %d): Sequence less than preceeding sequence"
                           % lineno)
            if not startseq or seq >= startseq:
                startseq = None
                try: entr = self.do_entr (elem, seq, xlang, grpdefs)
                except ParseError as e:
                    self.warn (" (line %d): %s" % (lineno, e))
                else: yield "entry", entr
                count += 1
                if elimit and count >= elimit: break
            root.clear()

    def do_grpdef (self, elem):
        o = jdb.Obj (id=int(elem.get('id')), kw=elem.findtext ('gd_name'))
        descr = elem.findtext ('gd_descr')
        if descr: o.descr = descr
        return o

    def do_entr (self, elem, seq, xlang=None, grpdefs=None):
        """
    Create an entr object from a parsed ElementTree entry
    element, 'elem'.  'lineno' is the source file line number
    of the "<entry>" line or None and is only used in error
    messages.

    Note that the entry object returned is different from one
    read from the database in the following respects:
    * The 'entr' record will have no .src (aka corpus) attribute
      if there is no <ent_corp> element in the entry.  In this
      case the .src attribute is expected to be added by the
      caller.
    * Items in sense's _xref list are unresolved xrefs, not
      resolved xrefs as in a database entr object.
      jdb.resolv_xref() or similar can be used to resolve the
      xrefs.
    * Attributes will be missing if the corresponding xml
      information is not present.  For example, if a particular
      entry has no <ke_ele> elements, the entr object will not
      have a '._kanj' attribute.  In an entr object read from
      the database, it will have a '._kanj' attribute with a
      value of [].
    * The entr object does not have many of the foreign key
      attributes: gloss.gloss, xref.xref, <anything>.entr, etc.
      However, it does have rdng.rdng, kanj.kanj, and sens.sens
      attributes since these are required when adding restr,
      stagr, stagk, and freq objects.
        """
        KW = self.KW

        entr = jdb.Entr ()

        if not seq:
            elemseq = elem.find ('ent_seq')
            if elemseq is None: raise ParseError ("No <ent_seq> element found")
            try: seq = int (elemseq.text)
            except ValueError:
                raise ParseError ("Invalid 'ent_seq' value, '%s'" % elem.text)
        if seq <= 0:
            raise ParseError ("Invalid 'ent_seq' value, '%s'" % elem.text)
        self.seq = entr.seq = seq

        id = elem.get('id')
        if id is not None: entr.id = entr.idx = int (id)
        dfrm = elem.get('dfrm')
        if dfrm is not None: entr.dfrm = int (dfrm)
        stat = elem.get('stat') or jdb.KW.STAT['A'].id
        try: stat = KW.STAT[stat].id
        except KeyError:
            raise ParseError ("Invalid <status> element value, '%s'" % stat)
        entr.stat = stat
        entr.unap = xmlbool (elem.get('unap'))
          # Get the corpus name and type.  These will have non-None values
          # only for "jmex" XML.
        corp, corpt = elem.get('corpus'), elem.get('type')
          # Get a srcid number for the pair.
        srcid = self.do_corpus_attrs (corp, corpt)
          # We leave entr.src set to None if there is no explicit corpus
          # name and supression of srcids was requested (eg when parsing
          # entries for tests of the caller wants to manage the srcids.)
        if corp or self.srcids: entr.src = srcid
          #FIXME: check contents of <ent_corp> element for condistency
          # with the corpus attributes just processed or use as def if
          # attributes not present.
        #corpname = elem.findtext('ent_corp')
        self.do_kanjs (elem.findall('k_ele'), entr)
        self.do_rdngs (elem.findall('r_ele'), entr)
        self.do_senss (elem.findall('sense'), entr, xlang)
        self.do_senss (elem.findall('trans'), entr, xlang)
        self.do_info  (elem.findall("info"), entr)
        self.do_audio (elem.findall("audio"), entr, jdb.Entrsnd)
        self.do_groups(elem.findall("group"), entr, grpdefs)
        return entr

    def do_corpus_attrs (self, corp, corpt):
        '''-------------------------------------------------------------------
        Assign an id number for entr.src and stash away a corresponding
        corpus record for use in kwsrc.
        The JMex format adds two attributes to <entry> tags: "corpus"
        and (corpus) "type".  We process them by creating a local record
        of each distict "corpus" name seen.  Each is assigned a value
        consisting of a 2-tuple of the "type" value and an integer that
        id that is assigned to Entr() object's .src attribute.

        In the case of non-jmex format xml (eg jmdict and jmnedict whos
        DTDs have no provision for a corpus identifier) the assigned .src
        id number is None.
        -------------------------------------------------------------------'''
        if corp in self.corpora:
              # If that named corpus has been already seen but with a
              # different corpus type, that's a no-no.  Note that 'corp'
              # will be None for jmdict and jmnedict entries and may
              # be None for jmex entries sometimes (eg tests).
            if corpt and corpt != self.corpora[corp][0]:
                raise InvalidError ("Corpus %s type change from %s to %s"
                                    % (corp, self.corpora[corpt][0], corpt))
        else:
              # First time this corpus name has been seen.
              # Save the name and type, along with a sequentially increasing
              # id number.  'corp' and/or 'corpt' may be None, that's ok.
              # We also assign an id number which may be used for entr.src.
              # This number will be one greater than the largest number
              # already assigned.  Note that these id values will be adjusted
              # when the data is imported into a database.
            srcids = [srcid for corp,(ctype,srcid) in self.corpora.items()]
            srcid = 1 + max (srcids or [0])
            self.corpora[corp] = (corpt, srcid)
        return self.corpora[corp][1]  # Return the assigned corpus id number.

    def get_corpora (self):
        "Return the corpora info keyed by id number."
        return 

    def do_info (self, elems, entr):
        if not elems: return
        elem = elems[0]   # DTD allows only one "info" element.
        x = elem.findtext ('srcnote')
        if x: entr.srcnote = x
        x = elem.findtext ('notes')
        if x: entr.notes = x
        self.do_hist (elem.findall("audit"), entr)

    def do_kanjs (self, elems, entr):
        if elems is None: return
        kanjs = []; dupchk_keb = {}
        for ord, elem in enumerate (elems):
            txt = elem.find('keb').text
            if not jdb.unique (txt, dupchk_keb):
                self.warn ("Duplicate keb text: '%s'" % txt)
                continue
            if not (jdb.jstr_keb (txt)):
                self.warn ("keb text '%s' not kanji." % txt)
            kanj = jdb.Kanj (kanj=ord+1, txt=txt)
            self.do_kws (elem.findall('ke_inf'), kanj, '_inf', 'KINF')
            dupchk_freq = {}
            for x in elem.findall ('ke_pri'):
                fkw, fval = self.parse_freq (x.text, "ke_pri")
                if not fkw: continue
                if not jdb.unique ((fkw, fval), dupchk_freq):
                    self.freq_warn ("Duplicate", None, kanj, x.text)
                    continue
                kanj._freq.append (jdb.Freq(kw=fkw, value=fval))
            kanjs.append (kanj)
        if kanjs: entr._kanj = kanjs

    def do_rdngs (self, elems, entr):
        if elems is None: return
        rdngs = getattr (entr, '_rdng', [])
        kanjs = getattr (entr, '_kanj', [])
        rdngs = []; dupchk_reb = {}
        for ord, elem in enumerate (elems):
            txt = elem.find('reb').text
            if not jdb.unique (txt, dupchk_reb):
                self.warn ("Duplicate reb text: '%s'" % txt)
                continue
            if not jdb.jstr_reb (txt):
                self.warn ("reb text '%s' not kana." % txt)
            rdng = jdb.Rdng (rdng=ord+1, txt=txt)
            self.do_kws (elem.findall('re_inf'), rdng, '_inf', 'RINF')
            dupchk_freq = {}
            for x in elem.findall ('re_pri'):
                fkw, fval = self.parse_freq (x.text, "re_pri")
                if not fkw: continue
                if not jdb.unique ((fkw, fval), dupchk_freq):
                    self.freq_warn ("Duplicate", rdng, None, x.text)
                    continue
                rdng._freq.append (jdb.Freq(kw=fkw, value=fval))
            nokanji = elem.find ('re_nokanji')
            self.do_restr (elem.findall('re_restr'),
                           rdng, kanjs, 'restr', nokanji)
            self.do_audio (elem.findall("audio"), rdng, jdb.Rdngsnd)
            rdngs.append (rdng)
        if rdngs: entr._rdng = rdngs

    def do_senss (self, elems, entr, xlang=None, prop_pos=False):
        KW = self.KW
        rdngs = getattr (entr, '_rdng', [])
        kanjs = getattr (entr, '_kanj', [])
        senss = [];  last_pos = None
        for ord, elem in enumerate (elems):
            sens = jdb.Sens (sens=ord+1)
            snotes = elem.find ('s_inf')
            if snotes is not None and snotes.text: sens.notes = snotes.text

            pelems = elem.findall('pos')
            if pelems:
                last_pos = self.do_kws (pelems, sens, '_pos', 'POS')
              # 'prop_pos' enables the propagation of a preceeding sense's
              # PoS tags to the following sense when the latter has none.
              # Very early JMdict XML files used that convention but it
              # hasn't been used for long long time now thus we disable
              # it by default and there is currently no API capability to
              # enable it but we leave the code here in case a need arises
              # in the future.
            elif prop_pos and last_pos:
                sens._pos = [jdb.Pos(kw=x.kw) for x in last_pos]

            self.do_kws   (elem.findall('name_type'), sens, '_misc',
                                                        'MISC', 'NAME_TYPE')
            self.do_kws   (elem.findall('misc'),      sens, '_misc', 'MISC')
            self.do_kws   (elem.findall('field'),     sens, '_fld',  'FLD')
            self.do_kws   (elem.findall('dial'),      sens, '_dial', 'DIAL')
            self.do_lsrc  (elem.findall('lsource'),   sens,)
            self.do_gloss (elem.findall('gloss'),     sens, xlang)
            self.do_gloss (elem.findall('trans_det'), sens,)
            self.do_restr (elem.findall('stagr'),     sens, rdngs, 'stagr')
            self.do_restr (elem.findall('stagk'),     sens, kanjs, 'stagk')
            self.do_xref  (elem.findall('xref'),  sens, jdb.KW.XREF['see'].id)
            self.do_xref  (elem.findall('ant'),   sens, jdb.KW.XREF['ant'].id)

            if not getattr (sens, '_gloss', None):
                self.warn ("Sense %d has no glosses." % (ord+1))
            senss.append (sens)
        if senss: entr._sens = senss

    def do_gloss (self, elems, sens, xlang=None):
        KW = self.KW
        glosses=[]; dupchk={}
        for elem in elems:
            lang = KW.LANG['eng'].id    # Default value
            ginf = KW.GINF['equ'].id    # Default value
            for attr in elem.keys():
                v = elem.get (attr)
                if attr == '{http://www.w3.org/XML/1998/namespace}lang':
                    try: lang = KW.LANG[v].id
                    except KeyError:
                        self.warn ("Invalid gloss lang attribute: '%s'" % v)
                        continue
                elif attr == "g_type":
                    try: ginf = KW.GINF[v].id
                    except KeyError:
                        self.warn ("Invalid gloss g_type attribute: '%s'" % v)
                        continue
                else:
                    self.warn ("Unknown gloss attribute: %s" % attr)
            txt = elem.text
            if not jdb.jstr_gloss (txt):
                self.warn ("gloss text '%s' not latin characters." % txt)
            if not jdb.unique ((lang,txt), dupchk):
                self.warn ("Duplicate lang/text in gloss '%s'/'%s'"
                           % (KW.LANG[lang].kw, txt))
                continue
            # (entr,sens,gloss,lang,txt)
            if txt and (not xlang or lang in xlang):
                glosses.append (jdb.Gloss (lang=lang, ginf=ginf, txt=txt))
        if glosses:
            if not hasattr (sens, '_gloss'): sens._gloss = []
            sens._gloss.extend (glosses)

    def do_lsrc (self, elems, sens):
        lsrc = [];
        for elem in elems:
            txt = elem.text or ''
            lng = elem.get ('{http://www.w3.org/XML/1998/namespace}lang')
            try: lang = self.KW.LANG[lng].id if lng else self.KW.LANG['eng'].id
            except KeyError:
                self.warn ("Invalid lsource lang attribute: '%s'" % lng)
                continue
            lstyp = elem.get ('ls_type')
            if lstyp and lstyp != 'part':
                self.warn ("Invalid lsource type attribute: '%s'" % lstyp)
                continue
            wasei = elem.get ('ls_wasei') is not None
            lsrc.append (jdb.Lsrc (lang=lang, txt=txt,
                                   part=lstyp=='part', wasei=wasei))
        if lsrc:
            if not hasattr (sens, '_lsrc'): sens._lsrc = []
            sens._lsrc.extend (lsrc)

    def do_xref (self, elems, sens, xtypkw):
          # Create a xresolv record for each xml <xref> element.  The xref
          # may contain a kanji string, kana string, or kanji.\x{30fb}kana.
          # (\x{30fb} is a mid-height dot.)  It may optionally be followed
          # by a \x{30fb} and a sense number.
          # Since jmdict words may also contain \x{30fb} as part of their
          # kanji or reading text we try to handle that by ignoring the
          # \x{30fb} between two kana strings, two kanji strings, or a
          # kana\x{30fb}kanji string.  Of course if a jmdict word is
          # kanji\x{30fb}kana then we're out of luck; it's ambiguous.

        xrefs = []
        for elem in elems:
            txt = elem.text

              # Split the xref text on the separator character.

            frags = txt.split ("\u30fb")

              # Check for a sense number in the rightmost fragment.
              # But don't treat it as a sense number if it is the
              # only fragment (which will leave us without any kana
              # or kanji text which will fail when loading xresolv.

            snum = None
            if len (frags) > 0 and frags[-1].isdigit():
                snum = int (frags.pop())

              # Go through all the fragments, from right to left.
              # For each, if it has no kanji, push it on the @rlst
              # list.  If it has kanji, and every fragment thereafter
              # regardless of its kana/kanji status, push on the @klst
              # list.  $kflg is set to true when we see a kanji word
              # to make that happen.
              # We could do more checking here (that entries going
              # into @rlst are kana for, example) but don't bother
              # since, as long as the data loads into xresolv ok,
              # wierd xrefs will be found later by being unresolvable.

            klst=[];  rlst=[];  kflg=False
            for frag in reversed (frags):
                if not kflg: jtyp = jdb.jstr_classify (frag)
                if kflg or jtyp & jdb.KANJI:
                    klst.append (frag)
                    kflg = True
                else: rlst.append (frag)

              # Put the kanji and kana parts back together into
              # strings, and write the xresolv record.

            ktxt = "\u30fb".join (reversed (klst)) or None
            rtxt = "\u30fb".join (reversed (rlst)) or None

            if ktxt or rtxt:
                xrefs.append (jdb.Xrslv (typ=xtypkw, ktxt=ktxt,
                                         rtxt=rtxt, tsens=snum))
        if xrefs:
            for n, x in enumerate (xrefs): x.ord = n + 1
            if not hasattr (sens, '_xrslv'): sens._xrslv = []
            sens._xrslv.extend (xrefs)

    def do_hist (self, elems, entr):  # Process <audit> element.
        KW = self.KW
        hists = []
        for elem in elems:
            dt = elem.get ('time')
              # The 'time" attribute is supposed to be formatted as
              # "YYYY-MM-DD hh:mm:ss" but the following will work with
              # date only, and/or time with fractional seconds.
            dtparts = (re.split (r'[ :.-]', dt)[:6] + [0,0,0])[:6]
            dt = datetime.datetime (*[int(x) for x in dtparts])
            stat = elem.get ('stat')
            stat = KW.STAT[stat].id if stat else KW.STAT['A'].id
            unap = xmlbool (elem.get ('unap'))
            o = jdb.Hist (dt=dt, stat=stat, unap=unap)
            o.userid = elem.findtext ("upd_uid") or None
            o.name = elem.findtext ("upd_name") or None
            o.email = elem.findtext ("upd_email") or None
            o.notes = elem.findtext ("upd_detl") or None
            o.refs = elem.findtext ("upd_refs") or None
            o.diff = elem.findtext ("upd_diff") or None
            hists.append (o)
        if hists:
            if not hasattr (entr, '_hist'): entr._hist = []
            entr._hist.extend (hists)

    def do_groups (self, elems, entr, grpdefs):
        grps = []
        for elem in elems:
            txt = elem.text
            try: grpdefid = grpdefs[txt].id
            except KeyError:
                self.warn ("Unrecognised group text '%s'." % txt)
                continue
            ordtxt = elem.get ('ord')
            if not ordtxt:
                self.warn ("Missing group 'ord' attribute "
                           "on group element '%s'." % (txt))
                continue
            try: ord = int (ordtxt)
            except (ValueError, TypeError):
                self.warn ("Invalid 'ord' attribute '%s' "
                           "on group element '%s'." % (ordtxt, txt))
                continue
            grps.append (jdb.Grp (kw=grpdefid, ord=ord))
        if grps:
            if not getattr (entr, '_grp', None): entr._grp = grps
            else: exnt._grps.extend (grps)

    def do_audio (self, elems, entr_or_rdng, sndclass):
        snds = []
        for n, elem in enumerate (elems):
            v =elem.get ('clipid')
            if not v:
                self.warn ("Missing audio clipid attribute."); continue
            try: clipid = int (v.lstrip('c'))
            except (ValueError, TypeError):
                self.warn ("Invalid audio clipid attribute: %s" % v)
            else:
                snds.append (sndclass (snd=clipid, ord=n+1))
        if snds:
            if not hasattr (entr_or_rdng, '_snd'): entr_or_rdng._snd = []
            entr_or_rdng._snd.extend (snds)

    def do_kws (self, elems, obj, attr, kwtabname, elemname=None):
        '''-------------------------------------------------------------------
        Extract the keywords in the elementtree elements 'elems',
        resolve them in kw table 'kwtabname', and append them to
        the list attached to 'obj' named 'attr'.

        elems -- List of XML elements containing keywords.
        obj -- Instance of one of the objects.* classes that the
          resolved tags will be attached to, e.g., a Sens() instance
          for MISC tags.
        attr -- The attribute name of the list on 'obj' that will
          contain the keyword objects, e.g., "_misc".
        kwtabname -- Name of domain of keywords in Kwds, e.g. "MISC".
        elemname -- Name of the XML element keywords are used in if
          different (ignoring case) than 'kwtabname', e.g., (for
          jmnedict) "NAME_TYPE".  This is used only for error messages.
        -------------------------------------------------------------------'''

        if elems is None or len(elems) == 0: return None
        kwtab = getattr (self.XKW, kwtabname)
        if elemname is None: elemname = kwtabname
        kwtxts, dups = jdb.rmdups ([x.text for x in elems])
        cls = getattr (jdb, kwtabname.capitalize())
        kwrecs = []
        for x in kwtxts:
            try: kw = kwtab[x].id
            except KeyError:
                self.warn("Unknown %s keyword '%s'" % (elemname,x))
            else:
                kwrecs.append (cls (kw=kw))
        dups, x = jdb.rmdups (dups)
        for x in dups:
            self.warn ("Duplicate %s keyword '%s'" % (elemname, x))
        if kwrecs:
            if not hasattr (obj, attr): setattr (obj, attr, [])
            getattr (obj, attr).extend (kwrecs)
        return kwrecs

    def do_restr (self, elems, rdng, kanjs, rtype, nokanji=None):
        """
        The function can be used to process stagr and stagk restrictions
        in addition to re_restr restrictions, but for simplicity, code
        comments and variable names assume re_restr processing.

            elems -- A list of 're_restr' xml elements (may be empty).
            rtype -- One of: 'restr', 'stgr', stagk', indicating the type
                    of restrictions being processed.
            rdng -- If 'rtype' is "restr", a Rdng object, otherwise a Sens
                    object.
            kanjs -- If 'rtype' is "restr" or "stagk", the entry's list
                    of Kanj objects.  Otherwise, the entry's list of Rdng
                    objects.
            nokanji -- True if the rtype in "restr" and the reading has a
                    <no_kanji> element, false otherwise.

        Examples:
        To use for restr restrictions:
            do_restrs (restr_elems, entr._rdng, entr._kanj, "restr", nokanji)

        or stagr restrictions:
            do_restrs (stagr_elems, entr._sens, entr._rdng, "stagr")

        or stagk restrictions:
            do_restrs (stagk_elems, entr._sens, entr._kanj, "stagk")
        """

        if   rtype == 'restr': rattr, kattr, pattr = 'rdng', 'kanj', '_restr'
        elif rtype == 'stagr': rattr, kattr, pattr = 'sens', 'rdng', '_stagr'
        elif rtype == 'stagk': rattr, kattr, pattr = 'sens', 'kanj', '_stagk'

          # Warning, do not replace the 'nokanji is None' tests below
          # with 'not nokanji'.  'nokanji' may be an elementtree element
          # which can be False, even if not None.  (See the element tree
          # docs.)

        if not elems and nokanji is None: return
        if elems and nokanji is not None:
            self.warn ("Conflicting 'nokanji' and 're_restr' in reading %d."
                       % rdng.rdng)
        if nokanji is not None: allowed_kanj = None
        else:
            allowed_kanj, dups = jdb.rmdups ([x.text for x in elems])
            if dups:
                self.warn ("Duplicate %s item(s) %s in %s %d."
                        % (pattr[1:], "'"+"','".join(dups)+"'",
                           rattr, getattr (rdng,rattr)))
        jdb.txt2restr (allowed_kanj, rdng, kanjs)

    def parse_freq (self, fstr, ptype):
        # Convert a re_pri or ke_pri element string (e.g "nf30") into
        # numeric (id,value) pair (like 4,30) (4 is the id number of
        # keyword "nf" in the database table "kwfreq", and we get it
        # by looking it up in JM2ID (from jmdictxml.pm). In addition
        # to the id,value pair, we also return keyword string.
        # $ptype is a string used only in error or warning messages
        # and is typically either "re_pri" or "ke_pri".

        KW = self.KW
        mo = re.match (r'^([a-z]+)(\d+)$', fstr)
        if not mo:
            self.warn ("Invalid %s, '%s'" % (ptype, fstr))
            return None, None
        kwstr, val = mo.group (1,2)
        try: kw = KW.FREQ[kwstr].id
        except KeyError:
            self.warn ("Unrecognised %s, '%s'" % (ptype, fstr))
            return None, None
        val = int (val)
        #FIXME -- check for invalid values in 'val'.
        return kw, val

    def freq_warn (self, warn_type, r, k, kwstr):
        tmp = []
        if r: tmp.append ("reading %s" % r.txt)
        if k: tmp.append ("kanji %s" % k.txt)
        self.warn ("%s pri value '%s' in %s"
                % (warn_type, kwstr, ', '.join (tmp)))

    def warn (self, msg):
        L('jmxml').warn("Seq %d: %s" % (self.seq, msg))

def make_enttab (KW, dtd):
        '''-------------------------------------------------------------------
        Make a copy of jdb.Kwds instance 'KW' modified so that the
        included kw records are appropriate for the processing the
        entities in XML of type 'dtd' ("jmdict' or "jmnedict").  For
        example, the .MISC[15].kw value for jmdict is "male" but for
        jmnedict is "masc".  .MISC[17] ("obs") is present for jmdict
        but missing for jmnedict because it is a valid entity in the
        former but not in the latter.  The records in the 'KW' copy
        are modified/deleted based on the information in the .ents
        item in each record.
        -------------------------------------------------------------------'''

          #FIXME: allow for dtd=="jmex".
        kwds = copy.deepcopy (KW)
        for attr in KW.Tables.keys():
           kwtab = getattr (kwds, attr)
           for r in kwds.recs (attr):
               ent = (getattr (r,'ents',{}) or {}).get (dtd, None)
                 # If the dtd is "jmdict" we assume all kw recs are
                 # applicable unless overridden by a ents["jmdict"]
                 # item.  Thus we can skip any further processing (to
                 # delete or modify a rec) for dtd=="jmdict" if there
                 # is no 'ent' value or if there is but it contains no
                 # no "jmdict' item.
               if dtd=='jmdict' and ent is None: continue
               if not isinstance (ent, dict):
                     # If 'ent' is a scalar (not a dict) then its bool
                     # determines whether the record shoulbe be included
                     # or not; since the record is alerady present we
                     # delete it if 'ent' is not true.
                     # Note that if 'ent' is None by virtue of it not
                     # being present in .ents at all, it is also deleted.
                     # Only when dtd=="jmdict" are recs kept by default.
                   if not ent: kwds.upd (attr, r.id)
               else:   # 'ent' is a dict() whose 'e' item if present gives
                     # and alternative entity name, 'v' item if present
                     # gives and alternative entity value.
                   id, kw, descr = r.id, None, None
                   if 'e' in ent: kw = ent['e']
                   if 'v' in ent: descr = ent['v']
                   if kw or descr: kwds.upd (attr, id, kw, descr)
                   else:   # An empty dict is not allowed.
                       m = "KW table %s (%s,'%s'): %s:"\
                           "must have a 'e' or 'v' item."\
                           % (attr, r.id, r.kw, dtd)
                       raise ValueError (m)
        return kwds

def sniff (filename):
        """
        Guess if a file contains JMdict, JMnedict, or Jmex entries.
        """
        with open (filename) as f: data = f.read (21000)
        jmex = jmdict = jmnedict = sense_seen = trans_seen = 0
        for ln in data.splitlines():
            if '<!DOCTYPE JMex'     in ln: jmex += 1
            if '<!DOCTYPE JMdict'   in ln: jmdict += 1
            if '<!DOCTYPE JMnedict' in ln: jmnedict += 1
            if '<JMex>'             in ln: jmex += 1
            if '<JMdict>'           in ln: jmdict += 1
            if '<JMnedict>'         in ln: jmnedict += 1
            if '<sense>' in ln and not sense_seen: sense_seen = True
            if '<trans>' in ln and not trans_seen: trans_seen = True
        if jmex and not jmdict and not jmnedict and not trans_seen:
            return 'jmex'
        if jmnedict and not jmdict and not jmex and not sense_seen:
            return 'jmnedict'
        if jmdict and not jmnedict and not jmex and not trans_seen:
            return 'jmdict'
        return None

def crossprod (*args):
        """
        Return the cross product of an arbitrary number of lists.
        """
        # From http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/159975
        result = [[]]
        for arg in args:
            result = [x + [y] for x in result for y in arg]
        return result

def extract (fin, seqs_wanted, dtd=False, fullscan=False, keepends=False):
        """
        Returns an iterator that will return the text lines in
        xml file 'fin' for the entries given in 'seqs_wanted'.

        Each call (of the iterator's next() method) will return
        a 2-tuple: the first item is the seq number of the entry
        and the second item is list of text lines the comprise
        the entry.  The lines are exactly as read from 'fin'
        (i.e. if 'fin'in a standard file object, the lines
        will have the encoding of the file (typically utf-8)
        and contain line terminators ('\n').  Entries are returned
        in the order they are encountered in the input file,
        regardless of the order given in 'seq_wanted'.  Comments
        within an entry will returned as part of that entry, but
        comments between entries are inaccessible.

        If the 'dtd' parameter is true, the first call will return
        a 2-tuple whose first item is a string naming the root tag
        (typically "JMdict" or JMnedict"; it is needed by the caller
        so that a correct closing tag can be written), and a list
        of the lines of the input file's DTD.

        Note that this function does *not* actually parse the xml;
        it relies on the lexical characteristics of the jmdict and
        jmnedict files (an entry tag occurs alone on a line, that
        an ent_seq element is on a single line, etc) for speed.
        If the format of the jmdict files changes, it is likely
        that this will fail or return erroneous results.

        TO-DO: document those assumtions.

        If a requested seq number is not found, a NotFoundError will
        be raised after all the found entries have been returned.

        fin -- Open file object for the xml file to use.

        seq_wanted -- A list of intermixed jmdict seq numbers or
            seq number/count pairs (tuple or list).  The seq number
            value indentifies the entry to return.  The count value
            gives the number of successive entries including seq
            number to return.  If the count is not given, 1 is
            assumed.  Entries  will be returned in the order found,
            not the order they occur in 'seq-wanted'.

        dtd -- If true, the first returned value will be a 2-tuple.
            The first item in it will be a list containng the text
            lines of the DTD in the input file (if any).  The second
            item is a single text string that is the line containing
            the root element (will be "<JMdict>\n" for a standard
            JMdict file, or "<JMnedict>\n" to the entries extracted.

        fullscan -- Normally this function assumes the input file
           entries are in ascending seq number order, and after it
           sees a sequence number greater that the highest seq number
           in 'seq_wanted', it will stop scanning and report any
           unfound seq numbers.  If the input file entries are not
           ordered, it may be necessary to use 'fullscan' to force
           scanning to the end of the file to find all the requested
           entries. This can take a long time for large files.

        keepends -- retain any trailing whitespace.
        """

          # Break the seqs_wanted listed into two lists: a list of
          # the sequence numbers, sorted in ascending order, and a
          # equal length list of the corresponding counts.  The
          # try/except below is to catch the failure of "len(s)"
          # which will happen if 's' is a seq number rather than
          # a (seq-number, count) pair.
        tmp = []
        for s in seqs_wanted:
            try:
                if len(s) == 2:  sv, sc = s
                elif len(s) == 1: sv, sc = s[0], 1
                else: raise ValueError (s)
            except TypeError:
                sv, sc = int(s), 1
            tmp.append ((sv, sc))
        tmp.sort (key=lambda x:x[0])
        seqs = [x[0] for x in tmp];  counts = [x[1] for x in tmp]

        scanning='in_dtd';  seq=0;  lastseq=None;  toplev=None;
        rettxt = [];  count=0;
        for line in fin:

              # The following "if" clauses are in order of frequency
              # of being true for efficiency.

            if scanning == 'copy' or  scanning == 'nocopy':
                if scanning == 'copy':
                      #FIXME? should we strip() when keepends is true?
                    if keepends: rettxt.append (line.strip())
                    else: rettxt.append (line.rstrip())
                if line.lstrip().startswith ('</entry>'):
                    if count <= 0 \
                          and (not seqs or (seqs[-1] < seq and not fullscan)):
                        break
                    if count > 0:
                        yield seq, rettxt;  rettxt = []
                    scanning = 'between_entries'
                    lastseq = seq

            elif scanning == 'between_entries':
                if line.lstrip().startswith ('<entry>'):
                    entryline = line
                    scanning = 'in_entry'

            elif scanning == 'in_entry':
                ln = line.lstrip()
                if ln.startswith ('<ent_seq>'):
                    n = ln.find ('</ent_seq>')
                    if n < 0:
                        raise IOError ('Invalid <ent_seq> element, line %d',
                                       lnnum)
                    seq = int (ln[9:n])
                else:
                    seq += 1  # Old-style (pre 2014-10) JMnedict has no seq
                              #  numbers, so just count entries.
                count = wanted (seq, seqs, counts, count)
                if count > 0:
                    if keepends:
                        rettxt.append (entryline)
                        rettxt.append (line)
                    else:
                        rettxt.append (entryline.rstrip())
                        rettxt.append (line.rstrip())
                    scanning = 'copy'
                else: scanning = 'nocopy'

            elif scanning == 'in_dtd':
                if dtd:
                    if keepends: rettxt.append (line)
                    else: rettxt.append (line.rstrip())
                ln = line.strip()
                if ln.lstrip() == "]>":
                    scanning = 'after_dtd'

            elif scanning == 'after_dtd':
                ln = line.strip()
                if len(ln) > 2 and ln[0] == '<' and ln[1] != '!':
                    if dtd:
                        toplev = line.strip()[1:-1]
                        yield toplev, rettxt;  rettxt = []
                    scanning = 'between_entries'

            else:
                raise ValueError (scanning)

        if seqs:
            raise NotFoundError ("Sequence numbers not found", seqs)

def wanted (seq, seqs, counts, count):
        """ Helper function for extract().
        Return the number of entries to copy."""

        if count > 0: count -= 1
        s = 0
        for n, s in enumerate (seqs):
            if s >= seq: break
        if s == seq:
            count = max (counts[n], count)
            del seqs[n]; del counts[n]
        return count

def parse_sndfile (
        inpf,           # (file) An open sound clips XML file..
        toptag=False):  # (bool) Make first item retuned by iterator
                        #   a string giving the name of the top-level
                        #   element.

        etiter = iter(ElementTree.iterparse( inpf, ("start","end")))
        event, root = next(etiter)
        vols = []
        for event, elem in etiter:
            tag = elem.tag
            if tag not in ('avol','asel','aclip'): continue
            if event == 'start': lineno = inpf.lineno; continue
            if   tag == 'aclip': yield do_clip (elem), 'clip', lineno
            elif tag == 'asel':  yield do_sel (elem), 'sel', lineno
            elif tag == 'avol':  yield do_vol (elem), 'vol', lineno

def do_vol (elem):
        return jdb.Sndvol (id=int(elem.get('id')[1:]),
                           title=elem.findtext('av_title'),
                           loc=elem.findtext('av_loc'),
                           type=elem.findtext('av_type'),
                           idstr=elem.findtext('av_idstr'),
                           corp=elem.findtext('av_corpus'),
                           notes=elem.findtext('av_notes'))

def do_sel (elem):
        return jdb.Sndfile (id=int(elem.get('id')[1:]),
                            vol=int(elem.get('vol')[1:]),
                            title=elem.findtext('as_title'),
                            loc=elem.findtext('as_loc'),
                            type=elem.findtext('as_type'),
                            notes=elem.findtext('as_notes'))

def do_clip (elem):
        return jdb.Snd (id=int(elem.get('id')[1:]),
                        file=int(elem.get('sel')[1:]),
                        strt=int(elem.findtext('ac_strt')),
                        leng=int(elem.findtext('ac_leng')),
                        trns=elem.findtext('ac_trns'),
                        notes=elem.findtext('ac_notes'))

def xmlbool (value):
        if not value: return False
        v = value.lower()
        try: return {"false":False, "0":False, "true":True, "1":True}[v]
        except KeyError:
            raise ValueError ("Illegal XML boolean value: %s" % value)

def main():
        from jmdictdb import fmtxml
        jdb.KW = jdb.Kwds ('')
        if len(sys.argv) not in (2,3): sys.exit (
            'Usage: %s: [xmltype] xml-filename\n'
            '  xmltype: one of "jmdict", jmnedict", "jmex"\n'
            '  xml-filename: name of XML file to parse. The entries must be\n'
            '  enclosed in a root element (e.g. <JMdict>...</JMdict>) but a\n'
            '  a DTD is not necessary.' % sys.argv[0])
        filename = sys.argv.pop (-1)
        xmltype = "jmex"
        if len (sys.argv) > 1: xmltype = sys.argv.pop (-1)
        inpf = JmdictFile( open( filename ))
        jmparser = Jmparser (jdb.KW, xmltype)
        for tag,entr in jmparser.parse_xmlfile (inpf):
            print (fmtxml.entr (entr))

if __name__ == '__main__': main()
