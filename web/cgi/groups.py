#!/usr/bin/env python3
# Copyright (c) 2009 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, cgi
try: import pkgpath.py  # Make jmdictdb package available on sys.path.
except ImportError: pass
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, jmcgi

def main( args, opts ):
        logger.enable()
        jdb.reset_encoding (sys.stdout, 'utf-8')
        errs = []
        try: form, svc, dbg, cur, sid, sess, parms, cfg = jmcgi.parseform()
        except Exception as e: jmcgi.err_page ([str(e)])

        fv = form.getfirst; fl = form.getlist
        orderby = "k.id,s.kw,e.src"
        sql = "SELECT k.id, k.kw, k.descr, s.kw AS corpus, count(*) AS cnt " \
                "FROM kwgrp k " \
                "LEFT JOIN grp g ON g.kw=k.id " \
                "LEFT JOIN entr e ON e.id=g.entr " \
                "LEFT JOIN kwsrc s ON s.id=e.src " \
                "GROUP BY k.id, k.kw, k.descr, e.src, s.kw " \
                "ORDER BY %s" % orderby

        rs = jdb.dbread (cur, sql)
        jmcgi.jinja_page ("groups.jinja",
                         results=rs, parms=parms,
                         svc=svc, dbg=dbg, sid=sid, session=sess, cfg=cfg,
                         this_page='goups.py')

if __name__ == '__main__':
        args, opts = jmcgi.args()
        main (args, opts)
