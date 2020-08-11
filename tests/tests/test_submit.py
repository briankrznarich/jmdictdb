import sys, unittest, os.path, pdb
import unittest_extensions
from jmdb import DBmanager, JelParser
from jmdictdb import jdb, db; from jmdictdb.objects import *
from jmdictdb import submit   # Module to test

  # Database name and load file for tests.
DBNAME, DBFILE = "jmtest01", "data/jmtest01.sql"

  # These tests are not intended to be comprehensive but test a few
  # common cases in the context of a complete submission.

  # These tests create entries in the "test" corpus (src=99) in
  # order not to change any of the entries in other corpora which
  # would invalidate the database for further tests.  All "test"
  # corpus entries are deleted in the module setup function so
  # preexisting detritus won't affect these tests, and again in
  # the module tear down function to leave things clean for tests
  # that use the database afterwards.

class General (unittest.TestCase):
    def test1000010(_):  # Minimal new entry
        inp = Entr (stat=2, src=99,
                    _rdng=[Rdng(txt='ゴミ')], _kanj=[],
                    _sens=[Sens(_gloss=[Gloss(txt="trash",lang=1,ginf=1)])],
                    _hist=[Hist()])
        eid,seq,src = submit_ (inp, disp='')
        for t in eid,seq,src: _.assertTrue(t)
        DBcursor.connection.commit()
          # An index exception on next line indicates the new entry
          #  was not found.
        out = jdb.entrList (DBcursor, None, [eid])[0]
          # Note that submit.submission() modified 'inp' to set all the
          #  object primary key fields to the values used in the database
          #  and thus it should exactly match 'out'.
        _.assertEqual (inp, out)

class Approval (unittest.TestCase):
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

    def test1000030(_):  # Fail when submit entries with same corpus/seq#.
                         # IS-213.
        inp = Entr (seq=1000030, stat=2, src=99,
                    _rdng=[Rdng(txt='パン')], _kanj=[],
                    _sens=[Sens(_gloss=[Gloss(txt="bread",lang=1,ginf=1)])],
                    _hist=[Hist()])
          # Create a new, approved entry.
        eid,seq,src = submit_ (inp, disp='a',is_editor=True,userid='smg')
        DBcursor.connection.commit()
        with _.assertRaisesRegex (db.IntegrityError,
                    'duplicate key value violates unique constraint '
                    '"entr_src_seq_idx"'):
            submit_ (inp, disp='a', is_editor=True, userid='smg')
          # The db connection is in failed transaction state at this point;
          # do a rollback to prevent failure of subsequent operations that
          # use it.  
        DBcursor.connection.rollback()

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

  # Submit an Entr via submit.submission().
def submit_ (entr, **kwds):  # Trailing "_" to avoid conflict
        errs = []             #  with submit module.
        kwds['errs'] = errs
        id,seq,src = submit.submission (DBcursor, entr, **kwds)
        if errs: raise RuntimeError (errs)
        DBcursor.connection.commit()
        return id,seq,src

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
        db.ex (DBcursor.connection,
               "DELETE FROM entr WHERE src=99; COMMIT")

def main(): unittest.main()

if __name__ == '__main__': unittest.main()
