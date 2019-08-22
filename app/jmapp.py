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
        logger.log_config ("debug")
        app.session_cookie_name = 'jmapp'
        app.secret_key = 'secret'
        jinja.init (jinja_env=app.jinja_env)
        try: cfg = config.cfgRead ('config.ini', 'config-pvt.ini')
        except IOError:
            print ("Unable to load config.ini file(s)", file=sys.stderr)
            flask.abort (500)
        app.config['CFG'] = cfg

App = flask.Flask (__name__, static_folder='./static',
                             template_folder='./tmpl')
app_config (App)

def prereq():
        G.user = Session.get ('user_'+G.svc)
        L('jmapp.prereq').debug("cfg files: %s"%G.cfg.get('status','cfg_files'))
          # The following logging statement should usually be disabled
          # because the output contains database login credentials.
          # Enable for debugging only.
        #L('jmapp.prereq').debug("svc=%s; cfg=%r"
        #                        % (G.svc,dict(G.cfg['db_'+G.svc])))
        G.dbcur = jdb.dbOpenSvc (G.cfg, G.svc)

@App.before_request
def before_request():
        L('view.before_request').debug("For endpoint %s" % Rq.endpoint)
        G.cfg = App.config['CFG']
        G.svc = fv ('svc') or G.cfg.get('web','DEFAULT_SVC') or 'jmdict'
        if Rq.endpoint in ('login','logout','static'): return
        prereq()

@App.route ('/')
def home():
        vLogEntry()
        return Redirect (Url('srchformq'))

@App.route ('/login', methods=['POST'])
def login():
        vLogEntry()
        return_to = fv ('this_page')
        if not return_to.startswith ('/'): flask.abort(400)
        srvlib.login_handler (G.svc, G.cfg)
        return flask.redirect (return_to)

@App.route ('/edform.py')
def edform():
        vLogEntry()
        return Render ('edform.jinja')

@App.route ('/entr.py')
def entr():
        vLogEntry()
        elist, qlist, disp = fvn('e'), fvn('q'), fv('disp')
        data,errs = rest.v_entr (elist, qlist, disp, cur=G.dbcur)
        return Render ('entr.jinja',
                        entries=data, disp=disp,
                        svc=G.svc, cfg=G.cfg, dbg=fv('dbg'), user=G.user,
                        this_page=Rq.full_path)

@App.route ('/help.py')
def help():
        vLogEntry()
        return Render ('help.jinja')

@App.route ('/helpq.py')
def helpq():
        vLogEntry()
        return Render ('helpq.jinja')

@App.route ('/srchformq.py')
def srchformq():
        vLogEntry()
        data, errs = rest.v_srchformq()
        corp = srvlib.reshape (data, 10)
        return Render ('srchformq.jinja', src=corp,
                        svc=G.svc, cfg=G.cfg, dbg=fv('dbg'), user=G.user,
                        this_page=Rq.full_path)

@App.route ('/srchres.py')
def srchres():
        vLogEntry()
        sqlp = (fv ('sql') or '')
        p0, pt = int(fv('p0') or 0), int(fv('pt') or -1)
        so = srvlib.extract_srch_params (Rq.args)
        rs, pt, stats
            = srvlib.srchres (G.dbcur, so, sqlp, pt, p0, G.cfg, G.user)
        return Render ("srchres.jinja",
            results=rs, p0=p0, pt=pt, stats=stats, so=so, sql=sqlp,
            svc=G.svc, cfg=G.cfg, dbg=fv('dbg'), user=G.user,
            this_page=Rq.full_path)

@App.route ('/submit.py', methods=['POST'])
def submit():
        vLogEntry()
        return Render ('submitted.jinja')

@App.route ('/updates.py')
def updates():
        vLogEntry()
        return Render ('updates.jinja')


if __name__ == '__main__': main()
