#!/usr/bin/env python3
# Copyright (c) 2021 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# Run the JMdictDB WSGI/Flask app under Flask's built-in debug server.
#
# If an argument is given, it is name of the config file to be used.
# Otherwise, if the environment variable JMAPP_CFGFILE is defined, it
# is used as the config file.  Relative filenames are relative to the
# current directory as usual.  If neither of those case hold, the config
# file used will be "../jmdictdb/lib/cfgapp.ini", relative to this file's
# location.

import sys, os, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'

from jmdictdb import jmapp
App = jmapp.App

DEFAULT_CFGFILE = '../jmdictdb/lib/cfgapp.ini'  # Relative to our directory.

def main():
        p = os.path      # For brevity.
        if len (sys.argv) > 1: cfgfile = sys.argv[1]
        else: cfgfile = os.environ.get('JMAPP_CFGFILE')
        if not cfgfile:
            d = p.dirname (__file__)
            cfgfile = p.normpath (p.join (d, DEFAULT_CFGFILE))
        print ("Using cfgfile: %s" % cfgfile, file=sys.stderr)
        os.environ['JMAPP_CFGFILE'] = cfgfile
        App.jinja_env.auto_reload = True
        App.config['TEMPLATES_AUTO_RELOAD'] = True
        App.run (host='0.0.0.0', debug=True)

main()
