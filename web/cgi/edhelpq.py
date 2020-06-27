#!/usr/bin/env python3
# Copyright (c) 2008-2010 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, cgi
try: import pkgpath.py  # Make jmdictdb package available on sys.path.
except ImportError: pass
from jmdictdb import logger; from jmdictdb.logger import L
from jumdictdb import jdb, jmcgi

def main (args, opts):
        logger.enable()
        jdb.reset_encoding (sys.stdout, 'utf-8')
        try: form, svc, dbg, cur, sid, sess, parms, cfg = jmcgi.parseform()
        except Exception as e: jmcgi.err_page ([str (e)])
        jmcgi.jinja_page ("edhelpq.jinja", cfg=cfg, svc=svc, dbg=dbg)

if __name__ == '__main__':
        args, opts = jmcgi.args()
        main (args, opts)
