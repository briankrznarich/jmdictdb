#!/usr/bin/env python3
# Copyright (c) 2019 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# flaskapp -- WSGI application for JMdictDB.
# Please see the installation documention for information about
# configuring a WSGI webserver.
#
# For production use, the App object created here is imported by a WSGI
# server and the server will call its methods in response to http requests
# it receives.  For development it can be run with the Flask debug server
# by the program tools/run-flask.py.
#
# Note that a lot of what happens here (such as reading the configuration
# files) happens when this module is imported.  An environment variable,
# JMDICTDB_CFGFILE, *MUST* be defined and point to a readable configuration
# file at import time.  Both cgi/jmdictdb.wsgi (run by Apache/mod_wsgi) and
# bin/run-flask.py (runs the Flask debug server) do so.
#
# Please see installation documentation and the source files web/lib/-
# jmdictdb.ini-sample and jmdictdb-pvt.ini-sample for details on the
# configuration file format and contents.

import sys, os, datetime, pdb
#_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'

import flask
from flask import Flask, request as Rq, session as Session, g as G, \
        Response, redirect as Redirect, url_for as Url, \
        render_template as Render,  _app_ctx_stack
from jmdictdb import jdb, logger, jinja, jmcgi
from jmdictdb import srvlib, rest
from jmdictdb.srvlib import fv, fvn
from jmdictdb.logger import L

def app_config (app, cfgfile):
        app.session_cookie_name = 'jmwsgi'
        # print ("Loading config file: %s" % cfgfile, file=sys.stderr) ##DEBUG
          # We may get an OSError exception if the config file given by
          # environment variable JMDICTDB_CFGFILE can not be opened for some
          # reason.  We let the exception happen with th assumption if will
          # end up in the webserver's log file.
        try: cfg = jmcgi.initcgi (cfgfile)
        except OSError as e:
            raise RuntimeError ("Unable to read configuration file")
        app.config['CFG'] = cfg
        app.secret_key = cfg.get ('flask', 'key')
        if app.secret_key in ('xxxxxxxxxxxxxxxx', ''):
            msg = "Configuration file error: [flask]/key not set"
            raise RuntimeError (msg)
        jinja.init (jinja_env=app.jinja_env)

App = flask.Flask (__name__, static_folder='../web',
                             template_folder='tmpla')

  # Environment variable identifying the config file MUST be set
  # when this module is imported.
try: cfgfile = os.environ['JMDICTDB_CFGFILE']
except KeyError:
    msg = "The JMDICTDB_CFGFILE environment variable was not set"
    raise RuntimeError (msg) from None

app_config (App, cfgfile)

def render (tmpl, **data):
        '''-------------------------------------------------------------------
        # Render a Jinja2 template adding additional standard data.
        # Almost all templates extend base template "layout.jinja" and
        # that template requires a standard set of variables that this
        # function will automatically add (svc, cfg, user), avoiding
        # the need to specifically reference them all directly in each
        # view.
        # Parameters:
        #   tmpl -- Name of the Jinja2 template.
        #   data -- (dict) Context data referenced by variables in the
        #     template.
        -------------------------------------------------------------------'''
        return Render (tmpl,
                       svc=G.svc, cfg=G.cfg, user=G.user,
                       **data)

def path(): return Rq.script_root + Rq.full_path

def prereq():
          # Get info about the logged in user.  Following sets G.user
          #  to a db.DbRow object containing user information if user is
          #  currently logged in, or None if not.  Note that logins are
          #  per 'svc' service (eg a login for service "jmdict" will not
          #  provide access to "jmtest", one will need to log into "jmtest"
          #  separately) but multiple logins can be stored simultaneously
          #  in Session.
        G.user = rest.get_user (G.svc, Session)
        L('jmwsgi.prereq').debug("cfg files: %s"
                                 % G.cfg.get('status','cfg_files'))
          # The following logging statement should usually be disabled
          # because the output contains database login credentials.
          # Enable for debugging only.
        #L('jmwsgi.prereq').debug("svc=%s; cfg=%r"
        #                         % (G.svc,dict(G.cfg['db_'+G.svc])))
        G.dbcur = rest.dbOpenSvc (G.cfg, G.svc)

@App.before_request
def before_request():
        L('view.before_request').debug("For endpoint %s" % Rq.endpoint)
        if Rq.endpoint and Rq.endpoint in ('cgiinfo'): return
        G.cfg = App.config['CFG']
        if not Rq.path.startswith ('/static'):
            down = srvlib.check_status (G.cfg, Rq.remote_addr)
            if down: return Redirect (Url('static', filename=down))
        G.svc = fv ('svc') or G.cfg.get('web','DEFAULT_SVC') or 'jmdict'
        if Rq.endpoint in ('login','logout','static'): return
        msg = None
        try: prereq()
        except rest.SvcUnknownError: msg = "Unknown service (%s)"
        except rest.SvcDbVersionError: msg = "Database version error (%s)"
        except rest.SvcDbError: msg = "Unavailable service (%s)"
        if msg: return Render ('error.jinja', svc=None, errs=[msg%G.svc],
                               cssclass='errormsg')

from werkzeug.exceptions import HTTPException
@App.errorhandler (Exception)
def app_error (e):
        # This error handler catches otherwise uncaught exceptions in
        # the rest of the views and library code.  The intent is to keep
        # application errors, typically accompanied by a Python stack
        # dump, out of the Apache system log files and put them in the
        # JMdictDB log file.
          # Flask uses exceptions to signal various conditions so we
          # pass them on...
        if isinstance(e, HTTPException): return e
          # Everything else we handle.  First, log the exception with
          # stack trace ti the JMdictDB log file.
        L('app.error').exception(e)
          # Generate a generic "something went wrong' page for the client.
          # The 'errid' value has same format as the timestamp in the
          # the JMdictDB log file and provides correlation with it.
        errid = datetime.datetime.now().strftime("%y%m%d-%H%M%S")\
                + '-' + str(os.getpid())
        msg = "We're sorry, something seems to gone kaput!"
        return Render ('error.jinja', errs=[msg], errid=errid,
                       cssclass='errormsg', svc='')

#=============================================================================
#  View functions.
#  The functions below are executed in response to Flask receiving
#  an HTTP request using the URL path given in each @App.route
#  decorator.
#
#  In order to keep this file skeletal, the heavy lifting for each
#  view is done in a separate module (one per view) in jmdictdb/view/.
#  The views code in this file are shims to call the view module and
#  render the data it returns.
#=============================================================================

@App.route ('/')
def home():
        srvlib.vLogEntry()
        return Redirect (Url('srchform'))

@App.route ('/login', methods=['POST'])
def login():
        srvlib.vLogEntry()
        return_to = fv ('this_page')
        #L('view.login').debug("return_to=%r"%return_to)
        if not return_to.startswith (Rq.script_root): flask.abort(400)
        srvlib.login_handler (G.svc, G.cfg)
        return Redirect (return_to)

# See lib/views/README.txt for a description of the conventions
# used in the following views.

@App.route ('/cgiinfo.py')
def cgiinfo():
        srvlib.vLogEntry()
        from jmdictdb.views.cgiinfo import view
        html = view (App, Rq.values)
        return html

@App.route ('/conj.py')
def conj():
        srvlib.vLogEntry()
        from jmdictdb.views.conj import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('conj.jinja', this_page=path(), **data)

@App.route ('/edconf.py', methods=['GET','POST'])
def edconf():
        srvlib.vLogEntry()
        from jmdictdb.views.edconf import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.values)
        if errs:
               # 'errs' is a dict with items: 'errs', a list of error
               # messages; optionally 'prolog', prolog text; and optionally
               # 'epilog', epilog text.
             return render ('error.jinja', cssclass='errormsg', **errs)
        return render ('edconf.jinja', this_page=path(), **data)

@App.route ('/edform.py')
def edform():
        srvlib.vLogEntry()
        from jmdictdb.views.edform import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('edform.jinja', this_page=path(), **data)

@App.route ('/entr.py')
def entr():
        srvlib.vLogEntry()
        from jmdictdb.views.entr import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('entr.jinja', this_page=path(), **data)

@App.route ('/edhelp.py')
def edhelp():
        srvlib.vLogEntry()
        from jmdictdb.views.edhelp import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('edhelp.jinja', this_page=path(), **data)

@App.route ('/edhelpq.py')
def edhelpq():
        srvlib.vLogEntry()
        return render ('edhelpq.jinja', this_page=path())

@App.route ('/groups.py')
def groups():
        srvlib.vLogEntry()
        from jmdictdb.views.groups import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('groups.jinja', this_page=path(), **data)

@App.route ('/srchform.py')
def srchform():
        srvlib.vLogEntry()
        from jmdictdb.views.srchform import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('srchform.jinja', this_page=path(), **data)

@App.route ('/srchformq.py')
def srchformq():
        srvlib.vLogEntry()
        from jmdictdb.views.srchformq import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        data['sid'] = 'xxx'
        return render ('srchformq.jinja', this_page=path(), **data)

@App.route ('/srchres.py')
def srchres():
        srvlib.vLogEntry()
        from jmdictdb.views.srchres import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
            return render ('error.jinja', errs=errs, cssclass='errormsg')
        if len(data['results']) == 1 and Rq.args.get('p0',0,type=int)==0 \
            and Rq.args.get('srchres',0,type=int)==0:
              # Show the entry itself rather than search results if there
              # is only one result *and* this is the first page *and* the
              # url parameter "srchres" (used to force showing the srchres
              # page even if only one result) is not set.
            return Redirect (Url ('entr', svc=G.svc, e=data['results'][0].id))
        return render ("srchres.jinja", this_page=path(), **data)

@App.route ('/srchsql.py')
def srchsql():
        srvlib.vLogEntry()
        return render ('srchsql.jinja', this_page=path())

@App.route ('/edsubmit.py', methods=['POST'])
@App.route ('/submit.py', methods=['POST'])
def submit():
        srvlib.vLogEntry()
        from jmdictdb.views.submit import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.form)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('submitted.jinja', **data)

@App.route ('/updates.py')
def updates():
        srvlib.vLogEntry()
        from jmdictdb.views.updates import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
          # Depending on the url parameters that were given the returned
          # data can be for either of two pages; the name of the one to
          # use is returned in data['page'] and will be either "updates"
          # or "entr".
        return render (data['page']+'.jinja', this_page=path(), **data)

@App.route ('/user.py')
def user():
        srvlib.vLogEntry()
        from jmdictdb.views.user import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('user.jinja', this_page=path(), **data)

@App.route ('/users.py')
def users():
        srvlib.vLogEntry()
        from jmdictdb.views.users import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        data['sid'] = 'xxx'
        return render ('users.jinja', this_page=path(), **data)

@App.route ('/userupd.py', methods=['POST'])
def userupd():
        srvlib.vLogEntry()
        from jmdictdb.views.userupd import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.form)
        if errs:
             return render ('error.jinja', **errs, cssclass='errormsg')
        data['sid'] = 'xxx'
        if 'result' in data:
          # Queue a confirmation message for display on the next page.
          # 'result' is a category like "success" or "error" and is
          # used in the template for styling.
            result, msg = data.get('result')
            flask.flash (msg, result)
          # If current user is an Admin user, redirect back to the users
          # list page since the page for the subject user may have been
          # deleted.
        if G.user.priv == 'A': redir_to = 'users'
          # For non-Admin user, send them back to their own user page.
        else: redir_to = 'user'
        return Redirect (Url (redir_to, svc=G.svc, **data))
