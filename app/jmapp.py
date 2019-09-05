#!/usr/bin/python3
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

import sys, os, io, inspect, pdb
_ = os.path.join (os.path.abspath(os.path.dirname(__file__)), 'lib')
if _ not in sys.path: sys.path.insert(0, _)

import flask
from flask import Flask, request as Rq, session as Session, g as G, \
        Response, redirect as Redirect, url_for as Url, \
        render_template as Render,  _app_ctx_stack
import jdb, logger, jinja, config
import srvlib, rest; from srvlib import vLogEntry, fv, fvn
from logger import L

def main():
        App.jinja_env.auto_reload = True
        App.config['TEMPLATES_AUTO_RELOAD'] = True
        App.run (host='0.0.0.0', debug=True)

def app_config (app):
        app.session_cookie_name = 'jmapp'
        app.secret_key = 'secret'
        try: cfg = config.cfgRead ('config.ini', 'config-pvt.ini')
        except IOError:
            print ("Unable to load config.ini file(s)", file=sys.stderr)
            flask.abort (500)
        app.config['CFG'] = cfg
        logger.log_config_from_cfg (cfg)
        jinja.init (jinja_env=app.jinja_env)

App = flask.Flask (__name__, static_folder='./static',
                             template_folder='./tmpl')
app_config (App)

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
        L('jmapp.prereq').debug("cfg files: %s"%G.cfg.get('status','cfg_files'))
          # The following logging statement should usually be disabled
          # because the output contains database login credentials.
          # Enable for debugging only.
        #L('jmapp.prereq').debug("svc=%s; cfg=%r"
        #                        % (G.svc,dict(G.cfg['db_'+G.svc])))
        G.dbcur = rest.dbOpenSvc (G.cfg, G.svc)

@App.before_request
def before_request():
        L('view.before_request').debug("For endpoint %s" % Rq.endpoint)
        G.cfg = App.config['CFG']
        if not Rq.path.startswith ('/static'):
            down = srvlib.check_status (G.cfg)
            if down: return Redirect (Url('static', filename=down))
        G.svc = fv ('svc') or G.cfg.get('web','DEFAULT_SVC') or 'jmdict'
        if Rq.endpoint in ('login','logout','static'): return
        msg = None
        try: prereq()
        except rest.SvcUnknownError: msg = "Unknown service (%s)" % G.svc
        except rest.SvcDbError: msg = "Unavailable service (%s)" % G.svc
        if msg: return Render ('error.jinja', svc=None, errs=[msg],
                               cssclass='errormsg')

#=============================================================================
#  View functions.
#  The functions below are executed in response to Flask receiving 
#  an HTTP request using the URL path given in each @App.route 
#  decorator.
#=============================================================================

@App.route ('/')
def home():
        vLogEntry()
        return Redirect (Url('srchform'))

@App.route ('/login', methods=['POST'])
def login():
        vLogEntry()
        return_to = fv ('this_page')
        #L('view.login').debug("return_to=%r"%return_to)
        if not return_to.startswith (Rq.script_root): flask.abort(400)
        srvlib.login_handler (G.svc, G.cfg)
        return Redirect (return_to)

# See lib/views/README.txt for a description of the conventions
# used in the following views.

@App.route ('/conj.py')
def conj():
        vLogEntry()
        from lib.views.conj import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('conj.jinja', this_page=path(), **data)

@App.route ('/edconf.py')
def edconf():
        vLogEntry()
        from lib.views.edconf import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('edconf.jinja', this_page=path(), **data)

@App.route ('/edform.py')
def edform():
        vLogEntry()
        from lib.views.edform import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('edform.jinja', this_page=path(), **data)

@App.route ('/entr.py')
def entr():
        vLogEntry()
        from lib.views.entr import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('entr.jinja', this_page=path(), **data)

@App.route ('/edhelp.py')
def edhelp():
        vLogEntry()
        from lib.views.edhelp import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('edhelp.jinja', this_page=path(), **data)

@App.route ('/edhelpq.py')
def edhelpq():
        vLogEntry()
        return render ('edhelpq.jinja', this_page=path())

@App.route ('/groups.py')
def groups():
        vLogEntry()
        from lib.views.groups import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('groups.jinja', this_page=path(), **data)

@App.route ('/srchform.py')
def srchform():
        vLogEntry()
        from lib.views.srchform import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('srchform.jinja', this_page=path(), **data)

@App.route ('/srchformq.py')
def srchformq():
        vLogEntry()
        from lib.views.srchformq import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('srchformq.jinja', this_page=path(), **data)

@App.route ('/srchres.py')
def srchres():
        vLogEntry()
        from lib.views.srchres import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
            return render ('error.jinja', errs=errs, cssclass='errormsg')
        if len(data['results']) == 1 and Rq.args.get('p0',0,type=int)==0:
              # Show the entry itself rather than search results if there
              # is only one result *and* this is the first page.
            return Redirect (Url ('entr', e=data['results'][0].id))
        return render ("srchres.jinja", this_page=path(), **data)

@App.route ('/srchsql.py')
def srchsql():
        vLogEntry()
        return render ('srchsql.jinja', this_page=path())

@App.route ('/edsubmit.py', methods=['POST'])
@App.route ('/submit.py', methods=['POST'])
def submit():
        vLogEntry()
        from lib.views.submit import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.form)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('submitted.jinja', **data)

@App.route ('/updates.py')
def updates():
        vLogEntry()
        from lib.views.updates import view
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
        vLogEntry()
        from lib.views.user import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('user.jinja', this_page=path(), **data)

@App.route ('/users.py')
def users():
        vLogEntry()
        from lib.views.users import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.args)
        if errs:
             return render ('error.jinja', errs=errs, cssclass='errormsg')
        return render ('users.jinja', this_page=path(), **data)

@App.route ('/userupd.py', methods=['POST'])
def userupd():
        vLogEntry()
        from lib.views.userupd import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Rq.form)
        if errs:
             return render ('error.jinja', **errs, cssclass='errormsg')
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

if __name__ == '__main__': main()
