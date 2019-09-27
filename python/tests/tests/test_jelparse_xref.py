import sys, os, unittest, signal, pdb
if '../lib' not in sys.path: sys.path.append ('../lib')
import jdb, jellex, jelparse, fmtjel
import unittest_extensions, jmdb
from jmdb import DBmanager
__unittest = 1

def main(): unittest.main()

  # Database name and load file for tests.
DBNAME, DBFILE = "jmtest01", "data/jmtest01.sql"

  # We initialize JEL lexer and parser objects that will be will be
  # fed test data and whose results will be checked.  The lexer and
  # parser are created once and reused for all tests.
  # Access to a JMdictDB database is required, both to supply KW mapping
  # tables and to provide entries for resolving xrefs.  A  singleton
  # jmdb.DBmanager instance to used to load the "test01" database if it
  # is not already loaded on the server.  The database is loaded
  # only once and reused by all tests.
  # For background on this test architecture see python/tests/README.txt.

  # Global variables.
DBcursor = JELparser = JELlexer = None

def setUpModule():
        global DBcursor, JELparser, JELlexer
        DBcursor = DBmanager.use (DBNAME, DBFILE)
        JELlexer, tokens = jellex.create_lexer ()
        JELparser = jelparse.create_parser (JELlexer, tokens)
        global SEE, ANT    #  Abbreviations for brevity.
        SEE, ANT = jdb.KW.XREF['see'].id, jdb.KW.XREF['ant'].id

# In the following tests chkx() will parse the given JEL text
# and create an entry object.  It will match each item in the last
# argrument with each sense in the entry and compare the item with
# the senses's xref list.  Each compare item is a dict whose key/value
# pairs should match the corresponding attribute value pairs in the
# sense's corresponding xref.
#
# There are also some older xref tests in test_jelparse.Xref and
# .Roundtrip based on round-trip testing.

class Xref (unittest.TestCase):
    longMessage = False
    def test000110(_):  # Basic xref.
        jel = "\fあ\f[1] xxx [see=双対]"
        chk (_, jel, [[dict(typ=SEE,
                             xentr=44, rdng=None, kanj=1,
                             nosens=None, lowpri=None)]])

    def test000120(_):  # Basic xref.
        jel = "\fあ\f[1] xxx [see=そうつい]"
        chk (_, jel, [[dict(typ=SEE,
                             xentr=44, rdng=1, kanj=None,
                             nosens=None, lowpri=None)]])

    def test000130(_):  # Basic xref.
        jel = "\fあ\f[1] xxx [see=1398850]"
        chk (_, jel, [[dict(typ=SEE,
                             xentr=44, rdng=1, kanj=1,
                             nosens=None, lowpri=None)]])

    def test000310(_):  # Xref default to multiple senses.
        jel = "\fあ\f[1] xxx [see=町]"
        chk (_, jel, [[dict(typ=SEE,
                           xentr=58, rdng=None, kanj=1,
                           nosens=None, lowpri=None)] * 5])

    def test000320(_):  # Xref explicitly to one of multiple senses.
        jel = "\fあ\f[1] xxx [see=町[2]]"
        chk (_, jel, [[dict(typ=SEE, xentr=58, rdng=None, kanj=1,
                             nosens=None, lowpri=None),]])

    def test000330(_):  # Xref explicitly to two of multiple senses.
        jel = "\fあ\f[1] xxx [see=町[2,5]]"
        chk (_, jel, [[dict(typ=SEE, xentr=58, rdng=None, kanj=1,
                             nosens=None, lowpri=None),
                       dict(typ=SEE, xentr=58, rdng=None, kanj=1,
                            nosens=None, lowpri=None)]])

    def test000220(_):  # Xref to 1st kanji.
        jel = "\fあ\f[1] xxx [see=治具]"
        chk (_, jel, [[dict(typ=SEE,
                             xentr=39, rdng=None, kanj=1,
                             nosens=None, lowpri=None)]])

    def test000230(_):  # Xref to 2nd kanji.
        jel = "\fあ\f[1] xxx [see=冶具]"
        chk (_, jel, [[dict(typ=SEE,
                             xentr=39, rdng=None, kanj=2,
                             nosens=None, lowpri=None)]])

    def test000240(_):  # Xref to 1st reading.
        jel = "\fあ\f[1] xxx [see=じぐ]"
        chk (_, jel, [[dict(typ=SEE,
                             xentr=39, rdng=1, kanj=None,
                             nosens=None, lowpri=None)]])

    def test000250(_):  # Xref to 2nd reading.
        jel = "\fあ\f[1] xxx [see=ジグ]"
        chk (_, jel, [[dict(typ=SEE,
                             xentr=39, rdng=2, kanj=None,
                             nosens=None, lowpri=None)]])

    def test000260(_):  # Xref to kanji with corpus.
        jel = "\fあ\f[1] xxx [see=治具 jmdict]"
        chk (_, jel, [[dict(typ=SEE,
                             xentr=39, rdng=None, kanj=1,
                             nosens=None, lowpri=None)]])

    def test000270(_):  # Xref to reading with corpus.
        jel = "\fあ\f[1] xxx [see=ジグ jmdict]"
        chk (_, jel, [[dict(typ=SEE,
                             xentr=39, rdng=2, kanj=None,
                             nosens=None, lowpri=None)]])

    # TO-DO: quoted and dotted targets, failures (not found,
    #  multiple, no sense, no corpus), nosens and lowpri.

# Check unresolved xrefs.  These are created in each sense's ._xrslv
# list.

class Xrslv (unittest.TestCase):
    def test000110(_):
        jel = "\fＸ\f[1] xref source [see=わわわ]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt='わわわ',
                      vsrc=None, vseq=None, tsens=None, prio=None)]])
    def test000120(_):
        jel = "\fＸ\f[1] xref source [see=和わ和]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt=None,
                      vsrc=None, vseq=None, tsens=None, prio=None)]])
    def test000130(_):
        jel = "\fＸ\f[1] xref source [see=和わ和・わわわ]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt='わわわ',
                      vsrc=None, vseq=None, tsens=None, prio=None)]])
    def test000140(_):
        jel = "\fＸ\f[1] xref source [see=9999999]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt=None,
                      vsrc=None, vseq=9999999, tsens=None, prio=None)]])
    def test000150(_):
        jel = "\fＸ\f[1] xref source [see=9999999・わわわ]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt='わわわ',
                      vsrc=None, vseq=9999999, tsens=None, prio=None)]])
    def test000160(_):
        jel = "\fＸ\f[1] xref source [see=9999999・和わ和]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt=None,
                      vsrc=None, vseq=9999999, tsens=None, prio=None)]])
    def test000170(_):
        jel = "\fＸ\f[1] xref source [see=9999999・和わ和・わわわ]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt='わわわ',
                      vsrc=None, vseq=9999999, tsens=None, prio=None)]])

#=============================================================================
# Support functions.
# These functions were originally written to support tests of both
# resolved and unresolved xrefs.  However, after the JEL parser was
# changed to always create unresolved xrefs and resolve them in a
# separate subsequent step (see revs 190628-e90a408e and 190827-8b86f59)
# it was realized the testing should follow the same pattern: for testing
# JEL parsing we need only test that that the correct unresolved xrefs
# are produced; resolution of unresolved xrefs should be a separate set
# of tests.  The support code for testing resolved xrefs is left
# here until a new module for testing the xref resolution process is
# created.

def chkv  (_, jel, x=None, v=None): chk (_, jel, x, v, False)

def chk (_, jel, x=None, v=None, rslv=True):
        '''-------------------------------------------------------------------
        Compares the Xrefs (or Xrslvs or both) on each e._sens[n]._xref
        (or e._sens[n]._xrslv) list to expected values given in 'xrefs'
        (or 'xrslvs').
        Parameters:
          jel -- JEL text describing entry with xrefs that will be
            parsed and the resulting entry's ._xref and ._xrslv lists
            compared to sets of expected values.
          x -- Xref expected values.  A list of lists.  The items of
            each contained list are dicts giving the xrefs attribute
            names and values expected on each xref for a sense.  Each
            contained list corresponds, in order, to a sense in 'e';
            thus the len('xrefs') must be the same as len(e._sens).
          v -- Xrslv expected values.  Like 'xrefs' but with expected
            values for the ._xrlv lists.
          rslv -- If true, attempt to resolve any unresolved xerfs.
            If false, leave unresolved xrefs as is.
        -------------------------------------------------------------------'''
        e = parse (jel, rslv)
        if x:   # xref expected values.
            _.assertEqual (len(e._sens), len(x),
                           "Expected %d senses but got %d"
                           % (len(x), len(e._sens)))
            for snum,(s,a) in enumerate (zip (e._sens, x)):
                cmpxrefs (_, snum, "xref", s._xref, a)

        if v:   # xrslv expected values.
            _.assertEqual (len(e._sens), len(v),
                           "Expected %d senses but got %d"
                           % (len(v), len(e._sens)))
            for snum,(s,a) in enumerate (zip (e._sens, v)):
                cmpxrefs (_, snum, "xrslv", s._xrslv, a)

def parse (intxt, rslv=True):  # Parse xrefs, optionally resolve.
        # Parse the jel text, 'intxt' and return the resulting Entr object.
        # We intentionally stay as close to the raw Ply parser as we can
        # rather than using any library helpers, for two reasons:
        # - Eliminate any potential problems in such helpers.
        # - Provide a reference for developing such helpers.

        jellex.lexreset (JELlexer, intxt)
        entr = JELparser.parse()
        if not rslv: return entr
        if not entr.src: entr.src = 1
        jdb.xresolv (DBcursor, entr)
        return entr

def cmpxrefs (_, snum, listname, xrefs, exps):
        _.assertEqual (len(xrefs), len(exps),
                       "Expected %d %s items for sense %d but got %d"
                       % (len(exps), listname, snum, len(xrefs)))
        for n, (x, e) in enumerate (zip (xrefs, exps)):
            cmp1xref (_, snum, listname, n, x, e)

def cmp1xref (_, snum, listname, itemnum, xref, exp):
        msgs = []
          # Check all attributes and generate a single failure for all
          # so they don't need to be discovered by fixing one at a time.
        for k,expected in exp.items():
            got = getattr (xref, k)
            if got != expected: msgs.append (
                "_sens[%d]._%s[%d].%s: expected '%r', got '%s'"
                % (snum, listname, itemnum, k, expected, got))
        if msgs:
            if len(msgs)==1: _.fail (msgs[0])
            _.fail ("\n  " + "\n  ".join (msgs))

if __name__ == '__main__': main()
