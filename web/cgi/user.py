#!/usr/bin/env python3
# Copyright (c) 2018 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, cgi, re, datetime, copy
try: import pkgpath.py  # Make jmdictdb package available on sys.path.
except ImportError: pass
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, jmcgi

def main (args, opts):
        logger.enable()
        jdb.reset_encoding (sys.stdout, 'utf-8')
        errs = []; chklist = {}
        try: form, svc, dbg, cur, sid, sess, parms, cfg = jmcgi.parseform()
        except Exception as e: jmcgi.err_page ([str (e)])
        fv = form.getfirst; fl = form.getlist
        L('cgi.user').debug("sess=%r" % sess)
        L('cgi.user').debug("u=%r, new=%r" % (fv('u'), fv('new')))
          # If 'sess' evaluates false, user is not logged in in which
          # case we go directly to the "user" page which will say that
          # one has to be logged in.  We do this instead of using jmcgi.-
          # err_page() because the notes on the users.jinja page inform
          # the user about the requirements for access.
          # If user is logged in but is not an Admin user, we ignore
          # the "u=..." url parameter and show user info only for
          # the logged in user.
          # If the user is an Admin user, we show info for the user 
          # requested by the "u=..." parameter if any, or the logged 
          # in user if not.
          # There may still be no user due to "u=..." for non-existant
          # or some corner-case but that's ok, page will show a "no user
          # found" message.
        user = userid = new = None
        if sess:  # I.e., if logged in...
            if sess.priv == 'A':
                userid, new = fv ('u'), fv('new')
            if not new and not userid: userid = sess.userid
            L('cgi.user').debug("userid=%r, new=%r" % (userid, new)) 
            if userid:
                user = jmcgi.get_user (userid, svc, cfg)
                L('cgi.user').debug("read user data: %s" % (sanitize_o(user),))
        L('cgi.user').debug("rendering template, new=%r" % new) 
        jmcgi.jinja_page ("user.jinja", user=user, result=fv('result'),
                          session=sess, cfg=cfg, parms=parms, new=new,
                          svc=svc, sid=sid, dbg=dbg, this_page='user.py')

def sanitize_o (obj):
        if not hasattr (obj, 'pw'): return obj
        o = obj.copy()
        if o.pw: o.pw = '***'
        return o

if __name__ == '__main__':
        args, opts = jmcgi.args()
        main (args, opts)
