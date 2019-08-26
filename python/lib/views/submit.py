#######################################################################
#  This file is part of JMdictDB.
#  Copyright (c) 2008-2012 Stuart McGraw
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

import sys
sys.path.extend (['../lib','../../python/lib','../python/lib'])
import logger; from logger import L
import jdb, jmcgi, serialize, submit

def view (svc, cfg, user, dbh, form):
        fv = form.get;  fl = form.getlist
        errs = []
        L('cgi.edsubmit').debug("started: userid=%s" % (user and user.userid))
          # disp values: '': User submission, 'a': Approve. 'r': Reject;
        disp = fv ('disp') or ''
        if not jmcgi.is_editor(user) and disp:
            errs.append ("Only logged in editors can approve or reject entries")
            return {}, errs
        try: entrs = serialize.unserialize (fv ("entr"))
        except Exception:
            return {}, ["Bad 'entr' parameter, unable to unserialize."]

        added = []
          # Clear any possible transactions begun elsewhere (e.g. by the
          # keyword table read in jdb.dbOpen()).  Failure to do this will
          # cause the following START TRANSACTON command to fail with:
          #  InternalError: SET TRANSACTION ISOLATION LEVEL must be
          #  called before any query
        L('cgi.edsubmit.main').debug("starting transaction")
        dbh.connection.rollback()
        dbh.execute ("START TRANSACTION ISOLATION LEVEL SERIALIZABLE");
          #FIXME: we unserialize the entr's xref's as they were resolved
          #  by the edconf.py page.  Should we check them again here?
          #  If target entry was deleted in meantime, attempt to add
          #  our entr to db will fail with obscure foreign key error.
          #  Alternatively an edited version of target may have been
          #  created which wont have our xref pointing to it as it should.
        for entr in entrs:
              #FIXME: temporary (I hope) hack...
            submit.Svc = svc
              #FIXME: submission() can raise a psycopg2
              # TransactionRollbackError if there is a serialization
              # error resulting from a concurrent update.  Detecting
              # such a condition is why run with serializable isolation
              # level.  We need to trap it and present some sensible
              # error message.
            e = submit.submission (dbh, entr, disp, errs,
                                   jmcgi.is_editor (user),
                                   user.userid if user else None)
              # The value returned by submission() is a 3-tuple consisting
              # of (id, seq, src) for the added entry.
            if e: added.append (e)

        if errs:
            L('cgi.edsubmit.main').info("rolling back transaction due to errors")
            dbh.connection.rollback()
            return {}, errs
        else:
            L('cgi.edsubmit.main').info("doing commit")
            dbh.connection.commit()
        return { 'added': added }, []
        L('cgi.edsubmit.main').debug("thank you page sent, exiting normally")
