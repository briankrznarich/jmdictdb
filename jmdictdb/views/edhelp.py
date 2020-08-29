# Copyright (c) 2008-2010 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, pdb
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb

def view (svc, cfg, user, cur, params):
        kwhash = {}
        for t in 'RINF KINF FREQ MISC POS FLD DIAL GINF SRC STAT XREF'.split():
            kw = jdb.KW.recs (t)
            kwset = [t.capitalize(), sorted (kw, key=lambda x:x.kw.lower())]
            kwhash[t] = kwset[1]
        kwhash['LANG'] = get_langs (cur)
        return dict (kwhash=kwhash), []

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
