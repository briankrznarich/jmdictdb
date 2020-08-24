#######################################################################
#  This file is part of JMdictDB.
#  Copyright (c) 2018 Stuart McGraw
#
#  JMdictDB is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published
#  by the Free Software Foundation; either version 2 of the License,
#  or (at your option) any later version.
#
#  JMdictDB is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with JMdictDB; if not, write to the Free Software Foundation,
#  51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
#######################################################################

import sys, pdb
sys.path.extend (['../lib','../../python/lib','../python/lib'])
import logger; from logger import L
import jdb

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
