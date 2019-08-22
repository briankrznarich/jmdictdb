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
            userobj = validate_user (G.svc, username, pw, cfg)
            G.user = Session['user_'+G.svc] = userobj
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
        if userprofile: userprofile = userprofile.__dict__
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

def entrs_per_page (cfg):
        epp = min (max (int(fv('ps')
                             or G.cfg.get('web','DEF_ENTRIES_PER_PAGE')),
                        int(G.cfg.get('web','MIN_ENTRIES_PER_PAGE'))),
                   int(G.cfg.get('web','MAX_ENTRIES_PER_PAGE')))
        return epp

def srchres (cur, so, sqlp, pt, p0, cfg, user):
        '''-------------------------------------------------------------------
        Run a database search for entries using the search parameters
        in 'so' or the sql query in 'sqlp' and return one page of results
        starting at offest 'p0' with 'epg' entries per page.
        cur -- Open JMdictDB database cursor from jdb.dbOpen() or equiv.
        so -- A srch.SearchItems object as return by extract_srch_params().
        sqlp --
        pt -- Total number of search results or -1.
        p0 -- Offset in search result.
        cfg -- Config object as returned by lib.config().
        user -- User object if user is logged or None if not.
        -------------------------------------------------------------------'''
        errs = []
        if so:
            try: condlist = srch.so2conds (so)
            except ValueError as e:
                errs.append (str (e))
              # FIXME: [IS-115] Following will prevent kanjidic entries from
              #  appearing in results.  Obviously hardwiring id=4 is a hack.
            else:
                #condlist.append (('entr e', 'e.src!=4', []))
                sql, sql_args = jdb.build_search_sql (condlist)
        elif sqlp:
              # 'sqlp' is a SQL statement string that allows an arbitrary
              # search.  Because arbitrary sql can also do other things
              # such as delete the database, it should only be run as a
              # user with read-only access to the database and it is the
              # job of srch.adv_srch_allowed() to check that.
            if not srch.adv_srch_allowed (cfg, user):
                jmcgi.err_page (["'sql' parameter is disallowed."])
            sql = sqlp.strip()
            if sql.endswith (';'): sql = sql[:-1]
            sql_args = []

        if errs: return [], errs

        srch_timeout = cfg.get ('search', 'SEARCH_TIMEOUT')
        rs, pt, stats \
           = rest.run_search (cur, sql, sql_args, srch_timeout,
                              pt, p0, entrs_per_page (cfg))

        return rs, pt, stats

def extract_srch_params (params):
        '''-------------------------------------------------------------------
        Extract search related url parameters from the current Flask
        request object.

        params -- A Flask request.args object (which will in turn be a
            a werkzeug.MultiDict object).  This contains the parsed
            url parameters in a request.

        returns: A srch.SearchItems item initiailized from 'params'
            that can be used to generate sql for performing the search.
        --------------------------------------------------------------------'''

        def fv(k): return params.get(k)
        def fl(k): return params.getlist(k)
        def fvi(k): return params.get(k,type=int)

        errs = []
        so = srch.SearchItems()
        so.idnum=fv('idval');  so.idtyp=fv('idtyp')
        tl = []
        for i in (1,2,3):
            txt = (fv('t'+str(i)) or '')
            if txt: tl.append (srch.SearchItemsTexts (
                                 srchtxt = txt,
                                 srchin  = fv('s'+str(i)),
                                 srchtyp = fv('y'+str(i)) ))
        if tl: so.txts = tl
        so.pos   = fl('pos');   so.misc  = fl('misc');
        so.fld   = fl('fld');   so.dial  = fl('dial');
        so.rinf  = fl('rinf');  so.kinf  = fl('kinf');  so.freq = fl('freq')
        so.grp   = rest.grpsparse (fv('grp'))
        so.src   = fl('src');   so.stat  = fl('stat');  so.unap = fl('appr')
        so.nfval = fv('nfval'); so.nfcmp = fv('nfcmp')
          # Search using gA freq criterion no longer supported.  See
          # the comments in srch._freqcond() but code left here for
          # reference.
        so.gaval = fv('gaval'); so.gacmp = fv('gacmp')
          # Sense notes criteria.
        so.snote = (fv('snote') or ''), fvi('snotem')
          # Next 5 items are History criteria...
          #FIXME? use selection boxes for dates?  Or a JS calendar control?
        so.ts = rest.dateparse (fv('ts0'), 0, errs),\
                rest.dateparse (fv('ts1'), 1, errs)
        so.smtr = (fv('smtr') or ''), fvi('smtrm')
        so.cmts = (fv('cmts') or ''), fvi('cmtsm')
        so.refs = (fv('refs') or ''), fvi('refsm')
        so.mt = fv('mt')
        return so
