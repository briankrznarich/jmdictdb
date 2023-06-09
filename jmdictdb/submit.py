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
#
#FIXME: several error messages say, "Bad URL parameter..." but
# these functions may not always be called via a web page.  Should
# use more neutral wording and let caller change it if need be.

import sys, pdb
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb
  #FIXME: temporary hack...
from jmdictdb import jmcgi
from jmdictdb import db     # To get psycopg2 exceptions.

class BranchesError (ValueError): pass
class NonLeafError (ValueError): pass
class IsApprovedError (ValueError): pass

  #FIXME: Temporary hack...
Svc, Sid = None, None

  # submission() and several sub-functions it calls normally return a
  # 3-tuple of (entry-id, sequence-number, src-id).  However if an error
  # condition is encountered, they will typically add an error message
  # to paramter 'errs[]' and return early.  In such case a 3-tuple also
  # needs to be returned since that is inevitably what the caller expects.
None3 = None, None, None

def submission (dbh, entr, disp, allowforks, errs, is_editor=False, userid=None):
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
        # allowforks -- bool. If False, a submission that would create
        #   a new fork will return an error instead.
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
        L('submit.submission').info(("disp=%r, is_editor=%r, userid=%r, entry id=%r,\n" + " "*24 + "parent=%r, stat=%r, unap=%r, seq=%r, src=%r")
          % (disp, is_editor, userid, entr.id, entr.dfrm, entr.stat,
             entr.unap, entr.seq, entr.src))
        L('submit.submission').info("entry text: %s %s"
          % ((';'.join (k.txt for k in entr._kanj)),
             (';'.join (r.txt for r in entr._rdng))))
        L('submit.submission').debug("seqset: %s"
          % logseq (dbh, entr.seq, entr.src))
        added = None3
        oldid = entr.id
        entr.id = None          # Submissions, approvals and rejections will
        entr.unap = not disp    #   always produce a new db entry object so
        merge_rev = False       #   nuke any id number.
          # Prepare an error message here since there are several places
          # we might use it.
        noentr_msg = "The entry you are editing no longer exists, "\
              "likely because it was approved, deleted or rejected "\
              "before your changes were submitted.  "\
              "Please search for the current version of the entry and "\
              "reenter your changes if they are still applicable."
        if not entr.dfrm:       # This is a submission of a new entry.
            entr.stat = KW.STAT['A'].id
            if not is_editor:
                entr.seq = None # Force addentr() to assign seq number.
            pentr = None        # No parent entr.
            edpaths, root_unap = [], None
        else:   # Modification of existing entry.
            edpaths, root_unap = get_edpaths (dbh, entr.dfrm)
            L('submit.submission').debug("get_edpaths returned %r"
                                         % ((edpaths,root_unap),))
            if edpaths is None:
                errs.append ("[noroot] "+noentr_msg);  return None3

              # Get the parent entry and augment the xrefs so when hist diffs
              # are generated, they will show xref details.
            L('submit.submission').debug("reading parent entry %d"
                                               % entr.dfrm)

            leafs = get_leafs (edpaths, entr.dfrm)
            if leafs and not allowforks and entr.dfrm not in leafs:
                # Note: there is now fully-duplicated error checking at the
                # initial form submission ([Next]) to make sure that Approvals
                # and Rejections only occur when the entry has a valid fork
                # history. We should only hit this error if something changed
                # between [Next] and [Submit]. This new check does make some
                # error checking farther down in this function unreachable.
                L('submit.submission').debug("dfrm %d is not a leaf" % entr.dfrm)
                errs.append ("Edits have been made to this entry between "\
                             "[Next] and [Submit]. Please user your browser's "\
                             "back button to return to the 'Edit Entry' "\
                             "form, then resubmit to see the latest changes.")
                return None3
            pentr, raw = jdb.entrList (dbh, None, [entr.dfrm], ret_tuple=True)
            if len (pentr) != 1:
                  #FIXME: this should be treated as an assertion error:
                  # it can't normally fail since we should be inside a
                  # transaction and looking at a consistent database
                  # snapshot; if the parent entry is gone now it was
                  # gone when get_edroot() was called above and would
                  # have produced a "noroot" error then.
                L('submit.submission').debug("missing parent %d"
                                                   % entr.dfrm)
                  # The editset may have changed between the time our user
                  # displayed the Confirmation screen and they clicked the
                  # Submit button.  Changes involving unapproved edits result
                  # in the addition of entries and don't alter the preexisting
                  # tree shape.  Approvals of edits, deletes or rejects may
                  # affect our subtree and if so will always manifest themselves
                  # as the disappearance of our parent entry.
                errs.append ("[noparent] "+noentr_msg)
                return None3
            pentr = pentr[0]
            if pentr.stat == KW.STAT['R'].id:
                  # Disallow editing rejected entries since there is seldom
                  # a need to and when previously allowed it led to abuse.
                  # The web interface does not provide an Edit button for
                  # rejected entries but a submission could be constructed
                  # to do so.
                  #FIXME? allow editors to edit?
                errs.append ("Rejected entries can not be edited.")
                return None3
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
            errs.append ("Can't approve because entry has unresolved xrefs.")

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
              # and recreate it.  Provide an empty record if one not
              # supplied (common with test submissions, etc.)
            h = entr._hist[-1] if entr._hist else jdb.Hist()
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
            try:
                  #FIXME? functions called below can raise a psycopg2
                  # TransactionRollbackError if there is a serialization
                  # error resulting from a concurrent update.  We currently
                  # trap it and report it as an error but it could be retried
                  # and would likely succeed.  Other exceptions
                  # (IntegrityError, etc) are hard errors, no point retrying.
                if not disp:
                    added = submit (dbh, entr, errs)
                elif disp == "a":
                    added = approve (dbh, entr, edpaths, errs)
                elif disp == "r":
                    added = reject (dbh, entr, edpaths, root_unap, errs)
                else:
                    L('submit.submission').debug("bad url parameter (disp=%s)"
                                                 % disp)
                    errs.append ("Bad url parameter (disp=%s)" % disp)
            except db.IntegrityError as e:
                c = None
                if 'entr_src_seq_idx' in str(e): c = 'seq'
                elif 'entr_dfrm_fkey' in str(e): c = 'dfrm'
                else: raise
                L('submit.submission').debug("constraint violation: %s" % c)
                errs.append ("["+c+"_vio] "+noentr_msg)
                dbh.connection.rollback()
        L('submit.submission').debug("seqset: %s"
                                     % logseq (dbh, entr.seq, entr.src))
        if errs:
            L('submit.submission').debug("Entry not submitted due to errors:")
            for e in errs: L('submit.submission').debug('  '+e)

          # Note that changes have not been committed yet, caller is
          # expected to do that.
          # If no errors the return value is a 3-tuple of:
          #   (entry-id, sequence-number, src-id)
          # If there were errors, parameter 'errs' will have the error
          # messages appended and return value will be (None,None,None).
        return added

def submit (dbh, entr, errs):
        """===================================================================
        Submit an unapproved entry.
        Write entry object 'entr' to the database as an active
        (entr.stat=2), unapproved (entr.unap=True) entry.  'entr' must
        have a .dfrm attribute value with the id number of the entry in
        the database that it is an edit of.

        Parameters:
          dbh -- An open cursor to a JMdictDB database.
          entr -- The entry object that will be written to the database
            as the approved entry.
          edpaths -- The full set of paths (as returned by get_edpaths()
            for the edit tree of which entr.dfrm is a leaf entry.
          errs -- a list to which any errors encountered will be appended.

        Returns:
          If successful: A 3-tuple of the new entry's id number, sequence
            number, and corpus (aka"src") number.
          If error: A 3-tuple: (None,None,None) and relevant error
            message(s) will be appended to list 'errs'.
        ===================================================================="""
        KW = jdb.KW
        L('submit.submit').debug("submitting entry with parent id %s"
                                       % entr.dfrm)
        if not entr.dfrm and entr.stat != KW.STAT['A'].id:
            L('submit.submit').debug("bad url param exit")
            errs.append ("Bad url parameter, no dfrm");  return None3
        if entr.stat == jdb.KW.STAT['R'].id:
            L('submit.submit').debug("bad stat=R exit")
            errs.append ("Bad url parameter, stat=R");  return None3
        res = addentr (dbh, entr)
        return res

def approve (dbh, entr, edpaths, errs):
        """===================================================================
        Approve an entry
        Write entry object 'entr' to the database as an active
        (entr.stat=2), approved (entr.unap=False) entry.  'entr' must be
        a leaf entry in the edit tree given by 'edpaths'.  The edit tree
        must have no branches ('edpaths' must be a list containing exactly
        one list of the edit chain leading to 'entr').  When 'entr' is
        written to the database, all the entries in 'edpaths' will be
        deleted.

        Parameters:
          dbh -- An open cursor to a JMdictDB database.
          entr -- The entry object that will be written to the database
            as the approved entry.
          edpaths -- The full set of paths (as returned by get_edpaths()
            for the edit tree of which entr.dfrm is a leaf entry.
          errs -- a list to which any errors encountered will be appended.

        Returns:
          If successful: A 3-tuple of the new entry's id number, sequence
            number, and corpus (aka"src") number.
          If error: A 3-tuple: (None,None,None) and relevant error
            message(s) will be appended to list 'errs'.
        ==================================================================="""
        KW = jdb.KW
        L('submit.approve').debug("approving entr id %s" % entr.dfrm)
          # Check stat.  May be A or D, but not R.
        if entr.stat == KW.STAT['R'].id:
            L('submit.approve').debug("stat=R exit")
            errs.append ("Bad url parameter, stat=R"); return None3

        dfrmid = entr.dfrm
        if dfrmid:
              # Since 'dfrmid' has a value, this is an edit of an
              # existing entry.  Check that there is a single edit
              # chain back to the root entry.
            try: approve_ok (edpaths, dfrmid)
            except NonLeafError as e:
                L('submit.approve').debug("NonLeafError")
                leafs = get_leafs (edpaths, e.args[0])
                errs.append (jmcgi.Markup("Edits have been made to this "\
                    "entry.  You need to reject those edits before you can "\
                    "approve this entry.  The id numbers are: %s"\
                    % ', '.join ("id="+url(x) for x in leafs)))
                return None3
            except BranchesError as e:
                L('submit.approve').debug("BranchesError")
                leafs = e.args[0]
                errs.append (jmcgi.Markup("There are other edits pending on "\
                    "some of the predecessor entries of this one, and this "\
                    "entry cannot be approved until those are rejected.  "\
                    "The id numbers are: %s"\
                    % ', '.join ("id="+url(x) for x in leafs)))
                return None3
          # Prepare 'entr' to become independent.
        entr.dfrm = None
        entr.unap = False
          # Delete the old root if any.  We need to delete the old active
          # entry before adding the new one, to avoid annoying the database
          # constraint the prohibits two active, approved entries.
          # Because the dfrm foreign key is "on delete cascade", deleting
          # the root entry will also delete all it's children. edpaths[0][0]
          # is the id number of the edit root.
        if edpaths: delentr (dbh, abs(edpaths[0][0]))
          # With the old approved entry gone we can write the new one to
          # the database.
        res = addentr (dbh, entr)
        return res

def reject (dbh, entr, edpaths, root_unap, errs):
        """===================================================================
        Reject an entry (and the unapproved edit leading to it.)
        A chain of edits is sequence of entries linked by their .dfrm
        fields.  No entry in the chain may be referenced by more than one
        other entry.  This function will delete all the entries on the
        chain (except possibly the first if it is the entr tree's root
        entry and an approved entry) from the database and add a new
        approved entry to the database using 'entr' which will have
        stat='R'.

        Parameters:
          dbh -- An open cursor to a JMdictDB database.
          entr -- The entry object that will be written to the database
            as the R (rejected) entry.
          edpaths -- The full set of paths (as returned by get_edpaths()
            for the edit tree of which entr.dfrm is a leaf entry.
          root_unap -- (bool) true if the root entry of the edit tree is
            an unapproved entry; false if it is an approved entry.
          errs -- a list to which any errors encountered will be appended.

        Returns:
          If successful: A 3-tuple of the new entry's id number, sequence
            number, and corpus (aka"src") number.
          If error: A 3-tuple: (None,None,None) and relevant error
            message(s) will be appended to list 'errs'.

        ==================================================================="""
        KW = jdb.KW
        L('submit.reject').debug("rejecting entry id %s" % (entr.dfrm))
          # get_segment() returns a list of entr ids from a leaf entry
          # back torwards the root up to but not including the first
          # entry that is in another path.  IOW, it is a sequence of
          # edits where each entry has only one "child" entry.  When
          # we reject a branch of edits we only reject back to the first
          # entry with multiple "child" edits and the list returned
          # by get_segment() provides those entries (sans a slight
          # adjustment described below.)
        rejs = get_segment (edpaths, entr.dfrm)
        L('submit.reject').debug("reject path 'rejs': %s" % rejs)
        if rejs is None:    # None signals 'entr.dfrm' was not a leaf entry.
                            # IOW, entr.dfrm itself has edits made to it.
            L('submit.reject').debug("NonLeafError")
            leafs = get_leafs (edpaths, entr.dfrm)
            errs.append (jmcgi.Markup("Edits have been made to this entry.  "\
                    "To reject entries, you must reject the version(s) most "
                    "recently edited, which are: %s"\
                    % ', '.join ("id="+url(x) for x in leafs)))
            return None3
        if len (rejs)==1 and rejs[0]==edpaths[0][0] and not root_unap:
              # If this is an edit of the root entry and the root entry
              # is approved, then fail.
              #FIXME? why shouldn't an approved entry be rejected?
            L('submit.reject').debug("IsApprovedrror")
            errs.append ("You can only reject unapproved entries.")
            return None3
          # If this segment goes back to and includes the root entry,
          # and the root entry is approved, remove the root entry.
          # IOW, we want to reject all the unapproved entries on the
          # path but not the approved root entry.
        if rejs and rejs[0]==edpaths[0][0] and not root_unap:
            L('submit.reject').debug("removing root entry from 'rejs'")
            rejs.pop(0)
          # If after all that we have nothing left to reject, then
          # something went wrong.
        assert rejs, "programming error"

          # Prepare the "reject" entry then add to the database.
        entr.stat, entr.unap, entr.dfrm = KW.STAT['R'].id, False, None
        L('submit.reject').debug("adding rejected entry")
        eid, seq, src = addentr (dbh, entr)
        L('submit.reject').debug("added 'R' entry: %s", ((eid,seq,src),))
          # 'rejs' is the path segment leading to the leaf entry that
          # was rejected.  When we delete the first entry in it, all the
          # following ones will also be deleted due to the CASCADE qualifier
          # on the entr.dfrm column in the database.
        L('submit.reject').debug("deleting db entries: %s" % rejs)
        if rejs: delentr (dbh, rejs[0])
        return eid, seq, src

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

def approve_ok (edpaths, eid):
        # edpaths -- A (root,dict) 2-tuple as returned by get_subtree().
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

        leafs = [b[-1] for b in edpaths]
        if eid not in leafs: raise NonLeafError (eid)
        leafs.remove (eid)
        if len (leafs) > 0: raise BranchesError (leafs)
        return

def get_edpaths (dbh, eid):
        """===================================================================
        # Versions of entries are linked together in a tree of edits via
        # each entry's .dfrm field, which references the parent entr from
        # which the referencing entry was derived.
        # This function returns a list of edit paths for the edit tree in
        # which the entry 'eid' appears somewhere.  Each item (path) is a
        # list of entry id's from the root entry of tree (common to every
        # path) to a leaf entry in the tree.   Example (using letters to
        # represent entry id numbers and A<--B represents B.dfrm=A):
        #   A<--B<-.---C
        #           `--D<--E
        # This function when called with D (or A, B, C or E) would return:
        #   [[A, B, C], [A, B, D, E]]
        # If an entry has no edits (no other entries exist with .dfrm=D)
        # or doesn't exist (no entry D in the database), a single item
        # list is returned: [[D]].  If the entry 'eid' doesn't exist, a
        # 2-tuple of (None,None) is returned.
        ===================================================================="""
        if eid is None: raise ValueError (eid)
        sql = "SELECT DISTINCT path FROM edpaths WHERE id=%s"
        rs = db.query (dbh.connection, sql, (eid,))
        edpaths = [r[0] for r in rs]
        rootid = edpaths[0][0] if edpaths else eid
          # Get the full entr record for the root entry.
        sql = "SELECT * FROM entr WHERE id=%s"
        entr = db.query1 (dbh.connection, sql, (rootid,))
          # It not uncommon for the target entry to disappear between the
          # time this function was called and we get here -- an edited entry
          # could have been approved by someone else for example.
        if not entr: return None, None
          # The edpaths data just retrieved will be empty if 'eid' is a
          # lone entry with no other entries referencing it via their
          # .dfrm fields.  If that's the case, put the 'eid' entry in it.
        if not edpaths: edpaths = [[rootid]]
        check_edpaths (edpaths)
          # The reject() function needs to know if the root entry is
          # approved or not.
        root_unap = entr[5]
        return edpaths, root_unap

def check_edpaths (edpaths, eid=None):
          # Some basic sanity checks:
          # 1. Every branch is expected to have the same root entry.
        for p in edpaths:
            assert p[0]==edpaths[0][0], "root conflict in edpaths"
          # 2. Our entry id should occur in at least one branch.
        if eid:
            assert any([(eid in p) for p in edpaths]),"'eid' not in any path"

def get_segment (edpaths, eid):
        """===================================================================
        #  Given a list of edit paths such as returned by get_edpaths(),
        #  and the entry id number 'eid' of a leaf entry 'edpaths', return
        #  list of entry id numbers from leaf 'eid' back towards the root
        #  until, and not including, an entry id that also exists on another
        #  path (but in reverse order, so the leaf entry is the right-most,
        #  i.e., index [-1], item.)  If 'eid' is not a leaf item on any path
        #  None is returned.
        #  Example: given a "dfrm" tree in the database like:
        #      A<-.--B<-.---C<---D
        #          `.    `--E
        #            `---F<---G<---H
        #  get_edpaths() would return a path list like:
        #     [[A, B, C, D],
        #      [A, B, E],
        #      [A, F, G, H]]
        #  get_segment(D) => [C, D]
        #  get_segment(E) => [E]
        #  get_segment(H) => [F, G, H]
        #  get_segment(C) => None
        ===================================================================="""
          # Find the path (aka branch) in 'edpaths' that has 'eid' as a
          # leaf entry.  While doing that, build a set of the id numbers
          # in all the other paths.
        our_path, others = None, set()
        for p in edpaths:
            if p[-1] == eid: our_path = p
            else: others |= set (p)
          # If 'eid' is not a leaf entry of any of any path, return None.
        if not our_path: return None
        segment = []
          # Starting from the leaf end of the path with 'eid' as its leaf,
          # accumulate entry id until we encounter one in another branch.
        for e in reversed (our_path):
            if e in others: break
            segment.append (e)
        return list (reversed (segment))

def get_leafs (edpaths, eid):
        # Return the leaf entry ids for all paths in which 'eid' occurs.
        leafs = []
        for p in edpaths:
            if eid in p: leafs.append(p[-1])
        return leafs

def get_tail_and_leafs (dbh, eid):
        # Return:
        #     1. List of entries between eid and the latest edit, if there is
        #        a single, unique path. (no forks past eid)
        #     2. List of all leafs for paths which contain eid
        #     3. List of all leafs for all entries associated with this sequence
        # This function exists to edit a submission on-the-fly, and append
        # a submission to the end of an edit list instead of creating a fork.
        edpaths, root_unap = get_edpaths (dbh, eid)
        if not edpaths:
            return None3
        tail = None
        for p in edpaths:
            try:
                idx = p.index( eid )
                  # Entry already forked. Handle traditionally.
                if tail:
                    tail = None
                    break
                tail = p[idx+1:] or None
            except ValueError:
                pass
        leafs = get_leafs( edpaths, eid )
        return tail, leafs, [p[-1] for p in edpaths]

def logseq (cur, seq, src):
        """===================================================================
        # Return a list of the id,dfrm pairs (plus stat and unap) for
        # all entries in a src/seq set.  We format the list into a text
        # string for the caller to print.  By looking at this someome
        # can figure out the shape of the edit tree (assuming that it
        # is entirely in the src/seq set).
        ==================================================================="""
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
          # [Postponing the tab expansion, needs more consideration
          # and discussion.]
        #cleaned = cleaned.expandtabs()
        if source and cleaned != s:
            errs.append ("Illegal characters in '%s'" % source)
        return cleaned
