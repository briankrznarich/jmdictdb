#######################################################################
#  This file is part of JMdictDB.
#  Copyright (c) 2019 Stuart McGraw
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

import sys, os, pdb
import jdb, logger, db
from logger import L

def validate_user (dburi, username, pw):
        '''-------------------------------------------------------------------
        Parameters:
          dburi -- A uri or dict of connection arguments for the jmdict
            session database that stores user profiles.
          username -- Username or email address to login in as.
          pw -- Password to log in with.
        Returns:
          DB record for user with fields:
            userid,fullname,email,priv,svc
          if the user was validated, or None if not.
        -------------------------------------------------------------------'''

        dbconn = db.connect (dburi)
        if '@' in username: field = 'email'
        else: field = 'userid'
        sql = "SELECT userid,fullname,email,priv FROM users "\
              "WHERE %s=%%s AND pw=crypt(%%s, pw) AND not disabled"\
              % (field,)
        userprofile = db.query1 (dbconn, sql, (username,pw))
        if not userprofile: return None
        return userprofile

#FIXME: we shouldn't be dealing with Flask objects in this module as we do
# below (should do that in srvlib) but we need access to db.DbRow and we
# don't have access to the db module in srvlib.

def get_user (svc, session):
        '''-------------------------------------------------------------------
        Extract the user profile of a logged user from a Flask session
        object.  If not logged in (ie there is no user info stored in
        the session object), return None.  Note that logins are per service;
        a login to the "jmdict" service is not valid for access to the
        "jmtest" service.

        svc -- Service name.
        session -- A Flask client-side 'session' object.
        -------------------------------------------------------------------'''

        u = session.get ('user_' + svc)
        if not u: return None
          # Convert the user info which is stored as a dict in the session
          # object back to a DbRoe object since we still use former cgi code
          # (e.g., jmcgi.is_editor()) tht expects a DbRow, not a dict.
        userobj = db.DbRow (u)
        return userobj

class SvcUnknownError(RuntimeError): pass
class SvcDbError(RuntimeError): pass

def dbOpenSvc (cfg, svcname, readonly=False, session=False, **kwds):
        '''-------------------------------------------------------------------
        A thin wrapper around jdb.dbOpenSvc() to catch common exceptions.
        Takes same arguments and returns same values as jdb.dbOpenSvc(),
        see that function for documentation.
        We transform a KeyError in a SvcUnknownError ('svcname' not found
        in configuration file 'cfg') and a OperationalError (database not
        found, an exception raised by psycopg2) into SvcDbError.
        FIXME? the exceptions caught may be too broad and could be caused
         by something other than the given reasons.
        -------------------------------------------------------------------'''
        try:
            cur = jdb.dbOpenSvc (cfg, svcname, readonly, session, **kwds)
        except KeyError as e: raise SvcUnknownError(svcname)
        except db.OperationalError as e: raise SvcDbError(svcname)
        return cur
