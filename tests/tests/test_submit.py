import sys, unittest, os.path, copy, pdb
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
  #
  # A number of tests create the entries in the test database that are
  # then edited and submitted.  The entries are (in some cases) created
  # directly in the database by local helper function addentr() (a thin
  # wrapper around jdb.addentr()) without going through submit.submission().
  # It is then convenient to "edit" the returned entr object (since it
  # already has kanj, rdng, sens, etc, values set) my modifying it and
  # passing it to submission() to check for the expected response.  This
  # editing is conveniently done with helper function edentr() which will
  # automatically create the necessary .dfrm link to the entry it is
  # editing.

class General (unittest.TestCase):
    def setUp(_):  # In case a test fail left an open aborted transaction.
        DBcursor.connection.rollback()

    def test1000010(_):  # Minimal new entry: no sense, reading or kanji.
        errs = []
        e = Entr (src=99, stat=2)
        submit.submission (DBcursor, e, '', errs)
        _.assertEqual (0, len(errs))

    def test1000020(_):  # A more realistic submission.
        inp = Entr (stat=2, src=99,
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
        e1 = addentr ('\fパン\f[1]bread', c=99, s=2)  # Add an entry...
        e2 = edentr (e1)                             # ...and edit it.
          # But before it's submitted, remove the parent entry as would
          # happen if someone else had approved a different edit of it.
        delentr (e1.id)
          # Now submit our first edit which should raise an exception
          # since the parent entry is gone.
        errs = submitE (_, e2, disp='')
        _.assertIn ('[noroot] The entry you are editing no longer exists',
                    errs[0])

    def test1000110(_):  # Non-editor can't edit rejected entry.
        e1 = addentr ('\fパン\f[1]bread', c=99, s=6)  # Add a rejected entry...
        e2 = edentr (e1, s=2)                        # ...and edit it.
        errs = submitE (_, e2, disp='')
        _.assertIn ("Rejected entries can not be edited", errs[0])

    def test1000120(_):  # Editor can't edit rejected entry.
        e1 = addentr ('\fパン\f[1]bread', c=99, s=6)  # Add a rejected entry...
        e2 = edentr (e1, s=2)                        # ...and edit it.
        errs = submitE (_, e2, disp='', is_editor=True)
        _.assertIn ("Rejected entries can not be edited", errs[0])


class Approval (unittest.TestCase):
    def setUp(_):  # In case a test fail left an open aborted transaction.
        DBcursor.connection.rollback()

    def test1000010(_):  # Create an new unapproved entry and approve.
        inp = Entr (stat=2, src=99,
                    _rdng=[Rdng(txt='パン')], _kanj=[],
                    _sens=[Sens(_gloss=[Gloss(txt="breab",lang=1,ginf=1)])])
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

    def test1500020(_):  # Edit an approved entry and approve.
        inp = Entr (stat=2, src=99,
                    _rdng=[Rdng(txt='パン')], _kanj=[],
                    _sens=[Sens(_gloss=[Gloss(txt="breab",lang=1,ginf=1)])])
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

    def test1501030(_):  # Fail when submit entries with same corpus/seq#.
                         # IS-213.
        e1 = addentr ('\fパン\f[1]bread', q=1501030, a=True)
          # Create a second, independent (because its .dfrm does not point
          # to e1), entry with same seq number...
        e2 = mkentr ('\fパンぼうし\f[1]bread hat', q=1501030)
          # ...then try to submit it.
        errs = submitE (_, e2, disp='a', is_editor=True, userid='smg')
        _.assertIn ('[seq_vio] The entry you are editing no longer exists',
                    errs[0])
        _.assertEqual (1, len(errs))   # Expect only 1 error message.

    def test1501040(_):  # Fail submit non-leaf approve.
          # Create edits: e1(A)-->e2(A*)-->e3(A*)
          # then try to approve e2.  It should fail because there is
          # a later edit on the same branch.
        e1 = addentr ('\fねこいし\f[1]cat stone', a=True)
        e2 = addedit (e1)
        e3 = addedit (e2)
          # Edit e2 and and try to approve with submit.submission().
        e = edentr (e2)
        errs = submitE (_, e, disp='a', is_editor=True, userid='smg')
          # Verify error message and conflicting edit ids.
        _.assertIn ('Edits have been made to this entry', errs[0])
        _.assertIn ('>%s<' % e3.id, errs[0])
        _.assertEqual (1, len(errs))   # Expect only 1 error message.

    def test1501050(_):  # Fail submit multiple (2) branches approve.
          # Create edits: e1(A)--.--->e2(A*)
          #                       `-->e3(A*)
          # then try to approve e3.  It should fail because there
          # is another edit branch.
        e1 = addentr ('\fねこぼうし\f[1]cathat', a=True)
        e2 = addedit (e1)
        e3 = addedit (e1)
        e = edentr (e3)   # Edit e3 and try to approve it.
        errs = submitE (_, e, disp='a', is_editor=True, userid='smg')
          # Verify error message and conflict edit ids.
        _.assertIn ('There are other edits pending', errs[0])
        _.assertIn ('>%s<' % e2.id, errs[0])
        _.assertEqual (1, len(errs))   # Expect only 1 error message.

    def test1501070(_):  # Fail submit multiple (3) branches approve.
          # Create edits: e1(A)--.--->e2(A*)
          #                       `-->e3(A*)--.--->e4(A*)
          #                                    `-->e5(A*)
        e1 = addentr ('\fかえばえ\f[1]nonsense', a=True)
        e2=addedit(e1);  e3=addedit(e1);  e4=addedit(e3);  e5=addedit(e3)

          # Try to approve e2.
        e = edentr (e2)
        errs = submitE (_, e, disp='a', is_editor=True, userid='smg')
          # Verify error message and conflict edit ids.
        _.assertIn ('There are other edits pending', errs[0])
        _.assertIn ('>%s<' % e4.id, errs[0])
        _.assertIn ('>%s<' % e5.id, errs[0])
        _.assertEqual (1, len(errs))   # Expect only 1 error message.

          # Try again but with e4 this time.
        e = edentr (e4)
        errs = submitE (_, e, disp='a', is_editor=True, userid='smg')
          # Verify error message and conflict edit ids.
        _.assertIn ('There are other edits pending', errs[0])
        _.assertIn ('>%s<' % e2.id, errs[0])
        _.assertIn ('>%s<' % e5.id, errs[0])
        _.assertEqual (1, len(errs))   # Expect only 1 error message.
          # Try again but with e4 this time.

          # Try again but with e3 this time.  This violates both the
          # the requirement that the edit must be to a leaf entry and
          # that here must no other branches.  Current behavior is
          # to fail on the following edit rather than the multiple
          # branches.
        e = edentr (e3)
        errs = submitE (_, e, disp='a', is_editor=True, userid='smg')
          # Verify error message and conflict edit ids.
        _.assertIn ('Edits have been made to this entry', errs[0])
        _.assertIn ('>%s<' % e4.id, errs[0])
        _.assertIn ('>%s<' % e5.id, errs[0])
        _.assertEqual (1, len(errs))   # Expect only 1 error message.


class Reject (unittest.TestCase):
    def setUp(_):  # In case a test fail left an open aborted transaction.
        DBcursor.connection.rollback()

    def test2000010(_):       # Reject new unapproved edit, c.f. test2001020
        e1 = addentr ("\fかえばえ\f[1]nonsense")
        e = edentr (e1)
        submit_ (e, disp='r',is_editor=True,userid='smg')
        f = _dbread (q=e1.seq)
        _.assertEqual (1, len(f), "Expected 1 entry, got: %s" % f)
        _.assertEqual ((e1.src, 6, e1.seq, None, False), f[0][1:6])

    def test2000020(_):       # Reject a single edit to an approved entry.
        e1 = addentr ("\fかえばえ\f[1]nonsense", a=True)
        e2 = addedit (e1)
        e = edentr (e2)
        submit_ (e, disp='r',is_editor=True,userid='smg')
        f = _dbread (q=e1.seq)
        _.assertEqual (2, len(f), "Expected 2 entries, got: %s" % f)
        _.assertEqual ((e1.src, e1.stat, e1.seq, None, e1.unap), f[0][1:6])
        _.assertEqual ((e2.src, 6,       e2.seq, None, False),   f[1][1:6])

    def test2000030(_):       # Reject a branch of edits to an unapproved entry.
        e1 = addentr ("\fかえばえ\f[1]nonsense")
        e2 = addedit (e1);  e3 = addedit (e2);  e = edentr (e3)
        submit_ (e, disp='r',is_editor=True,userid='smg')
        f = _dbread (q=e1.seq)
        _.assertEqual (1, len(f), "Expected 1 entries, got: %s" % f)
        _.assertEqual ((e2.src, 6,       e2.seq, None, False),   f[0][1:6])

    def test2000040(_):       # Reject a branch of edits to an approved entry.
        e1 = addentr ("\fかえばえ\f[1]nonsense", a=True)
        e2 = addedit (e1);  e3 = addedit (e2);  e = edentr (e3)
        submit_ (e, disp='r',is_editor=True,userid='smg')
        f = _dbread (q=e1.seq)
        _.assertEqual (2, len(f), "Expected 2 entries, got: %s" % f)
        _.assertEqual ((e1.src, e1.stat, e1.seq, None, e1.unap), f[0][1:6])
        _.assertEqual ((e2.src, 6,       e2.seq, None, False),   f[1][1:6])

    def test2000050(_):       # Reject branch up to branch point.
        e1 = addentr ("\fかえばえ\f[1]nonsense", a=True)
        e2 = addedit (e1)                        # Branch 1.
        e3 = addedit (e1);  e4 = addedit (e3)    # Branch 2.
        e = edentr (e4)
        submit_ (e, disp='r',is_editor=True,userid='smg')  # Reject branch 2.
        f = _dbread (q=e1.seq)
        _.assertEqual (3, len(f), "Expected 3 entries, got: %s" % f)
        _.assertEqual ((99, 2, e1.seq, None,    False), f[0][1:6])
        _.assertEqual ((99, 2, e1.seq, e2.dfrm, True),  f[1][1:6])
        _.assertEqual ((99, 6, e1.seq, None,    False), f[2][1:6])

    def test2000060(_):       # Reject single edit on first branch.
          # This tests a bug that was present in revisions prior to the
          # one this test appeared in that caused a "programming error"
          # assertion failure in submit.reject().
        e1 = addentr ("\fかえばえ\f[1]nonsense", a=True)
        e2 = addedit (e1)                        # Branch 1.
        e3 = addedit (e1);  e4 = addedit (e3)    # Branch 2.
        e = edentr (e2)
          # Reject branch 1.
        submit_ (e, disp='r',is_editor=True,userid='smg')
        f = _dbread (q=e1.seq)
        _.assertEqual (4, len(f), "Expected 3 entries, got: %s" % f)
        _.assertEqual ((99, 2, e1.seq, None,  False), f[0][1:6])  # e1
        _.assertEqual ((99, 2, e1.seq, e1.id,  True), f[1][1:6])  # e3
        _.assertEqual ((99, 2, e1.seq, e3.id,  True), f[2][1:6])  # e4
        _.assertEqual ((99, 6, e1.seq, None,  False), f[3][1:6])  # e

    def test2001010(_):       # Fail: reject non-leaf entry.
        e1 = addentr ("\fかえばえ\f[1]nonsense", a=True)
        e2 = addedit (e1);  e3 = addedit (e2)
        e = edentr (e2)   # Edit a non-leaf entry for rejection.
        regex = "Edits have been made to this entry.  To reject entries"
        with _.assertRaisesRegex (RuntimeError, regex):
            submit_ (e, disp='r',is_editor=True,userid='smg')

    def test2001020(_):       # Fail: reject approved entry, c.f. test2000010
        e1 = addentr ("\fかえばえ\f[1]nonsense", a=True)
        e = edentr (e1)   # Edit root entry for rejection.
        regex = "You can only reject unapproved entries"
        with _.assertRaisesRegex (RuntimeError, regex):
            submit_ (e, disp='r',is_editor=True,userid='smg')


class Delete (unittest.TestCase):
    # Test submission of "delete" entries.  We  only test the basic edits
    # since the processing of branch edits and such is done be the same
    # code as for other submissions and is tested by other test classes.

    def setUp(_):  # In case a test fail left an open aborted transaction.
        DBcursor.connection.rollback()

    def test3000010(_):        # unapproved delete of unapproved entry.
        e1 = addentr ("\fかえばえ\f[1]nonsense")
        e = edentr (e1, s=4)   # Edit root entry for deletion.
        submit_ (e, disp='',is_editor=True,userid='smg')
        f = _dbread (q=e1.seq)
          # We expect both the original approved entry 'e1' and the
          # new entry to exist.
        _.assertEqual (2, len(f), "Expected 2 entries, got: %s" % f)
                     # src stat  seq   dfrm     unap
        _.assertEqual ((99, 2, e1.seq, None,    True), f[0][1:6])
        _.assertEqual ((99, 4, e1.seq, e1.id,   True), f[1][1:6])

    def test3000020(_):        # unapproved delete of approved entry.
        e1 = addentr ("\fかえばえ\f[1]nonsense", a=True)
        e = edentr (e1, s=4)   # Edit root entry for deletion.
        submit_ (e, disp='',is_editor=True,userid='smg')
        f = _dbread (q=e1.seq)
          # We expect both the original approved entry 'e1' and the
          # new entry to exist.
        _.assertEqual (2, len(f), "Expected 2 entries, got: %s" % f)
                     # src stat  seq   dfrm     unap
        _.assertEqual ((99, 2, e1.seq, None,   False), f[0][1:6])
        _.assertEqual ((99, 4, e1.seq, e1.id,   True), f[1][1:6])

    def test3000030(_):        # approved delete of unapproved entry.
        e1 = addentr ("\fかえばえ\f[1]nonsense")
        e = edentr (e1, s=4)   # Edit root entry for deletion.
        submit_ (e, disp='a',is_editor=True,userid='smg')
        f = _dbread (q=e1.seq)
          # We expect the original unapproved entry 'e1' to be gone, and
          # the lone new approved (arg 5 below == False) entry to have
          # status 'D' (arg 2 below == 4).
        _.assertEqual (1, len(f), "Expected 2 entries, got: %s" % f)
                     # src stat  seq   dfrm     unap
        _.assertEqual ((99, 4, e1.seq, None,   False), f[0][1:6])

    def test3000040(_):        # approved delete of approved entry.
        e1 = addentr ("\fかえばえ\f[1]nonsense", a=True)
        e = edentr (e1, s=4)   # Edit root entry for deletion.
        submit_ (e, disp='a',is_editor=True,userid='smg')
        f = _dbread (q=e1.seq)
          # We expect the original unapproved entry 'e1' to be gone, and
          # the lone new approved (arg 5 below == False) entry to have
          # status 'D' (arg 2 below == 4).
        _.assertEqual (1, len(f), "Expected 2 entries, got: %s" % f)
                     # src stat  seq   dfrm     unap
        _.assertEqual ((99, 4, e1.seq, None,   False), f[0][1:6])


class History (unittest.TestCase):
    def setUp(_):  # In case a test fail left an open aborted transaction.
        DBcursor.connection.rollback()

    def test4000010(_):
          # Create a new unapproved entry from an approved entry with
          # no history.  This represents probably the most common edit
          # operation that occurs since the vast majority of JMdictDB
          # entries are approved with no history.
        e1 = addentr ("\fかえばえ\f[1]nonsense", a=True)
        e = edentr (e1, h=Hist(name="hist-test"))
        submit_ (e, disp='')
        sql = "SELECT id FROM entr WHERE src=99 AND seq=%s"
        f = jdb.entrList (DBcursor, sql, (e1.seq,))
        _.assertEqual (2, len(f), "Expected 2 entries, got: %s" % f)
          # Original entry's history list should remain empty.
        _.assertEqual (0, len(f[0]._hist))
          # We expect a single item in the new entry hist list.
        _.assertEqual (1, len(f[1]._hist))
          # It should have the name we provided above.
        _.assertEqual ("hist-test", f[1]._hist[0].name)
          # The "eid" field should be same as the "entr" field.
        _.assertEqual (f[1]._hist[0].entr, f[1]._hist[0].eid)

    def test4000020(_):  # Appr entry w/hists -> unappr entry
        e1 = addentr ("\fかえばえ\f[1]nonsense", a=True,
                      h=[Hist(name="hist-1",stat=2,unap=True, dt=db.DEFAULT),
                         Hist(name="hist-2",stat=2,unap=False,dt=db.DEFAULT)])
        e = edentr (e1, h=Hist(name="hist-test"))
        submit_ (e, disp='')
        sql = "SELECT id FROM entr WHERE src=99 AND seq=%s"
          # Retrieve 'e1' and 'e' from the database as 'f[0]' and 'f[1]'.
        f = jdb.entrList (DBcursor, sql, (e1.seq,))
        _.assertEqual (2, len(f), "Expected 2 entries, got: %s" % f)
          # Original entry's history list should remain at two items.
        _.assertEqual (2, len(f[0]._hist))
          # We expect three items in the new entry hist list.
        _.assertEqual (3, len(f[1]._hist))
          # It should have the names we provided above.
        _.assertEqual ("hist-1",    f[1]._hist[0].name)
        _.assertEqual ("hist-2",    f[1]._hist[1].name)
        _.assertEqual ("hist-test", f[1]._hist[2].name)
          # When 'e1' was added to the database, jdb.addentr() set the last
          # hist item's .eid value but didn't touch its first.  When 'e' was
          # submmitted, it received e1 hists and added a new one; the new
          # one's .eid value was set by jdb.addentr().
        _.assertEqual (None, f[1]._hist[0].eid)
        _.assertEqual (f[0].id, f[1]._hist[1].eid)
        _.assertEqual (f[1].id, f[1]._hist[2].eid)

    def test4000030(_):  # Appr entry w/hists -> appr entry
        e1 = addentr ("\fかえばえ\f[1]nonsense", a=True,
                      h=[Hist(name="hist-1",stat=2,unap=True, dt=db.DEFAULT),
                         Hist(name="hist-2",stat=2,unap=False,dt=db.DEFAULT)])
        e = edentr (e1, h=Hist(name="hist-test"))
        submit_ (e, disp='a')
        sql = "SELECT id FROM entr WHERE src=99 AND seq=%s"
        f = jdb.entrList (DBcursor, sql, (e1.seq,))
          # We should get only one entry, the newly approved one.
        _.assertEqual (1, len(f), "Expected 1 entry, got: %s" % f)
        f = f[0]
          # We expect three items in the new entry hist list.
        _.assertEqual (3, len(f._hist))
          # It should have the names we provided above.
        _.assertEqual ("hist-1",    f._hist[0].name)
        _.assertEqual ("hist-2",    f._hist[1].name)
        _.assertEqual ("hist-test", f._hist[2].name)
          # When 'e1' was added to the database, jdb.addentr() set the last
          # hist item's .eid value but didn't touch its first.  When 'e' was
          # submmitted, it received 'e1' hists and added a new one; the new
          # one's .eid value was set by jdb.addentr().  When checking hist[1]'s
          # eid value, compare to our local 'e1' since 'e1' was deleted from
          # the database when 'e' was approved.
        _.assertEqual (None,    f._hist[0].eid)
        _.assertEqual (e1.id,   f._hist[1].eid)
        _.assertEqual (e.id,    f._hist[2].eid)
        _.assertEqual (f.id,    e.id)

    def test4000040(_):  # Unappr entry w/hists, multiple edits -> rej entry
        e1 = addentr ("\fかえばえ\f[1]nonsense", a=False,
                      h=[Hist(name="hist-1",stat=2,unap=True,dt=db.DEFAULT)])
        e2 = addedit (e1, h=Hist(name="hist-2",stat=2,unap=True,dt=db.DEFAULT))
        e3 = addedit (e2, h=Hist(name="hist-3",stat=2,unap=True,dt=db.DEFAULT))
        e = edentr (e3, h=Hist(name="hist-test"))
        submit_ (e, disp='r')
        sql = "SELECT id FROM entr WHERE src=99 AND seq=%s"
          # Retrieve 'e1' and 'e' from the database as 'f[0]' and 'f[1]'.
        f = jdb.entrList (DBcursor, sql, (e1.seq,))
        _.assertEqual (1, len(f), "Expected 1 entry, got: %s" % f)
        f = f[0]
          # We expect three items in the new entry hist list.
        _.assertEqual (4, len(f._hist))
          # It should have the names we provided above.
        _.assertEqual ("hist-1",    f._hist[0].name)
        _.assertEqual ("hist-2",    f._hist[1].name)
        _.assertEqual ("hist-3",    f._hist[2].name)
        _.assertEqual ("hist-test", f._hist[3].name)
        _.assertEqual (e1.id,       f._hist[0].eid)
        _.assertEqual (e2.id,       f._hist[1].eid)
        _.assertEqual (e3.id,       f._hist[2].eid)
        _.assertEqual (e.id,        f._hist[3].eid)
        _.assertEqual (f.id,        e.id)


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
    def setUp(_):  # In case a test fail left an open aborted transaction.
        DBcursor.connection.rollback()

    def test0001(_):
          # Create a single, simple xref.
        e0 = mkentr ('犬\fいぬ\f[1]dog [see=猫]', c=99)
        id,seq,src = submit_ (e0, disp='')
        e1 = jdb.entrList (DBcursor, None, [id])[0]
        expect = [Xref (id,1,1,3,_.t1.id,1,None,1,None,False,False)]
        _.assertEqual (expect, e1._sens[0]._xref)
        _.assertEqual ([],     e1._sens[0]._xrslv)

    def test0002(_):
          # Xref to kanji and sense #1.
        e0 = mkentr ('犬\fいぬ\f[1]dog [see=馬[2]]', c=99)
        id,seq,src = submit_ (e0, disp='')
        e1 = jdb.entrList (DBcursor, None, [id])[0]
        expect = [Xref (id,1,1,3,_.t2.id,2,None,1,None,False,False)]
        _.assertEqual (expect, e1._sens[0]._xref)
        _.assertEqual ([],     e1._sens[0]._xrslv)

    def test0003(_):
          # Xref to reading and sense #1.
        e0 = mkentr ('子犬\fこいぬ\f[1]puppy [see=うま[2]]', c=99)
        id,seq,src = submit_ (e0, disp='')
        e1 = jdb.entrList (DBcursor, None, [id])[0]
        expect = [Xref (id,1,1,3,_.t2.id,2,1,None,None,False,False)]
        _.assertEqual (expect, e1._sens[0]._xref)
        _.assertEqual ([],     e1._sens[0]._xrslv)


class Xrslvs (unittest.TestCase):  # Named with plural form because "Xrslv"
    def test0001(_):               #  conflicts objects.Xrslv.
          # An xref to a non-existant target will generate an Xrslv object.
        e0 = mkentr ('犬\fいぬ\f[1]dog[see=猫猫]', c=99)
        errs = []
        id,seq,src = submit_ (e0, disp='')
        e1 = jdb.entrList (DBcursor, None, [id])[0]
        expect = [Xrslv (id,1,1,3,None,'猫猫',None,None,None,None,None)]
        _.assertEqual (expect, e1._sens[0]._xrslv)
        _.assertEqual ([],     e1._sens[0]._xref)

#=============================================================================
# Support functions.

# Please note that the functions below that add entries to the database
# (addentr(), addedit()) do so using the low level jdb.addentr() function
# and will attempt to write whatever they are given.  They do not perform
# any of the validity checking or application-level rule enforcement done
# by submit.submission() such as deleting ancestor entries when an approved
# entry is written.

  # Create an Entr object from JEL and optionally add to the database.
def mkentr (jel, q=None, c=99, s=2, a=False, d=None, h=[], dbw=False):
          # We need to pass srcid, stat, unap to .parse because they
          # are used when resolving any xrefs.
        e = JELparser.parse (jel, src=c, stat=s, unap=not a, dfrm=d)
        e.seq, e.src, e.stat, e.unap, e.dfrm = q, c, s, not a, d
        if h: e._hist.extend (h)
        if dbw: _dbwrite (e, c, q)
        return e
  # Same as mkentr() but default database write is True.
def addentr (*args, **kwargs): return mkentr (*args, dbw=True, **kwargs)

  # "Edit" a copy of an existing entry, 'entr' and optionally add to the
  # database.  Unless overridden by parameter 'd', the new entry's 'dfrm'
  # value is set to 'entr.id' and its 'id set to None.  Other parameters,
  # if given, will set the corresponding attributes.  The new entry object
  # is returned and, if succesfully written to the database, will have
  # its .id and .seq attributes set to the values assigned in the database.
NoChange = object()
def edentr (entr, q=NoChange, c=NoChange, s=NoChange, a=False,
                  d=NoChange, h=None, dbw=False):
        e = copy.deepcopy (entr)
        if d is NoChange: e.dfrm, e.id = e.id, None
        else: e.dfrm = d
        e.unap = not a
        if q is not NoChange: e.seq = q
        if c is not NoChange: e.src = c
        if s is not NoChange: e.stat = s
        if h: e._hist.append (h)
        if dbw: _dbwrite (e, c, q)
        return e
  # Same as edentr() but default database write is True.
def addedit (*args, **kwargs): return edentr (*args, dbw=True, **kwargs)

  # Internal  helper function for mkentr() and edentr().
def _dbwrite (e, c, q):
        if q is NoChange: q = e.seq
        if c is NoChange: c = e.src
        id,seq,src = jdb.addentr (DBcursor, e)
        if not id: raise RuntimeError ("entry not added to database")
        if q is not None and seq!=q:
            raise RuntimeError ("entry has wrong seq# (got %s)"%e.seq)
        if c is not None and src!=c:
            raise RuntimeError ("entry has wrong src# (got %s)"%e.src)
        DBcursor.connection.commit()

def _dbread (e=None, q=None, c=99):
        if e and q: raise ValueError("call with 'e' or 'q', not both")
        if not e and not q: raise ValueError("'e' or 'q' required")
        if e: whr, args = "id=%s", (e,)
        else: whr, args = "seq=%s AND src=%s", (q, c)
        sql = "SELECT id,src,stat,seq,dfrm,unap"\
              " FROM entr WHERE %s ORDER BY id" % whr
        rs = db.query (DBcursor.connection, sql, args)
        return rs

def delentr (id):
        DBcursor.execute ("DELETE FROM entr WHERE id=%s", (id,))
        DBcursor.connection.commit()

  # Submit an Entr via submit.submission().  Call this when no errors are
  # expected.  If any occur, a Runtime Exception is raised so they will
  # be noticed without need for caller to explicitly pass and check 'errs'.
def submit_ (entr, **kwds):   # Trailing "_" in function name to avoid
        errs = []             #  conflict with submit module.
        kwds['errs'] = errs
        id,seq,src = submit.submission (DBcursor, entr, **kwds)
        if errs or id is None: raise RuntimeError (errs)
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
