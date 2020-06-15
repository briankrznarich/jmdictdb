import sys, unittest, unittest.mock, pdb
from jmdictdb import jdb
from jmdictdb.objects import *

class Mark_seq_xrefs (unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: jdb.KW
        except AttributeError: jdb.KW = jdb.Kwds (jdb.std_csv_dir())

    # These are tests for the jdb.mark_seq_xref() function.
    # Each test case creates a list of xrefs and calls jdb.mark_seq_xref()
    # on them.  mark_seq_xrefs() searches the database for other entries
    # having the same sequence number in order to determine its response.
    # We provide a mock cursor for that database access.  The mock cursor
    # arguments are a list of the rows that the simulated database returns
    # which should be a list of 3-tuples: (src,seq,count) where 'count'
    # is the number of active entries with that src,seq value.
    # After calling mark_seq_xrefs() we use check_sql() to check that
    # the mock cursor was called with the right sql and sql args.
    # The check_sql() arguments are the sql args that were expected
    # and are a list of: srcid, n*seq, KW.STAT['A'].id (=2).
    # Following that we use unittest assert methods to check that
    # mark_seq_xrefs() made the expected changes to the xrefs.

    def test_001(_):
        cur = MockCursor (None)
        jdb.mark_seq_xrefs (cur, [])  # Empty list for no xrefs at all.
        check_sql (cur, None)

    def test_002(_):
        e1 = Entr(id=200,src=1,seq=12345,stat=2,unap=False)
        x1 = Xref(entr=100,sens=1,typ=2,xentr=200,xsens=2)
        x1.TARG = e1;  x1._xsens = [2]
        cur = MockCursor ([[e1.src,e1.seq,1]])
        jdb.mark_seq_xrefs (cur, [x1])
        check_sql (cur, [1,12345,2])
        _.assertTrue (hasattr (x1, 'SEQ'))
        _.assertEqual (True, x1.SEQ)

    def test_003(_):
          # 2 xrefs -> 2 senses of same target.
        e1 = Entr(id=200,src=1,seq=12345,stat=2,unap=False)
        x1 = Xref(entr=100,sens=1,typ=2,xentr=200,xsens=2)
        x1.TARG = e1;  x1._xsens = [2,3]
        x2 = Xref(entr=100,sens=1,typ=2,xentr=200,xsens=3)
        x2.TARG = e1;  x2._xsens = []
        cur = MockCursor ([[1,12345,1]])
        jdb.mark_seq_xrefs (cur, [x1,x2])
        check_sql (cur, [1,12345,2])
        _.assertTrue (hasattr (x1, 'SEQ'))
        _.assertEqual (True, x1.SEQ)
        _.assertTrue (hasattr (x2, 'SEQ'))
        _.assertEqual (True, x2.SEQ)    #???

    def test_004(_):
          # 2 xrefs -> 2 different seq# targets.
        e1 = Entr(id=200,src=1,seq=12345,stat=2,unap=False)
        e2 = Entr(id=201,src=1,seq=87654,stat=2,unap=False)
        x1 = Xref(entr=100,sens=1,typ=2,xentr=200,xsens=2)
        x1.TARG = e1;  x1._xsens = [2]
        x2 = Xref(entr=100,sens=1,typ=2,xentr=201,xsens=3)
        x2.TARG = e2;  x2._xsens = [3]
        cur = MockCursor ([[1,12345,1],[1,87654,1]])
        jdb.mark_seq_xrefs (cur, [x1,x2])
        check_sql (cur, [1,12345,87654,2])
          # We expect both xrefs to be tagged with a true SEQ value
          # even though they are for the same target seq because the
          # .xsens is different.  If the first has a ._xsens list,
          # then the displaying app will likely skip the second.  If
          # it doesn't, then it should display in seq form
        _.assertTrue (hasattr (x1, 'SEQ'))
        _.assertEqual (True, x1.SEQ)
        _.assertTrue (hasattr (x2, 'SEQ'))
        _.assertEqual (True, x2.SEQ)

    def test_005(_):
          # 2 xrefs -> 2 different targets w same seq number.
        e1 = Entr(id=200,src=1,seq=12345,stat=2,unap=False)
        e2 = Entr(id=201,src=1,seq=12345,stat=2,unap=True)
        x1 = Xref(entr=100,sens=1,typ=2,xentr=200,xsens=2)
        x1.TARG = e1;  x1._xsens = [2]
        x2 = Xref(entr=100,sens=1,typ=2,xentr=201,xsens=2)
        x2.TARG = e2;  x2._xsens = [2]
        cur = MockCursor ([[1,12345,2]])
        jdb.mark_seq_xrefs (cur, [x1,x2])
        check_sql (cur, [1,12345,2])
          # Both xrefs of the single source entry point to target
          # entries of the same seq num, and all the entries if that
          # seq number are covered by the xrefs, so first xref gets
          # a .SEQ=True attribute, subsequent ones get SEQ=False.
        _.assertTrue (hasattr (x1, 'SEQ'))
        _.assertEqual (True, x1.SEQ)
        _.assertTrue (hasattr (x2, 'SEQ'))
        _.assertEqual (False, x2.SEQ)

    def test_006(_):
          # 2 xrefs with different .sens -> 2 different targets with
          # same seq number.
        e1 = Entr(id=200,src=1,seq=12345,stat=2,unap=False)
        e2 = Entr(id=201,src=1,seq=12345,stat=2,unap=True)
        x1 = Xref(entr=100,sens=1,typ=2,xentr=200,xsens=2)
        x1.TARG = e1;  x1._xsens = [2]
        x2 = Xref(entr=100,sens=1,typ=2,xentr=201,xsens=3)
        x2.TARG = e2;  x2._xsens = [3]
        cur = MockCursor ([[1,12345,2]])
        jdb.mark_seq_xrefs (cur, [x1,x2])
        check_sql (cur, [1,12345,2])
          # Both xrefs of the single source entry point to target
          # entries of the same seq num, and all the entries of that
          # seq number are covered by the xrefs, but source .xsens are
          # different, so each xref gets a .SEQ=True attribute.
        _.assertTrue (hasattr (x1, 'SEQ'))
        _.assertEqual (True, x1.SEQ)
        _.assertTrue (hasattr (x2, 'SEQ'))
        _.assertEqual (True, x2.SEQ)

    def test_007(_):
          # Same as test_005 but each xref in a different source entry.
        e1 = Entr(id=200,src=1,seq=12345,stat=2,unap=False)
        e2 = Entr(id=201,src=1,seq=12345,stat=2,unap=True)
        x1 = Xref(entr=100,sens=1,typ=2,xentr=200,xsens=2)
        x1.TARG = e1;  x1._xsens = [2]
        x2 = Xref(entr=101,sens=1,typ=2,xentr=201,xsens=2)
        x2.TARG = e2;  x2._xsens = [2]
        cur = MockCursor ([[1,12345,2]])
        jdb.mark_seq_xrefs (cur, [x1,x2])
        check_sql (cur, [1,12345,2])
          # Expect no .SEQ attribute because there are two q=12345
          # entries, but each of the two source entry points to only
          # one of them, hence they cannot use a seq representation.
        _.assertTrue (not hasattr (x1, 'SEQ'))
        _.assertTrue (not hasattr (x2, 'SEQ'))

    def test_008(_):
          # 3 xrefs -> 3 different targets w same seq number, one
          # of which is a "rejected" entry.
        e1 = Entr(id=200,src=1,seq=12345,stat=2,unap=False)
        e2 = Entr(id=201,src=1,seq=12345,stat=3,unap=False)
        e3 = Entr(id=202,src=1,seq=12345,stat=2,unap=True)
        x1 = Xref(entr=100,sens=1,typ=2,xentr=200,xsens=2)
        x1.TARG = e1;  x1._xsens = [2]
        x2 = Xref(entr=100,sens=1,typ=2,xentr=201,xsens=2)
        x2.TARG = e2;  x2._xsens = [2]
        x3 = Xref(entr=100,sens=1,typ=2,xentr=202,xsens=2)
        x3.TARG = e3;  x2._xsens = [2]
        cur = MockCursor ([[1,12345,2]])
        jdb.mark_seq_xrefs (cur, [x1,x2,x3])
        check_sql (cur, [1,12345,2])
          # Both xrefs of the single source entry point to target
          # entries of the same seq num, and all the entries of that
          # seq number are covered by the xrefs, so first xref gets
          # a .SEQ=True attribute, subsequent ones get SEQ=False.
        _.assertTrue (hasattr (x1, 'SEQ'))
        _.assertEqual (True, x1.SEQ)
        _.assertTrue (not hasattr (x2, 'SEQ'))
        _.assertTrue (hasattr (x3, 'SEQ'))
        _.assertEqual (False, x3.SEQ)

#=============================================================================
# Support functions

def MockCursor (rv):    # Create a mock database cursor.
          # rv -- Rows expected to be returned from cursor.fetchall()
        m = unittest.mock.Mock(['fetchall', 'execute'])
        m.fetchall.return_value = rv
        return m

def check_sql (mock, sqlargs):
          # Check that the database cursor (represented by 'mock') was
          # asked to execute the expected SQL and args.
        if not sqlargs:  # If no sqlargs, mark_seq_xrefs() wont use db.
            mock.execute.assert_not_called()
            mock.fetchall.assert_not_called()
            return
        sql = "SELECT src,seq,COUNT(*) FROM entr " \
          "WHERE src=%%s AND seq IN(%s) AND stat=%%s GROUP BY src,seq" \
           % ",".join(["%s"]*(len(sqlargs)-2))
        mock.execute.assert_called_once_with (sql, sqlargs)
        mock.fetchall.assert_called_once_with()

if __name__ == '__main__': unittest.main()
