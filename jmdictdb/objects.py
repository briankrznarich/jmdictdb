# Copyright (c) 2006-2012 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, pdb
from jmdictdb.db import DbRow, Obj

#  NOTE:
#  When adding/deleting/modifying the classes below, be sure to
#  check in python/lib/serialize.py for any corresponding changes
#  that need to be made there.
#
# JMdictDB database objects...
# * Each corresponds to a database table containing some
#    part of a dictionary entry object.
# * Based on DbRow so that column values can be accessed
#    by attribute or index.
# * Fields used to initialize DbRow part correspond exactly
#    to the database columns for the table come first in the
#    parameter list and aren't prefixed with underscores.
# * Extra fields (that don't represent columns in the table)
#    follow in the parameter list.  If they have list values,
#    they are prefixed with an "_".  The attributes are for
#    lists of JMdictDB database objects from other tables
#    having a 1:N relationship with this table.

class Entr (DbRow):
    def __init__ (s, id=None, src=None, stat=None, seq=None, dfrm=None,
                     unap=None, srcnote=None, notes=None, idx=None,
                     _kanj=None, _rdng=None, _sens=None, _hist=None,
                     _snd=None, _grp=None, chr=None, _krslv=None):
        DbRow.__init__(s, ( id,  src,  stat,  seq,  dfrm,  unap,  srcnote,  notes,  idx),
                          ('id','src','stat','seq','dfrm','unap','srcnote','notes','idx'))
        s._kanj = _kanj or []
        s._rdng = _rdng or []
        s._sens = _sens or []
        s._hist = _hist or []
        s._snd  = _snd  or []
        s._grp  = _grp  or []
        s.chr   =  chr
        s._krslv = _krslv  or []

class Rdng (DbRow):
    def __init__ (s, entr=None, rdng=None, txt=None,
                     _inf=None, _freq=None, _restr=None, _snd=None):
        DbRow.__init__(s, ( entr,  rdng,  txt),
                          ('entr','rdng','txt'))
        s._inf   = _inf   or []
        s._freq  = _freq  or []
        s._restr = _restr or []
        s._snd   = _snd   or []

class Kanj (DbRow):
    def __init__ (s, entr=None, kanj=None, txt=None,
                     _inf=None, _freq=None):
        DbRow.__init__(s, ( entr,  kanj,  txt),
                          ('entr','kanj','txt'))
        s._inf   = _inf   or []
        s._freq  = _freq  or []

class Sens (DbRow):
    def __init__ (s, entr=None, sens=None, notes=None,
                     _gloss=None, _pos=None, _misc=None, _fld=None,
                     _dial=None, _lsrc=None, _stagr=None, _stagk=None,
                     _xref=None, _xrer=None, _xrslv=None):
        DbRow.__init__(s,  (entr,  sens,  notes),
                          ('entr','sens','notes'))
        s._gloss = _gloss or []
        s._pos   = _pos   or []
        s._misc  = _misc  or []
        s._fld   = _fld   or []
        s._dial  = _dial  or []
        s._lsrc  = _lsrc  or []
        s._stagr = _stagr or []
        s._stagk = _stagk or []
        s._xref  = _xref  or []
        s._xrer  = _xrer  or []
        s._xrslv = _xrslv or []

class Gloss (DbRow):
      #FIXME: change param order to: ...,txt,ginf,lang.  This will allow
      # ginf and lang to to be defaulted more easily.  But can we do this
      # given the DB column order matches current param order?
    def __init__ (s, entr=None, sens=None, gloss=None, lang=None, ginf=None, txt=None):
        DbRow.__init__(s, ( entr,  sens,  gloss,  lang,  ginf,  txt),
                          ('entr','sens','gloss','lang','ginf','txt'))

class Rinf (DbRow):
    def __init__ (s, entr=None, rdng=None, ord=None, kw=None):
        DbRow.__init__(s, ( entr,  rdng,  ord,  kw),
                          ('entr','rdng','ord','kw'))

class Kinf (DbRow):
    def __init__ (s, entr=None, kanj=None, ord=None, kw=None):
        DbRow.__init__(s, ( entr,  kanj,  ord,  kw),
                          ('entr','kanj','ord','kw'))

class Freq (DbRow):
    def __init__ (s, entr=None, rdng=None, kanj=None, kw=None, value=None):
        DbRow.__init__(s, ( entr,  rdng,  kanj,  kw,  value),
                          ('entr','rdng','kanj','kw','value'))

class Restr (DbRow):
    def __init__ (s, entr=None, rdng=None, kanj=None):
        DbRow.__init__(s, ( entr,  rdng,  kanj),
                          ('entr','rdng','kanj'))

class Stagr (DbRow):
    def __init__ (s, entr=None, sens=None, rdng=None):
        DbRow.__init__(s, ( entr,  sens,  rdng),
                          ('entr','sens','rdng'))

class Stagk (DbRow):
    def __init__ (s, entr=None, sens=None, kanj=None):
        DbRow.__init__(s, ( entr,  sens,  kanj),
                          ('entr','sens','kanj'))

class Pos (DbRow):
    def __init__ (s, entr=None, sens=None, ord=None, kw=None):
        DbRow.__init__(s, ( entr,  sens,  ord,  kw),
                          ('entr','sens','ord','kw'))

class Misc (DbRow):
    def __init__ (s, entr=None, sens=None, ord=None, kw=None):
        DbRow.__init__(s, ( entr,  sens,  ord,  kw),
                          ('entr','sens','ord','kw'))

class Fld (DbRow):
    def __init__ (s, entr=None, sens=None, ord=None, kw=None):
        DbRow.__init__(s, ( entr,  sens,  ord,  kw),
                          ('entr','sens','ord','kw'))

class Dial (DbRow):
    def __init__ (s, entr=None, sens=None, ord=None, kw=None):
        DbRow.__init__(s, ( entr,  sens,  ord,  kw),
                          ('entr','sens','ord','kw'))

class Lsrc (DbRow):
    def __init__ (s, entr=None, sens=None, ord=None, lang=1, txt=None, part=False, wasei=False):
        DbRow.__init__(s, ( entr,  sens,  ord,  lang,  txt,  part,  wasei),
                          ('entr','sens','ord','lang','txt','part','wasei'))

class Xref (DbRow):
    def __init__ (s, entr=None, sens=None, xref=None, typ=None, xentr=None, xsens=None,
                  rdng=None, kanj=None, notes=None, nosens=None, lowpri=None):
        DbRow.__init__(s, ( entr,  sens,  xref,  typ,  xentr,  xsens,  rdng,  kanj,  notes,  nosens,  lowpri),
                          ('entr','sens','xref','typ','xentr','xsens','rdng','kanj','notes','nosens','lowpri'))

class Hist (DbRow):
    def __init__ (s, entr=None, hist=None, stat=None, unap=None, dt=None, userid=None, name=None,
                  email=None, diff=None, refs=None, notes=None, eid=None):
        DbRow.__init__(s, ( entr,  hist,  stat,  unap,  dt,  userid,  name,  email,  diff,  refs,  notes,  eid),
                          ('entr','hist','stat','unap','dt','userid','name','email','diff','refs','notes','eid'))

class Grp (DbRow):
    def __init__ (s, entr=None, kw=None, ord=None, notes=None):
        DbRow.__init__(s, ( entr,  kw,  ord,  notes),
                          ('entr','kw','ord','notes'))

class Cinf (DbRow):
    def __init__ (s, entr=None, kw=None, value=None, mctype=None):
        DbRow.__init__(s, ( entr,  kw,  value,  mctype),
                          ('entr','kw','value','mctype'))

class Chr (DbRow):
    def __init__ (s, entr=None, chr=None, bushu=None, strokes=None,
                  freq=None, grade=None, jlpt=None, _cinf=None):
        DbRow.__init__(s, ( entr,  chr,  bushu,  strokes,  freq,  grade,  jlpt),
                          ('entr','chr','bushu','strokes','freq','grade','jlpt'))
        s._cinf = _cinf or []

class Xrslv (DbRow):
    def __init__ (s, entr=None, sens=None, ord=None, typ=None,
                  rtxt=None, ktxt=None, tsens=None,
                  vsrc=None, vseq=None, notes=None, prio=None):
        DbRow.__init__(s, ( entr,  sens,  ord,  typ,  rtxt,  ktxt,  tsens,  vsrc,  vseq,  notes,  prio),
                          ('entr','sens','ord','typ','rtxt','ktxt','tsens','vsrc','vseq','notes','prio'))

class Krslv (DbRow):
    def __init__ (s, entr=None, kw=None, value=None):
        DbRow.__init__(s, ( entr,  kw,  value),
                          ('entr','kw','value'))

class Entrsnd (DbRow):
    def __init__ (s, entr=None, ord=None, snd=None):
        DbRow.__init__(s, ( entr,  ord,  snd),
                          ('entr','ord','snd'))

class Rdngsnd (DbRow):
    def __init__ (s, entr=None, rdng=None, ord=None, snd=None):
        DbRow.__init__(s, ( entr,  rdng,  ord,  snd),
                          ('entr','rdng','ord','snd'))

class Snd (DbRow):
    def __init__ (s, id=None, file=None, strt=None, leng=None, trns=None, notes=None):
        DbRow.__init__(s, ( id,  file,  strt,  leng,  trns,  notes),
                          ('id','file','strt','leng','trns','notes'))

class Sndfile (DbRow):
    def __init__ (s, id=None, vol=None, title=None, loc=None, type=None, notes=None):
        DbRow.__init__(s, ( id,  vol,  title,  loc,  type,  notes),
                          ('id','vol','title','loc','type','notes'))

class Sndvol (DbRow):
    def __init__ (s, id=None, title=None, loc=None, type=None, idstr=None, corp=None, notes=None):
        DbRow.__init__(s, ( id,  title,  loc,  type,  idstr,  corp,  notes),
                          ('id','title','loc','type','idstr','corp','notes'))
