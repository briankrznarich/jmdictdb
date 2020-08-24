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

        if not sess or sess.priv != 'A': users = []
        else:
            sql = "SELECT * FROM users ORDER BY userid"
            sesscur = jdb.dbOpenSvc (cfg, svc, session=True, noverchk=True, nokw=True)
            users = jdb.dbread (sesscur, sql)
            L('cgi.users').debug('read %d rows from table "user"' % (len(users),))
        jmcgi.jinja_page ("users.jinja", users=users, session=sess,
                          cfg=cfg, parms=parms, svc=svc, dbg=dbg,
                          sid=sid, this_page='user.py', result=fv('result'))

if __name__ == '__main__':
        args, opts = jmcgi.args()
        main (args, opts)
