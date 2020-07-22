#!/usr/bin/env python3
# Copyright (c) 2006-2012 Stuart McGraw
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

        qs = jmcgi.form2qs (form)
        corp = reshape (sorted (jdb.KW.recs('SRC'),
                                key=lambda x:x.kw.lower()), 10)
        jmcgi.jinja_page ("srchformq.jinja",
                        src=corp, parms=parms,
                        svc=svc, dbg=dbg, sid=sid, session=sess, cfg=cfg,
                        this_page='srchformq.py')

def reshape (array, ncols, default=None):
        result = []
        for i in range(0, len(array), ncols):
            result.append (array[i:i+ncols])
        if len(result[-1]) < ncols:
            result[-1].extend ([default]*(ncols - len(result[-1])))
        return result

if __name__ == '__main__':
        args, opts = jmcgi.args()
        main (args, opts)
