import sys, unittest, os.path, pdb
if '../lib' not in sys.path: sys.path.append ('../lib')
import jdb, fmtjel, jmxml, xmlkw, jelparse, jellex
from objects import *
import unittest_extensions
from jmdb import DBmanager
__unittest = 1

def main(): unittest.main()

  # Database name and load file for tests.
DBNAME, DBFILE = "jmtest01", "data/jmtest01.sql"

  # We initialize JEL lexer and parser objects that will be will be
  # fed test data and whose results will be checked.  The lexer and
  # parser are created once and reused for all tests.
  # For many tests a round-trip test is used -- JEL text describing
  # and entry is parsed resulting in a jdb.Entr object which is then
  # reformated back into JEL with fmtjel(); the results should match
  # the input text.
  # Access to a JMdictDB database is required, both to supply KW mapping
  # tables and to provide entries for resolving xrefs.  A  singleton
  # jmdb.DBmanager instance to used to load a well-defined test database
  # if it is not already loaded on the server.  The database is loaded
  # only once and reused by all tests.
  # For background on this test architecture see README.txt.

  # Global variables.
DBcursor = JELparser = JELlexer = JMparser = None

def setUpModule():
        global DBcursor, JELparser, JELlexer, JMparser
        DBcursor = DBmanager.use (DBNAME, DBFILE)
        JELlexer, tokens = jellex.create_lexer ()
        JELparser = jelparse.create_parser (JELlexer, tokens)
        JMparser = jmxml.Jmparser (jdb.KW)

class General (unittest.TestCase):
    def test1000290(_): check(_,1000290)  # simple, 1H1S1Ts1G
    def test1000490(_): check(_,1000490)  # simple, 1H1K1S1Ts1G
    def test1004020(_): check(_,1004020)  #
    def test1005930(_): check(_,1005930)  # Complex, 3KnTk4RnTr1S2Ts1G1Xf1XrNokanj
    def test1324440(_): check(_,1324440)  # restr: One 'nokanji' reading
    def test1000480(_): check(_,1000480)  # dialect
    def test1002480(_): check(_,1002480)  # lsrc lang=nl
    def test1013970(_): check(_,1013970)  # lsrc lang=en+de
    def test1017950(_): check(_,1017950)  # lsrc wasei
    def test1629230(_): check(_,1629230)  # lsrc 3 lsrc's
    def test1077760(_): check(_,1077760)  # lsrc lang w/o text
    def test1000520(_): check(_,1000520)  # sens.notes (en)
    def test1000940(_): check(_,1000940)  # sens.notes (en,jp)
    def test1002320(_): check(_,1002320)  # sens notes on mult senses
    def test1198180(_): check(_,1198180)  # sens.notes, long
    def test1079110(_): check(_,1079110)  # sens.notes, quotes
    def test1603990(_): check(_,1603990)  # gloss with starting with numeric char, stagr, stagk, restr
    def test1416050(_): check(_,1416050)  # stagr, stagk, nokanji
    def test1542640(_): check(_,1542640)  # stagr, stagk, restr
    def test1593470(_): check(_,1593470)  # gloss with aprostrophe, stagr, stagk, restr
    def test1316860(_): check(_,1316860)  # mult kinf
    def test1214540(_): check(_,1214540)  # mult kinf
    def test1582580(_): check(_,1582580)  # mult rinf
    def test1398850(_): check(_,1398850)  # mult fld
    def test1097870(_): check(_,1097870)  # mult fld, lsrc
    def test1517910(_): check(_,1517910)  # gloss in quotes
    def test1516925(_): check(_,1516925)  # gloss containg quotes and apostrophe
    def test1379360(_): check(_,1379360)  # gloss, initial paren
    def test1401950(_): check(_,1401950)  # gloss, trailing numeric and paren
    def test1414950(_): check(_,1414950)  # gloss, mult quotes
    def test1075210(_): check(_,1075210)  # gloss, initial digits
    #2 def test1000090(_): check(_,1000090)       # xref and ant with hard to classify kanji.
    def test1000920(_): check(_,1000920)  # xref w rdng (no kanj) and sense number.
    def test1000420(_): check(_,1000420)  # xref w K.R pair.
    def test1011770(_): check(_,1011770)  # ant with K.R.s triple.
    def test2234570(_): check(_,2234570)  # xref w K.s pair.
    def test1055420(_): check(_,1055420)  # dotted reb, wide ascii xref.
    def test1098650(_): check(_,1098650)  # dotted reb, kanji xref.
    def test1099200(_): check(_,1099200)  # mult rdng w dots, kanj xref.
    def test1140360(_): check(_,1140360)  # xref w kanj/katakana.
    def test1578780(_): check(_,1578780)  # dotted pair (K.R) in stagk.
    #2 def test2038530(_): check(_,2038530)       # dotted keb w dotted restr.
    def test2107800(_): check(_,2107800)  # double-dotted reb.
    #3 def test2159530(_): check(_,2159530)       # wide ascii kanj w dot and restr.
    def test1106120(_): check(_,1106120)  # semicolon in gloss.
    def test1329750(_): check(_,1329750)  # literal gloss.

    #1 -- Error due to dotted K.R pair in stagk.
    #2 -- Fails due to xref not found because of K/R misclassification.
    #3 -- Fails due to mid-dot in restr text which is confused with the
    #       mid-dot used to separate K.R pairs.

class Restr (unittest.TestCase):
    def test_001(_):
        e1 = Entr (id=100, src=1, seq=1000010, stat=2, unap=False)
        expect = 'jmdict 1000010 A {100}\n\n\n'
        jeltxt = fmtjel.entr (e1)
        _.assertEqual (expect, jeltxt)
    def test_002(_):
        e1 = Entr (id=100, src=1, seq=1000010, stat=2, unap=False)
        e1._kanj = [Kanj(txt='手紙',), Kanj(txt='切手')]
        e1._rdng = [Rdng(txt='てがみ'), Rdng(txt='あとで'), Rdng(txt='きって')]
        e1._rdng[0]._restr.append (jdb.Restr(kanj=2))
        e1._rdng[1]._restr.append (jdb.Restr(kanj=1))
        e1._rdng[2]._restr.append (jdb.Restr(kanj=1))
        e1._rdng[2]._restr.append (jdb.Restr(kanj=2))
        expect =  'jmdict 1000010 A {100}\n' \
                  '手紙；切手\n' \
                  'てがみ[手紙]；あとで[切手]；きって[nokanji]\n'
        jeltxt = fmtjel.entr (e1)
        msg = "\nA:\n%s\nB:\n%s" % (expect, jeltxt)
        _.assertEqual (expect, jeltxt, msg)

class Extra (unittest.TestCase):
    def test_x00001(_):
        dotest (_, 'x00001')    # dotted restrs in quotes.

class Base (unittest.TestCase):
    def setUp(_):
        _.data = loadData ('data/fmtjel/base.txt', r'# ([0-9]{7}[a-zA-Z0-9_]+)')
    def test0000010(_): check2(_,'0000010')     # lsrc wasei
    def test0000020(_): check2(_,'0000020')     # lsrc partial
    def test0000030(_): check2(_,'0000030')     # lsrc wasei,partial
    def test0000040(_): check2(_,'0000040')     # lsrc wasei,partial

#=============================================================================
# Support functions

def check (_, seq):
          # Read expected text, remove any unicode BOM or trailing whitespace
          # that may have been added when editing.
        with open ("data/fmtjel/"+str(seq)+".txt",encoding='utf-8') as f:
            expected = f.read().rstrip()
        if expected[0] == '\ufeff': expected = expected[1:]
          # Read the entry from the database.  Be sure to get from the right
          # corpus and get only the currently active entry.  Assert that we
          # received excatly one entry.
        sql = "SELECT id FROM entr WHERE src=1 AND seq=%s AND stat=2 AND NOT unap"
        entrs,data = jdb.entrList (DBcursor, sql, (seq,), ret_tuple=True)
        _.assertEqual (1, len (entrs))
          # Add the annotations needed for dislaying xrefs in condensed form.
        jdb.augment_xrefs (DBcursor, data['xref'])
        jdb.augment_xrefs (DBcursor, data['xrer'], rev=True)
        fmtjel.markup_xrefs (DBcursor, data['xref'])
          # Test fmtjel by having it convert the entry to JEL.
        resulttxt = fmtjel.entr (entrs[0]).splitlines(True)
          # Confirm that the received text matched the expected text.
        if resulttxt: resulttxt = ''.join(resulttxt[1:])
        _.assertTrue (10 < len (resulttxt))
        msg = "\nExpected:\n%s\nGot:\n%s" % (expected, resulttxt)
        _.assertEqual (expected, resulttxt, msg)

def check2 (_, test, exp=None):
        intxt = _.data[test + '_data']
        try: exptxt = (_.data[test + '_expect']).strip('\n')
        except KeyError: exptxt = intxt.strip('\n')
        outtxt = roundtrip (intxt, JELlexer, JELparser, DBcursor).strip('\n')
        _.assertTrue (8 <= len (outtxt))    # Sanity check for non-empty entry.
        msg = "\nExpected:\n%s\nGot:\n%s" % (exptxt, outtxt)
        _.assertEqual (outtxt, exptxt, msg)

def roundtrip (intxt, lexer, jelparser, dbcursor):
          # Since hg-180523-6b1a12 we use '\f' to separate the kanji, reading
          # and senses sections in JEL text used as input to jelparse()
          # rather than '\n' which was previously used.  To avoid changing
          # all the test data that still uses '\n', we call secsepfix() to
          # replace the first two '\n's in the test data with '\f's to make
          # suitable for parsing.
        intxt = secsepfix (intxt)
        jellex.lexreset (lexer, intxt)
        entr = jelparser.parse (intxt, lexer=lexer)
        entr.src = 1
        jelparse.resolv_xrefs (dbcursor, entr)
        for s in entr._sens: jdb.augment_xrefs (dbcursor, getattr (s, '_xref', []))
        for s in entr._sens: jdb.add_xsens_lists (getattr (s, '_xref', []))
        for s in entr._sens: jdb.mark_seq_xrefs (dbcursor, getattr (s, '_xref', []))
        outtxt = fmtjel.entr (entr, nohdr=True)
        return outtxt

def loadData (filename, secsep, last=[None,None]):
        # Read test data file 'filename' caching its data and returning
        # cached data on subsequent consecutive calls with same filename.
        if last[0] != filename:
            last[1] = unittest_extensions.readfile_utf8 (filename,
                         rmcomments=True, secsep=secsep)
            last[0] = filename
        return last[1]

def secsepfix (s):
        return s.replace('\n', '\f', 2)

def dotest (_, testid, xmlfn=None, jelfn=None, dir='data/fmtjel', enc='utf_8_sig'):
        if xmlfn is None: xmlfn = os.path.join (dir, testid + '.xml')
        if jelfn is None: jelfn = os.path.join (dir, testid + '.jel')
        expected = readfile (jelfn, enc)
        xmlu = readfile (xmlfn, enc)
        xml8 = xmlu #xmlu.encode ('utf-8')
        elist = JMparser.parse_entry (xml8)
        got = fmtjel.entr (elist[0], nohdr=True)
        msg = "\nExpected:\n%s\nGot:\n%s" % (expected, got)
        _.assertEqual (expected, got, msg)

def readfile (filename, enc):
        with open (filename, 'r', encoding=enc) as f:
            contents = f.read()
        return contents.strip()

if __name__ == '__main__': main()
