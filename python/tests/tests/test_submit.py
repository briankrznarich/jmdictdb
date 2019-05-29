import sys, unittest, os.path, pdb
if '../lib' not in sys.path: sys.path.append ('../lib')
import jdb, db
from objects import *
import unittest_extensions
from jmdb import DBmanager
__unittest = 1

# Module to test
import submit

  # Database name and load file for tests.
DBNAME, DBFILE = "jmtest01", "data/jmtest01.sql"

  # Global variables.
DBcursor = None

def setUpModule():
        global DBcursor
        DBcursor = DBmanager.use (DBNAME, DBFILE)
def tearDownModule():
        db.ex (DBcursor.connection, 
               "DELETE FROM entr WHERE src=99; COMMIT")

class General (unittest.TestCase):
    def test1000010(_):  # Minimal new entry
        inp = Entr (stat=2, src=99,
                    _rdng=[Rdng(txt='ゴミ')], _kanj=[],
                    _sens=[Sens(_gloss=[Gloss(txt="trash",lang=1,ginf=1)])],
                    _hist=[Hist()])
        errs = []
        eid,seq,src = submit.submission (DBcursor, inp, '', errs)
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
