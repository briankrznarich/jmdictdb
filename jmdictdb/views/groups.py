# Copyright (c) 2009 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, pdb
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb

def view (svc, cfg, user, cur, params):
        orderby = "k.id,s.kw,e.src"
        sql = "SELECT k.id, k.kw, k.descr, s.kw AS corpus, count(*) AS cnt " \
                "FROM kwgrp k " \
                "LEFT JOIN grp g ON g.kw=k.id " \
                "LEFT JOIN entr e ON e.id=g.entr " \
                "LEFT JOIN kwsrc s ON s.id=e.src " \
                "GROUP BY k.id, k.kw, k.descr, e.src, s.kw " \
                "ORDER BY %s" % orderby
        rs = jdb.dbread (cur, sql)
        return dict (results=rs), []
