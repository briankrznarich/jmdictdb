#!/usr/bin/env python3
# Copyright (c) 2008-2012 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# This program will read an Examples file containing paired
# English and Japanese sentences and available for download
# at
#   ftp://ftp.monash.edu.au/pub/nihongo/examples.utf.gz
#   (This file is derived from data from the Tatoeba
#   project: http://tatoeba.org)
# and create an output file containing postgresql data COPY
# commands.  This file can be loaded into a Postgresql JMdictDB
# database after subsequent processing with jmload.pl.
#
# The Example file "A" lines create database entries with
# a entr.src=3 which identifies them as from the Examples
# files.  These entries will have an single kanji, single
# sense, and single gloss.  They may have a misc tag and
# sense note if there was a parsable "[...]" comment on the
# line.
#
# "B" line items create database xref table rows.  However,
# like jmparse, we do not create the xrefs directly from
# within this program, but instead write pseudo-xref records
# that contain the target reading and kanji text, to the
# xrslv table, and generate the resolved xrefs later by
# running insert queries based on joins of xrslv and the
# jmdict entries.  All the pseudo-xref genereated by this
# program will have a typ=6.

import sys, datetime, os, io, re, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, pgi
from jmdictdb.pylib import diagnum
from jmdictdb.pylib import progress_bar

Seq = None
Lnnum = None
Opts = None

class ParseError (Exception): pass

def main (args, opts):
        global msg
        global Opts; Opts = opts
        global KW; jdb.KW = KW = jdb.Kwds (jdb.std_csv_dir())

          # Create a globally accessible function, msg() that has
          # has 'logfile' and 'opts.verbose' already bound and
          # which will be called elsewhere when there is a need to
          # write a message to the logfile.
        logfile = sys.stderr
        if opts.logfile:
            logfile = open (opts.logfile, "w")
        def msg (message): _msg (logfile, opts.verbose, message)
        pbar = None
        if opts.progbar:
            total_items = opts.count \
                          or progress_bar.count_items (args[0]) / 2
            pbar = progress_bar.InitBar (
                    title=args[0], size=total_items, offset=2)

        fin = ABPairReader (args[0])
          # FIXME: following gives localtime, change to utc or lt+tz.
        pgio = pgi.PgiWriter (opts.tempdir if not opts.noaction else None)
        srcid = 1    # This id, which will reference kwsrc.id after import,
                     # will be adjusted when data is imported into database
                     # so its value is arbitrary here.
        for eid, entr in enumerate (parse_ex (fin, opts.begin)):
            entr.src = srcid
            if not opts.noaction:
                jdb.setkeys (entr, eid+1)
                pgio.wrentr (entr)
            if pbar: pbar (eid)
            if opts.count and eid+1 >= opts.count: break
        mtime = datetime.date.fromtimestamp(os.stat(args[0])[8]).isoformat()
        pgio.wrcorpora ({opts.corpus:('examples',srcid)}, other={'dt':mtime})
        if not opts.noaction: pgio.finalize (opts.output, not opts.keep)

def parse_ex (fin, begin):
        # This is a generator function that will process one (A and B) pair
        # of lines from open file object 'fin' each time it is called.
        #
        # fin -- An open Examples file.
        # begin -- Line number at which to begin processing.  Lines
        #    before that are skipped.

        global Lnnum, Seq
        seq_cache = set()
        for aln, bln in fin:
            if fin.lineno < begin: continue
            Lnnum = fin.lineno
            mo = re.search (r'(\s*#\s*ID\s*=\s*(\d+)_(\d+)\s*)$', aln)
            if mo:
                aln = aln[:mo.start(1)]
                  # The ID number is of the form "nnnn_mmmm" where "nnnn" is
                  # the Tatoeba English sentence id number, and "mmmm" is the
                  # Japanese id number.  Generate a seq number by mapping each
                  # pair to a "square number".  These are numbers generated
                  # by assigning sequential numbers on a grid (x>=0, y>=0)
                  # starting at the origin proceeding down the diagonal,
                  # assigning number to each cell on the column and row at
                  # the diagonal cell.
                id_en, id_jp = int(mo.group(2)), int(mo.group(3))
                Seq = diagnum.xy2sq1 (id_en, id_jp)
            else:
                msg ("No ID number found"); continue
            try:
                jtxt, etxt = parsea (aln)
                idxlist = parseb (bln, jtxt)
            except ParseError as e:
                msg (e.args[0]); continue
            if not idxlist: continue
              # Turns out some of the entries in the examples file are
              # duplicates (including the ID#) so we check the seq#.
            if Seq in seq_cache:
                msg ("Duplicate id#: %s_%s" % (id_en, id_jp))
                continue
            seq_cache.add (Seq)
            entr = mkentr (jtxt, etxt)
            entr.seq = Seq
            entr._sens[0]._xrslv = mkxrslv (idxlist)
            yield entr

def parsea (aln):
          # When we're called, 'aln' has had the "A: " stripped from
          # its start, and the ID field stripped from it's end.
        mo = re.search (r'^\s*(.+)\t(.+?)\s*$', aln)
        if not mo: raise ParseError ('"A" line parse error')
        jp, en = mo.group (1,2)
        kws = []
        return jp, en

def parseb (bln, jtxt):
        parts = bln.split()
        res = []
        for n,x in enumerate (parts):
            try: res.append (parsebitem (x, n, jtxt))
            except ParseError as e: msg (e.args[0])
        return res

def parsebitem (s, n, jtxt):
        mo = re.search (r'^([^([{~]+)(\((\S+)\))?(\[\d+\])*(\{(\S+)\})?(~)?\s*$', s)
        if not mo:
            raise ParseError ("\"B\" line parse error in item %d: '%s'" % (n, s))

        ktxt,rtxt,sens,atxt,prio = mo.group (1,3,4,6,7)

        if rtxt and not jdb.jstr_reb (rtxt):
            raise ParseError ("Expected kana in item %d: '%s'" % (n, rtxt))
        if kana_only (ktxt):
            if rtxt: raise ParseError ("Double kana in item %d: '%s', '%s'" % (n, ktxt, rtxt))
            rtxt = ktxt;  ktxt = None
        if sens:
            sens = sens.replace(']', '')
            sens = [x for x in sens.split ('[') if len(x)>0]

        if atxt and jtxt.find (atxt) < 0:
            raise ParseError ("{%s} not in A line in item %d" % (atxt, n))
        return ktxt, rtxt, sens, atxt, not not prio

def hw (ktxt, rtxt):
        if ktxt and rtxt: return "%s(%s)" % (ktxt,rtxt)
        return ktxt or rtxt

def mkentr (jtxt, etxt):
        global Lnnum
          # Create an entry object to represent the "A" line text of the
          # example sentence.
        e = jdb.Entr (stat=KW.STAT_A, unap=False)
        e.srcnote = str (Lnnum)
        if jdb.jstr_reb (jtxt): e._rdng = [jdb.Rdng (txt=jtxt)]
        else:                   e._kanj = [jdb.Kanj (txt=jtxt)]
        e._sens = [jdb.Sens (_gloss=[jdb.Gloss (txt=etxt, ginf=KW.GINF_equ,
                                                lang=KW.LANG_eng)])]
        return e

def mkxrslv (idxlist):
        # Convert the $@indexlist that was created by bparse() into a
        # list of database xrslv table records.  The fk fields "entr"
        # and "sens" are not set in the xrslv records; they are set
        # by setids() just prior to writing to the database.

        res = []
        for ktxt, rtxt, senslst, note, prio in idxlist:
            if senslst:
                  # A list of explicit sens were give in the B line,
                  # create an xrslv record for each.
                res.extend ([jdb.Obj (ktxt=ktxt, rtxt=rtxt, tsens=s,
                                      typ=KW.XREF_uses, notes=note, prio=prio)
                                for s in senslst])
            else:
                  # This is not list of senses so this cross-ref will
                  # apply to all the target's senses.  Don't set a "sens"
                  # field in the xrslv record which will result in a NULL
                  # in the database record.
                res.append (jdb.Obj (ktxt=ktxt, rtxt=rtxt,
                            typ=KW.XREF_uses, notes=note, prio=prio))
        for n,r in enumerate (res): r.ord = n + 1
        return res

def kana_only (txt):
        v = jdb.jstr_reb (txt)
        return (v & jdb.KANA) and not (v & jdb.KANJI)

def _msg (logfile, verbose, message):
        # This function should not be called directly.  It is called
        # by the global function, msg(), which is a closure with 'logfile'
        # and 'verbose' already bound, created in main() and which should
        # be called instead of calling _msg() directly.
        global Seq, Lnnum
        m = "Seq %d (line %s): %s" % (Seq, Lnnum, message)
        if verbose and logfile !=sys.stderr:
            print (m, file=sys.stderr)
        if logfile:  print (m, file=logfile)

class ABPairReader:
    def __init__ (self, *args, **kwds):
        self.__dict__['stream'] = open (*args, **kwds)
        self.lineno = 0  # This creates attribute on self.stream object.
    def readpair( self ):
        aline = self.getline ('A: ')
        bline = self.getline ('B: ')
        return aline, bline
    def getline( self, key ):
        didmsg = False
        while 1:
            line = self.stream.readline(); self.lineno += 1
            if not line: return None
            if line.startswith (key) \
                    or (line[1:].startswith(key) and line[0]=='\uFEFF'):
                if didmsg:
                    msg ("Line %d: resyncronised." % self.lineno)
                    didmsg = False
                return line[len(key):].strip()
            else:
                if not didmsg:
                    msg ("Line %d: expected '%s' line not found, resyncronising..."
                           % (self.lineno, key.strip()))
                    didmsg = True
    def __next__( self ):
        a, b = self.readpair()
        if not a: raise StopIteration
        return a, b
    def __iter__ (self): return self

    # Delegate all other method calls to the stream.
    def __getattr__(self, attr):
        return getattr(self.stream, attr)
    def __setattr__(self, attr, value):
        return setattr(self.stream, attr, value)


from optparse import OptionParser

def parse_cmdline ():
        u = \
"""\n\t%prog [options] [filename]

%prog will read a file containing Tanaka corpus example sentence pairs
(as described at http://www.edrdg.org/wiki/index.php/Tanaka_Corpus) and
create a data file that can be subsequently loaded into a JMdictDB
database.

Arguments:
        filename -- Name of input examples file.  Default is
        "examples.txt"."""

        p = OptionParser (usage=u, add_help_option=False)

        p.add_option ("--help",
            action="help", help="Print this help message.")

        p.add_option ("-o", "--output", default="examples.pgi",
            dest="output", metavar="FILENAME",
            help="Name of output postgresql rebasable dump file.  "
                "By convention this is usually given the suffix \".pgi\".")

        p.add_option ("-b", "--begin", default=0,
            dest="begin", type="int", metavar="SEQNUM",
            help="Line number of first entry to process.  If not "
                "given or 0, processing will start with the first entry.")

        p.add_option ("-c", "--count", default=0,
            dest="count", type="int", metavar="NUM",
            help="Number of entries to process.  If not given or 0, "
                "all entries in the file will be processed.")

        p.add_option ("-s", "--corpus", default="examples",
            help='Corpus name to use for entries.  Default is "examples".')

        p.add_option ("-l", "--logfile",
            dest="logfile", metavar="FILENAME",
            help="Name of file to write log messages to.")

        p.add_option ("-T", "--tempdir", default=None,
            help="Directory in which to create temporary files.  "
                "If not given temporary files will be buffered in memory "
                "rather than on disk.  This option may be need on machines "
                "with limited memory to force the use of disk.")

        p.add_option ("-k", "--keep", default=False, action="store_true",
            help="Do not delete temporary files after program exits.  "
                "Ignored if -T/--tmpdir is not also given.")

        p.add_option("--no-progress",
            dest="progbar", action="store_false", default=True,
            help="Don't show the progress bar.")

        p.add_option ("-n", "--noaction", default=False,
            dest="noaction", action="store_true",
            help="Parse only, no database access used: do not resolve "
                "index words from it.")

        p.add_option ("-v", "--verbose", default=None,
            dest="verbose", action="store_true",
            help="Write log messages to stderr.  Default is true if "
                "--logfile was not given, or false if it was.")

        opts, args = p.parse_args ()
        if opts.verbose is None: opts.verbose = not bool (opts.logfile)
        if len (args) > 1:
            print ("%d arguments given, expected at most one",file=sys.stderr)
        if len (args) < 1: args = ["examples.txt"]
        return args, opts

if __name__ == '__main__':
        args, opts = parse_cmdline()
        main (args, opts)
