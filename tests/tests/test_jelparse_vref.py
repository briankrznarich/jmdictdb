import sys, os, unittest, signal, pdb
if '../lib' not in sys.path: sys.path.append ('../lib')
import jdb, jellex, jelparse, fmtjel
import unittest_extensions, jmdb
from jmdb import DBmanager
__unittest = 1

def main(): unittest.main()

  # Database name and load file for tests.  Even though we do not resolve
  # xrefs to database entries in these tests, we need to open a database
  # in order to initialize the jdb.KW table. 
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

# In the following tests chkv() will parse the given JEL text
# and create an entry object.  It will match each item in the last
# argrument with each sense in the entry and compare the item with
# the senses's ._xrslv list.  Each compare item is a dict whose
# key/value pairs should match the corresponding attribute value
# pairs in the sense's corresponding xrslv item.  We use a dict
# rather than an object.Xrslv object for the comparison standard
# so that we can leave out any attribute values we don't care about.

# Check unresolved xrefs.  These are created in each sense's ._xrslv
# list.  This is the most relevant test of JEL parsing since xrefs are
# always parsed into unresoved xrefs first, and then resolved as a
# second, independent step.

class ParserCheck (unittest.TestCase):
  # We reuse a single parser instance for all the tests.  These two
  # tests check that the parser can continue properly after a parse
  # fail.  test1() intentionally generates an syntax error, test2()
  # then tries to parse valid jel which should succeed; if not any
  # further parses will also fail so there is no point in running
  # any further tests in this module.  os._exit() is used to bail
  # because unittest seems to catch all exceptions including SystemExit
  # which is used by sys.exit() making that call ineffective.
  # Unfortunately this terminates *all* subsequent tests including
  # those in other modules.  I don't know how to terminate only this
  # module's tests.

    def test1(_):
        jel = "\fＸ\f[1] vref test ["     # Syntax error
        _.assertRaises (jelparse.ParseError, parse, jel)
    def test2(_):
        jel = "\fＸ\f[1] vref test"       # Valid entry
        try: parse (jel, rslv=False)
        except jelparse.ParseError:
            print ("ParserCheck.test2 failed, unable to continue",
                   file=sys.stderr)
            os._exit(1)

class Xrslv (unittest.TestCase):

  # Basic tests specifying combinations of reading, kanji and seq
  # number.  These (along with sense numbers, see below) are the
  # most common forms encountered in practice.

    def test000110(_):
        jel = "\fＸ\f[1] vref test [see=わわわ]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt='わわわ',
                      vsrc=None, vseq=None, tsens=None, prio=None)]])
    def test000120(_):
        jel = "\fＸ\f[1] vref test [see=和わ和]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt=None,
                      vsrc=None, vseq=None, tsens=None, prio=None)]])
    def test000121(_):
        jel = "\fＸ\f[1] vref test [ant=和わ和]"
        chkv (_, jel, v=[[dict(typ=ANT, ord=1, ktxt='和わ和', rtxt=None,
                      vsrc=None, vseq=None, tsens=None, prio=None)]])
    def test000130(_):
        jel = "\fＸ\f[1] vref test [see=和わ和・わわわ]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt='わわわ',
                      vsrc=None, vseq=None, tsens=None, prio=None)]])
    def test000140(_):
        jel = "\fＸ\f[1] vref test [see=9999999]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt=None,
                      vsrc=None, vseq=9999999, tsens=None, prio=None)]])
    def test000150(_):
        jel = "\fＸ\f[1] vref test [see=9999999・わわわ]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt='わわわ',
                      vsrc=None, vseq=9999999, tsens=None, prio=None)]])
    def test000160(_):
        jel = "\fＸ\f[1] vref test [see=9999999・和わ和]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt=None,
                      vsrc=None, vseq=9999999, tsens=None, prio=None)]])
    def test000170(_):
        jel = "\fＸ\f[1] vref test [see=9999999・和わ和・わわわ]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt='わわわ',
                      vsrc=None, vseq=9999999, tsens=None, prio=None)]])

  # Basic forms above with target sense numbers.

    def test000210(_):
        jel = "\fＸ\f[1] vref test [see=わわわ[1]]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt='わわわ',
                      vsrc=None, vseq=None, tsens=1, prio=None)]])
    def test000220(_):
        jel = "\fＸ\f[1] vref test [see=和わ和[2]]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt=None,
                      vsrc=None, vseq=None, tsens=2, prio=None)]])
    def test000230(_):
        jel = "\fＸ\f[1] vref test [see=和わ和・わわわ[3]]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt='わわわ',
                      vsrc=None, vseq=None, tsens=3, prio=None)]])
    def test000240(_):
        jel = "\fＸ\f[1] vref test [see=9999999[4]]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt=None,
                      vsrc=None, vseq=9999999, tsens=4, prio=None)]])
    def test000250(_):
        jel = "\fＸ\f[1] vref test [see=9999999・わわわ[5]]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt='わわわ',
                      vsrc=None, vseq=9999999, tsens=5, prio=None)]])
    def test000260(_):
        jel = "\fＸ\f[1] vref test [see=9999999・和わ和[6]]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt=None,
                      vsrc=None, vseq=9999999, tsens=6, prio=None)]])
    def test000270(_):
        jel = "\fＸ\f[1] vref test [see=9999999・和わ和・わわわ[7]]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt='わわわ',
                      vsrc=None, vseq=9999999, tsens=7, prio=None)]])
    def test000280(_):
        jel = "\fＸ\f[1] vref test [see=和わ和[2,5]]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt=None,
                      vsrc=None, vseq=None, tsens=2, prio=None),
                          dict(typ=SEE, ord=2, ktxt='和わ和', rtxt=None,
                      vsrc=None, vseq=None, tsens=5, prio=None)]])

  # Cross-corpus xrefs, without senses.

    def test000710(_):
        jel = "\fＸ\f[1] vref test [see=わわわ test]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt='わわわ',
                      vsrc=99, vseq=None, tsens=None, prio=None)]])
    def test000720(_):
        jel = "\fＸ\f[1] vref test [see=和わ和 test]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt=None,
                      vsrc=99, vseq=None, tsens=None, prio=None)]])
    def test000730(_):
        jel = "\fＸ\f[1] vref test [see=和わ和・わわわ test]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt='わわわ',
                      vsrc=99, vseq=None, tsens=None, prio=None)]])
    def test000740(_):
        jel = "\fＸ\f[1] vref test [see=9999999 test]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt=None,
                      vsrc=99, vseq=9999999, tsens=None, prio=None)]])
    def test000750(_):
        jel = "\fＸ\f[1] vref test [see=9999999 test・わわわ]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt='わわわ',
                      vsrc=99, vseq=9999999, tsens=None, prio=None)]])
    def test000760(_):
        jel = "\fＸ\f[1] vref test [see=9999999 test・和わ和]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt=None,
                      vsrc=99, vseq=9999999, tsens=None, prio=None)]])
    def test000770(_):
        jel = "\fＸ\f[1] vref test [see=9999999 test・和わ和・わわわ]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt='わわわ',
                      vsrc=99, vseq=9999999, tsens=None, prio=None)]])

  # Cross-corpus xrefs, with senses.

    def test000810(_):
        jel = "\fＸ\f[1] vref test [see=わわわ[1] test]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt='わわわ',
                      vsrc=99, vseq=None, tsens=1, prio=None)]])
    def test000820(_):
        jel = "\fＸ\f[1] vref test [see=和わ和[2,3] test]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt=None,
                      vsrc=99, vseq=None, tsens=2, prio=None),
                          dict(typ=SEE, ord=2, ktxt='和わ和', rtxt=None,
                      vsrc=99, vseq=None, tsens=3, prio=None)]])
    def test000830(_):
        jel = "\fＸ\f[1] vref test [see=和わ和・わわわ[3,2] test]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt='わわわ',
                      vsrc=99, vseq=None, tsens=3, prio=None),
                          dict(typ=SEE, ord=2, ktxt='和わ和', rtxt='わわわ',
                      vsrc=99, vseq=None, tsens=2, prio=None)]])
    def test000840(_):
        jel = "\fＸ\f[1] vref test [see=9999999 test[4]]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt=None,
                      vsrc=99, vseq=9999999, tsens=4, prio=None)]])
    def test000850(_):
        jel = "\fＸ\f[1] vref test [see=9999999 test・わわわ[5]]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt='わわわ',
                      vsrc=99, vseq=9999999, tsens=5, prio=None)]])
    def test000860(_):
        jel = "\fＸ\f[1] vref test [see=9999999 test・和わ和[6]]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt=None,
                      vsrc=99, vseq=9999999, tsens=6, prio=None)]])
    def test000870(_):
        jel = "\fＸ\f[1] vref test [see=9999999 test・和わ和・わわわ[7]]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt='和わ和', rtxt='わわわ',
                      vsrc=99, vseq=9999999, tsens=7, prio=None)]])


  # Check multiple xrefs.

    def test000910(_):
        jel = "\fＸ\f[1] vref test [see=9999999 test・わわわ[5]] "\
                                  "[ant=和わ和[1,2]]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt='わわわ',
                      vsrc=99, vseq=9999999, tsens=5, prio=None),
                          dict(typ=ANT, ord=2, ktxt='和わ和', rtxt=None,
                      vsrc=None, vseq=None, tsens=1, prio=None),
                          dict(typ=ANT, ord=3, ktxt='和わ和', rtxt=None,
                      vsrc=None, vseq=None, tsens=2, prio=None)]])

    def test000920(_):  # Xrefs in multiple senses
        jel = "\fＸ\f[1] vref test [see=9999999・わわわ] "\
                    "[3] vref test "\
                    "[2] vref test [see=和わ和][see=わわわ test]"
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt='わわわ',
                      vsrc=None, vseq=9999999, tsens=None, prio=None)],
                         [],  # no xrefs in sense #2.
                         [dict(typ=SEE, ord=1, ktxt='和わ和', rtxt=None,
                      vsrc=None, vseq=None, tsens=None, prio=None),
                          dict(typ=SEE, ord=2, ktxt=None, rtxt='わわわ',
                      vsrc=99, vseq=None, tsens=None, prio=None)]])

  # Miscellaneous conditions...
 
    def test001010(_):  # Target with embedded middot (requires quotes).
        jel = '\fＸ\f[1] vref test [see="ドア・マン"]'
        chkv (_, jel, v=[[dict(typ=SEE, ord=1, ktxt=None, rtxt="ドア・マン",
                      vsrc=None, vseq=None, tsens=None, prio=None)]])

    def test001020(_):  # Target rdng,kanj both with middot.
       jel='\fＸ\f[1] vref test '\
             '[see="アジア・太平洋戦争"・"アジア・たいへいようせんそう"]'
       chkv (_, jel, v=[[dict(typ=SEE, ord=1,
                      ktxt="アジア・太平洋戦争", rtxt="アジア・たいへいようせんそう",
                      vsrc=None, vseq=None, tsens=None, prio=None)]])

  # TO-DO:
  # - check whitespace variations (eg one line vs multiple lines).
  # - check failures: exception types, location info.
  # - check other xref types (eg "uses", "example",...)

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
