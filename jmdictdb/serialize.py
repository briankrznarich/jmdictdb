# Copyright (c) 2019,2020 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# Serialize and deserialize a jdb.Entr object.
# The current version reconstructs a jdb.Entr object that is
# functionally equivalent but not identical to the original
# Entr object.  A reconstructed object may not compare equal
# to the original object but should function equivalently.
# In particular:
# - Fields representing foreign key values and order in the
#   database (the .entr, .rdng, .kanj. .sens, .gloss attribute
#   values, etc.) are not neccesarily preserved since the
#   relationships are implicit in objects' presence in lists
#   bound to a parent object.
# - Fields used to order an object among siblings may not be
#   preserved since order in implicit in lists.
# - For example. an object:
#     Entr(id=334455,..., _rdng=[Rdng(entr=334455,rdng=2,txt=...)
#   will be serialized and reconstructed as:
#     Entr(id=334455,..., _rdng=[Rdng(entr=None,rdng=None,txt=...)
#   The FK and order attributes of all an entry's sub-objects
#   can be set by jdb.setkeys().

import sys, datetime, pdb
import json, zlib, base64, urllib.parse
from jmdictdb import jdb, dbver
from jmdictdb.objects import *
from pprint import pprint as pp    # For debugging.

def serialize (entr, compress=False):
        s = jencode (entr)
        if compress:
            b = s.encode ('utf-8')
            b = zlib.compress (b)
            b = base64.b64encode (b)
            s = urllib.parse.quote_plus (b)
        return s

def unserialize (s):
        s = s.strip()
        if s[0] not in '{[':
            s = urllib.parse.unquote_plus (s)
            b = base64.b64decode (s)
            b = zlib.decompress (b)
            s = b.decode ('utf-8')
        entr = jdecode (s)
        return entr

def jencode (entr, ascii=False):
        r = e2t (entr)
        wrap = {"jmver": [("%0.6x"%x) for x in dbver.DBVERS],
                "entry": r}
        jstr = json.dumps (wrap, ensure_ascii=ascii)
        return jstr

def jdecode (jstr):
        wrap = json.loads (jstr)
          #FIXME: check version number in 'wrap'.
        entr = t2e (wrap["entry"])
        return entr

#-----------------------------------------------------------------------------
# Generate a JSONifyable data structure from an Entr instance (e2t)
# or reconstruct an Entr instance from the data structure (t2e).
# Entr objects are trees of data and can thus be represented and
# recontructed from nested lists.  (Prior to revs 190608-620303c
# and 190429-ecd5374 which restructured the _restr and _freq lists
# respectively, the data in Entr objects was an acyclic graph.
# Previous revs also allowed JSONification of arbitrary sub-parts
# of Entr objects (e.g. Rdng objects) which we have dispensed with.)
#
# The reconstructed Entr object is functionally equivalent to the
# original but not necessarily equal to it; in particular, foreign
# key and order fields are not reproduce since their values are
# implied by the object's position in its containing list.

def e2t (e): return (    # Entr object -> nested lists
        e.id,e.src,e.stat,e.seq,e.dfrm,e.unap,e.srcnote,e.notes,e.idx,
        [(k.txt,
            [i.kw for i in k._inf],
            [(f.kw,f.value) for f in k._freq])
            for k in e._kanj],
        [(r.txt,
            [i.kw for i in r._inf],
            [(f.kw,f.value) for f in r._freq],
            [rk.kanj for rk in r._restr],
            [s.snd for s in r._snd],)
            for r in e._rdng],
        [(s.notes,
            [(g.lang,g.ginf,g.txt) for g in s._gloss],
            [x.kw for x in s._pos],
            [x.kw for x in s._misc],
            [x.kw for x in s._fld],
            [x.kw for x in s._dial],
            [(x.lang,x.txt,x.part,x.wasei) for x in s._lsrc],
            [x.rdng for x in s._stagr],
            [x.kanj for x in s._stagk],
            [(x.typ,x.xentr,x.xsens,      # .entr,.sens,.xref omitted.
              x.rdng,x.kanj,x.notes,x.nosens,x.lowpri) for x in s._xref],
            [(x.entr,x.sens,x.xref,x.typ, # .xentr,.xsens omitted.
              x.rdng,x.kanj,x.notes,x.nosens,x.lowpri) for x in s._xrer],
            [(x.typ,x.rtxt,x.ktxt,x.tsens,x.vsrc,x.vseq,x.notes,x.prio)
              for x in s._xrslv],)
            for s in e._sens],
        [(h.stat,h.unap,ts2str(h.dt),h.userid,h.name,h.email,
            h.diff,h.refs,h.notes) for h in e._hist],
        [(x.id,x.file,x.strt,x.leng,x.trns,x.notes)
            for x in e._snd],
        [(x.kw,x.notes) for x in e._grp],
        None if not e.chr else
            (e.chr.chr,e.chr.bushu,e.chr.strokes,
             e.chr.freq,e.chr.grade,e.chr.jlpt,
             [(i.kw,i.value,i.mctype) for i in e.chr._cinf]),
        [(x.kw,x.value) for x in e._krslv],)

def t2e (t):  # Inverse of e2t(): nestsed lists -> Entr object
        id, src, stat, seq, dfrm, unap, srcnote, notes, idx, \
          pkanj, prdng, psens, phist, psnd, pgrp, pchr, pkrslv = t
        e = Entr (id, src, stat, seq, dfrm, unap, srcnote, notes, idx,
            _kanj=[Kanj(txt=k[0],
                        _inf=[Kinf(kw=x) for x in k[1]],
                        _freq=[Freq(kw=kw,value=v) for kw,v in k[2]]
                        ) for k in pkanj],
            _rdng=[Rdng(txt=r[0],
                        _inf=[Rinf(kw=x) for x in r[1]],
                        _freq=[Freq(kw=k,value=v) for k,v in r[2]],
                        _restr=[Restr(kanj=x) for x in r[3]],
                        _snd=[Snd(*x) for x in r[4]]
                        ) for r in prdng],
            _sens=[Sens(notes=s[0],
                        _gloss=[Gloss(None,None,None,*g) for g in s[1]],
                        _pos=[Pos(kw=x) for x in s[2]],
                        _misc=[Misc(kw=x) for x in s[3]],
                        _fld=[Fld(kw=x) for x in s[4]],
                        _dial=[Dial(kw=x) for x in s[5]],
                        _lsrc=[Lsrc(lang=lang,txt=txt,part=part,wasei=wasei)
                              for lang,txt,part,wasei in s[6]],
                        _stagr=[Stagr(rdng=x) for x in s[7]],
                        _stagk=[Stagk(kanj=x) for x in s[8]],
                        _xref=[Xref(None,None,None,typ,xentr,xsens,
                                    rdng,kanj,notes,nosens,lowpri)
                               for typ,xentr,xsens,rdng,kanj,notes,nosens,lowpri
                               in s[9]],
                        _xrer=[Xref(entr,sens,xref,typ,None,None,
                                    rdng,kanj,notes,nosens,lowpri)
                               for entr,sens,xref,typ,rdng,kanj,notes,nosens,lowpri
                               in s[10]],
                        _xrslv=[Xrslv(None,None,None,typ,rtxt,ktxt,tsens,
                                      vsrc,vseq,notes,prio)
                                for typ,rtxt,ktxt,tsens,vsrc,vseq,notes,prio
                                in s[11]])
                   for s in psens],
            _hist=[Hist(None,None,stat,unap,str2ts(dt),
                        userid,name,email,diff,refs,notes)
                   for stat,unap,dt,userid,name,email,diff,refs,notes
                   in phist],
            _snd=[Snd(*x) for x in psnd],
            _grp=[Grp(kw=kw,notes=notes) for kw,notes in pgrp],
            chr=None if not pchr else \
                Chr(None,*pchr[:6],
                    [Cinf(kw=k,value=v,mtype=m) for k,v,m in pchr[6]]),
            _krslv=[Krslv(kw=k,value=v) for k,v in pkrslv],
            )
        return e

# The following two functions serialize and de-serialize
# jmcgi.SearchItems objects.

def so2js (obj):
        # Convert a SearchItems object to JSON.

        js = obj.__dict__.copy()
        if  hasattr (obj, 'txts'):
            txts = [x.__dict__.copy() for x in obj.txts]
            if txts: js['txts'] = txts
        soj = json.dumps (js)
        return soj

def js2so (soj):
        # Convert a JSON-serialized SearchItems object back to an
        # object.  For convenience, we don't restore it to a SearchItem
        # but to an Obj.  SearchItem's purpose is to prevent adding
        # unexpected attributes, something we don't have to worry about
        # here since we're receiving one that was already checked.
        # 'soj' is a serialized SearchItems object to be restored.

        js = json.loads (soj)
        obj = jdb.Obj()
        obj.__dict__ = js
        sis = []
        for si in js.get ('txts', []):
            o = jdb.Obj()
            o.__dict__ = si
            sis.append (o)
        if sis: obj.txts = sis
        return obj

def ts2str (dt):        # Convert datetime timestamp to str.
        if not dt: return None
        return dt.strftime ("%Y-%m-%d %H:%M:%S")

def str2ts (s):         # Convert str to datetime timestamp.
        if not s: return None
        return datetime.datetime.strptime (s, "%Y-%m-%d %H:%M:%S")

def main():
        cur = jdb.dbopen ('jmdict')
        e = jdb.entrList (cur, None, [1971310])[0]
        x = serialize (e, compress=False)
        d = unserialize (x)
        jdb.setkeys (d)
        print ("MATCH!!" if e==d else "BZZZ, sorry.")
        pdb.set_trace()

  # Assuming you are cd'd to jmdictdb/ when running this, you will
  # need to run like:
  #   PYTHONPATH='..' python3 -mpdb serialize.py
  # to make sure the local modules are imported.

if __name__ == '__main__': main()
