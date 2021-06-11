#!/usr/bin/env python3
# Copyright (c) 2021 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# run-app.py -- Run the JMdictDB WSGI/Flask application under Flask's
# built-in debug server.

import sys, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'

from jmdictdb import jmapp
App = jmapp.App

def main():
        global Cfgfile
        App.jinja_env.auto_reload = True
        App.config['TEMPLATES_AUTO_RELOAD'] = True
        App.run (host='0.0.0.0', debug=True)

main()
