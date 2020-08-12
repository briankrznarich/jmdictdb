# Copyright (c) 2006-2012 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Module: Functions for writing Postgres "COPY" data to ".pgi" files.
"""
import sys, os, operator, datetime
from jmdictdb import jdb

def wrentr (e, workfiles):
        _wrrow (e, workfiles['entr'])
        for r in getattr (e, '_rdng', []):
            _wrrow (r, workfiles['rdng'])
            for x in getattr (r, '_inf',   []): _wrrow (x, workfiles['rinf'])
            for x in getattr (r, '_freq',  []): _wrrow (x, workfiles['freq'])
            for x in getattr (r, '_restr', []): _wrrow (x, workfiles['restr'])
            for x in getattr (r, '_snd',   []): _wrrow (x, workfiles['rdngsnd'])
        for k in getattr (e, '_kanj', []):
            _wrrow (k, workfiles['kanj'])
            for x in getattr (k, '_inf',   []): _wrrow (x, workfiles['kinf'])
            for x in getattr (k, '_freq',  []):
                if not x.rdng: _wrrow (x, workfiles['freq'])
        for s in getattr (e, '_sens', []):
            _wrrow (s, workfiles['sens'])
            for x in getattr (s, '_gloss', []): _wrrow (x, workfiles['gloss'])
            for x in getattr (s, '_pos',   []): _wrrow (x, workfiles['pos'])
            for x in getattr (s, '_misc',  []): _wrrow (x, workfiles['misc'])
            for x in getattr (s, '_fld',   []): _wrrow (x, workfiles['fld'])
            for x in getattr (s, '_dial',  []): _wrrow (x, workfiles['dial'])
            for x in getattr (s, '_lsrc',  []): _wrrow (x, workfiles['lsrc'])
            for x in getattr (s, '_stagr', []): _wrrow (x, workfiles['stagr'])
            for x in getattr (s, '_stagk', []): _wrrow (x, workfiles['stagk'])
            for x in getattr (s, '_xref',  []): _wrrow (x, workfiles['xref'])
            for x in getattr (s, '_xrer',  []): _wrrow (x, workfiles['xref'])
            for x in getattr (s, '_xrslv', []): _wrrow (x, workfiles['xresolv'])
        for x in getattr (e, '_snd',   []): _wrrow (x, workfiles['entrsnd'])
        for x in getattr (e, '_hist',  []): _wrrow (x, workfiles['hist'])
        for x in getattr (e, '_grp',   []): _wrrow (x, workfiles['grp'])
        for x in getattr (e, '_krslv', []): _wrrow (x, workfiles['kresolv'])
        if e.chr is not None:
            _wrrow (e.chr, workfiles['chr'])
            for x in e.chr._cinf: _wrrow (x, workfiles['cinf'])

def wrcorpora (corpora, defcorp, deftype, workfiles):
        for cname, (ctype, id) in corpora.items():
            if not cname: cname = defcorp
            if not ctype: ctype = deftype
            rowobj = jdb.Obj (id=id, kw=cname, seq='seq_'+cname, srct=ctype)
            _wrrow (rowobj, workfiles['kwsrc'])

def wrgrpdef (rowobj, workfiles):
        _wrrow (rowobj, workfiles['kwgrp'])

def wrsnd (cur, workfiles):
        vols = jdb.dbread (cur, "SELECT * FROM sndvol")
        for v in vols:
            _wrrow (x, workfiles['sndvol'])
            sels = jdb.dbread (cur, "SELECT * FROM sndfile s WHERE s.vol=%s", [v.id])
            for s in sels:
                _wrrow (x, workfiles['sndfile'])
                clips = jdb.dbread (cur, "SELECT * FROM snd c WHERE c.file=%s", [s.id])
                for c in clips:
                    _wrrow (x, workfiles['snd'])

def initialize (tmpdir):
        data = (
          ('kwsrc',  ['id','kw','descr','dt','notes','seq','sinc','smin','smax','srct']),
          ('kwgrp',  ['id','kw','descr']),
          ('entr',   ['id','src','stat','seq','dfrm','unap','srcnote','notes','idx']),
          ('kanj',   ['entr','kanj','txt']),
          ('kinf',   ['entr','kanj','ord','kw']),
          ('rdng',   ['entr','rdng','txt']),
          ('rinf',   ['entr','rdng','ord','kw']),
          ('restr',  ['entr','rdng','kanj']),
          ('freq',   ['entr','rdng','kanj','kw','value']),
          ('sens',   ['entr','sens','notes']),
          ('gloss',  ['entr','sens','gloss','lang','ginf','txt']),
          ('pos',    ['entr','sens','ord','kw']),
          ('misc',   ['entr','sens','ord','kw']),
          ('fld',    ['entr','sens','ord','kw']),
          ('dial',   ['entr','sens','ord','kw']),
          ('lsrc',   ['entr','sens','ord','lang','txt','part','wasei']),
          ('stagr',  ['entr','sens','rdng']),
          ('stagk',  ['entr','sens','kanj']),
          ('xref',   ['entr','sens','xentr','xsens','typ','notes']),
          ('xresolv',['entr','sens','typ','ord','rtxt','ktxt','tsens','vsrc','vseq','notes','prio']),
          ('hist',   ['entr','hist','stat','unap','dt','userid','name','email','diff','refs','notes']),
          ('grp',    ['entr','kw','ord','notes']),
          ('chr',    ['entr','chr','bushu','strokes','freq','grade','jlpt','radname']),
          ('cinf',   ['entr','kw','value']),
          ('kresolv',['entr','kw','value']),
          ('sndvol', ['id','title','loc','type','idstr','corp','notes']),
          ('sndfile',['id','vol','title','loc','type','notes']),
          ('snd',    ['id','file','strt','leng','trns','notes']),
          ('entrsnd',['entr','ord','snd']),
          ('rdngsnd',['entr','rdng','ord','snd']),
          )

        workfiles = {}
        for n,(t,v) in enumerate (data):
            fn = "%s/_jm_%s.tmp" % (tmpdir, t)
            workfiles[t] = jdb.Obj (ord=n, tbl=t, file=None, fn=fn, cols=v)
        return workfiles

def finalize (workfiles, outfn, delfiles=True, transaction=True):
        # Close all the temp files, merge them all into a single
        # output file, and delete them (if 'delfiles is true).

        if outfn: fout = open (outfn, "w", encoding='utf-8')
        else: fout = sys.stdout
        if transaction:
            print ("\\set ON_ERROR_STOP 1\nBEGIN;\n", file=fout)
        for v in sorted (list(workfiles.values()), key=operator.attrgetter('ord')):
            if not v.file: continue
            v.file.close()
            fin = open (v.fn, encoding='utf-8')
            print ("COPY %s(%s) FROM STDIN;" % (v.tbl,','.join(v.cols)), file=fout)
            for ln in fin: print (ln, end='', file=fout)
            print ('\\.\n', file=fout)
            fin.close()
            if delfiles: os.unlink (v.fn)
        if transaction: print ('COMMIT', file=fout)
        if fout != sys.stdout: fout.close()

def _wrrow (rowobj, workfile):
        if not workfile.file:
            workfile.file = open (workfile.fn, "w", encoding='utf-8')
        s = "\t".join ([pgesc(getattr (rowobj, x, None)) for x in workfile.cols])
        print (s, file=workfile.file)

def pgesc (s):
          # Escape characters that are special to the Postgresql COPY
          # command.  Backslash characters are replaced by two backslash
          # characters.   Newlines are replaced by the two characters
          # backslash and "n".  Similarly for tab and return characters.
        if s is None: return '\\N'
        if isinstance (s, int): return str (s)
        if isinstance (s, (datetime.date, datetime.time)): return s.isoformat()
        if isinstance (s, datetime.datetime): return s.isoformat(' ')
        if s.isdigit(): return s
        s = s.replace ('\\', '\\\\')
        s = s.replace ('\n', '\\n')
        s = s.replace ('\r', '')  #Delete \r's.
        s = s.replace ('\t', '\\t')
        return s
