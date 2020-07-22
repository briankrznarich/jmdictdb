#!/usr/bin/env python3
# Copyright (c) 2008-2010 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, cgi
try: import pkgpath.py  # Make jmdictdb package available on sys.path.
except ImportError: pass
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, jmcgi

def main (args, opts):
        logger.enable()
        jdb.reset_encoding (sys.stdout, 'utf-8')
        try: form, svc, dbg, cur, sid, sess, parms, cfg = jmcgi.parseform()
        except Exception as e: jmcgi.err_page ([str (e)])
        kwhash = {}
        for t in 'RINF KINF FREQ MISC POS FLD DIAL GINF SRC STAT XREF'.split():
            kw = jdb.KW.recs (t)
            kwset = [t.capitalize(), sorted (kw, key=lambda x:x.kw.lower())]
            kwhash[t] = kwset[1]
        kwhash['LANG'] = get_langs (cur)
        jmcgi.jinja_page ("edhelp.jinja", svc=svc, dbg=dbg, cfg=cfg, 
                          kwhash=kwhash)

def get_langs (cur):
        """Get set of kwlang rows for languages currently used in the
        the database (for gloss and lsrc.)"""

        sql = \
          "SELECT k.id,k.kw,k.descr FROM "\
              "(SELECT lang FROM gloss "\
              "UNION DISTINCT "\
              "SELECT lang FROM lsrc) AS l "\
          "JOIN kwlang k ON k.id=l.lang "\
          "ORDER BY k.kw!='eng', k.kw "
          # The first "order by" term will sort english to the top
          # of the list.
        rows = jdb.dbread (cur, sql)
        return rows

if __name__ == '__main__':
        args, opts = jmcgi.args()
        main (args, opts)
