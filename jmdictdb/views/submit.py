# Copyright (c) 2006-2012 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, pdb
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, jmcgi, serialize, submit

def view (svc, cfg, user, dbh, form):
        fv = form.get;  fl = form.getlist
        errs = []
        L('cgi.edsubmit').debug("started: userid=%s" % (user and user.userid))
          # disp values: '': User submission, 'a': Approve. 'r': Reject;
        disp = fv ('disp') or ''
        if not jmcgi.is_editor(user) and disp:
            errs.append ("Only logged in editors can approve or reject entries")
            return {}, errs
        try: entr = serialize.unserialize (fv ("entr"))
        except Exception:
            return {}, ["Bad 'entr' parameter, unable to unserialize."]
        entrs = [entr]  # 'unserialize() returns a single entry but formerly
                        #  returned a list.  Wrap 'entr' in a list to minimize
                        #  further code changes.
        added = []
          # Clear any possible transactions begun elsewhere (e.g. by the
          # keyword table read in jdb.dbOpen()).  Failure to do this will
          # cause the following START TRANSACTON command to fail with:
          #  InternalError: SET TRANSACTION ISOLATION LEVEL must be
          #  called before any query
        L('cgi.edsubmit.main').debug("starting transaction")
        dbh.connection.rollback()
        dbh.execute ("START TRANSACTION ISOLATION LEVEL SERIALIZABLE");
          # The entr's we deserialized have plain (un-augmented) xrefs
          # so re-augment them.
        xrefs = jdb.collect_xrefs (entrs)
        jdb.augment_xrefs (dbh, xrefs)
        for entr in entrs:
              #FIXME: temporary (I hope) hack...
            submit.Svc = svc
            e = submit.submission (dbh, entr, disp, errs,
                                   jmcgi.is_editor (user),
                                   user.userid if user else None)
              # The value returned by submission() is a 3-tuple consisting
              # of (id, seq, src) for the added entry.
            if e: added.append (e)

        if errs:
            L('cgi.edsubmit.main').info("rolling back transaction due to errors")
            dbh.connection.rollback()
            return {}, errs
        else:
            L('cgi.edsubmit.main').info("doing commit")
            dbh.connection.commit()
        return { 'added': added }, []
        L('cgi.edsubmit.main').debug("thank you page sent, exiting normally")
