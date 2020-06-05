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
          #  Abbreviations for brevity.
        global N, SEE, ANT         
        N=None; SEE,ANT = jdb.KW.XREF['see'].id, jdb.KW.XREF['ant'].id

class Resolve (unittest.TestCase):
    longMessage = False
      # 'data' argument for chkr() is::
      #   [rtxt, ktxt, slist,      seq,  corp, extra] 
      #    (str) (str) (list(int)) (int) (int) (dict)
      # 'N' is abbreviation for None (see setUpModule() above.)

    def test000110(_):  # Basic xref, kanji only.
        d = [N, "双対", [], N, N, {}]
        chkxr (_, d, [dict(xentr=44, xsens=1, rdng=None, kanj=1,
                           nosens=None, lowpri=None)])

    def test000120(_):  # Basic xref, reading only.
        d = ["そうつい", N, [], N, N, {}]
        chkxr (_, d, [dict(xentr=44, xsens=1, rdng=1, kanj=None,
                           nosens=None, lowpri=None)])

    def test000130(_):  # Basic xref, seq# and corp# only.
        d = [N, N, [], 1398850, 1, {}]   # Note corp# is required since
                                         # without it, seq# will be
                                         # interpreted as an entry id#.
        chkxr (_, d, [dict(xentr=44, xsens=1, rdng=1, kanj=1,
                           nosens=None, lowpri=None)])

    def test000310(_):  # No senses defaults to all senses.
        d = [N, '町', [], N, N, {}]
        chkxr (_, d, [dict(xentr=58, xsens=1, rdng=None, kanj=1,
                           nosens=None, lowpri=None),
                      dict(xentr=58, xsens=2, rdng=None, kanj=1,
                           nosens=None, lowpri=None),
                      dict(xentr=58, xsens=3, rdng=None, kanj=1,
                           nosens=None, lowpri=None),
                      dict(xentr=58, xsens=4, rdng=None, kanj=1,
                           nosens=None, lowpri=None),
                      dict(xentr=58, xsens=5, rdng=None, kanj=1,
                           nosens=None, lowpri=None) ])

    def test000320(_):  # Xref explicitly to one of multiple senses.
        d = [N, '町', [2], N, N, {}]
        chkxr (_, d, [dict(xentr=58, xsens=2, rdng=None, kanj=1,
                           nosens=None, lowpri=None)])

    def test000330(_):  # Xref explicitly to two of multiple senses.
        d = [N, "町", [2,5], N, N, {}]
        chkxr (_, d, [dict(xentr=58, xsens=2, rdng=None, kanj=1,
                           nosens=None, lowpri=None),
                      dict(xentr=58, xsens=5, rdng=None, kanj=1,
                         nosens=None, lowpri=None)])

    def test000220(_):  # Xref to 1st kanji.
        d = [N, "治具", [], N, N, {}]
        chkxr (_, d, [dict(xentr=39, xsens=1, rdng=None, kanj=1,
                           nosens=None, lowpri=None)])

    def test000230(_):  # Xref to 2nd kanji.
        d = [N, "冶具", [], N, N, {}]
        chkxr (_, d, [dict(xentr=39, xsens=1, rdng=None, kanj=2,
                           nosens=None, lowpri=None)])

    def test000240(_):  # Xref to 1st reading.
        d = ["じぐ", N, [], N, N, {}]
        chkxr (_, d, [dict(xentr=39, xsens=1, rdng=1, kanj=None,
                           nosens=None, lowpri=None)])

    def test000250(_):  # Xref to 2nd reading.
        d = ["ジグ", N, [], N, N, {}]
        chkxr (_, d, [dict(xentr=39, xsens=1, rdng=2, kanj=None,
                           nosens=None, lowpri=None)])

    def test000260(_):  # Xref to kanji with corpus.
        d = [N, "治具", [], N, 1, {}]
        chkxr (_, d, [dict(xentr=39, xsens=1, rdng=None, kanj=1,
                           nosens=None, lowpri=None)])

    def test000270(_):  # Xref to reading with corpus.
        d = ["ジグ", N, [], N, 1, {}]
        chkxr (_, d, [dict(xentr=39, xsens=1, rdng=2, kanj=None,
                           nosens=None, lowpri=None)])

    # TO-DO: quoted and dotted targets, failures (not found,
    #  multiple, no sense, no corpus), nosens and lowpri.

#=============================================================================
# Support functions


def chkxr (_, data, expect):
        rtxt, ktxt, slist, enum, corp, kwargs = data
        xrefs = jdb.resolv_xref (DBcursor, None, rtxt, ktxt, slist,
                                           enum, corp, **kwargs)
        _.assertEqual (len(expect), len(xrefs),
                       "Expected %d xrefs but got %d"
                       % (len(expect), len(xrefs)))
        for n,(x,e) in enumerate (zip (xrefs, expect)):
            cmp1xref (_, n, x, e)

def cmp1xref (_, n, xref, exp):
        msgs = []
          # Check all attributes and generate a single failure for all
          # so they don't need to be discovered by fixing one at a time.
        for k,expected in exp.items():
            got = getattr (xref, k)
            if got != expected: msgs.append (
                "xref[%s]: expected '%r', got '%s'" % (n, expected, got))
        if msgs:
            if len(msgs)==1: _.fail (msgs[0])
            _.fail ("\n  " + "\n  ".join (msgs))

if __name__ == '__main__': main()
