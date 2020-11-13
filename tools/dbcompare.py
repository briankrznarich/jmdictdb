#!/usr/bin/env python3

import sys, os, re, time, pdb
#from pprint import pprint as pp
from itertools import zip_longest as zipl
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, db, fmtxml

TMPTBL_NAME = "_tmp_dbcmp"

def main():
        args = parse_cmdline()
        cur2 = jdb.dbopen (args.dbcmp); kwcmp = jdb.KW
        cur1 = jdb.dbopen (args.dbref); kwref = jdb.KW
        #v = cmpkw (kwref, kwcmp)
        #kwcmp = jdb.Kwds('')

        seqlist = []
          # opts.seqnums and opts.seqfile won't both be true (although
          # both may be false); prohibited in parse_cmdline().
          # The --entries option changes the interpretation of these
          # values from sequence numbers to entry id numbers.
        if args.seqnums: seqlist = args.seqnums
        if args.seqfile: seqlist = read_seqfile (args.seqfile)
        corp = args.corpus
        if corp:
            try: corp = kwref.SRC[int(corp) if corp.isdigit() else corp].id
            except (KeyError, ValueError):
                sys.exit ('Unknown corpus: "%s"' % args.corp)

        verbose = args.verbose
        blksz = 5000
        entries1 = EntrIter (cur1, (0,0), blksz, src=corp, seqlist=seqlist)
        entries2 = EntrIter (cur2, (0,0), blksz, src=corp, seqlist=seqlist)
        e1, e2 = entries1.next(), entries2.next()
        while True:
            if not e1 and not e2: break
            if not e2 or seq(e1) < seq(e2):
                print ("%s: missing in db2" % (seq(e1),))
                e1 = entries1.next()
                continue
            if not e1 or seq(e2) < seq(e1):
                print ("%s: missing in db1" % (seq(e2),))
                e2 = entries2.next()
                continue
            assert seq(e1) == seq(e2)
              # The two entries will likely have different id numbers.
              # The prep() function will normalize the id numbers and
              # references to them to None to prevent them from causing
              # a false difference.
            prep (e1);  prep(e2)
            e1xml, e2xml = fmtxml.entr (e1), fmtxml.entr (e2)
            diff = fmtxml.entr_diff (e1xml, e2xml)
            if diff:
                if verbose:
                    print ("%s: entries differ:" % (seq2(e1,e2),))
                    print ("  " + diff.replace('\n', '\n  ')) 
                else: print ("%s: entries differ" % (seq2(e1,e2),))
            else: 
                pass #print ("%s: entries match" % (seq2(e1,e2),))
            e1, e2 = entries1.next(), entries2.next()

def seq (e):
        if not e: return None
        return e.src, e.seq
def seq2 (e1, e2):
        return e1.src, e1.seq, (e1.idx, e2.idx)

def prep (e):
          # Save copy of original id number.
        e.idx = e.id
          # Set the entry id number and all references to it to None.
        jdb.setkeys (e, None)

class EntrIter:
    def __init__ (self, cur, start, blksz, src=None,
                  unap=None, rej=None, seqlist=[]):
        self.cursor = cur
        self.blksz = blksz
        self.src, self.seqlist = src, seqlist
        self.unap, self.rej = unap, rej
        self.last = start   # This is a (src,seq) 2-tuple
        self.entrs = []
        self.eof = False

        create_tmptbl (cur)
    def next (self):
        if self.eof: return None
        if not self.entrs:
            self.entrs = get_block (self.cursor, self.last, self.blksz,
                                    self.src, self.unap, self.rej,
                                    self.seqlist)
            if not self.entrs:
                self.eof = True
                return None
            self.last = self.entrs[-1].src, self.entrs[-1].seq
        entr = self.entrs.pop(0)
        return entr

def get_block (cur, start, blksz,
               src=None, unap=None, rej=None, seqlist=None):
        '''-------------------------------------------------------------------
        Get a block of approximately 'blksz' entries from the database
        connection 'cur' in (src,seq) number order starting at 'start'
        and return them as Entr instances.  If 'src', 'unap, 'rej' or
        'seqlist' are given the returned entries are restriced by those
        values.
        Parameters:
          start -- (int,int) A 2-tuple of (src,seq)
          blksiz -- (int) Number of seq numbered entrires to return.  
            For any seq number, all entries of that sequence number are
            returned (subject to filtering by 'unap' and 'rej') so more
            entries may be returned than 'blksz'.
          src -- (int or None) Limit retuned entries to those with a 
            "src" value of 'src'.
          unap -- (bool) If true approved and unapproved entries are
            returned.  Otherwise only approved entries are returned.
          rej -- (bool) If true active, rejected and deleted entries are
            returned.  Otherwise only active entriers are returned.
          seqlist -- (int[]) List of sequence numbers; only entries with
            seq numbers in this list will be returned.  
        -------------------------------------------------------------------'''
        whrterms = [];  sqlargs = []
        if seqlist:
             whrterms.append ("seq IN %s")
             sqlargs.append (tuple(seqlist))
        if src: whrterms.append ("src=%d" % src)
        if not unap: whrterms.append ("NOT unap") 
        if not rej: whrterms.append ("stat=2")
        whrclause = " AND ".join(whrterms)
        if whrclause: whrclause = "AND " + whrclause
        startsrc, startseq = start
        sql = "DELETE FROM %s; "\
              "INSERT INTO %s(id) "\
                "(SELECT id FROM entr "\
                "WHERE (src>%d OR (src=%d AND seq>%d)) "\
                  "%s"\
                "ORDER BY src,seq,id LIMIT %d);"\
              % (TMPTBL_NAME, TMPTBL_NAME,
                 startsrc, startsrc, startseq, whrclause, blksz)
        db.ex (cur.connection, sql, sqlargs)
        entries, raw = entrList (cur, TMPTBL_NAME, ord="src,seq,id",
                                 ret_tuple=True)
        jdb.augment_xrefs (cur, raw['xref'])
        return entries

def entrList (dbh, crit, args=None, ord=None, ret_tuple=False):
        t = {}; entrs = []
        t   = jdb.entr_data (dbh, crit, args, ord)
        if t: entrs = jdb.entr_bld (t)
        if ret_tuple: return entrs,t
        return entrs

def create_tmptbl (cur):
        sql = "CREATE TEMP TABLE %s (id INT PRIMARY KEY);" % TMPTBL_NAME
        db.ex (cur.connection, sql)

def cmpkw (kw1, kw2):
        attrs = sorted (kw1.attrsall())
        if attrs != sorted (kw2.attrsall()): return False
        for a in attrs:
            if a in ('SRC','COPOS'): continue
            rs1 = sorted (kw1.recs (a), key=lambda x: x.id)
            rs2 = sorted (kw2.recs (a), key=lambda x: x.id)
            for r1, r2 in zipl (rs1, rs2):
                if r1 != r2: return False
        return True

  #FIXME: consolidate with same function in entrs2xml.py.
def read_seqfile (seqfilename):
        if seqfilename == '-': f = sys.stdin
        else:
            f = open (seqfilename)
        seqlist = []
        for lnnum, ln in enumerate (f):
            lnnum += 1
            ln = re.sub (r'\s*#.*', '', ln)
            if not ln: continue
            try: seqlist.extend ([int(x) for x in ln.split()])
            except ValueError as e:
                print ("Bad value in %s at line %s:\n  %s"
                       % (seqfilename, lnnum, str(e)), file=sys.stderr)
        if f != sys.stdin: f.close()
        return seqlist

def parse_cmdline():
        import argparse
        p = argparse.ArgumentParser (description=
            'Compares entries with matching sequence numbers from '
            'two databases.  '
            'Enties to compare are specified a corpus name or number '
            '(corpora are expected to match between the two databases) '
            'and zero or more sequence numbers, given on either the '
            'command line of via the --seqfile option.  If none are '
            'given, all entries of the given corpus are compared or '
            'all entries if no --corpus option is given.  '
            'Output for differing entries is in the form '
            '"corp, seq, (id1, id2)" where \'corp\' is corpus number, '
            '\'seq\' is the sequence number of two compared entries, '
            '\'id1\' and \'id2\' are the id numbers of the entries in '
            'the first and second databases.')
        p.add_argument ('dbref',
            help="URL for the first JMdictDB database.")
        p.add_argument ('dbcmp',
            help="URL for the second JMdictDB database.")
        p.add_argument ("seqnums", nargs='*', type=int,
            help="Sequence numbers of entries (in the corpus specified "
                "by --corpus) to be written to the XML output file.  "
                "No notification is currently given for sequence numbers "
                "with non-existent entries, they are effectively ignored.  "
                "If no arguments are given (nor the --seqfile option), "
                "all the entries in the corpus will be written.  "
                "Sequence numbers may be given on the command line "
                "or in the file specified by --seqfile but not both.")
        p.add_argument ("-s", "--corpus",
            help="One or more comma-separated corpus names or id numbers "
                "to output.  May be prefixed with \"!\" to output all "
                "corpora except the ones given.")
        p.add_argument ("--seqfile", default=None,
            help="Name of a file that contains a sequence numbers "
                "to be processed.  A line may contain multiple sequence "
                "numbers separated by spaces.  A # character indicates a "
                "comment and it and any text to the end of line will be "
                "ignored, as will blank lines.  "
                "No notification is currently given for sequence numbers "
                "with non-existent entries, they are effectively ignored.  "
                "Mutually exclusive with sequence numbers arguments "
                "and the --begin and --count options.")
        p.add_argument ("-v", "--verbose", default=False, action='store_true',
            help="Print entry differences rather than just a note "
                "that they differ.")
        args = p.parse_args ()
        return args

if __name__ == '__main__': main()
