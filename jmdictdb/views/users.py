# Copyright (c) 2018 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, pdb
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb

def view (svc, cfg, user, cur, params):
       errs = []; chklist = {}
       fv = params.get; fl = params.getlist

       if not user or user.priv != 'A': users = []
       else:
           sql = "SELECT * FROM users ORDER BY userid"
           sesscur = jdb.dbOpenSvc (cfg, svc, session=True, noverchk=True, nokw=True)
           users = jdb.dbread (sesscur, sql)
           L('cgi.users').debug('read %d rows from table "user"' % (len(users),))
       return dict (users=users), []
