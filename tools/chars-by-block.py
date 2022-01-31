#!/usr/bin/env python3

# This program will read the kanji, reading and gloss text strings from
# an existing JMdictDB database and gather some data about the numbers
# and kinds of characters (as classified by jdb.jstr_classify()).

import sys, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from collections import Counter, defaultdict as Ddict
from jmdictdb import jdb, db
# Following module borrowed from:
#   https://stackoverflow.com/questions/243831/unicode-block-of-a-character-in-python
from jmdictdb.pylib import unicodeblock as ub

def main():
        args = parse_cmdline()
        dbconn = db.open (args.dburi)
        kchars, rchars, gchars = Ddict(set), Ddict(set), Ddict(set)
        ktypes, rtypes, gtypes = Counter(), Counter(), Counter()

        count (dbconn, "kanj", args.corpus, kchars, ktypes)
        count (dbconn, "rdng", args.corpus, rchars, rtypes)
        count (dbconn, "gloss", args.corpus, gchars, gtypes)

        print (header())
        print ("kanj types:\n%s"  % fmt(kchars, ktypes))
        print ("rdng types:\n%s"  % fmt(rchars, rtypes))
        print ("gloss types:\n%s" % fmt(gchars, gtypes))

def count (dbconn, table, corpus, xchars, xtypes):
        print ("reading %s texts..." % table)
        for txt in dbget (dbconn, table, corpus):
            for c in txt:
                t = ub.block(c)
                xchars[t].add(c); xtypes[t] += 1

def header():
        t = []
        tmpl = "  %-34.34s  %8s  %5s  %s"
        t.append (tmpl % (" ", "Total", "Uniq", " "))
        t.append (tmpl % ("Unicode block", "chars", "chars", "Characters"))
        t.append (tmpl % ('-'*34, '-'*8, '-'*5, '-'*23))
        return '\n'.join(t)

def fmt (xchars, xtypes):
        keys = sorted (xtypes.keys())
        lines = []
        for k in keys:
            chars = "[...too many...]"
            if len(xchars[k]) < 100: chars = ''.join(sorted(xchars[k]))
            lines.append ("  %-34.34s %8s  %4s  %s"
                          % (k, xtypes[k], len(xchars[k]), chars))
        s = '\n'.join(lines)
        return s

def dbget (dbconn, tblname, corpus=None):
        if not corpus: where, sqlargs = "k.kw!='test'", ()
        else: where, sqlargs = "k.kw=%s", (corpus,)
        if tblname == 'kanj': key = "entr,kanj"
        elif tblname == 'rdng': key = "entr,rdng"
        elif tblname == 'gloss': key = "entr,sens,gloss"
        else: raise ValueError ("bad tblname: %s" % tblname)
          # Restrict consideration to active-approved entries.  There is
          # all kinds of weird junk in the deleted and rejected entries.
        sql = """SELECT txt,%s
                 FROM %s x
                 JOIN entr e ON e.id=x.entr
                 JOIN kwsrc k ON k.id=e.src
                 WHERE stat=2 and NOT unap AND %s
                 ORDER BY %s""".replace(' '*16,'')\
              % (key, tblname, where, key)
        rs = db.query (dbconn, sql, sqlargs)
        for r in rs: yield (r.txt)

import argparse
def parse_cmdline ():
        p = argparse.ArgumentParser (description=\
                "%(prog)s will read the kanji, readings and gloss texts "
                "from a JMdictDB database and report on the characters "
                "belonging to each unicode block.")
        p.add_argument ("corpus", nargs='?', default=None,
            help="Optional name of a corpus to limit results to. If not "
                "given all corpora will be examined except for 'test'.")
        p.add_argument ("-d", "--dburi", default='jmdict',
            help="URI of the database to use.  If the database is local "
                "(on the same machine) and no additional connection "
                "information (username, etc) is needed, this can be "
                "simply the database name.  Default is \"jmdict\".")
        args = p.parse_args ()
        return args
main()
