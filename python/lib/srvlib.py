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
#
#  Support functions for the jmapp Flask application.
#  The functions in this module are intented to be called directly
#  by the view functions in a Flask application and are located in
#  this module only to allow the main app module to be limited to
#  view functions as much as possible.  These functions should
#  not supply results data to the application view functions; that
#  is the job of the functions in rest.py.
#
########################################################################

import sys, re, datetime, dateutil.parser, pdb
import flask; from flask import session as Session, g as G, request as Rq
import jinja2, rest, jdb, srch
import logging; L = logging.getLogger;
# Note: some import statements are inside functions below.

def vLogEntry():
        '''
          Generates a log debug entry when a view is entered.  Should be
          called as the first statement in a view function.
        '''
        L('jmapp.views').debug("Enter view '%s: %r'"
                                  % (Rq.endpoint,Rq.view_args))

def init_logging (cfg):
        import logger
        logfname = cfg.get ('logging', 'LOG_FILENAME')
        loglevel = cfg.get ('logging', 'LOG_LEVEL')
        filters = parse_cfg_logfilters (
                   cfg.get ('logging', 'LOG_FILTERS'))
        logger.log_config (level=loglevel, filename=logfname, filters=filters)
        return cfg

def login_handler (svc, cfg):
        action = fv ('loginout')  # Will be None, "login" or "logout"
        L('login_handler').debug("svc=%s, action=%s" % (svc, action))
        if action == 'login':
            username, pw = fv('username'), fv('password')
            prev_page = fv('this_page')
            u = validate_user (G.svc, username, pw, cfg)
              # validate_user() returns a DbRow object or None.  In
              # order to store the non-None value in the Flask session,
              # we convert it to a dict via its _todict() method.
            if u:
               G.user, Session['user_'+G.svc] = u, u._todict()
        elif action == 'logout':
            G.user = Session['user_'+G.svc] = None
        return

def validate_user (svc, username, pw, cfg):
        '''-------------------------------------------------------------------
        Parameters:
          svc -- Name of the service defined in the config.ini or
            config_pvt.ini files that access is being checked for.
          username -- Username or email address of the user to validate.
          pw -- Password to validate with.
          cfg -- Python configparser object typically initialized from
            the config.ini and config_pvt files.  This is typically
            stored in <app object>.config['CFG'].
        Returns:
          DB record for user with fields: userid,fullname,email,priv
          if the user was validated, or None if not.
        --------------------------------------------------------------------'''

          # Look up the authentication details for the user database
          # used for service 'svc'.
        L('srvlib.validate').debug("svc=%s, username=%s %s" % (svc,username,pw))
        sessdb_connargs = jdb.getSvc (cfg, svc, session=True)
          # Check the given 'username' and 'pw' against the users in
          # the user database.  If such a user exists, return his/her
          # profile (ie, the corresponding row in the database).
          # Otherwise None is returned.
        userprofile = rest.validate_user (sessdb_connargs, username, pw)
        L('srvlib.validate').debug("returning: %s" % userprofile)
        return userprofile

def fv (key, type=None):
        v = Rq.values.get (key)
        if v == '': v = None
        if type and v is not None: v = type (v)
        if isinstance (v, str): v = v.replace('\r\n', '\n')
        return v

def fvn (key, type=lambda x:x):
        vl = Rq.values.getlist (key)
        v = [(x if x is not None else type(x)) for x in vl]
        return v

def reshape (array, ncols, default=None):
        result = []
        for i in range(0, len(array), ncols):
            result.append (array[i:i+ncols])
        if len(result[-1]) < ncols:
            result[-1].extend ([default]*(ncols - len(result[-1])))
        return result



