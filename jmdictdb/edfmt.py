# -*- coding: utf-8 -*-       # non-ascii used in comments only.
# Copyright (c) 2009 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later


import sys, pdb
from . import jdb, fmt
from .objects import *

def entr (e):
        _kanjs = getattr (e, '_kanj', [])
        _rdngs = getattr (e, '_rdng', [])
        _senss = getattr (e, '_sens', [])
        k = (kanjs (_kanjs))
        r = (rdngs (_rdngs, _kanjs))
        s = (senss (_senss, _rdngs, _kanjs, jdb.is_p(e)))
        if k: r = '[' + r + ']'
        if s: s = '/' + s + '/'
        t = []
        if k: t.append (k)
        if r: t.append (r)
        if s: t.append (s)
        return ' '.join (t)

def kanjs (_kanjs):
        markp = len(_kanjs) > 1 #FIXME: is this right? check against xsl.
        t = ';'.join ([kanj(k, markp) for k in _kanjs])
        return t

def kanj (_kanj, markp=False):
        KW = jdb.KW
        t = _kanj.txt
        infs = [KW.KINF[x.kw].kw for x in getattr(_kanj,'_inf',[])]
        infs = ('(' + ','.join(infs) + ')') if infs else ''
        p = '(P)' if markp and jdb.is_pj (_kanj) else ''
        return t + infs + p

def rdngs (_rdngs, kanjs):
        markp = len(_rdngs) > 1 #FIXME: is this right? check against xsl.
        t = ';'.join ([rdng(r, kanjs, markp) for r in _rdngs])
        return t

def rdng (_rdng, kanjs, markp=False):
        KW = jdb.KW
        t = _rdng.txt
        infs = [KW.RINF[x.kw].kw for x in getattr(_rdng,'_inf',[])]
        infs = ('(' + ','.join(infs) + ')') if infs else ''
        p = '(P)' if (markp and jdb.is_pj (_rdng)) else ''
        restrtxt = ';'.join (jdb.restrs2txts (_rdng, kanjs, '_restr'))
        if restrtxt == 'nokanji': restrtxt = '' # Edict2 format doesn't use "nokanji".
        if restrtxt: restrtxt = "(" + restrtxt + ")"
        return t + restrtxt + infs + p

def senss (_senss, kanjs, rdngs, isp=False):
        KW = jdb.KW
        gtxts = []; prev_posstr = None
          # Tag order:
          #   POS, sense_num, STAG, see, ant, MISC, DIAL, FLD, s_inf, ginf (e.g. lit:)
        for n, s in enumerate (_senss):
            spre = []

              # To do: see, ant, lsrc.
            if getattr (s, '_pos', None):
                posstr = '(%s)' % ','.join([KW.POS[x.kw].kw for x in s._pos])
                if not prev_posstr or posstr != prev_posstr:
                    spre.append (posstr)
                    prev_posstr = posstr
            if n > 0: spre.append ("(%d)" % (n+1))
            stagk = jdb.restrs2txts (s, kanjs, '_stagk')
            stagr = jdb.restrs2txts (s, rdngs, '_stagr')
            stag = stagk + stagr
            if stag: spre.append ("( %s only)" % ', '.join (stag))
            if getattr (s, '_xref', []): pass   #FIXME
            if getattr (s, '_misc', None): spre.append (
                '(%s)' % ','.join([KW.MISC[x.kw].kw for x in s._misc]))
            if getattr (s, '_dial', None): spre.append (
                '(%s)' % ','.join([KW.DIAL[x.kw].kw + ':' for x in s._dial]))
            if getattr (s, '_fld', None): spre.append (
                '{%s}' % ','.join([KW.FLD[x.kw].kw for x in s._fld]))
            if getattr (s, 'notes', None): spre.append ('(%s)' % s.notes)
            spre = ' '.join (spre)
            if spre: spre += ' '

            for m, g in enumerate (s._gloss):
                if g.ginf != 1:
                    ginf = KW.GINF[g.ginf].kw + ":"
                      # If this is the first gloss in a sense, prefix it
                      # with the ginf tag (by appending ginf to the prefixes
                      # list.)
                    if m == 0: spre += ginf + ' '
                      # If not the first gloss in the sense, then put the
                      # ginf tagged gloss in parens and append it to the
                      # previous gloss.  This more or less reverses the
                      # extraction of "lit:" glosses, etc, into separate
                      # that occurs during parsing.
                    else:
                        gtxts[-1] += " (%s %s)" % (ginf, g.txt)
                        continue
                gtxts.append (spre + g.txt)
                spre = ''
        if isp: gtxts.append ('(P)')
        return '/'.join (gtxts)
