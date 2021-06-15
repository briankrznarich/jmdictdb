# Copyright (c) 2019 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

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

import sys, os, re, datetime, dateutil.parser, pdb
import flask, jinja2
from flask import session as Session, g as G, request as Rq
from jmdictdb import jdb
from jmdictdb import rest, srch
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

def check_status (cfg, ipaddr):
        '''-------------------------------------------------------------------
        Checks the operator-controlled status of the server by checking for
        the existence of a "flag" file and if present return the name of a
        status html page that the caller should return to the requestor
        rather than the originally requested page.
        The flag files are looked for in the status file directory defined
        in the  configuration file by the setting [web]/STATUS_DIR.
        Three status conditions are possible:
          _Condition_                  _Status file name_
          Down for maintenance         status_maint
          Down due to excessive load   status_load
          IP address blocked           status_blocked
        In the case of the first two files, the presence of the file is
        sufficient to trigger the return of the corresponding status page.
        For the third, the 'status_blocked' file is read and if the
        requestor's IP address appears in it as the first white-space
        delimited word on a line, the ip_blocked page will be returned.
        Comments lines may be included in the 'status_blocked' file as
        long as their first word in not an ip address, and comments can
        follow ip addresses since only the first word on a line is matched.
        If none of the three conditions obtain, None is returned.
        -------------------------------------------------------------------'''

        sfd = cfg.get ('web', 'STATUS_DIR')  # Status file directory.
        page = None
        if check_blocked (sfd, ipaddr):
            page = 'status_blocked.html'
        elif os.access (os.path.join (sfd, 'status_maint'), os.F_OK):
            page = 'status_maint.html'
        elif os.access (os.path.join (sfd, 'status_load'), os.F_OK):
            page = 'status_load.html'
        return page

def check_blocked (sfd, ipaddr):
        if not ipaddr: return False
        try:
            with open (os.path.join (sfd, 'status_blocked')) as f:
                lines = f.readlines()
        except OSError: return False
        for ln in lines:
              # Comment lines allowed but need no special check since
              # they won't match an IP address.
              # Look at only the first word, allowing ip address to be
              # followed by comment.
            words = ln.strip().split()
            if words and words[0] == ipaddr: return True
        return False
