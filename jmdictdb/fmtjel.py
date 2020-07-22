# Copyright (c) 2006-2010 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import re, pdb
from collections import defaultdict
from jmdictdb import jdb, fmt

MIDDOT = '\u30FB'
  # The following characters are recognised as special
  # in the TAGLIST state in jellex.py.
SPECIALS = '[ :;,.#/=\\[\\]\u3000\uFF1B\u3001\uFF0F\u30FB]'

def qtxt (txt):
        # Enclose txt in quotes if it contains any special
        # characters.
        if not txt: return ''
        if re.search (SPECIALS, txt):
           txt = '"' + txt.replace ('"', '\\"') + '"'
        return txt

def escgloss (txt):
        # Add backslash escape characters in front of any
        # ";" or "[" characters in txt.  This is the escaping
        # used in glosses processed by the JEL parser.
        txt = re.sub (r'([;\[])', r'\\\1', txt)
        return txt

def entr (entr, nohdr=False):
        # Create a JEL text representation of 'entr'.
        # We assume that the caller has called jdb.add_xsens_lists()
        # and jdb.mark_seq_xrefs() on entr before calling fmt_entr()
        # because xref() uses the info added by those functions.
        #
        # Caution: The JEL text entry returned by this function can not
        # be used directly as input to the JEL parser because the latter
        # requires the kanji, reading and sense sections to be separated
        # with '\f' ('\x0c') characters but this function returns the
        # sections separated with '\n' characters (for display purposes).
        # Assuming no header line is included, replacing the first two
        # '\n' characters in the returned text with '\f' will make it
        # parsable by jelparse().

        sects = []
        if not nohdr: sects.append (entrhdr (entr))
        k = getattr (entr, '_kanj', [])
        r = getattr (entr, '_rdng', [])
        s = getattr (entr, '_sens', [])
        sects.append (kanjs (k))
        sects.append (rdngs (r, k))
        sects.append (senss (s, k, r))
        txt = '\n'.join (sects)
        return txt

def kanjs (kanjs):
        txt = '\uFF1B'.join ([kanj (x) for x in kanjs])
        return txt

def kanj (kanj):
        KW = jdb.KW
        txt = kanj.txt
        inf = [KW.KINF[x.kw].kw for x in getattr(kanj,'_inf',[])]
        inf.sort()
        freq = jdb.freq2txts (getattr(kanj,'_freq',[]))
        if inf or freq: txt += '[' + ','.join (inf + freq) + ']'
        return txt

def rdngs (rdngs, kanjs):
        txt = '\uFF1B'.join ([rdng (x, kanjs) for x in rdngs])
        return txt

def rdng (rdng, kanjs):
        KW = jdb.KW
        txt = rdng.txt
        restrtxt = fmt.restrtxts (getattr(rdng,'_restr',[]),
                                  kanjs, '_restr', qtxt)
          # Join restrs with "," if they are alone, but with
          # ";" if in a list prefixed with "restr=".
        if restrtxt: txt += '[' + ','.join(restrtxt) + ']'
        inf = [KW.RINF[x.kw].kw for x in getattr(rdng,'_inf',[])]
        inf.sort()
        freq = jdb.freq2txts (getattr(rdng,'_freq',[]))
        if inf or freq: txt += '[' + ','.join (inf + freq) + ']'
        return txt

def senss (senss, kanjs, rdngs):
        nsens = 0;  stxts = []
        for s in senss:
            nsens += 1
            if s.sens and s.sens != nsens:
                raise ValueError ("Sense %d has \{sens\} value of %s" % (nsens, s.sens))
            stxts.append (sens (s, kanjs, rdngs, nsens))
        txt = '\n'.join (stxts)
        return txt

def sens (sens, kanjs, rdngs, nsens):
        KW = jdb.KW
        dial = ['dial='+KW.DIAL[x.kw].kw for x in getattr(sens,'_dial',[])]
        misc = [        KW.MISC[x.kw].kw for x in getattr(sens,'_misc',[])]
        pos  = [        KW.POS [x.kw].kw for x in getattr(sens,'_pos', [])]
        fld  = ['fld='+ KW.FLD [x.kw].kw for x in getattr(sens,'_fld', [])]
        stagk = fmt.restrtxts (getattr(sens,'_stagk',[]), kanjs, '_stagk')
        stagr = fmt.restrtxts (getattr(sens,'_stagr',[]), rdngs, '_stagr')
        _lsrc = [lsrc(x) for x in getattr(sens,'_lsrc',[])]

        a = KW.STAT['A'].id    # get id num for entry "active" status (usu. 2).
        _xref =  ['[' + xref (x)  + ']' for x in getattr (sens, '_xref', [])
                                          if getattr (x, 'SEQ', None) is not False
                                               #FIXME? should "None" be "[]"?
                                             and getattr (x, '_xsens', None)!=[]
                                               # Exclude xrefs to deleted/rejected entries
                                               # (i.e. not "active" status).  If no TARG
                                               # attrib (jdb,augment_xrefs() not previously
                                               # called on entry) we have no way to tell so
                                               # format anyway and hope for the best.)
                                             and a == getattr (getattr (x, 'TARG', None), 'stat', a)]

        _xrslv = ['[' + xrslv (x) + ']' for x in getattr (sens, '_xrslv', [])]

        kwds  = '[' + ','.join (pos)  + ']' if pos else ''
        if misc: kwds += '[' + ','.join (misc) + ']'
        if fld:  kwds += '[' + ','.join (fld)  + ']'
        dial  = '[' + ','.join(dial)  + ']' if dial else ''
        restr = stagk + stagr
          # Join restrs with "," if they are alone, but with
          # ";" if in a list prefixed with "restr=".
        restr = '[restr=' + '; '.join (qtxt(x) for x in restr) + ']'\
                if restr else ''
        _lsrc = '[' + ','.join (_lsrc) + ']' if _lsrc else ''
        note  = ''
        if getattr(sens,'notes',None): note = '[note=' + qtxt(sens.notes) + ']'

        lastginf = -1;  gloss = [];  gtxt = []
        for n,g in enumerate (getattr (sens, '_gloss', [])):
            kws = []
            if g.ginf != KW.GINF['equ'].id: kws.append (KW.GINF[g.ginf].kw)
            if g.lang != KW.LANG['eng'].id:
                if g.lang == KW.LANG['lit'].id:
                      # Lithuanian language tag needs an explicit "lang="
                      # tag to disabiguate from a ginf lit ("literal") tag.
                    kws.append ("lang="+KW.LANG[g.lang].kw)
                else:
                    kws.append (KW.LANG[g.lang].kw)
            nl = '' if n==0 else '\n  '
            kwstr = ('%s[%s] ' % (nl, ','.join(kws))) if kws else ''
            gtxt.append ('%s%s' % (kwstr, escgloss (g.txt)))
        gloss = ['; '.join (gtxt)]
        lines = []
        lines.append ("[%d]%s%s" % (nsens,kwds,dial))
        if restr: lines.append (restr)
        if _lsrc: lines.append (_lsrc)
        if note: lines.append (note)
        lines.extend (gloss)
        lines.extend (_xref)
        lines.extend (_xrslv)
        txt = '\n  '.join (lines)
        return txt

def xref (x):
        # If only ordinary xrefs are available, the generated text will
        # be of the form "id#[n]" where 'id' is the target entry Id and
        # 'n' is the target sense number, or a comma separated list of
        # sense numbers.
        #
        # If .TARG is available, the format will be "Qc.K.R[n]" where
        # 'Q' is the seq number, 'c' is the corpus name, 'K' and 'R' are
        # the target's
        # kanji and reading texts (either but not both may be absent),
        # and 'n' is the target sense number, or a comma separated list
        # of sense numbers.  If the target entry has only one sense,
        # the "[n]" part is dropped.
        #
        # Note that if output from this function will be parsed to generate
        # a (possibly modified) copy of an entry, augmented xrefs *must*
        # be used to ensure accurate regeneration of the xrefs.  Lacking
        # the reading and kanji texts, the regenerated xrefs will use the
        # first kanji/reading of the target entry.

        KW = jdb.KW

        #FIXME:
        corpid = 1; kwsrc = KW.SRC;  txt = []
        p = getattr (x, 'SEQ', None)
        if p is False: return None
        elif p: txt = fmt_xref_seq (x, corpid, kwsrc)
        else: txt = fmt_xref_entr (x)
        return txt


def fmt_xref_seq (xref, corpid, kwsrc):
        # Format a group of entries having a common seq number
        # to a single seq-style JEL xref line.
        # xrefs -- A list of augmented xref objects whose target
        #   entries are assumed to have the same seq number and
        #   the same set of target senses.
        KW = jdb.KW
        corptxt = kwsrc[xref.TARG.src].kw if xref.TARG.src != corpid else ''
        numtxt = str(xref.TARG.seq) + corptxt
        krtxt = fmt_xref_kr (xref)
        return KW.XREF[xref.typ].kw + '=' + numtxt + MIDDOT + krtxt

def fmt_xref_entr (xref):
        KW = jdb.KW
        krtxt = fmt_xref_kr (xref)
        numtxt = str(xref.xentr) + "#"
        return KW.XREF[xref.typ].kw + '=' + numtxt + MIDDOT + krtxt

def fmt_xref_kr (xref):
        snum_or_slist = getattr (xref, '_xsens', xref.xsens)
        if snum_or_slist is None: ts = ''
        elif hasattr (snum_or_slist, '__iter__'):
            ts = '[' + ','.join ((str(x) for x in snum_or_slist)) + ']'
        else: ts = '[%d]' % snum_or_slist
        t = getattr (xref, 'TARG', None)
        if t:
            kt = (getattr (t, '_kanj', [])[xref.kanj-1]).txt if getattr (xref, 'kanj', None) else ''
            rt = (getattr (t, '_rdng', [])[xref.rdng-1]).txt if getattr (xref, 'rdng', None) else ''
        else:
            kt = getattr (xref, 'ktxt', '') or ''
            rt = getattr (xref, 'rtxt', '') or ''
        txt = qtxt(kt) + (MIDDOT if kt and rt else '') + qtxt(rt) + ts
        return txt

def xrslv (xr):
        KW = jdb.KW
        v = [];
        ts = getattr (xr, 'tsens', '') or ''
        if ts: ts  = '[%d]' % ts
        kt = getattr (xr, 'ktxt', '') or ''
        rt = getattr (xr, 'rtxt', '') or ''
        txt = KW.XREF[xr.typ].kw + '=' + kt + ('\u30FB' if kt and rt else '') + rt + ts
        return txt

def lsrc (lsrc):
        KW = jdb.KW
        lang = KW.LANG[lsrc.lang].kw
        p = '';  w = ''
        if lsrc.part: p = 'p'
        if lsrc.wasei: w = 'w'
        t = p + w
        if t: t = '/' + t
        return 'lsrc=' + lang + t + ':' + (qtxt(lsrc.txt))

def grp (grp):
        KW = jdb.KW
          # FIXME: Handle grp.notes which is currently ignored.
        ord = '' if grp.ord is None else ("." + str (grp.ord))
        return KW.GRP[grp.kw].kw + ord

def entrhdr (entr):
        if not (entr.seq or entr.src or entr.stat or entr.unap): return ""
        a = [str(entr.seq) if entr.seq else "0"]
        if entr.src: a.append (jdb.KW.SRC[entr.src].kw)
        statt = jdb.KW.STAT[entr.stat].kw if entr.stat else ""
        if entr.unap: statt += "*"
        if statt: a.append (statt)
        extra = []
        for x in ('id', 'dfrm'):
            if getattr (entr, x): extra.append("%s=%r" % (x,getattr(entr,x)))
        if extra: a.append ("[" + "; ".join(extra) + "]")
        hdr = " ".join (a)
        return hdr

def main():
        cur = jdb.dbOpen ('jmnew')
        entrs, data = jdb.entrList (cur, [542], ret_tuple=True)
        jdb.augment_xrefs (cur, data['xref'])
        jdb.augment_xrefs (cur, data['xref'], rev=1)
        jdb.add_xsens_lists (xrefs)
        jdb.mark_seq_xrefs (cur, xrefs)
        for e in entrs:
            txt = entr (e)
            print (txt)

if __name__ == '__main__': main ()
