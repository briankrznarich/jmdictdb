#!/usr/bin/env python3

# This program will read the kanji, reading and gloss text strings from
# an existing JMdictDB database and gather some data about the numbers
# and kinds of characters (as classified by jdb.jstr_classify()).

import sys, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from collections import Counter, defaultdict
from jmdictdb import jdb, db
# Following module borrowed from:
#   https://stackoverflow.com/questions/243831/unicode-block-of-a-character-in-python
try: from jmdictdb.pylib import unicodeblock as ub
except ImportError: ub = None

def main():
        dbconn = db.open ('jmdict')
          #FIXME? we assume that jdb.jstr_classify() applied to a single
          # character will return one of the values in i2n.keys().  If
          # that changes (eg it could return several bits or'ed for a 
          # single character), some revision will be needed here. 
        i2n = {1:'KANA', 2:'KANJI', 4:'KSYM', 16:'LATIN', 32:'OTHER'}
        kchars, rchars, gchars = {}, {}, {}
        for a in (kchars, rchars, gchars):
            for i in i2n.values(): a[i] = set()
        ktypes, rtypes, gtypes = Counter(), Counter(), Counter()
        print ("reading kanj texts...")
        for txt in dbget (dbconn, 'kanj'):
            for c in txt:
                t = i2n[jdb.jstr_classify(c)]
                kchars[t].add(c); ktypes[t] += 1
        print ("reading rdng texts...")
        for txt in dbget (dbconn, 'rdng'):
            for c in txt:
                t = i2n[jdb.jstr_classify(c)]
                rchars[t].add(c); rtypes[t] += 1
        print ("reading gloss texts...")
        for txt in dbget (dbconn, 'gloss'):
            for c in txt:
                t = i2n[jdb.jstr_classify(c)]
                gchars[t].add(c); gtypes[t] += 1

        print ("Total number of characters of each type (dups counted):")
        print ("kanj types:  %s" % [(i,c) for i,c in sorted (ktypes.items())])
        print ("rdng types:  %s" % [(i,c) for i,c in sorted (rtypes.items())])
        print ("gloss types: %s" % [(i,c) for i,c in sorted (gtypes.items())])
        print ("Number of unique characters of each type (dups not counted): ")
        print ("kanj chars:  %s" % [(i,len(s)) for i,s in sorted (kchars.items())])
        print ("rdng chars:  %s" % [(i,len(s)) for i,s in sorted (rchars.items())])
        print ("gloss chars: %s" % [(i,len(s)) for i,s in sorted (gchars.items())])

          # Print the oddball characters and the unicode block they are from:
        if ub:
            print ("kchars['KSYM']:",  ubclass(kchars['KSYM']))
            print ("kchars['LATIN']:", ubclass(kchars['LATIN']))
            print ("kchars['OTHER']:", ubclass(kchars['OTHER']))
            print ("rchars['KSYM']:",  ubclass(rchars['KSYM']))
            print ("gchars['OTHER']:", ubclass(gchars['OTHER']))
        else:
            print ('"unicodeblock" module not available: cant print block details.')

          # Can look at kchars, rchars and gchars here to see what characters
          # in what classifications occur in the various text strings.  The
          # contents are sets so one can do things like look for kana characters
          # that occur in readings but not in kanji using a set difference:
          #   (pdb) p rchars['KANA'] - kchars['KANA']
        pdb.set_trace()

def ubclass(chars):
        blocks = defaultdict(list)
        for c in chars:
            blocks[ub.block(c)].append(c)
        lines = []
        for k,v in sorted (blocks.items()):
            lines.append ("  %s: %s" % (k, sorted (v)))
        return '\n'+'\n'.join (lines)

def dbget (dbconn, tblname):
        if tblname == 'kanj': key = "entr,kanj"
        elif tblname == 'rdng': key = "entr,rdng"
        elif tblname == 'gloss': key = "entr,sens,gloss"
        else: raise ValueError ("bad tblname: %s" % tblname)
          # Restrict consideration to active-approved entries.  There is all
          # kinds of weird junk in the deleted and rejected entries.
        sql = """SELECT txt,%s
                 FROM %s x
                 JOIN entr e ON e.id=x.entr
                 WHERE stat=2 and NOT unap
                 ORDER BY %s""".replace(' '*16,'') % (key, tblname, key)
        rs = db.query (dbconn, sql)
        for r in rs: yield (r.txt)

main()
