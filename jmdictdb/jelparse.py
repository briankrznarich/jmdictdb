
# Copyright (c) 2008-2010 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, ply.yacc, re, unicodedata, pdb
from collections import defaultdict
from jmdictdb import jellex, jdb, restr
from jmdictdb.objects import *

class ParseError (ValueError):
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
        if err: perror (p, err)
    if hasattr (e, '_sens') and hasattr (e, '_kanj'):
        err = mk_restrs ("_STAGK", e._sens, e._kanj)
        if err: perror (p, err)
    if hasattr (e, '_sens') and hasattr (e, '_rdng'):
        err = mk_restrs ("_STAGR", e._sens, e._rdng)
        if err: perror (p, err)
    p[0] = e

def p_preentr_1(p):
    '''preentr : kanjsect FF rdngsect FF senses'''
    p[0] = jdb.Entr(_kanj=p[1], _rdng=p[3], _sens=p[5])

def p_preentr_2(p):
    '''preentr : FF rdngsect FF senses'''
    p[0] = jdb.Entr(_rdng=p[2], _sens=p[4])

def p_preentr_3(p):
    '''preentr : kanjsect FF FF senses'''
    p[0] = jdb.Entr(_kanj=p[1], _sens=p[4])

def p_kanjsect_1(p):
    '''kanjsect : kanjitem'''
    p[0] = [p[1]]

def p_kanjsect_2(p):
    '''kanjsect : kanjsect SEMI kanjitem'''
    p[0] = p[1];  p[0].append (p[3])

def p_kanjitem_1(p):
    '''kanjitem : krtext'''
    p[0] = jdb.Kanj(txt=p[1])

def p_kanjitem_2(p):
    '''kanjitem : krtext taglists'''
    kanj = jdb.Kanj(txt=p[1])
    err = bld_kanj (kanj, p[2])
    if err: perror (p, err)
    p[0] = kanj

def p_rdngsect_1(p):
    '''rdngsect : rdngitem'''
    p[0] = [p[1]]

def p_rdngsect_2(p):
    '''rdngsect : rdngsect SEMI rdngitem'''
    p[0] = p[1];  p[0].append (p[3])

def p_rdngitem_1(p):
    '''rdngitem : krtext'''
    p[0] = jdb.Rdng(txt=p[1])

def p_rdngitem_2(p):
    '''rdngitem : krtext taglists'''
    rdng = jdb.Rdng(txt=p[1])
    err = bld_rdng (rdng, p[2])
    if err: perror (p, err)
    p[0] = rdng

def p_krtext_1(p):
    '''krtext : KTEXT'''
    p[0] = p[1]

def p_krtext_2(p):
    '''krtext : RTEXT'''
    p[0] = p[1]

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
    if err: perror (p, "Unable to build sense %s\n%s" % (p[1], err))
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
    p[0] = p[1]

def p_tags_2(p):
    '''tags : tags COMMA tagitem'''
    p[0] = p[1]
    p[0].extend (p[3])

def p_tagitem_1(p):
    '''tagitem : KTEXT'''
    p[0] = [['RESTR', None, p[1]]]

def p_tagitem_2(p):
    '''tagitem : RTEXT'''
    p[0] = [['RESTR', p[1], None]]

def p_tagitem_3(p):
    '''tagitem : TEXT'''
    if p[1] == 'nokanji':
        p[0] = [['RESTR', 'nokanji', None]]
    else:
        x = lookup_tag (p[1])
        if not x: perror (p, "Unknown keyword: '%s'" % p[1])
        else: p[0] = [[None, p[1]]]

def p_tagitem_4(p):
    '''tagitem : QTEXT'''
    #FIXME: why isn''t a QTEXT already cleaned up by jellex?
    txt = jellex.qcleanup (p[1][1:-1])
      #FIXME: we should check for ascii text here and treat
      #  that as TEXT above.
    if jdb.jstr_keb (txt): p[0] = [['RESTR', None, txt]]
    else:                  p[0] = [['RESTR', txt, None]]

def p_tagitem_5(p):
    '''tagitem : TEXT EQL TEXT'''
    p[0] = [tag_eql_text (p, p[1], p[3])]

def p_tagitem_6(p):
    '''tagitem : TEXT EQL TEXT COLON'''
    KW = jdb.KW
    if p[1] != "lsrc": perror (p, "Keyword must be \"lsrc\"")
    la = KW.LANG.get(p[3])
    if not la: perror (p, "Unrecognised language '%s'" % p[3])
    p[0] = [["lsrc", None, la.id, None]]

def p_tagitem_7(p):
    '''tagitem : TEXT EQL TEXT COLON atext'''
    KW = jdb.KW
    lsrc_flags = None; lang = None
    if p[1] in ["lsrc"]:
        la = KW.LANG.get(p[3])
        if not la:
            if p[3] not in ('w','p','wp','pw'):
                perror (p, "Unrecognised language '%s'" % p[3])
            else: lsrc_flags = p[3]
        else: lang = la.id
    else: perror (p, "Keyword not \"lsrc\", \"lit\", or \"expl\"")
    p[0] = [["lsrc", p[5], lang, lsrc_flags]]

def p_tagitem_8(p):
    '''tagitem : TEXT EQL TEXT SLASH TEXT COLON'''
    KW = jdb.KW
    if p[1] != "lsrc": perror (p, "Keyword not \"lsrc\"")
    la = KW.LANG.get(p[3])
    if not la: perror (p, "Unrecognised language '%s'" % p[3])
    if p[5] not in ('w','p','wp','pw'):
        perror (p, "Bad lsrc flags '%s', must be 'w' (wasei), "
                    "'p' (partial),or both" % p[5])
    p[0] = [["lsrc", '', la.id, p[5]]]

def p_tagitem_9(p):
    '''tagitem : TEXT EQL TEXT SLASH TEXT COLON atext'''
    KW = jdb.KW
    if p[1] != "lsrc": perror (p, "Keyword not \"lsrc\"")
    la = KW.LANG.get(p[3])
    if not la: perror (p, "Unrecognised language '%s'" % p[3])
    if p[5] not in ('w','p','wp','pw'):
        perror (p, "Bad lsrc flags '%s', must be 'w' (wasei), "
                    "'p' (partial),or both" % p[5])
    p[0] = [["lsrc", p[7], la.id, p[5]]]

def p_tagitem_10(p):
    '''tagitem : TEXT EQL jrefs'''
    tag = p[1];  taglist = [];  tagtype = 'XREF';  KW = jdb.KW
    for jref in p[3]:
        dotlist, slist, seq, corpus = jref
        if corpus:
              # Convert corpus name to id number here (rather than
              # than later in say, x2xrslv()), so that any error
              # will point to position close to the corpus text in
              # the input.
            try: corpus = KW.SRC[corpus].id
            except KeyError: perror (p, "Unknown corpus: %s" % corpus)
        if tag in [x.kw for x in KW.recs('XREF')]:
              #FIXME: instead of using XREF kw''s directly, do we want to
              #  change to an lsrc syntax like, "xref=cf:..."
              #  (possibly keeping "see" and "ant" as direct keywords)?
            if len (dotlist) == 1:
                if jdb.jstr_keb (dotlist[0]):
                    taglist.append (['XREF', tag, None, dotlist[0], slist, seq, corpus])
                else:
                    taglist.append (['XREF', tag, dotlist[0], None, slist, seq, corpus])
            elif len (dotlist) == 2:
                taglist.append (['XREF', tag, dotlist[1], dotlist[0], slist, seq, corpus])
            elif len(dotlist) == 0:
                taglist.append (['XREF', tag, None, None, slist, seq, corpus])
            else: perror ("No more than on kanji and one reading string can be given in an xref.")
            continue
          # The full 'jref' syntax is only used by xrefs (above)
          # so if we get here, complain if the 'jref' item has
          # any xref-specific elements.
        if seq or corpus or slist:
            perror ("Seq number, corpus, or a sense list can only be given with xref tags")
          # Xrefs are also the only contruct that uses the middot character
          # syntactically.  Since we don''t have an xref, then the middots are
          # just characters in the text, so put the original text string back
          # together.
        txt = u'\u30FB'.join (dotlist)
        if tag == 'restr':
            if jdb.jstr_keb (txt):
                taglist.append (['RESTR', None, txt])
            else:
                taglist.append (['RESTR', txt, None])
        else:
              # This must be a tag=QTEXT contruct.
            taglist.append (tag_eql_text (p, tag, txt))
    p[0] = taglist

def p_atext_1(p):
    '''atext : TEXT'''
    p[0] = p[1]

def p_atext_2(p):
    '''atext : QTEXT'''
    p[0] = jellex.qcleanup (p[1][1:-1])

def p_jrefs_1(p):
    '''jrefs : jref'''
    p[0] = [p[1]]

def p_jrefs_2(p):
    '''jrefs : jrefs SEMI jref'''
    p[0] = p[1];  p[0].append (p[3])

def p_jref_1(p):
    '''jref : xrefnum'''
    p[0] = [[],[]] + p[1]

def p_jref_2(p):
    '''jref : xrefnum slist'''
    p[0] = [[],p[2]] + p[1]

def p_jref_3(p):
    '''jref : xrefnum DOT jitem'''
    p[0] = p[3] + p[1]

def p_jref_4(p):
    '''jref : jitem'''
    p[0] = p[1] + [None,None]

def p_jref_5(p):
    '''jref : jitem TEXT'''
    p[0] = p[1] + [None, p[2]]

def p_jitem_1(p):
    '''jitem : dotlist'''
    p[0] = [p[1], None]

def p_jitem_2(p):
    '''jitem : dotlist slist'''
    p[0] = [p[1], p[2]]

def p_dotlist_1(p):
    '''dotlist : jtext'''
    p[0] = [p[1]]

def p_dotlist_2(p):
    '''dotlist : dotlist DOT jtext'''
    p[0] = p[1];  p[0].append (p[3])

def p_jtext_1(p):
    '''jtext : KTEXT'''
    p[0] = p[1]

def p_jtext_2(p):
    '''jtext : RTEXT'''
    p[0] = p[1]

def p_jtext_3(p):
    '''jtext : QTEXT'''
    p[0] = jellex.qcleanup (p[1][1:-1])

def p_xrefnum_1(p):
    '''xrefnum : NUMBER'''
    p[0] = [toint(p[1]), None]

def p_xrefnum_2(p):
    '''xrefnum : NUMBER HASH'''
    p[0] = [-toint(p[1]), None]

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
        perror (p, "Invalid sense number: '%s'" % n)
    p[0] = [n]

def p_snums_2(p):
    '''snums : snums COMMA NUMBER'''
    n = int(p[3])
    if n<1 or n>99:
        perror (p, "Invalid sense number: '%s'" % n)
    p[0] = p[1] + [n]

# -------------- RULES END ----------------

def p_error (token):
        # Ply insists on having a p_error function that takes
        # exactly one argument so provide a wrapper around perror.
        perror (token)

def perror (t_or_p, msg="Syntax Error", loc=True):
        # 't_or_p' is either a YaccProduction (if called from
        # jelparse code), a LexToken (if called by Ply), or None
        # (if called by Ply at end-of-text).
        if loc:
            errpos = -1
            if t_or_p is None: errpos = None
            elif hasattr (t_or_p, 'stack'):
                  # 't_or_p' is a production.  Replace with a real token or
                  # grammar symbol from the parser stack.
                t_or_p = t_or_p.stack[-1]
              # Grammar symbols will have a "endlexpos" attribute (presuming
              # that the parse() function was called with argument: tracking=True).
            if hasattr (t_or_p, 'endlexpos'):
                errpos = t_or_p.endlexpos
              # LexTokens will have a "lexpos" attribute.
            elif hasattr (t_or_p, 'lexpos'):
                errpos = t_or_p.lexpos
            if errpos == -1: errpos = None
            t = errloc (errpos)
            loc_text = '\n'.join (t)
        else:
            loc_text = None
        raise ParseError (msg, loc_text)

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
        MARKER = '\u2587\u2587'
        if errpos is None: out = input
        else: out = input[:errpos] + MARKER + input[errpos:]
        out = out.splitlines(0)
        return out

def tag_eql_text (p, tag, text):
        # Process a tag=text syntax contructs as they are parsed.
        # We extract this activity into a function since, in the
        # "tagitem" section, we do it both for the TEXT=TEXT rule,
        # and TEXT=QTEXT (which is a possible condition in the
        # TEXT=jrefs rule.)

        if tag in ["note","lsrc","restr"]:
            if tag == "restr":
                if text != "nokanji":
                    perror (p, "Bad restr value (expected \"nokanji\"): '%s'" % p[3])
                r = ["RESTR", "nokanji", None]
            else: r = [tag, text, 1, None]
        else:
            x = lookup_tag (text, tag)
            if x and len(x) > 1:
                raise ValueError ("Unexpected return value from lookup_tag()")
            if x is None: perror (p, "Unknown keyword type '%s'" % tag)
            elif not x:   perror (p, "Unknown %s keyword '%s'" % (tag,text))
            else:         r = x[0]
        return r

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
        if isinstance (typs, str): typs = [typs]
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
                return None
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
              # Each tag, t, is a list where t[0] is the tag type (aka
              # domain) as a string, or None if it is unknown.  There
              # will be one or more additional items in the list, the
              # number depending on what type of tag it is.
            vals = None
            typ = t.pop(0)      # Get the item type.

            if typ is None:
                  # Unknown domain (that is, user gave a simple unadorned
                  # tag like [n] rather than [pos=n]) so figure it what
                  # domain it belongs to...
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
                      # There is currently only one ambiguity: "lit" may
                      #  be either GINF "literal" or LANG "Lithuanian".
                      #  We unilaterally choose the former interpretation
                      #  as it is much more common than the latter, and
                      #  the latter when needed can be specified as
                      #  [lang=lit].
                    candidate = candidates[0]
                    typ = candidate[0];  t = [candidate[1]]
            if typ is None:
                errs.append ("Unknown tag '%s'" % t)
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
                # We can't create real _stagk or _stagr lists here
                # because the readings and kanji we are given by the user
                # are allowed ones, but we need to store disallowed ones.
                # To get the disallowed ones, we need access to all the
                # readings/kanji for this entry and we don't have that
                # info at this point.  So we do what checking we can. and
                # save the texts as given, and will fix later after the
                # full entry is built and we have access to the entry's
                # readings and kanji.

                rtxt,ktxt = t
                #if num or corp:
                if ((rtxt and ktxt) or (not rtxt and not ktxt)):
                    errs.append ("Sense restrictions must have a "
                                 "reading or kanji (but not both): "
                                 + fmt_xitem (t))
                if ktxt: append (sens, '_STAGK', ktxt)
                if rtxt: append (sens, '_STAGR', rtxt)

            elif typ == 'lsrc':
                wasei   = t[2] and 'w' in t[2]
                partial = t[2] and 'p' in t[2]
                append (sens, '_lsrc',
                        jdb.Lsrc(txt=t[0] or '', lang=(t[1] or lang_en),
                                part=partial, wasei=wasei))

            elif typ == 'note':
                if getattr (sens, 'notes', None):
                    errs.append ("Only one sense note allowed")
                sens.notes = t[0]

            elif typ == 'XREF':
                kw = KW.XREF[t[0]].id
                t[0] = kw
                sens._xrslv.extend (x2xrslv (t))

            elif typ == 'GINF':
                t = t[0]        # GINF tags have only one value, the ginf code.
                if getattr (gloss, 'ginf', None):
                    errs.append (
                        "Warning, duplicate GINF tag '%s' ignored\n" % KW.GINF[t].kw)
                else: gloss.ginf = t

            elif typ == 'LANG':
                t = t[0]        # LANG tags have only one value, the lang code.
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
                    errs.append ("Unknown reading tag '%s'" % t[0])
                else:
                    typ, t = v[0][0], v[0][1:]
            if typ == 'RINF': append (r, '_inf', jdb.Rinf(kw=t[0]))
            elif typ == 'FREQ':
                append (r, '_freq', Freq (kw=t[0], value=t[1]))
            elif typ == 'RESTR':
                # We can't generate real restr records here because the real
                # records are the disallowed kanji.  We have the allowed
                # kanji here and need the set of all kanji in order to get
                # the disallowed set, and we don't have that now.  So we
                # just save the allowed kanji as given, and will convert it
                # after the full entry is built and we have all the info we
                # need.
                #for xitem in t[0]:
                      # An xitem represents a reference to another entry
                      # or other info within an entry, in textual form.  It
                      # is used for xrefs and restr info.  It is a 5-seq
                      # with the following values:
                      #   [0] -- Reading text
                      #   [1] -- Kanji text
                      # For a reading restr, it is expected to contain only
                      # a kanji text.
                rtxt,ktxt = t
                if rtxt == "nokanji":
                    nokanj = True
                    r._NOKANJI = 1
                    continue
                if rtxt:
                    errs.append ("Reading restrictions must be kanji only: " + rtxt)
                append (r, "_RESTR", ktxt)
                if hasattr (r,'_RESTR') and nokanj:
                    errs.append ("Can't use both kanji and \"nokanji\" in 'restr' tags")
            elif typ:
                errs.append ("Cannot use '%s' tag in a reading" % typ)
        return "\n".join (errs)

def bld_kanj (k, taglist=[]):
        errs = []
        for t in taglist:
            typ = t.pop(0)
            if typ is None:
                v = lookup_tag (t[0], ('KINF','FREQ'))
                if not v: perror ("Unknown kanji tag '%s'" % t[0])
                  # Warning: The following simply uses the first resolved tag in
                  # the candidates list returned by lookup_tag().  This assumes
                  # there are no possible tags that are ambiguous in the KINF and
                  # FREQ which could cause lookup_tag() to return more than one
                  # candidate tags.
                typ, t = v[0][0], v[0][1:]
            if typ == "KINF": append (k, "_inf", jdb.Kinf(kw=t[0]))
            elif typ == "FREQ":
                append (k, "_freq", jdb.Freq (kw=t[0], value=t[1]))
            else:
                errs.append ("Cannot use '%s' tag in kanji section" % typ);
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
            restrtxts = getattr (r, listkey, None)
            if restrtxts: delattr (r, listkey)
            nokanj = getattr (r, '_NOKANJI', None)
            if nokanj: delattr (r, '_NOKANJI')

              # Continue with next reading if nothing to be done
              # with this one.
            if not nokanj and not restrtxts: continue

              # bld_rdngs() guarantees that {_NOKANJI} and {_RESTR}
              # won't both be present on the same rdng.
            if nokanj and not kanjs:
                  # Only rdng-kanj restriction should have "nokanji" tag, so
                  # message can hardwire "reading" and "kanji" text even though
                  # this function in also used for sens-rdng and sens-kanj
                  # restrictions.
                msg = "Reading %d has 'nokanji' tag but entry has no kanji"\
                      % (n+1)
                errs.append (msg)
                continue
            if nokanj: restrtxts = None
              # txt2restr() will lookup each string in list 'restrtxts'
              # in list of Kanj/Rdng items, 'kanjs', and then for each,
              # create a Restr/Stagr/Stagk item and append it to the
              # proper attribute (.restr/.stanr/.stagk) of Rdng/Sens
              # item 'r'.  If the resttxts sting is not found, a KeyError
              # is raised.
            try: z = restr.txt2restr (restrtxts, r, kanjs, listkey.lower())
            except KeyError as e: errs.append (str (e))
        return "\n".join (errs)

def x2xrslv (t):
        # The parsed xrefs are turned into unresolved xrefs; we
        # don't try to resolve them here since we don't want JEL
        # parsing to be dependent on having access to a populated
        # database.  This is similar to how jmparse (the XML parser)
        # does it, the unresolved xrefs can be resolved in a later
        # step when the database is accessible.
          # 't' is the info for a JEL XREF tag, specifically:
          #   [0] -- xref type already mapped to KW.XREF id number.
          #   [1] -- Target reading text or None.
          #   [2] -- Target kanji text or None.
          #   [3] -- List of target senses, may be None.
          #   [4] -- Target sequence number (if positive) or target
          #          entry id number (if negative) or None.
          #   [5] -- Target corpus id number or None (=resolve against
          #          the entry's '.src' corpus.)  See yacc rule
          #          "tagitem|TEXT EQL jrefs", also rules "xrefnum"
          #          and "jref".
        results = []
        for s in t[3] or [None]:
            x = Xrslv (typ=t[0], rtxt=t[1], ktxt=t[2], tsens=s,
                       vsrc=t[5], vseq=t[4])
            results.append (x)
        return results

def resolv_xrefs (cur, entr):  #FIXME: Temp shim for back compatibility.
        errs = jdb.xresolv (cur, entr)
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
        if len (xitem) == 5: rtxt, ktxt, slist, num, corp = xitem
        else: rtxt, ktxt, slist, num, corp = xitem + [[], None, None]
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

def parse_grp (grpstr):
        rv = [];  KWGRP = jdb.KW.GRP
        if not grpstr.strip(): return rv
          #FIXME: Handle grp.notes which is currently ignored.
        for g in grpstr.split (';'):
            grp, x, ord = g.strip().partition ('.')
            if grp.isdigit(): grp = int(grp)
            grp = KWGRP[grp].id
            ord = int(ord)
            rv.append (Grp (kw=grp, ord=ord))
        return rv

def create_parser (lexer, toks, **args):
          # Set global JelParser since we need access to it
          # from error handling function p_error() and I don't
          # know any other way to make it available there.
        global tokens, JelParser
          # The tokens also have to be global because Ply
          # doesn't believe in user function parameters for
          # argument passing.
        tokens = toks

          # The following sets default keyword arguments to
          # to Ply's parser factory function.  These are
          # intended to cause it to use the "jelparse_tab.py"
          # file that should be in sys.path somewhere (either
          # in the development dir's python/lib, or in the
          # web lib dir.) so as to prevent Ply from trying
          # to rebuild it, and worse, writing it like bird
          # droppings wherever we happen to be running.

        if 'module'       not in args: args['module']       = sys.modules['jmdictdb.jelparse']
        if 'tabmodule'    not in args: args['tabmodule']    = 'jelparse_tab'
        if 'write_tables' not in args: args['write_tables'] = 1
        if 'optimize'     not in args: args['optimize']     = 1
        if 'debug'        not in args: args['debug']        = 0

        JelParser = ply.yacc.yacc (**args)
        JelParser.lexer = lexer   # Access to lexer needed in error handler.
        return JelParser
