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
        try: form, svc, dbg, cur, sid, sess, parms, cfg = jmcgi.parseform()
        except Exception as e: jmcgi.err_page ([str (e)])

        adv_srch_allowed = jmcgi.adv_srch_allowed (cfg, sess)
        jmcgi.jinja_page ("srchsql.jinja",
                        svc=svc, dbg=dbg, sid=sid, session=sess, cfg=cfg,
                        adv_srch_allowed = adv_srch_allowed, parms=parms,
                        this_page='srchsql.py')

if __name__ == '__main__':
        args, opts = jmcgi.args()
        main (args, opts)
