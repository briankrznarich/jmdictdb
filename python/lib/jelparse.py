
#######################################################################
#  This file is part of JMdictDB. 
#  Copyright (c) 2008 Stuart McGraw 
# 
#  JMdictDB is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published 
#  by the Free Software Foundation; either version 2 of the License, 
#  or (at your option) any later version.
# 
#  JMdictDB is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with JMdictDB; if not, write to the Free Software Foundation,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#######################################################################

__version__ = ('$Revision$'[11:-2], \
               '$Date$'[7:-11]);

import sys, ply.yacc, re, pdb
from collections import defaultdict
import jellex, jdb
from objects import *
import fmt, fmtjel      # For code in main().

class ParseError (Exception): 
    def __init__ (self, msg, loc=None, token=None):
        self.args = (msg,)
        self.loc = loc
        self.token = token

precedence =  []

# -------------- RULES ----------------

def p_entr_1(p):
    '''entr : preentr'''
    p.lexer.begin('INITIAL')
    e = p[1]
      # The Freq objects on the readings are inependent of
      # those on the kanjis.  The following function merges
      # common values.
    merge_freqs (e)
      # Set the foreign key ids since they will be used 
      # needed by mk_restrs() below.
    jdb.setkeys (e, None)
      # The reading and sense restrictions here are simple
      # lists of text strings that give the allowed readings
      # or kanji.  mk_restrs() converts those to the canonical
      # format which uses the index number of the disallowed 
      # readings or kanji.
    if hasattr (e, '_rdng') and hasattr (e, '_kanj'): 
        err = mk_restrs ("_RESTR", e._rdng, e._kanj)
        if err: xerror (p, err)
    if hasattr (e, '_sens') and hasattr (e, '_kanj'): 
        err = mk_restrs ("_STAGK", e._sens, e._kanj)
        if err: xerror (p, err)
    if hasattr (e, '_sens') and hasattr (e, '_rdng'): 
        err = mk_restrs ("_STAGR", e._sens, e._rdng)
        if err: xerror (p, err)
      # Note that the entry object returned may have an _XREF list
      # on its senses but the supplied xref records are not
      # complete.  We do not assume database access is available
      # when parsing so we cannot look up the xrefs to find the 
      # the target entry id numbers, validate that the kanji
      # reading (if given) are unique, or the target senses exist,
      # etc.  It is expected that the caller will do this resolution
      # on the xrefs using something like jdb.resolv_xref() prior
      # to using the object.
    p[0] = e

def p_preentr_1(p):
    '''preentr : rdngsect senses'''
    p[0] = jdb.Entr(_rdng=p[1], _sens=p[2])

def p_preentr_2(p):
    '''preentr : kanjsect senses'''
    p[0] = jdb.Entr(_kanj=p[1], _sens=p[2])

def p_preentr_3(p):
    '''preentr : kanjsect rdngsect senses'''
    p[0] = jdb.Entr(_kanj=p[1], _rdng=p[2], _sens=p[3])

def p_kanjsect_1(p):
    '''kanjsect : kanjitem'''
    p[0] = [p[1]]

def p_kanjsect_2(p):
    '''kanjsect : kanjsect SEMI kanjitem'''
    p[0] = p[1];  p[0].append (p[3])

def p_kanjitem_1(p):
    '''kanjitem : KTEXT'''
    p[0] = jdb.Kanj(txt=p[1])

def p_kanjitem_2(p):
    '''kanjitem : KTEXT taglists'''
    kanj = jdb.Kanj(txt=p[1])
    err = bld_kanj (kanj, p[2])
    if err: xerror (p, err)
    p[0] = kanj

def p_rdngsect_1(p):
    '''rdngsect : rdngitem'''
    p[0] = [p[1]]

def p_rdngsect_2(p):
    '''rdngsect : rdngsect SEMI rdngitem'''
    p[0] = p[1];  p[0].append (p[3])

def p_rdngitem_1(p):
    '''rdngitem : RTEXT'''
    p[0] = jdb.Rdng(txt=p[1])

def p_rdngitem_2(p):
    '''rdngitem : RTEXT taglists'''
    rdng = jdb.Rdng(txt=p[1])
    err = bld_rdng (rdng, p[2])
    if err: xerror (p, err)
    p[0] = rdng

def p_senses_1(p):
    '''senses : sense'''
    p[0] = [p[1]]

def p_senses_2(p):
    '''senses : senses sense'''
    p[0] = p[1]; p[0].append(p[2])

def p_sense_1(p):
    '''sense : SNUM glosses'''
    sens = jdb.Sens()
    err = bld_sens (sens, p[2])
    if err: xerror (p, "Unable to build sense %s\n%s" % (p[1], err))
    p[0] = sens

def p_glosses_1(p):
    '''glosses : gloss'''
    p[0] = [p[1]]

def p_glosses_2(p):
    '''glosses : glosses SEMI gloss'''
    p[0] = p[1]; p[0].append (p[3])

def p_gloss_1(p):
    '''gloss : GTEXT'''
    p[0] = [p[1], []]

def p_gloss_2(p):
    '''gloss : GTEXT taglists'''
    p[0] = [p[1], p[2]]

def p_gloss_3(p):
    '''gloss : taglists GTEXT'''
    p[0] = [p[2], p[1]]

def p_gloss_4(p):
    '''gloss : taglists GTEXT taglists'''
    p[0] = [p[2], p[1] + p[3]]

def p_taglists_1(p):
    '''taglists : taglist'''
    p[0] = p[1]

def p_taglists_2(p):
    '''taglists : taglists taglist'''
    p[0] = p[1]
    p[0].extend(p[2])

def p_taglist_1(p):
    '''taglist : BRKTL tags BRKTR'''
    p[0] = p[2]

def p_tags_1(p):
    '''tags : tagitem'''
    p[0] = [p[1]]

def p_tags_2(p):
    '''tags : tags COMMA tagitem'''
    p[0] = p[1]
    p[0].append (p[3])

def p_tagitem_1(p):
    '''tagitem : KTEXT'''
    p[0] = ['RESTR', [None, p[1], None, None, None]]

def p_tagitem_2(p):
    '''tagitem : RTEXT'''
    p[0] = ['RESTR', [p[1], None, None, None, None]]

def p_tagitem_3(p):
    '''tagitem : TEXT'''
    if p[1] == 'nokanji':
        p[0] = ['RESTR', [['nokanji', None, None, None, None]]]
    else:
        x = lookup_tag (p[1])
        if not x: xerror (p, "Unknown keyword: '%s'" % p[1])
        else: p[0] = [None, p[1]]

def p_tagitem_4(p):
    '''tagitem : TEXT EQL TEXT'''
    KW = jdb.KW
    if p[1] in ["note","lsrc","restr"]:
        if p[1] == "restr":
            if p[3] != "nokanji":
                xerror (p, "Bad restr value (expected \"nokanji\"): '%s'" % p[3])
            p[0] = ["RESTR", [["nokanji", None, None, None, None]]]
        else: p[0] = [p[1], p[3], 1, None]
    else:
        x = lookup_tag (p[3], p[1])
        if x and len(x) > 1:
            raise ValueError ("Unexpected return value from lookup_tag()")
        if x is None: xerror (p, "Unknown keyword type: '%s'" % p[1])
        elif not x:   xerror (p, "Unknown %s keyword: '%s" % (p[1],p[3]))
        else:         p[0] = x[0]

def p_tagitem_5(p):
    '''tagitem : TEXT EQL QTEXT'''
    KW = jdb.KW 
    if p[1] in ["note","lsrc"]:
        p[0] = [p[1], jellex.qcleanup (p[3][1:-1]), 1, None] 
    else: xerror (p, "Unknown keyword: '%s" % p[1])

def p_tagitem_6(p):
    '''tagitem : TEXT EQL TEXT COLON'''
    KW = jdb.KW 
    if p[1] != "lsrc": xerror (p, "Keyword must be \"lsrc\"")
    la = KW.LANG.get(p[3])
    if not la: xerror (p, "Unrecognised language '%s'" % p[3])
    p[0] = ["lsrc", None, la.id, None]

def p_tagitem_7(p):
    '''tagitem : TEXT EQL TEXT COLON atext'''
    KW = jdb.KW 
    lsrc_flags = None; lang = None
    if p[1] in ["lsrc"]:
        la = KW.LANG.get(p[3])
        if not la:
            if p[3] not in ('w','p','wp','pw'):
                xerror (p, "Unrecognised language '%s'" % p[3])
            else: lsrc_flags = p[3]
        else: lang = la.id
    else: xerror (p, "Keyword not \"lsrc\", \"lit\", or \"expl\"")
    p[0] = ["lsrc", p[5], lang, lsrc_flags]

def p_tagitem_8(p):
    '''tagitem : TEXT EQL TEXT SLASH TEXT COLON atext'''
    KW = jdb.KW 
    if p[1] != "lsrc": xerror (p, "Keyword not \"lsrc\"")
    la = KW.LANG.get(p[3])
    if not la: xerror (p, "Unrecognised language '%s'" % p[3])
    if p[5] not in ('w','p','wp','pw'):
        xerror (p, "Bad lsrc flags '%s', must be 'w' (wasei), "
                    "'p' (partial),or both" % p[5])
    p[0] = ["lsrc", p[7], la.id, p[5]]

def p_tagitem_9(p):
    '''tagitem : TEXT EQL xrefs'''
    # 'xrefs' represents both xrefs and restrs, is list of 5-tuples:
      #   0 -- reading text
      #   1 -- kanji text
      #   2 -- sense number list
      #   3 -- number (entry, seq, or None)
      #   4 -- corpus (str:corp kw, "":current corp, None:entry id) 
    KW = jdb.KW 
    if p[1] == 'restr': 
        p[0] = ['RESTR', p[3]]
    elif p[1] in [x.kw for x in KW.recs('XREF')]:
          # FIXME: instead of using XREF kw''s directly, do we want to
          #  change to an lsrc syntax like, "xref=cf:..." (possibly
          #  keeping "see" and "ant" as direct keywords)?
        p[0] = ['XREF', KW.XREF[p[1]].id, p[3]]
    else: 
          # FIXME: msg is misleading, we also except other
          #  xref keywords.
        xerror (p, 'Bad keyword, expected one of "restr", "see", or "ant"')

def p_atext_1(p):
    '''atext : TEXT'''
    p[0] = p[1]

def p_atext_2(p):
    '''atext : QTEXT'''
    p[0] = jellex.qcleanup (p[1][1:-1])

def p_xrefs_1(p):
    '''xrefs : xref'''
    p[0] = [p[1]]

def p_xrefs_2(p):
    '''xrefs : xrefs SEMI xref'''
    p[0] = p[1]
    p[0].append (p[3])

def p_xref_1(p):
    '''xref : xrefnum'''
    p[0] = [None,None,None] + p[1]

def p_xref_2(p):
    '''xref : xrefnum slist'''
    p[0] = [None,None,p[2]] + p[1]

def p_xref_3(p):
    '''xref : xrefnum DOT jitem'''
    p[0] = p[3] + p[1]

def p_xref_4(p):
    '''xref : jitem'''
    p[0] = p[1] + [None,'']

def p_jitem_1(p):
    '''jitem : jtext'''
    p[0] = p[1]

def p_jitem_2(p):
    '''jitem : jtext slist'''
    p[0] = p[1]
    p[0][2] = p[2]

def p_jtext_1(p):
    '''jtext : KTEXT'''
    p[0] = [None, p[1], None]

def p_jtext_2(p):
    '''jtext : RTEXT'''
    p[0] = [p[1], None, None]

def p_jtext_3(p):
    '''jtext : KTEXT DOT RTEXT'''
    p[0] = [p[3], p[1], None]

def p_xrefnum_1(p):
    '''xrefnum : NUMBER'''
    p[0] = [toint(p[1]), '']

def p_xrefnum_2(p):
    '''xrefnum : NUMBER HASH'''
    p[0] = [toint(p[1]), None]

def p_xrefnum_3(p):
    '''xrefnum : NUMBER TEXT'''
    p[0] = [toint(p[1]), p[2]]

def p_slist_1(p):
    '''slist : BRKTL snums BRKTR'''
    p[0] = p[2]

def p_snums_1(p):
    '''snums : NUMBER'''
    n = int(p[1])
    if n<1 or n>99:
        xerror (p, "Invalid sense number: '%s' % n")
    p[0] = [n]

def p_snums_2(p):
    '''snums : snums COMMA NUMBER'''
    n = int(p[3])
    if n<1 or n>99:
        xerror (p, "Invalid sense number: '%s' % n")
    p[0] = p[1] + [n]

# -------------- RULES END ----------------

def p_error (token): 
        #pdb.set_trace()
        if token: errpos = token.lexpos
        else: errpos = None
        descr = errloc (errpos)
        raise ParseError ("Syntax error", '\n'.join (descr))

def xerror (p, msg=None):
        #pdb.set_trace()
        token = p.stack[-1]
          # Caution: token will only have an 'endlexpos' if parser.parse()
          #  was called with the argument, tracking=True.
        if token: errpos = token.endlexpos
        else: errpos = None
        descr = errloc (errpos)
        raise ParseError (msg, '\n'.join (descr))

def errloc (errpos):
        # Return a list of text lines that consitute the parser
        # input text (or more accurately the input text to the
        # lexer used by the parser) with an inserted line containing
        # a caret character that points to the lexer position when
        # the error was detected.  'errpos' is the character offset
        # in the input text of the error, or None if the error was
        # at the end of input.
        # Note: Function create_parser() makes the parser it creates
        # global (in JelParser) and also make the lexer availble as 
        # attribute '.lexer' of the parser, both of whech we rely on
        # here.

        global JelParser
        input = JelParser.lexer.lexdata
        if errpos is None: errpos = len (input)
        lines = input.splitlines (True)
        eol = 0;  out = []
        for line in lines:
            out.append (line.rstrip())
            eol += len (line)
            if eol >= errpos and errpos >= 0:
                errcol = len(line) + errpos - eol
                out.append ((' ' * errcol) + '^')
                errpos = -1     # Ignore errpos on subsequent loops.
        return out

def lookup_tag (tag, typs=None):
        # Lookup 'tag' (given as a string) in the keyword tables
        # and return the kw id number.  If 'typs' is given it 
        # should be a string or list of strings and gives the
        # specific KW domain(s) (e.g. FREQ, KINF, etc) that 'tag'
        # should be looked for in. 
        # The return value is:
        #   None -- A non-existent KW domain was given in'typs'.
        #   [] -- (Empty list) The 'tag' was not found in any of 
        #         the doimains given in 'typs'.
        #   [[typ1,id1],[typ2,id2],...] -- A list of lists.  Each
        #         item represents a domain in which 'tag' was found.
        #         The first item of each item is a string giving  
        #         the domain name.  The second item gives the id 
        #         number of that tag in the domain.  In the case of
        #         the FREQ keyword, the item will be a 3-list
        #         consisting of "FREQ", the freq kw id, and the 
        #         a number for the freq value.  E.g. lookup_tag('nf23')
        #         will return [["FREQ",5,23]] (assuming that the "nf"
        #         kw has the id value of 5 in the kwfreq table.)

        KW = jdb.KW 
        matched = []
        if not typs:
            typs = [x for x in KW.attrs()]
        if isinstance (typs, (str, unicode)): typs = [typs]
        for typ in typs:
            typ = typ.upper(); val = None
            if typ == "FREQ":
                mo = re.search (r'^([^0-9]+)(\d+)$', tag)
                if mo:
                    tagbase = mo.group(1)
                    val = int (mo.group(2))
            else: tagbase = tag
            try:
                x = (getattr (KW, typ))[tagbase]
            except AttributeError: 
                raise ParseError ("Unknown 'typ' value: %s." % typ)
            except KeyError: pass
            else: 
                if not val: matched.append ([typ, x.id])
                else: matched.append ([typ, x.id, val])
        return matched

def bld_sens (sens, glosses):
        # Build a sense record.  'glosses' is a list of gloss items.
        # Each gloss item is a 2-tuple: the first item is the gloss
        # record and the second, a list of sense tags.  
        # Each of the sense tag items is an n-tuple.  The first item
        # in an n-tuple is either a string giving the type of the tag
        # ('KINF', 'POS'. 'lsrc', etc) or None indicating the type was
        # not specified (for example, the input text contained a single
        # keyword like "vi" rather than "pos=vi").  The second and any
        # further items are dependent on the the tag type.
        # Our job is to iterate though this list, and put each item 
        # on the appropriate sense list: e.g. all the "gloss" items go 
        # into the list @{$sens->{_gloss}}, all the "POS" keyword items 
        # go on @{$sens->{_pos}}, etc.

        KW = jdb.KW 
        errs = []; sens._gloss = []
        for gtxt, tags in glosses:
            gloss = jdb.Gloss (txt=jellex.gcleanup(gtxt))
            sens._gloss.append (gloss)
            if tags: errs.extend (sens_tags (sens, gloss, tags))
            if gloss.ginf is None: gloss.ginf = KW.GINF['equ'].id
            if gloss.lang is None: gloss.lang = KW.LANG['eng'].id
        return "\n".join (errs)

def sens_tags (sens, gloss, tags):
        # See the comments in the "taglist" production for a description
        # of the format of 'taglist'.

        KW = jdb.KW 
        errs = []
        for t in tags:
            vals = None
            typ = t.pop(0)      # Get the item type.

            if typ is None:
                  # Unknown type, figure it out...
                  # First, if we can interpret the tag as a sense tag, do so.
                candidates = lookup_tag (t[0], ('POS','MISC','FLD','DIAL'))
                if candidates and len(candidates) > 1: 
                    errs.append (
                        "Sense tag '%s' is ambiguous, may be either any of %s." 
                        " Please specify tag explicity, using, for instance,"
                        " \"%s=%s\"" % (t[0], ','.join([x[0] for x in candidates]),
                                        candidates[0][0], t[0]))
                    continue
                if candidates:
                    typ, t = candidates[0][0], [candidates[0][1]]
            if typ is None:
                candidates = lookup_tag (t[0], ('GINF','LANG'))
                if candidates: 
                      # FIXME: assume kw that is iterpretable as both a GINF
                      #   kw and a LANG kw (e.g. "lit") is a GINF keyword.
                    candidate = candidates[0] 
                    typ, t = candidate
            if typ is None:
                errs.append ("Unknown tag '%r'" % t)
                continue

            if typ in ('POS','MISC','FLD','DIAL'):
                assert len(t)==1, "invalid length"
                assert type(t[0])==int, "Unresolved kw"
                if typ == 'POS': o = Pos(kw=t[0])
                elif typ == 'MISC': o = Misc(kw=t[0])
                elif typ == 'FLD': o = Fld(kw=t[0])
                elif typ == 'DIAL': o = Dial(kw=t[0])
                append (sens, "_"+typ.lower(), o)

            elif typ == 'RESTR':
                # We can't create real @{_stagk} or @{_stagr} lists here
                # because the readings and kanji we are given by the user
                # are allowed ones, but we need to store disallowed ones. 
                # To get the disallowed ones, we need access to all the
                # readings/kanji for this entry and we don't have that
                # info at this point.  So we do what checking we can. and
                # save the texts as given, and will fix later after the 
                # full entry is built and we have access to the entry's
                # readings and kanji.

                for xitem in t[0]:
                    rtxt,ktxt,slist,num,corp = xitem
                    #if num or corp:
                    if ((rtxt and ktxt) or (not rtxt and not ktxt)): 
                        errs.append ("Sense restrictions must have a "
                                     "reading or kanji (but not both): "
                                     + fmt_xitem (xitem))
                    if ktxt: append (sens, '_STAGK', ktxt)
                    if rtxt: append (sens, '_STAGR', rtxt)

            elif typ == 'lsrc':  
                wasei   = t[2] and 'w' in t[2]
                partial = t[2] and 'p' in t[2]
                append (sens, '_lsrc', 
                        jdb.Lsrc(txt=t[0], lang=(t[1] or lang_en), 
                                part=partial, wasei=wasei))

            elif typ == 'note': 
                if getattr (sens, 'notes', None): 
                    errs.append ("Only one sense note allowed")
                sens.notes = t[0]

            elif typ == 'XREF':
                xtyp = t[0]
                for xitem in t[1]:
                    kw = KW.XREF[xtyp].id
                    xitem.insert (0, kw)
                    append (sens, '_XREF', xitem)

            elif typ == 'GINF':
                assert isinstance(t,int)
                if getattr (gloss, 'ginf', None): 
                    errs.append ( 
                        "Warning, duplicate GINF tag '%s' ignored\n" % KW.GINF[t].kw)
                else: gloss.ginf = t

            elif typ == 'LANG': 
                assert isinstance(t,int)
                if getattr (gloss, 'lang', None): 
                    errs.append ( 
                        "Warning, duplicate LANG tag '%s' ignored\n" % KW.LANG[t].kw)
                else: gloss.lang = t

            elif typ: 
                errs.append ("Cannot use '%s' tag in a sense" % typ)

        return errs

def bld_rdng (r, taglist=[]):
        errs = [];  nokanj = False
        for t in taglist:
            typ = t.pop(0)
            if typ is None:
                v = lookup_tag (t[0], ('RINF','FREQ'))
                if not v: 
                    typ = None
                    errs.append ("Unknown reading tag %s" % t[0])
                else:
                    typ, t = v[0][0], v[0][1:] 
            if typ == 'RINF': append (r, '_inf', jdb.Rinf(kw=t[0]))
            elif typ == 'FREQ':
                  # _freq objects are referenced by both the reading and
                  # kanji _freq lists.  Since we don't have access to 
                  # the kanj here, temporarily save the freq (kw, value)
                  # tuple in attribute "._FREQ".  When the full entry is
                  # processed, the info in here will be removed, merged
                  # with parallel info from the kanj objects, and proper
                  # ._freq objects created.
                append (r, '_FREQ', (t[0], t[1]))
            elif typ == 'RESTR':
                # We can't generate real restr records here because the real
                # records are the disallowed kanji.  We have the allowed
                # kanji here and need the set of all kanji in order to get
                # the disallowed set, and we don't have that now.  So we 
                # just save the allowed kanji as given, and will convert it
                # after the full entry is built and we have all the info we
                # need.
                for xitem in t[0]:
                      # An xitem represents a reference to another entry
                      # or other info within an entry, in textual form.  It
                      # is used for xrefs and restr info.  It is a 5-seq
                      # with the following values:
                      #   [0] -- Reading text
                      #   [1] -- Kanji text
                      #   [2] -- A sequence of sense numbers.
                      #   [3] -- An entry or seq number.
                      #   [4] -- Corpus name or id number, "",  or None.
                      # For a reading restr, it is expected to contain only 
                      # a kanji text.
                    rtxt,ktxt,slist,num,corp = xitem
                    if rtxt == "nokanji": 
                        nokanj = True
                        r._NOKANJI = 1
                        continue
                    if rtxt or not ktxt or slist or num or corp:
                        errs.append ("Reading restrictions must be kanji only: "
                                      + fmt_xitem (xitem))
                    append (r, "_RESTR", ktxt)
                if hasattr (r,'_RESTR') and nokanj:
                    errs.append ("Can't use both kanji and 'nokanji' in 'restr' tags")
            elif typ: 
                errs.append ("Cannot use '%s' tag in a reading" % typ)
        return "\n".join (errs)

def bld_kanj (k, taglist=[]):
        errs = []
        for t in taglist:
            typ = t.pop(0)
            if typ is None:
                v = lookup_tag (t[0], ('KINF','FREQ'))
                if not v: xerror ("Unknown kanji tag %s" % t[0])
                  # Warning: The following simply uses the first resolved tag in
                  # the candidates list returned by lookup_tag().  This assumes
                  # there are no possible tags that are ambiguous in the KINF and
                  # FREQ which could cause lookup_tag() to return more than one
                  # candidate tags.
                typ, t = v[0][0], v[0][1:]
            if typ == "KINF": append (k, "_inf", jdb.Kinf(kw=t[0]))
            elif typ == "FREQ": 
                  # _freq objects are referenced by both the reading and
                  # kanji _freq lists.  Since we don't have access to 
                  # the rdng here, temporarily save the freq (kw, value)
                  # tuple in attribute "._FREQ".  When the full entry is
                  # processed, the info in here will be removed, merged
                  # with parallel info from the rdng objects, and proper
                  # ._freq objects created.
                append (k, "_FREQ", (t[0], t[1]))
            else: 
                errs.append ("Cannot use %s tag in kanji section" % typ); 
        return "\n".join (errs)

def mk_restrs (listkey, rdngs, kanjs):
        # Note: mk_restrs() are used for all three
        # types of restriction info: restr, stagr, stagk.  However to
        # simplify things, the comments and variable names assume use
        # with reading restrictions (restr).  
        #
        # What we do is take a list of restr text items received from
        # a user which list the kanji (a subset of all the kanji for
        # the entry) that are valid with this reading, and turn it 
        # into a list of restr records that identify the kanji that
        # are *invalid* with this reading.  The restr records identify
        # kanji by id number rather than text.
        #
        # listkey -- Name of the key used to get the list of text
        #    restr items from 'rdngs'.  These are the text strings
        #    provided by the user.  Should be "_RESTR", "_STAGR", 
        #    or "_STAGK".
        # rdngs -- List of rdng or sens records depending on whether
        #    we're doing restr or stagr/stagk restrictions.
        # kanjs -- List of the entry's kanji or reading records 
        #    depending on whether we are doing restr/stagk or stagr
        #    restrictions.

        errs = []
        ktxts = [x.txt for x in kanjs]

        for n,r in enumerate (rdngs):
              # Get the list of restr text strings and nokanji flag and
              # delete them from the rdng object since they aren't part
              # of the standard api.
            restrtxt = getattr (r, listkey, None)
            if restrtxt: delattr (r, listkey)
            nokanj = getattr (r, '_NOKANJI', None)
            if nokanj: delattr (r, '_NOKANJI')

              # Continue with next reading if nothing to be done 
              # with this one.
            if not nokanj and not restrtxt: continue

              # bld_rdngs() guarantees that {_NOKANJI} and {_RESTR} 
              # won't both be present on the same rdng.
            if nokanj and restrtxt:
                  # Only rdng-kanj restriction should have "nokanji" tag, so
                  # message can hardwire "reading" and "kanji" text even though
                  # this function in also used for sens-rdng and sens-kanj
                  # restrictions.
                errs.append ("Reading %d has 'nokanji' tag but entry has no kanji" % (n+1))
                continue
            if nokanj: restrtxt = None
            z = jdb.txt2restr (restrtxt, r, kanjs, listkey.lower())
              # Check for kanji erroneously in the 'restrtxt' but not in
              # 'kanjs'.  As an optimization, we only do this check if the
              # number of Restr objects created (len(z)) plus the number of
              # 'restrtxt's are not equal to the number of 'kanjs's.  (This
              # criterion my not be valid in some corner cases.)
            if restrtxt is not None and len (z) + len (restrtxt) != len (kanjs):
                nomatch = [x for x in restrtxt if x not in ktxts]
                if nomatch:
                    if   listkey == "_RESTR": not_found_in = "kanji"
                    elif listkey == "_STAGR": not_found_in = "readngs"
                    elif listkey == "_STAGK": not_found_in = "kanji"
                    errs.append ("restr value(s) '" + 
                            "','".join (nomatch) + 
                            "' not in the entry's %s" % not_found_in)
        return "\n".join (errs)

def resolv_xrefs (
    cur,         # An open DBAPI cursor to the current JMdictDB database.
    entr         # An entry with ._XREF tuples.
    ):
        """\
        Convert any jelparser generated _XREF lists that are attached
        to any of the senses in 'entr' to a normal augmented xref list.
        An _XREF list is a list of 6-tuples:
          [0] -- The type of xref per id number in table kwxref.
          [1] -- Reading text of the xref target entry or None.
          [2] -- Kanji text of the target xref or None.
          [3] -- A list of ints specifying the target senses in
                 in the target entry.
          [4] -- None or a number, either seq or entry id.
          [5] -- None, '', or a corpus name.  None means 'number'
                 is a entry id, '' means it is a seq number in the
                 corpus 'entr.src', otherwise it is the name or id
                 number of a corpus in which to try resolving the
                 xref. 
        At least one of [3], [4], or [1] must be non-None.\
        """
        errs = []
        for s in getattr (entr, '_sens', []):
            if not hasattr (s, '_XREF'): continue
            xrefs = []; xunrs = []
            for typ, rtxt, ktxt, slist, seq, corp in s._XREF:
                if corp == '': corp = entr.src
                xrf, xunr = find_xref (cur, typ, rtxt, ktxt, slist, seq, corp)
                if xrf: xrefs.extend (xrf)
                else:
                    xunrs.append (xunr)
                    errs.append (xunr.msg)
            if xrefs: s._xref = xrefs
            if xunrs: s._xrslv = xunrs
            del s._XREF
        return errs

def find_xref (cur, typ, rtxt, ktxt, slist, seq, corp, 
                corpcache={}, clearcache=False):

        xrfs = [];  xunrs = None;  msg = ''
        if clearcache: corpcache.clear()
        if isinstance (corp, (str, unicode)):
            if corpcache[corp]: corpid = corpcache[corp]
            else:
                rs = jdb.dbread ("SELECT id FROM kwsrc WHERE kw=%s", [corp])
                if len(rs) != 1: raise ValueError ("Invalid corpus name: '%s'" % corp)
                corpid = corpcache[corp] = rs[0][0]
        else: corpid = corp

        try:
            xrfs = jdb.resolv_xref (cur, typ, rtxt, ktxt, slist, seq, corpid)
        except ValueError, e:
            msg = e.args[0]
            xunrs = jdb.Xrslv (typ=typ, ktxt=ktxt, rtxt=rtxt,tsens=None)
            xunrs.msg = msg
        return xrfs, xunrs

def merge_freqs (entr):
        # This function is used by code that contructs Entr objects
        # by parsing a textual entry description.  Generally such code
        # will parse freq (a.k.a. prio) tags for readings and kanji
        # individually.  Before the entry is used, these independent
        # tags must be combined so that a rdng/kanj pairs with the 
        # same freq tag point to a single Freq object.  This function
        # does that merging.
        # It expects the entry's Rdng and Kanj objects to have a temp
        # attribute named "_FREQ" that contains a list of 2-tuples.
        # Each 2-tuple contains the freq table kw id number, and the
        # freq value.  After  merge_freqs() runs, all those .FREQ 
        # attributes will have been deleted, and .freq attributes 
        # created with equivalent, properly linked Freq objects.

        fmap = defaultdict (lambda:([list(),list()]))

          # Collect the info in .FREQ attributes from all the readings.
        for r in getattr (entr, '_rdng', []):
            for kw_val in getattr (r, '_FREQ', []):
                  # 'kw_val' is a 2-tuple denoting the freq as a freq table
                  # keyword id and freq value pair.
                rlist = fmap[(kw_val)][0]
                  # Add 'r' to rlist if it is not there already.
                  # Use first() as a "in" operator that uses "is" rather
                  #  than "==" as compare function.
                if not jdb.isin (r, rlist): rlist.append (r)
            if hasattr (r, '_FREQ'): del r._FREQ

          # Collect the info in .FREQ attributes from all the kanji.
          # This works on kanj's the same as above section works on 
          # rdng's and comments above apply here too.
        for k in getattr (entr, '_kanj', []):
            for kw_val in getattr (k, '_FREQ', []):
                klist = fmap[(kw_val)][1]
                if not jdb.isin (k, klist): klist.append (k)
            if hasattr (k, '_FREQ'): del k._FREQ

          # 'fmap' now has one entry for every unique freq (kw,value) tuple
          # which is a pair of sets.  The first set consists of all Rdng
          # objects that (kw,value) freq spec applies to.  The second is 
          # the set of all kanji it applies to.  We take all combinations
          # of readings with kanji, and create a Freq object for each.

        errs = jdb.make_freq_objs (fmap, entr)
        return errs

def append (sens, key, item):
    # Append $item to the list, @{$sens->{$key}}, creating 
    # the latter if needed.
        v = []
        try: v = getattr (sens, key)
        except AttributeError: setattr (sens, key, v)
        v.append (item)

_uni_numeric = {
    '\uFF10':'0','\uFF11':'1','\uFF12':'2','\uFF13':'3',
    '\uFF14':'4','\uFF15':'5','\uFF16':'6','\uFF17':'7',
    '\uFF18':'8','\uFF19':'9',}

def toint (s):
        n = int (s.translate (_uni_numeric))
        return n

def fmt_xitem (xitem):
        typ = None
        if len (xitem) == 6: typ = xitem.pop (0)
        rtxt, ktxt, slist, num, corp = xitem
        k = ktxt or '';  r = rtxt or '';  n = num or ''
        if num:
            if corp: c = ' ' + corp
            else: c = '#' if corp is None else ''
            n = n + c
        else: c = ''
        kr = k + (u'\u30FB' if k and r else '') + r
        t = n + (u'\u30FB' if n and kr else '') + kr 
        s = ('[%s]' % ','.join(slist)) if slist else ''
        return t + s

def create_parser (lexer, toks, **args):
        global tokens, JelParser
        tokens = toks
          # Set global JelParser since we need access to it
          # from error handling function p_error() and I don't
          # know any other way to make it available there. 
        JelParser = ply.yacc.yacc (**args)
        JelParser.lexer = lexer   # Access to lexer needed in error handler.
        return JelParser

def main (args, opts):
        global KW, tokens

        cur = jdb.dbOpen ('jmdict')
        # Get local ref to the keyword tables...
        KW = jdb.KW

        lexer, tokens = jellex.create_lexer (debug=opts.debug>>8)
        parser = create_parser (lexer, tokens)
        parser.debug = opts.debug

        if opts.seq:
            seq = opts.seq
              #FIXME: Corpid (used for xref resolution) is hardwired
              # to 1 (jmdict) below.
            srctxt, parsedtxt = _roundtrip (cur, lexer, parser, seq, 1)
            if not srctxt:
                print "Entry %s not found" % seq
            else:
                print srctxt
                print "----"
                print parsedtxt
        else:
            _interactive (cur, lexer, parser)

def _roundtrip (cur, lexer, parser, seq, src):
    # Helper function useful for testing.  It will read an entry
    # identified by 'seq' and 'src' from the database opened on the
    # dpapi cursor object 'cur', convert that entry to a JEL text
    # string, parse the text to get a new entry object, and convert
    # that entry object top JEL text.  The text generated from the
    # the original object, and from the parser-generated object,
    # are returned and can be compared.  The should be identical.

        #pdb.set_trace()
        sql = "SELECT id FROM entr WHERE seq=%s AND src=%s"
        obj = jdb.entrList (cur, sql, [seq, src])
        if not obj: return None,None
        for s in obj[0]._sens:
            jdb.augment_xrefs (cur, getattr (s, '_xref', []))
        jeltxt = _get_jel_text (obj[0])
        jellex.lexreset (lexer, jeltxt)
        result = parser.parse (jeltxt,lexer=lexer,tracking=True)
        resolv_xrefs (cur, result)
        jeltxt2 = _get_jel_text (result)
        return jeltxt, jeltxt2

def _get_jel_text (entr):

        '''Generate and return a JEL string from entry object
        'entr'.  The first line (text before the first "\n"
        character) is removed since it contains nformation
        that will vary between objects read from a database
        and created by parsing input text.'''

        jeltxt = fmtjel.entr (entr)
        return jeltxt.partition('\n')[2]

def _interactive (cur, lexer, parser):
        cnt = 0;  instr = ''
        while 1:
            instr = _getinptext ()
            if not instr: break
            jellex.lexreset (lexer, instr)
            try: 
                result = parser.parse(instr,lexer=lexer,debug=opts.debug)
            except ParseError, e: 
                print e
            try:
                resolv_xrefs (cur, result)
            except ValueError:
                print e
            s = fmtjel.entr (result)
            print s

def _getinptext ():
        instr = '';  cnt = 0;  prompt = 'test> '
        while cnt < 1:
            try: s = raw_input(prompt).decode('sjis')
            except EOFError: break
            prompt = ''
            if s: cnt = 0
            else: cnt += 1
            if cnt < 1: instr += s + '\n'
        return instr.rstrip()


def _parse_cmdline ():
        from optparse import OptionParser 
        u = \
"""\n\tpython %prog [-d n][-q SEQ]
        
  This is a simple test/exerciser for the JEL parser.  It operates
  in two different modes depending on the presence or absense of 
  the --seq (-q) option.  

  When present it will read the entry with the given seq number
  from the jmdict corpus in the database, format it as a JEL text 
  string, and parse it.  It prints both the input text and the
  object generated from the parse in the same format, and both
  should be functionally identical.  (There may be non-significant
  differences such as tag order.)

  If the --seq (-q) option is not given, this program will read 
  text input interactively until a blank line is entered, feed the 
  text to the parser, and print the resulting object.  Note that
  because a database is not available in this mode, xrefs will not
  be resolved and thus not appear in the recreated output, even
  if present in the input.
Arguments: (None)
"""
        p = OptionParser (usage=u)
        p.add_option ("-q", "--seq", 
            type="int", dest="seq", default=None,
            help="Parse text generated by reading jmdict seq SEQ from" 
                " database rather than the default behavior of prompting" 
                " interactively for input text.")
        p.add_option ("-d", "--debug",
            type="int", dest="debug", default=0,
            help="Debug value to pass to parser:"
                " 2: Productions,"
                " 4: Shifts,"
                " 8: Reductions,"
                " 16: Actions,"
                " 32: States,"
                " 256: Lexer tokens")
        opts, args = p.parse_args ()
        #...arg defaults can be setup here...
        return args, opts

if __name__ == '__main__': 
        args, opts = _parse_cmdline ()
        main (args, opts)
