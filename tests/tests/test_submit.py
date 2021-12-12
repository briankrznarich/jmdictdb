import sys, unittest, os.path, pdb
import unittest_extensions
from jmdb import DBmanager, JelParser
from jmdictdb import jdb, db; from jmdictdb.objects import *
from jmdictdb import submit   # Module to test

  # Database name and load file for tests.
DBNAME, DBFILE = "jmtest01", "data/jmtest01.sql"

  # These tests are not intended to be comprehensive but test a few
  # common cases in the context of a complete submission.
  #
  # These tests create entries in the "test" corpus (src=99) in
  # order not to change any of the entries in other corpora which
  # could invalidate the database for further tests.
  #
  # The tests all share the same database connection (via global
  # 'DBcursor') so sequential operations (eg submit an entry then
  # read it) are in the same transaction and the first operation
  # need not do a commit for the second to see its changes.
  #
  # Conversly a failure of any test will leave the database connection
  # in a failed transaction state which will break any following tests.
  # This is avoided by having a setUp() method in each class, which
  # is run before each test, do a rollback.
  #
  # Both at start of this module's tests and again after they've all
  # run, module setup and teardown functions delete all the entries in
  # the test corpus so preexisting detritus won't affect these tests
  # and to leave things clean for tests that use the database afterwards.

class General (unittest.TestCase):
    def setUp(_):
          # In case a test fail left an open aborted transaction.
        DBcursor.connection.rollback()
    def test_1000010(_):  # Minimal new entry: no sense, reading or kanji.
        errs = []
        e = Entr (src=99, stat=2, _hist=[Hist()])
        submit.submission (DBcursor, e, '', errs)
        _.assertEqual (0, len(errs))

    def test_1000020(_):  # A more realistic submission.
        inp = Entr (stat=2, src=99, _hist=[Hist()],
                    _rdng=[Rdng(txt='ゴミ')], _kanj=[],
                    _sens=[Sens(_gloss=[Gloss(txt="trash",lang=1,ginf=1)])],)
        eid,seq,src = submit_ (inp, disp='')
        for t in eid,seq,src: _.assertTrue(t)
          # An index exception on next line indicates the new entry
          #  was not found.  Note that we do not have to commit it;
          # because we read with the same connection it was written
          # with the read is in the same transaction.
        out = jdb.entrList (DBcursor, None, [eid])[0]
          # Note that submit.submission() modified 'inp' to set all the
          #  object primary key fields to the values used in the database
          #  and thus it should exactly match 'out'.
        _.assertEqual (inp, out)

    def test1000040(_):  # Parent entry disappears before commit of child
                         #  as can happen when someone else approves a
                         #  different edit of the same entry.
        inp = Entr (stat=2, src=99,
                    _rdng=[Rdng(txt='パン')], _kanj=[],
                    _sens=[Sens(_gloss=[Gloss(txt="breab",lang=1,ginf=1)])],
                    _hist=[Hist()])
        eid,seq,src = submit_ (inp, disp='')
        DBcursor.connection.commit()
          # An index exception on next line indicates the new entry
          #  was not found.
        out = jdb.entrList (DBcursor, None, [eid])[0]
          # Make a change to the entry.
        inp._sens[0]._gloss[0].txt = "bread"
        inp.dfrm = eid
          # Remove the original entry as would happen if someone else had
          # approved a different edit of it.
        DBcursor.execute ("DELETE FROM entr WHERE id=%s", (eid,))
        DBcursor.connection.commit()
          # Now submit our first edit which should raise an exception
          # since the parent entry is gone.
        errs = submitE (_, inp, disp='')
        _.assertIn ('[noroot] The entry you are editing no longer exists',
                    errs[0])

class Approval (unittest.TestCase):
    def setUp(_):
          # In case a test fail left an open aborted transaction.
        DBcursor.connection.rollback()

    def test1000010(_):  # Create an new unapproved entry and approve.
        inp = Entr (stat=2, src=99,
                    _rdng=[Rdng(txt='パン')], _kanj=[],
                    _sens=[Sens(_gloss=[Gloss(txt="breab",lang=1,ginf=1)])],
                    _hist=[Hist()])
        eid,seq,src = submit_ (inp, disp='')
        DBcursor.connection.commit()
          # An index exception on next line indicates the new entry
          #  was not found.
        out = jdb.entrList (DBcursor, None, [eid])[0]
          # Make a change to the entry.
        inp._sens[0]._gloss[0].txt = "bread"
        inp.dfrm = eid
          # And submit with editor approval.
        eid2,seq2,src2 = submit_ (inp, disp='a',is_editor=True,userid='smg')
        out2 = jdb.entrList (DBcursor, None, [eid2])[0]
        _.assertEqual (inp, out2)
          # The original entry should have been disappeared.
        out3 = jdb.entrList (DBcursor, None, [eid])
        _.assertEqual ([], out3)
        #FIXME? should also check history records?

    def test1000020(_):  # Edit an approved entry and approve.
        inp = Entr (stat=2, src=99,
                    _rdng=[Rdng(txt='パン')], _kanj=[],
                    _sens=[Sens(_gloss=[Gloss(txt="breab",lang=1,ginf=1)])],
                    _hist=[Hist()])
          # Create a new, approved entry.
        eid,seq,src = submit_ (inp, disp='a',is_editor=True,userid='smg')
          # An index exception on next line indicates the new entry
          #  was not found.
        out = jdb.entrList (DBcursor, None, [eid])[0]
          # Make a change to the entry.
        inp._sens[0]._gloss[0].txt = "bread"
        inp.dfrm = eid
          # And submit with editor approval.
        eid2,seq2,src2 = submit_ (inp, disp='a',is_editor=True,userid='smg')
        out2 = jdb.entrList (DBcursor, None, [eid2])[0]
        _.assertEqual (inp, out2)
          # The original entry should have been disappeared.
        out3 = jdb.entrList (DBcursor, None, [eid])
        _.assertEqual ([], out3)

    def test1000030(_):  # Fail when submit entries with same corpus/seq#.
                         # IS-213.
        inp = Entr (seq=1000030, stat=2, src=99,
                    _rdng=[Rdng(txt='パン')], _kanj=[],
                    _sens=[Sens(_gloss=[Gloss(txt="bread",lang=1,ginf=1)])],
                    _hist=[Hist()])
          # Create a new, approved entry.
        eid,seq,src = submit_ (inp, disp='a',is_editor=True,userid='smg')
        errs = submitE (_, inp, disp='a', is_editor=True, userid='smg')
        _.assertIn ('entry you are editing no longer exists', errs[0])

class Clean (unittest.TestCase):
      # Tests for submit.clean() which strips ascii control characters
      # from a string and expands tabs.
    def test_0010(_): _.assertEqual (None, submit.clean (None))
    def test_0020(_): _.assertEqual ('', submit.clean (''))
    def test_0030(_): _.assertEqual ('a b', submit.clean ('a b'))
    def test_0040(_): _.assertEqual ('a\nb', submit.clean ('a\nb'))
    def test_0050(_): _.assertEqual ('a\nb', submit.clean ('a\r\nb'))
      # Tests 0060: currently tab expansion was reverted hence the change here.
    #def test_0060(_): _.assertEqual ('aa      b', submit.clean ('aa\tb'))
    def test_0060(_): _.assertEqual ('aa\tb', submit.clean ('aa\tb'))
    def test_0070(_): _.assertEqual ('ab', submit.clean ('a\bb\x1f'))

       # When given 'source' and 'errs' arguments it will record the
       # cleanup by adding a message to 'errs'.

    def test_0310(_):   # Nothing removed, no message.
         errs = []
         _.assertEqual ('ab', submit.clean ('ab', 'test', errs))
         _.assertEqual ([], errs);

    def test_0320(_):  # Make sure we get expected message and existing
         errs = ['x']  #  messages are not overwritten.
         _.assertEqual ('ab', submit.clean ('a\x0cb', 'test', errs))
         _.assertEqual ('x', errs[0]);
         _.assertEqual ("Illegal characters in 'test'", errs[1])

    def test_0330(_):  # In context of a submission, bad characters
        errs = []      #  abort it.
        e = Entr (src=99, stat=2, _hist=[Hist(notes='a\r\nb')])
        eid,seq,src = submit.submission (DBcursor, e, '', errs)
        _.assertEqual ((None,None,None), (eid,seq,src))
        _.assertEqual (1, len(errs))
        _.assertEqual ("Illegal characters in 'comments'", errs[0])

class Xrefs (unittest.TestCase):   # Named with plural form because "Xref"
    @classmethod                   #  conflicts with objects.Xref.
    def setUpClass(cls):
          # Create some entries to use as xref targets.  These are created
          # in the test corpus (c=99) since all entries in that corpus are
          # removed by the tearDownModule() function when all tests are
          # finished.
        cls.t1 = addentr ('猫\fねこ\f[1]cat', q=20100, c=99)
        cls.t2 = addentr ('馬\fうま\f[1]horse[2]mule', q=20110, c=99)
    def setUp(_):
          # In case a test fail left an open aborted transaction.
        DBcursor.connection.rollback()

    def test0001(_):
          # Create a single, simple xref.
        e0 = mkentr ('犬\fいぬ\f[1]dog [see=猫]', c=99, h=[Hist()])
        id,seq,src = submit_ (e0, disp='')
        e1 = jdb.entrList (DBcursor, None, [id])[0]
        expect = [Xref (id,1,1,3,_.t1.id,1,None,1,None,False,False)]
        _.assertEqual (expect, e1._sens[0]._xref)
        _.assertEqual ([],     e1._sens[0]._xrslv)

    def test0002(_):
          # Xref to kanji and sense #1.
        e0 = mkentr ('犬\fいぬ\f[1]dog [see=馬[2]]', c=99, h=[Hist()])
        id,seq,src = submit_ (e0, disp='')
        e1 = jdb.entrList (DBcursor, None, [id])[0]
        expect = [Xref (id,1,1,3,_.t2.id,2,None,1,None,False,False)]
        _.assertEqual (expect, e1._sens[0]._xref)
        _.assertEqual ([],     e1._sens[0]._xrslv)

    def test0003(_):
          # Xref to reading and sense #1.
        e0 = mkentr ('子犬\fこいぬ\f[1]puppy [see=うま[2]]', c=99, h=[Hist()])
        id,seq,src = submit_ (e0, disp='')
        e1 = jdb.entrList (DBcursor, None, [id])[0]
        expect = [Xref (id,1,1,3,_.t2.id,2,1,None,None,False,False)]
        _.assertEqual (expect, e1._sens[0]._xref)
        _.assertEqual ([],     e1._sens[0]._xrslv)

class Xrslvs (unittest.TestCase):  # Named with plural form because "Xrslv"
    def test0001(_):               #  conflicts objects.Xrslv.
          # An xref to a non-existant target will generate an Xrslv object.
        e0 = mkentr ('犬\fいぬ\f[1]dog[see=猫猫]', c=99, h=[Hist()])
        errs = []
        id,seq,src = submit_ (e0, disp='')
        e1 = jdb.entrList (DBcursor, None, [id])[0]
        expect = [Xrslv (id,1,1,3,None,'猫猫',None,None,None,None,None)]
        _.assertEqual (expect, e1._sens[0]._xrslv)
        _.assertEqual ([],     e1._sens[0]._xref)


#=============================================================================
# Support functions

  # Create an Entr object from JEL.
def mkentr (jel, q=None, c=99, s=2, u=False, d=None, h=[]):
          # We need to pass srcid, stat, unap to .parse because they
          # are used when resolving any xrefs.
        entr = JELparser.parse (jel, src=c, stat=s, unap=u, dfrm=d)
        if h: entr._hist.extend (h)
        return entr

  # Create an Entr object from JEL and add it to the database.
def addentr (jel, q=None, c=99, s=2, u=False, d=None):
        entr = mkentr (jel, q, c, s, u, d)
        id,seq,src = jdb.addentr (DBcursor, entr)
        DBcursor.connection.commit()
        return entr

  # Submit an Entr via submit.submission().  Call this when no errors are
  # expected.  If any occur, a Runtime Exception is raised so they will
  # be noticed without need for caller to explicitly pass and check 'errs'.
def submit_ (entr, **kwds):   # Trailing "_" in function name to avoid
        errs = []             #  conflict with submit module.
        kwds['errs'] = errs
        id,seq,src = submit.submission (DBcursor, entr, **kwds)
        if errs: raise RuntimeError (errs)
          # Don't commit, transaction will be rolled back automatically.
        return id,seq,src

  # Submit an Entr via submit.submission().  Call this when errors are
  # expected.  The submission() return values confirmed to be None*3
  # and the value of the 'errs' parameter returned for checking by the
  # caller.
def submitE (_, entr, **kwds):
        errs = []
        kwds['errs'] = errs
        id,seq,src = submit.submission (DBcursor, entr, **kwds)
          # Don't commit, transaction will be rolled back automatically.
        _.assertEqual ((id,seq,src), (None,None,None))
        return errs

  # Global variables.
DBcursor = JELparser = None

def setUpModule():
        global DBcursor, JELparser
        DBcursor = DBmanager.use (DBNAME, DBFILE)
        JELparser = JelParser (DBcursor)
        db.ex (DBcursor.connection,
               "DELETE FROM entr WHERE src=99; COMMIT")

def tearDownModule():
        #print ("Deleting entries from 'test' corpus", file=sys.stderr)
        DBcursor.connection.rollback()   # In case a test fail left an
                                         #  open aborted transaction.
          # Remove any test entries that we couldn't avoid committing.
        db.ex (DBcursor.connection,
               "DELETE FROM entr WHERE src=99; COMMIT")

def main(): unittest.main()

if __name__ == '__main__': unittest.main()
