# Copyright (c) 2006-2012 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Module: Functions for writing Postgres "COPY" data to ".pgi" files.
"""
import sys, os, operator, datetime
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb

class PgiWriter:
    def __init__ (self, tmpdir=None):
        self.tmpdir = tmpdir
        self.ftmpl = os.path.join (tmpdir or "", "_jm-%s.tmp")
        self.tables = {}
        self.out = {}
        tables = (
            # Order of tables is significant: tables with foreign keys must occur
            # after the table(s) the foreign keys refer to.
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
          ('krslv',  ['entr','kw','value']),
          ('sndvol', ['id','title','loc','type','idstr','corp','notes']),
          ('sndfile',['id','vol','title','loc','type','notes']),
          ('snd',    ['id','file','strt','leng','trns','notes']),
          ('entrsnd',['entr','ord','snd']),
          ('rdngsnd',['entr','rdng','ord','snd']),
          )
          # Index the table data above in a dict for easier lookup.  The order
          # value 'n' goes first because we will sort the items later.
        for n,(name,cols) in enumerate (tables): self.tables[name] = (n, cols)

    def wrentr (self, e):
        "Write Entr instance 'e' to the .pgi files."
        self.addrow (e, 'entr')
        for r in getattr (e, '_rdng', []):
            self.addrow (r, 'rdng')
            for x in getattr (r, '_inf',   []): self.addrow (x, 'rinf')
            for x in getattr (r, '_freq',  []): self.addrow (x, 'freq')
            for x in getattr (r, '_restr', []): self.addrow (x, 'restr')
            for x in getattr (r, '_snd',   []): self.addrow (x, 'rdngsnd')
        for k in getattr (e, '_kanj', []):
            self.addrow (k, 'kanj')
            for x in getattr (k, '_inf',   []): self.addrow (x, 'kinf')
            for x in getattr (k, '_freq',  []):
                if not x.rdng: self.addrow (x, 'freq')
        for s in getattr (e, '_sens', []):
            self.addrow (s, 'sens')
            for x in getattr (s, '_gloss', []): self.addrow (x, 'gloss')
            for x in getattr (s, '_pos',   []): self.addrow (x, 'pos')
            for x in getattr (s, '_misc',  []): self.addrow (x, 'misc')
            for x in getattr (s, '_fld',   []): self.addrow (x, 'fld')
            for x in getattr (s, '_dial',  []): self.addrow (x, 'dial')
            for x in getattr (s, '_lsrc',  []): self.addrow (x, 'lsrc')
            for x in getattr (s, '_stagr', []): self.addrow (x, 'stagr')
            for x in getattr (s, '_stagk', []): self.addrow (x, 'stagk')
            for x in getattr (s, '_xref',  []): self.addrow (x, 'xref')
            for x in getattr (s, '_xrer',  []): self.addrow (x, 'xref')
            for x in getattr (s, '_xrslv', []): self.addrow (x, 'xresolv')
        for x in getattr (e, '_snd',   []): self.addrow (x, 'entrsnd')
        for x in getattr (e, '_hist',  []): self.addrow (x, 'hist')
        for x in getattr (e, '_grp',   []): self.addrow (x, 'grp')
        for x in getattr (e, '_krslv', []): self.addrow (x, 'krslv')
        if e.chr is not None:
            self.addrow (e.chr, 'chr')
            for x in e.chr._cinf: self.addrow (x, 'cinf')

    def wrcorpora (self, corpora, defcorp=None, deftype=None, other={}):
        '''-------------------------------------------------------------------
        corpora -- (dict) Each key is a corpus name (used for the value
            of kwsrc.kw); each value is a 2-tuple of corpus type (one of:
            "jmdict", "jmnedict","kanjidic" or "examples"; used for the
            value of kwsrc.srct) and an id number (used for the value
            of kwsrc.id).
        defcorp -- (str) Value to use for corpus name for a key of None.
            Used for the value of kwsrc.kw
        deftype -- (str) value to use for the corpus type if the first item
            of the 2-tuple in None.  Used for the value of kwsrc.srct.
        other -- (dict) Other kwsrc fields to set.  Each item is the name
            and value of a kwsrc table field.
        If the 'other' parameter is not supplied the corpus (kwsrc) record
        written will contain only the fields "id", "kw", "srct" and "seq",
        the latter constructed from "kw".
        -------------------------------------------------------------------'''
        for cname, (ctype, id) in corpora.items():
            if not cname: cname = defcorp
            if not cname: raise ValueError ("No value for corpus name")
            if not ctype: ctype = deftype
            if not ctype: raise ValueError ("No value for corpus type")
            rowobj = jdb.Obj (id=id, kw=cname, seq='seq_'+cname, srct=ctype)
            for k,v in other.items():
                if k not in self.tables['kwsrc'][1]:
                    raise ValueError ("Invalid kwsrc field: %s" % k)
                setattr (rowobj, k, v)
            self.addrow (rowobj, 'kwsrc')

    def wrgrpdef (self, rowobj):
        self.addrow (rowobj, 'kwgrp')

    def wrsnd (self, cur):
        vols = jdb.dbread (cur, "SELECT * FROM sndvol")
        for v in vols:
            self.addrow (x, 'sndvol')
            sels = jdb.dbread (cur, "SELECT * FROM sndfile s WHERE s.vol=%s", [v.id])
            for s in sels:
                self.addrow (x, 'sndfile')
                clips = jdb.dbread (cur, "SELECT * FROM snd c WHERE c.file=%s", [s.id])
                for c in clips:
                    self.addrow (x, self, 'snd')

    def finalize (self, outfn, delfiles=True, transaction=True):
          # Close all the temp files, merge them all into a single
          # output file, and delete them (if 'delfiles is true).

        if outfn: fout = open (outfn, "w")
        else: fout = sys.stdout
        if transaction:
            print ("\\set ON_ERROR_STOP 1\nBEGIN;\n", file=fout)
        for table,(_,cols) in sorted (self.tables.items(), key=lambda x:x[1]):
            try: o = self.out[table]
            except KeyError:
                L('pgi').info("table %s: no records" % table)
                continue
            if isinstance (o, list):
                for ln in o: print (ln, file=fout)
            else:   # if not a list, assume it's a file.
                o.close()
                with open (o.name) as fin:
                   for ln in fin: print (ln, end='', file=fout)
                if delfiles: os.unlink (o.name)
            print ('\\.\n', file=fout)
        if transaction: print ('COMMIT', file=fout)
        if fout != sys.stdout: fout.close()

    def addrow (self, rowobj, table):
        cols = self.tables[table][1]
        s = "\t".join ([pgesc(getattr (rowobj, x, None)) for x in cols])
        if table not in self.out:
            hdr = "COPY %s(%s) FROM STDIN;" % (table,','.join(cols))
        if self.tmpdir:
            if table not in self.out:
                self.out[table] = open (self.ftmpl % table, "w")
                print (hdr, file=self.out[table])
            print (s, file=self.out[table])
        else:
            if table not in self.out:
                self.out[table] = [hdr]
            self.out[table].append (s)

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
