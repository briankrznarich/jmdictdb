#######################################################################
#  This file is part of JMdictDB.
#  Copyright (c) 2019 Stuart McGraw
#
#  JMdictDB is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published
#  by the Free Software Foundation; either version 2 of the License,
#  or (at your option) any later version.
#
#  JMdictDB is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with JMdictDB; if not, write to the Free Software Foundation,
#  51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
#######################################################################
#
#  Server independent view functions.
#  The functions in this module are intended to be called by view
#  code for a jmdictdb server.  They should not depend on the kind
#  of view code calling them (wsgi app, cgi, etc).  Their job is
#  to provide appropriate data (as a JSON object [*1]) based on
#  the arguments they receive.
#
#  [*1] By JSON object we mean a Python object that is serializable
#    into JSON.
#
########################################################################

import sys, os, pdb
import jdb, logger, db
from logger import L
# Note: some import statements are inside functions below.

#=============================================================================
# View functions
#=============================================================================

def v_entr (elist, qlist, disp, cur=None):
        import fmtxml, fmtjel, xslfmt, jmcgi
        errs = []
        entries = jmcgi.get_entrs (cur, elist, qlist, errs)
        if errs: {'data':[], 'errors':errs}

          # Add a .SEQKR attribute to each entry in 'entries' that
          # gives the kanji and reading of the newest (most recently
          # edited) entry that has the same sequence number.
        seqkr_decorate (entries)

          # Sort the entries.  The sorting order will group entries
          # with the same sequence number (.src,.seq) together and
          # each of those groups will be ordered by the kanji/reading
          # of the newest (most recently edited) entry in the group.
          # (The kanji and/or readings of an entry are sometimes changed
          # and this order will keep the changed entries together with
          # their pre-changed versions, while maintaining an overall
          # ordering by kanji/reading.)  Within each group having the
          # same sequence number, entries are sorted in descending order
          # by the timestamp of the most recent history; that is, from
          # the most recently edited entry to the least recently edited
          # one.
        entries.sort (key=lambda e: (
                e.SEQKR[0], e.SEQKR[1],
                e.src, e.seq,  # In case different seqs have same SEQKR.
                  # e._hist[*].dt is a datatime.datetime instance.
                -(e._hist[-1].dt.timestamp() if e._hist else 0),
                -e.id))
        for e in entries:
            for s in e._sens:
                if hasattr (s, '_xref'): jdb.augment_xrefs (cur, s._xref)
                if hasattr (s, '_xrer'): jdb.augment_xrefs (cur, s._xrer, 1)
            if hasattr (e, '_snd'): jdb.augment_snds (cur, e._snd)
        cur.close()
        if disp == 'xml':
            etxts = [fmtxml.entr (e) for e in entries]
        elif disp == 'jm':
            etxts = [fmtxml.entr (e, compat='jmdict') for e in entries]
        elif disp == 'jmne':
            etxts = [fmtxml.entr (e, compat='jmnedict') for e in entries]
        elif disp == 'jel':
            etxts = [fmtjel.entr (e) for e in entries]
        elif disp == 'ed':
            etxts = [xslfmt.entr (e) for e in entries]
        else:
            etxts = ['' for e in entries]
        jmcgi.htmlprep (entries)
        jmcgi.add_encodings (entries)    # For kanjidic entries.
        if disp == 'ed': etxts = [jmcgi.txt2html (x) for x in etxts]
        jmcgi.add_filtered_xrefs (entries, rem_unap=True)
        entrs = list (zip (entries, etxts))
        return [entrs, []]

def v_srchformq():
        data = sorted (jdb.KW.recs('SRC'), key=lambda x:x.kw.lower())
        return [data, []]

#=============================================================================
# Support functions
#=============================================================================

def validate_user (dburi, username, pw):
        '''
        Parameters:
          dburi -- A uri or dict of connection arguments for the jmdict
            session database that stores user profiles.
          username -- Username or email address to login in as.
          pw -- Password to log in with.
        Returns:
          DB record for user with fields:
            userid,fullname,email,priv,svc
          if the user was validated, or None if not. '''

        dbconn = db.connect (dburi)
        if '@' in username: field = 'email'
        else: field = 'userid'
        sql = "SELECT userid,fullname,email,priv FROM users "\
              "WHERE %s=%%s AND pw=crypt(%%s, pw) AND not disabled"\
              % (field,)
        userprofile = db.query1 (dbconn, sql, (username,pw))
        if not userprofile: return None
        return userprofile

def seqkr_decorate (entries):
        # Add a .SEQKR attribute to every entry in 'entries'.
        # The value of the added attribute is a 2-tuple of the kanji
        # and reading texts of the most recently edited entry (i.e.
        # the entry with the most recent history record whose src,seq
        # value is the same as the entry being decorated) of those with
        # the same src,seq number.
        # The purpose is to permit a later a sort of 'entries' that will
        # keep all entries with the same src,seq number together even
        # when some have had their kanji or reading values changed, yet
        # order the groups by kanji,reading order.

        import collections, datetime
        seqlist = collections.defaultdict(list)
          # 'old' should be older than any existant history record.
        old = datetime.datetime (1970, 1, 1)  # Jan 1, 1970.
          # Group the entries by e.src,e.seq.
        for e in entries:
            seqlist[(e.src,e.seq)].append (e)
          # 'seqlist' is now a dict with keys that are src,seq 2-tuples and
          # values that are lists of the entries in 'entries' with that value
          # of e.src and e.seq.
          # For each list of entries with a common .src,.seq value...
        for (src,seq),elist in seqlist.items():
              # Find the newest entry (the entry with the most recent
              # history record in .hist[].  .hist is ordered from oldest
              # to newest so the most recent history record in an entry
              # is always .hist[-1].
            newest = max (elist, key=
                          lambda e: (e._hist[-1].dt.timestamp()
                                     if e._hist else 0, e.id))
              # Decorate each entry in the list with the kanji/-
              # reading of the newest entry.
            seqkr = (newest._kanj[0].txt if newest._kanj else ''),\
                    (newest._rdng[0].txt if newest._rdng else '')
            for e in elist: e.SEQKR = seqkr
        return
