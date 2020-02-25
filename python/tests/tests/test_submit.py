import sys, unittest, os.path, pdb
if '../lib' not in sys.path: sys.path.append ('../lib')
import jdb, db; from objects import *
import unittest_extensions
from jmdb import DBmanager, JelParser
import submit   # Module to test

  # Database name and load file for tests.
DBNAME, DBFILE = "jmtest01", "data/jmtest01.sql"

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
        errs = []
        eid,seq,src = submit_ (inp, disp='')
        _.assertFalse (errs)
        for t in eid,seq,src: _.assertTrue(t)
        DBcursor.connection.commit()
          # An index exception on next line indicates the new entry
          #  was not found.
        out = jdb.entrList (DBcursor, None, [eid])[0]
          # Note that submit.submission() modified 'inp' to set all the
          #  object primary key fields to the values used in the database
          #  and thus it should exactly match 'out'.
        _.assertEqual (inp, out)

class Xrefs (unittest.TestCase):  #! name "Xref" conflicts with objects.Xref!
    def test0001(_):
          # Create a single, simple xref.
        et = addentr ('猫\fねこ\f[1]cat', q=20100, c=99)
        e0 = mkentr ('犬\fいぬ\f[1]dog [see=猫]', c=99, h=[Hist()])
        errs = []
        id,seq,src = submit_ (e0, disp='')
        e1 = jdb.entrList (DBcursor, None, [id])[0]
        expect = [Xref (id,1,1,3,et.id,1,None,1,None,False,False)]
        _.assertEqual (expect, e1._sens[0]._xref)
        _.assertEqual ([],     e1._sens[0]._xrslv)

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
def submit_ (entr, disp=''):  # Trailing "_" to avoid conflict
        errs = []             #  with submit module.
        id,seq,src = submit.submission (DBcursor, entr, '', errs)
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
        db.ex (DBcursor.connection,
               "DELETE FROM entr WHERE src=99; COMMIT")

def main(): unittest.main()

if __name__ == '__main__': unittest.main()
