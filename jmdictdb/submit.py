#!/usr/bin/env python3
# Copyright (c) 2019 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# In the database entr table rows have three attributes that
# support entry editing:
#   dfrm -- Contains the entr.id number of the entry that the
#       current entry was derived from.
#   unap -- Indicates the current entry is not "approved"
#   stat -- Has value corresponding to one of the kwstat kw's:
#       A -- Active entry
#       D -- Deleted entry
#       R -- Rejected entry
#
# Basics:
# 1. When an entry is edited and submited a new entry object is
#    added to the database that represents the object as edited,
#    but leaves the original entry object in the database as well.
# 2. The edited entry contains the id number of the entry it was
#    derived from in atttribute "dfrm".
# 3. Any entry can be edited and submitted including previously
#    edited entries.
# The result is that there can exist in the database a "tree" of
# edited entries, linked by "dfrm" values, with the original entry
# at its root.
# We define a 'chain" to be a subtree in which no branches exist,
# that is, each parent entry has only one child.  The "chain head"
# is the entry on the chain that is nearest to the root.
#
# Parameters:
# There are two URL parameters processed by this script that
# describe the action to be taken:
#    serialized:
#       A serialized representation of the edited object
#        that was given in the edit form.
#    disp:
#       "" (or no disp param) -- Submit
#       "a" -- Approve
#       "r" -- Reject
# A submission made by this cgi script always creates a new entry
# object in the database. ("object" means an entr table row, and
# related rows in the other tables).
#
# A "submit" submission:
# ---------------------
# In the case of a "submit" entry (this is the only kind of
# submission permitted by non-editors), the serialized entry
# parameter is desserialized to a python entry object and is
# used to create a new database object.  If the user submits
# a new entry:
#       stat=N, dfrm=NULL, unap=T
# If it is edited version of an existing entry:
#       stat=A, dfrm=<previous entr.id>, unap=T
# Related rows are created in other table as needed to create a
# database representation of the edited entry.
# This process adds an entry to the database but makes no changes
# to existing entries.
# The history record in the submitter's entry is combined with
# the history records from the parent entry to form a complete
# history for the edited entry.
#
# An "approve" submission:
# -----------------------
# The root entry is found by following the dfrm links, and then
# all leaf entries are found.  Each of these is an edit that
# hasn't been itself edited.  If there is more that one, we
# refuse to allow the approval of the edit we are processing
# and require the editor to explicitly reject the other edits
# first, to ensure that edits aren't inadvertantly missed.
#
# If there is only one leaf entry, it must be our parent.
# We save it's history and then delete the chain containing
# it, bach to the root entry.
# A new entry is created as for a "submit" entry except unap=F,
# and if stat=N, it is changed to A, and dfrm is set to NULL.
#
# A "reject" submission
# ---------------------
# We make a rejection by creating an entry with stat=R, unap=F,
# and dfrm=NULL.  We delete the chain containing the parent
# entry.   This may not go back to the root entry.
#
# Concurrency:
# ------------
# A long time may pass between when an entry is read for
# editing by edform.py and when it is submitted by edsubmit.py.
# During this time anoher user may submit other edits of the
# same entry, or of one of its parents.
# An editor may approve or reject edits resulting in the
# disappearance of the edited entry's parents.
# This situation is detected in submission() when it tries
# read the parent entry and finds it gone.
# Like other systems that permit concurrent editing (e.g.
# CVS) we create two separate "forks" of an entry two people
# change the same base entry.  Unlike CVS-like systems, we
# don't attempt to automatically merge them together again,
# relying instead on editors to do that manually.
#
# It is also possible that the edit tree could change while
# edsubmit.py is running: between the time it is checked for
# changes but before the edited entry is written or previous
# entries deleted.  This is guarded against by doing the
# checks and updates inside a transaction run with "serializable"
# isolation.  The database state within the transaction is
# garaunteed not to change, and if someone else makes a
# conflicting change outside the transaction, the transaction
# will fail with an error.  (However, this situation in not
# yet handled gracefully in the code -- so the result will
# be an unhandled exception and traceback.)

import sys, pdb
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb
  #FIXME: temporary hack...
from jmdictdb import jmcgi

class BranchesError (ValueError): pass
class NonLeafError (ValueError): pass
class IsApprovedError (ValueError): pass

  #FIXME: Temporary hack...
Svc, Sid = None, None

def submission (dbh, entr, disp, errs, is_editor=False, userid=None):
        # Add a changed entry, 'entr', to the jmdictdb database accessed
        # by the open DBAPI cursor, 'dbh'.
        #
        # dbh -- An open DBAPI cursor
        # entr -- A populated Entr object that defines the entry to
        #   be added.  See below for description of how some of its
        #   attributes affect the submission.
        # disp -- Disposition, one of three string values:
        #   '' -- Submit as normal user.
        #   'a' -- Approve this submission.
        #   'r' -- Reject this submission.
        # errs -- A list to which an error messages will be appended.
        #   Note that if the error message contains html it should be
        #   wrapped in jmcgi.Markup() to prevent it from being escaped
        #   in the template.  Conversely, error messages that contain
        #   text from user input should NOT be so wrapped since they
        #   must be escaped in the template.
        # is_editor -- True is this submission is being performed by
        #   a logged in editor.  Approved or Rejected dispositions will
        #   fail if this is false.  Its value may be conveniently
        #   obtained from jmcgi.is_editor().  False if a normal user.
        # userid -- The userid if submitter is logged in editor or
        #   None if not.
        #
        # Returns:
        # A 3-tuple of (entry-id, sequence-number, src-id) for the
        # added entry (or None,None,None if there was an error in
        # which case error message(s) added to parameter 'errs').
        #
        # Note that we never modify existing database entries other
        # than to sometimes completetly erase them.  Submissions
        # of all three types (submit, approve, reject) *always*
        # result in the creation of a new entry object in the database.
        # The new entry will be created by writing 'entr' to the
        # database.  The following attributes in 'entr' are relevant:
        #
        #   entr.dfrm -- If None, this is a new submission.  Otherwise,
        #       it must be the id number of the entry this submission
        #       is an edit of.
        #   entr.stat -- Must be consistent with changes requested. In
        #       particular, if it is 4 (Delete), changes made in 'entr'
        #       will be ignored, and a copy of the parent entry will be
        #       submitted with stat D.
        #   entr.src -- Required to be set, new entry will copy.
        #       # FIXME: prohibit non-editors from making src
        #       #  different than parent?
        #   entr.seq -- If set, will be copied.  If not set, submission
        #       will get a new seq number but this untested and very
        #       likely to break something.
        #       # FIXME: prohibit non-editors from making seq number
        #       #  different than parent, or non-null if no parent?
        #   entr.hist -- The last hist item on the entry will supply
        #       the comment, email and name fields to newly constructed
        #       comment that will replace it in the database.  The time-
        #       stamp and diff are regenerated and the userid field is
        #       set from our userid parameter.
        #       # FIXME: should pass history record explicity so that
        #       #  we can be sure if the caller is or is not supplying
        #       #  one.  That will make it easier to use this function
        #       #  from other programs.
        # The following entry attributes need not be set:
        #   entr.id -- Ignored (reset to None).
        #   entr.unap -- Ignored (reset based on 'disp').
        # Additionally, if 'is_editor' is false, the rdng._freq and
        # kanj._freq items will be copied from the parent entr rather
        # than using the ones supplied  on 'entr'.  See jdb.copy_freqs()
        # for details about how the copy works when the rdng's or kanj's
        # differ between the parent and 'entr'.

        KW = jdb.KW
          #FIXME: temporary hack...
        global Svc, Sid
        L('submit.submission').info(("disp=%s, is_editor=%s, userid=%s, entry id=%s,\n" + " "*36 + "parent=%s, stat=%s, unap=%s, seq=%s, src=%s")
          % (disp, is_editor, userid, entr.id, entr.dfrm, entr.stat,
             entr.unap, entr.seq, entr.src))
        L('submit.submission').info("entry text: %s %s"
          % ((';'.join (k.txt for k in entr._kanj)),
             (';'.join (r.txt for r in entr._rdng))))
        L('submit.submission').debug("seqset: %s"
          % logseq (dbh, entr.seq, entr.src))
        added = None, None, None
        oldid = entr.id
        entr.id = None          # Submissions, approvals and rejections will
        entr.unap = not disp    #   always produce a new db entry object so
        merge_rev = False       #   nuke any id number.
        if not entr.dfrm:       # This is a submission of a new entry.
            entr.stat = KW.STAT['A'].id
            if not is_editor:
                entr.seq = None # Force addentr() to assign seq number.
            pentr = None        # No parent entr.
            edtree = None
        else:   # Modification of existing entry.
            edroot = get_edroot (dbh, entr.dfrm)
            edtree = get_subtree (dbh, edroot)
              # Get the parent entry and augment the xrefs so when hist diffs
              # are generated, they will show xref details.
            L('submit.submission').debug("reading parent entry %d"
                                               % entr.dfrm)
            pentr, raw = jdb.entrList (dbh, None, [entr.dfrm], ret_tuple=True)
            if len (pentr) != 1:
                L('submit.submission').debug("missing parent %d"
                                                   % entr.dfrm)
                  # The editset may have changed between the time our user
                  # displayed the Confirmation screen and they clicked the
                  # Submit button.  Changes involving unapproved edits result
                  # in the addition of entries and don't alter the preexisting
                  # tree shape.  Approvals of edits, deletes or rejects may
                  # affect our subtree and if so will always manifest themselves
                  # as the disappearance of our parent entry.
                errs.append (
                    "The entry you are editing no loger exists because it "
                    "was approved, deleted or rejected.  "
                    "Please search for entry '%s' seq# %s and reenter your changes "
                    "if they are still applicable." % (KW.SRC[ent.src].kw, entr.seq))
                return
            pentr = pentr[0]
            jdb.augment_xrefs (dbh, raw['xref'])

            if entr.stat == KW.STAT['D'].id:
                  # If this is a deletion, set $merge_rev.  When passed
                  # to function merge_hist() it will tell it to return the
                  # edited entry's parent, rather than the edited entry
                  # itself.  The reason is that if we are doing a delete,
                  # we do not want to make any changes to the entry, even
                  # if the submitter has done so.
                merge_rev = True

          # Merge_hist() will combine the history entry in the submitted
          # entry with the all the previous history records in the
          # parent entry, so the the new entry will have a continuous
          # history.  In the process it checks that the parent entry
          # exists -- it might not if someone else has approved a
          # different edit in the meantime.
          # merge_hist also returns an entry.  If 'merge_rev' is false,
          # the entry returned is 'entr'.  If 'merge_rev' is true,
          # the entry returned is the entr pointed to by 'entr.dfrm'
          # (i.e. the original entry that the submitter edited.)
          # This is done when a delete is requested and we want to
          # ignore any edits the submitter may have made (which 'entr'
          # will contain.)

          # Before calling merge_hist() check for a condition that would
          # cause merge_hist() to fail.
        if entr.stat==KW.STAT['D'].id and not getattr (entr, 'dfrm', None):
            L('submit.submission').debug("delete of new entry error")
            errs.append ("Delete requested but this is a new entry.")

        if disp == 'a' and has_xrslv (entr) and entr.stat==KW.STAT['A'].id:
            L('submit.submission').debug("unresolved xrefs error")
            errs.append ("Can't approve because entry has unresolved xrefs")

        if not errs:
              # If this is a submission by a non-editor, restore the
              # original entry's freq items which non-editors are not
              # allowed to change.
            if not is_editor:
                if pentr:
                    L('submit.submission').debug("copying freqs from parent")
                    jdb.copy_freqs (pentr, entr)
                  # Note that non-editors can provide freq items on new
                  # entries.  We expect an editor to vet this when approving.

              # Entr contains the hist record generate by the edconf.py
              # but it is not trustworthy since it could be modified or
              # created from scratch before we get it.  So we extract
              # the unvalidated info from it (name, email, notes, refs)
              # and recreate it.
            h = entr._hist[-1]
              # When we get here, if merge_rev is true, pentr will also be
              # true.  If we are wrong, add_hist() will throw an exception
              # but will never return a None, so no need to check return val.
            L('submit.submission').debug("adding hist for '%s', merge=%s"
                                               % (h.name, merge_rev))
              # Check that the user-supplied info has no ascii control
              # characters.  If there are, the submission is not done
              # rather than quietly doimng the cleaning ourselves.
              # Justification is that the caller (in the cgi case that
              # would be the edconf.py page) should have already checked
              # and fixed the problem.
            entr = jdb.add_hist (entr, pentr, userid,
                                 clean (h.name, 'submitter name', errs),
                                 clean (h.email, 'submitter emil', errs),
                                 clean (h.notes, 'comments', errs),
                                 clean (h.refs, 'refs', errs),
                                 merge_rev)
        if not errs:
              # Occasionally, often from copy-pasting, a unicode BOM
              # character finds its way into one of an entry's text
              #  strings.  We quietly remove any here.
            n = jdb.bom_fixall (entr)
            if n > 0:
                L('submit.submission').debug("removed %s BOM character(s)" % n)

        if not errs:
            if not disp:
                added = submit (dbh, entr, edtree, errs)
            elif disp == "a":
                added = approve (dbh, entr, edtree, errs)
            elif disp == "r":
                added = reject (dbh, entr, edtree, errs, None)
            else:
                L('submit.submission').debug("bad url parameter (disp=%s)" % disp)
                errs.append ("Bad url parameter (disp=%s)" % disp)
        L('submit.submission').debug("seqset: %s"
                                     % logseq (dbh, entr.seq, entr.src))
        if errs:
            L('submit.submission').debug("Entry not submitted due to errors")
            for e in errs: L('submit.submission').debug('  '+e)

          # Note that changes have not been committed yet, caller is
          # expected to do that.
          # If no errors the return value is a 3-tuple of:
          #   (entry-id, sequence-number, src-id)
          # If there were errors, parameter 'errs' will have the error
          # messages appended and return value will be (None,None,None).
        return added

def submit (dbh, entr, edtree, errs):
        KW = jdb.KW
        L('submit.submit').debug("submitting entry with parent id %s"
                                       % entr.dfrm)
        if not entr.dfrm and entr.stat != KW.STAT['A'].id:
            L('submit.submit').debug("bad url param exit")
            errs.append ("Bad url parameter, no dfrm");  return
        if entr.stat == jdb.KW.STAT['R'].id:
            L('submit.submit').debug("bad stat=R exit")
            errs.append ("Bad url parameter, stat=R");  return
        res = addentr (dbh, entr)
        return res

def approve (dbh, entr, edtree, errs):
        KW = jdb.KW
        L('submit.approve').debug("approving entr id %s" % entr.dfrm)
          # Check stat.  May be A or D, but not R.
        if entr.stat == KW.STAT['R'].id:
            L('submit.approve').debug("stat=R exit")
            errs.append ("Bad url parameter, stat=R"); return

        dfrmid = entr.dfrm
        if dfrmid:
              # Since 'dfrmid' has a value, this is an edit of an
              # existing entry.  Check that there is a single edit
              # chain back to the root entry.
            try: approve_ok (edtree, dfrmid)
            except NonLeafError as e:
                L('submit.approve').debug("NonLeafError")
                errs.append (jmcgi.Markup("Edits have been made to this "\
                    "entry.  You need to reject those edits before you can "\
                    "approve this entry.  The id numbers are: %s"\
                    % ', '.join ("id="+url(x) for x in leafsn([e.args[0]]))))
                return
            except BranchesError as e:
                L('submit.approve').debug("BranchesError")
                errs.append (jmcgi.Markup("There are other edits pending on "\
                    "some of the predecessor entries of this one, and this "\
                    "entry cannot be approved until those are rejected.  "\
                    "The id numbers are: %s"\
                    % ', '.join ("id="+url(x) for x in leafsn(e.args[0]))))
                return
          # Prepare 'entr' to become independent.
        entr.dfrm = None
        entr.unap = False
          # Delete the old root if any.  We need to delete the old active
          # entry before adding the new one, to avoid annoying the database
          # constraint the prohibits two active, approved entries.
          # Because the dfrm foreign key is "on delete cascade", deleting
          # the root entry will also delete all it's children.  edtree[0].id
          # is the id number of the edit root.
        if edtree: delentr (dbh, edtree[0].id)
          # With the old approved entry gone we can write the new one to
          # the database.
        res = addentr (dbh, entr)
        return res

def reject (dbh, entr, edtree, errs, rejcnt=None):
        KW = jdb.KW
        L('submit.reject').debug("rejecting entry id %s, rejcnt=%s"
                                       % (entr.dfrm, rejcnt))
          # rejectable() returns a list entr rows on the path to the edit
          # edit root, starting with the one closest to the root, and ending
          # with our entry's parent, that can be rejected.  If this is a new
          # entry, 'rejs' will be set to [].
        try: rejs = rejectable (edtree, entr.dfrm)
        except NonLeafError as e:
            L('submit.reject').debug("NonLeafError")
            errs.append (jmcgi.Markup("Edits have been made to this entry.  "\
                    "To reject entries, you must reject the version(s) most "
                    "recently edited, which are: %s"\
                    % ', '.join ("id="+url(x) for x in leafsn([e.args[0]]))))
            return
        except IsApprovedError as e:
            L('submit.reject').debug("IsApprovedrror")
            errs.append ("You can only reject unapproved entries.")
            return
        if not rejcnt or rejcnt > len(rejs): rejcnt = len(rejs)
        chhead = (rejs[-rejcnt]).id if rejcnt else None
        L('submit.reject').debug("rejs=%r, rejcnt=%d, chhead=%s"
          % ([x.id for x in rejs], -rejcnt, chhead))
        entr.stat = KW.STAT['R'].id
        entr.dfrm = None
        entr.unap = False
        res = addentr (dbh, entr)
        if chhead: delentr (dbh, chhead)
        return res

def addentr (dbh, entr):
        entr._hist[-1].unap = entr.unap
        entr._hist[-1].stat = entr.stat
        L('submit.addentr').debug("adding entry to database")
        L('submit.addentr').debug("%d hists, last hist is %s [%s] %s"
          % (len(entr._hist), entr._hist[-1].dt, entr._hist[-1].userid,
             entr._hist[-1].name))
        res = jdb.addentr (dbh, entr)
        L('submit.addentr').info("entry id=%s, seq=%s, src=%s added to database" % res)
        return res

def delentr (dbh, id):
        # Delete entry 'id' (and by cascade, any edited entries
        # based on this one).  This function deletes the entire
        # entry, including history.  To delete the entry contents
        # but leaving the entr and hist records, use database
        # function delentr.  'dbh' is an open dbapi cursor object.

        L('submit.delentr').debug("deleting entry id %s from database"
                                        % id)
        sql = "DELETE FROM entr WHERE id=%s";
        dbh.execute (sql, (id,))

def has_xrslv (entr):
        for s in entr._sens:
            if getattr (s, '_xrslv', None): return True
        return False

def approve_ok (edtree, id):
        # edtree -- A (root,dict) 2-tuple as returned by get_subtree().
        # id -- (int) An id number of an entr row in 'edtree'.
        # Returns: None
        #
        # An entry is approvable if:
        # 1. It is a leaf in the edit tree.
        #    We can't approve a non-leaf node because that would
        #    require changing the dfrm links of following nodes
        #    (rule is that we only add or erase entries; we don't
        #    change existing ones) and even if we did that, the
        #    history records of the following nodes would no
        #    longer be correct.
        # 2. There are no edit branches on the path back to the
        #    root node, i.e. we have a single linear string of
        #    edits.  All other edits in the tree are erased when
        #    we approve this one.  The approved entry carries
        #    the history of all earlier entries on its path, but
        #    not any history from other branches.  We require
        #    those branches be explicitly rejected (removing
        #    them from our tree) first so that history is not
        #    unknowingly discarded and to be sure approver is
        #    aware of them.
        #
        #    If the given entry is not approvable, an error is raised.

        if not edtree:
            L('submit.approve_ok').debug("edtree is none, returning")
            return
        root, d = edtree;  erow = d[id];  branches = []
        if erow._dfrm: raise NonLeafError (erow)
        while erow != root:
            last = erow
            erow = d[erow.dfrm]
            if len(erow._dfrm) > 1:
                branches.extend ([x for x in erow._dfrm if x!=last])
        if branches: raise BranchesError (branches)
        return

def rejectable (edtree, id):
        # edtree -- A (root,dict) 2-tuple as returned by get_subtree().
        # id -- (int) An id number of an entr row in 'edtree'.
        #
        # Returns: A list of rows in 'edtree' starting at row 'id'
        # and moving back towards the root via the 'dfrm' references
        # until one of the following conditions obtain:
        # * An entry is reached that is referenced by more than one
        #   other entry.  (This is an entry that has two or more
        #   direct edits.)
        # * An entry that is not "unapproved".
        # The entry that terminated the search is not included
        # in the list.
        # If the entry row designated by 'id' is not a leaf node,
        # or is approved, an error is raised.

        if not edtree:
            L('submit.rejectable').debug("edtree is none, returning")
            return []
        root, d = edtree;  erow = d[id]
        if erow._dfrm: raise NonLeafError (erow)
        if not erow.unap: raise IsApprovedError (erow)
        erows = []
        while 1:
            erows.append (erow)
            if not erow.dfrm: break
            erow = d[erow.dfrm]
            if not erow.unap or len(erow._dfrm)>1: break
        erows.reverse()
        return erows

def get_edroot (dbh, id):
        # Given the id number of an 'entr' row, return the id
        # of the root of the edit tree it is part of.  The
        # edit tree on an entry is that set of entries from
        # which the first entry can be reached by following
        # 'dfrm' links.

        if id is None: raise ValueError (id)
        sql = "SELECT * FROM get_edroot(%s)"
        rs = jdb.dbread (dbh, sql, [id])
        if not rs: return None
        return rs[0][0]

def get_subtree (dbh, id):
        # Read the "entr" table row for entry with id 'id'
        # and all the rows with a 'dfrm' attribute that points
        # to that row, and all the rows with 'dfrm' attributes
        # that point to any of thoses rows, and so on recursively.
        # That is, we read all the rows in the edit sub-tree
        # below (leaf-ward) and including row 'id'.  If 'id'
        # denotes an edit root row, then we will read the
        # entire edit tree.
        #
        # After reading the rows, they are linked together in a
        # tree structure that mirrors that in the database by
        # adding an attribute, '._dfrm' tO each row which is set
        # to a list of rows that have 'dfrm' values equal to the
        # id number of the ._dfrm row.
        #
        # Return a 2-tuple of:
        # 1. The entr row with id 'id' (which is the root of
        #    the subtree.
        # 2. A dict of (id, entr row) key value pairs allows
        #    quick lookup of a row by 'id'..

        if id is None: raise ValueError (id)
        root = None
        sql = "SELECT * FROM get_subtree(%s)"
        rs = jdb.dbread (dbh, sql, [id])
        d = dict ((r.id,r) for r in rs)
        for r in rs: r._dfrm = []
        for r in rs:
            if r.dfrm:
                d[r.dfrm]._dfrm.append (r)
            else:
                if root: raise ValueError ("get_subtree: Multiple roots returned by get_subtree")
                root = r
        return root, d

def leafs (erow):
        # erow -- An entry row with a '_dfrm' attribute such
        #        produced by get_subtree().
        # Returns: A list of entry nodes that are leaf entries
        #        for the subtree rooted at 'erow'.
        v = []
        if not erow._dfrm: return [erow]
        for x in erow._dfrm: v.extend (leafs (x))
        return v

def leafsn (erows):
        # Given a list of entr rows, 'erows', find the
        # leaf entries of all of them and return a sorted
        # list of their id numbers (without duplicates).
        lst = set()
        for e in erows:
            lst.update (x.id for x in leafs (e))
        return sorted (list (lst))

def logseq (cur, seq, src):
        # Return a list of the id,dfrm pairs (plus stat and unap) for
        # all entries in a src/seq set.  We format the list into a text
        # string for the caller to print.  By looking at this someome
        # can figure out the shape of the edit tree (assuming that it
        # is entirely in the src/seq set).
        sql = "SELECT id,dfrm,stat,unap FROM entr WHERE seq=%s AND src=%s ORDER by id"
        cur.execute (sql, (seq,src))
        rs = cur.fetchall()
        return ','.join ([str(r) for r in rs])

def url (entrid):
        return '<a href="entr.py?svc=%s&sid=%s&e=%s">%s</a>' \
                 % (Svc, Sid, entrid, entrid)

def clean (s, source=None, errs=None):
        '''-------------------------------------------------------------------
        Remove all ascii control characters except '\n's from str 's'.
        If 'source' is not None it indicates an error message will
        be appended to list 'errs' (which should also be supplied)
        if any characters are removed and is a str giving the source
        of 's' for use in the error message (eg. "history comments",
        "gloss", etc.)
        -------------------------------------------------------------------'''
        if not s: return s
        N = None
          # Delete all ascii control characters in 's' except for
          # '\n' ('\x0a') and tabs ('\x09') which are expanded.
          #FIXME: what about unicode bogons?
        cleaned = s.translate ([
          #  00 01 02 03 04 05 06 07 08  09    0a     0b 0c 0d 0e 0f
             N, N, N, N, N, N, N, N, N, '\x09','\x0a',N, N, N, N, N,
          #  10 11 12 13 14 15 16 17 18  19    1a     1b 1c 1d 1e 1f
             N, N, N, N, N, N, N, N, N,  N,    N,     N, N, N, N, N ])
          # Expand any tabs to spaces.
        cleaned = cleaned.expandtabs()
        if source and cleaned != s:
            errs.append ("Illegal characters in '%s'" % source)
        return cleaned
