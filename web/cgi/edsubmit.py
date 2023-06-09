#!/usr/bin/env python3
# Copyright (c) 2008-2012 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys
try: import pkgpath.py  # Make jmdictdb package available on sys.path.
except ImportError: pass
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, jmcgi, serialize, submit

def main( args, opts ):
        logger.enable()
        jdb.reset_encoding (sys.stdout, 'utf-8')
        errs = []; dbh = svc = None
        try: form, svc, dbg, dbh, sid, sess, parms, cfg = jmcgi.parseform()
        except ValueError as e: jmcgi.err_page ([str (e)])

        L('cgi.edsubmit').debug("started: userid=%s, sid=%s"
                                % (sess and sess.userid, sess and sess.id))
        fv = form.getfirst
          # disp values: '': User submission, 'a': Approve. 'r': Reject;
        disp = fv ('disp') or ''
        if not sess and disp:
            errs.append ("Only registered editors can approve or reject entries")
        if errs: jmcgi.err_page (errs)
        try: entr = serialize.unserialize (fv ("entr"))
        except Exception:
            jmcgi.err_page (["Bad 'entr' parameter, unable to unserialize."])
        entrs = [entr]  # 'unserialize() returns a single entry but formerly
                        #  returned a list.  Wrap 'entr' in a list to minimize
                        #  further code changes,
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
              #FIXME: temporary hack...
            submit.Svc, submit.Sid = svc, sid
            e = submit.submission (dbh, entr, disp, errs, jmcgi.is_editor (sess),
                                   sess.userid if sess else None)
              # The value returned by submission() is a 3-tuple consisting
              # of (id, seq, src) for the added entry.
            if e: added.append (e)

        if errs:
            L('cgi.edsubmit.main').info("rolling back transaction due to errors")
            dbh.connection.rollback()
            jmcgi.err_page (errs)
        else:
            L('cgi.edsubmit.main').info("doing commit")
            dbh.connection.commit()
        jmcgi.jinja_page ("submitted.jinja",
                        added=added, parms=parms,
                        svc=svc, dbg=dbg, sid=sid, session=sess, cfg=cfg,
                        this_page='edsubmit.py')
        L('cgi.edsubmit.main').debug("thank you page sent, exiting normally")

def err_page (errs):
        L('cgi.edsubmit.err_page').debug("going to error page. Errors:\n%s"
                                         % '\n'.join (errs))
        jmcgi.err_page (errs)

if __name__ == '__main__':
        args, opts = jmcgi.args()
        main (args, opts)
