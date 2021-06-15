#!/usr/bin/env python3
# Copyright (c) 2021 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# Run the JMdictDB WSGI/Flask app under Flask's built-in debug server.
#
# If an argument is given, it is name of the config file to be used.
# Otherwise, if the environment variable JMAPP_CFGFILE is defined, it
# is used as the config file.  A relative filename given on the command
# line is relative to the current working directory; a filename given
# by environment variable is relative to the location of this file.
# If the config file name is given by either command line or environment
# variable it will default to  '../web/lib/cfgapp.ini' relative to this
# file's location.

import sys, os, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
p = os.path     # For brevity

  # Following should be defined relative to run-jmapp.py's directory.
DEFAULT_CFGFILE = '../web/lib/cfgapp.ini'

def main():
        if len (sys.argv) > 1: cfgfile = abspath (sys.argv[1])
        else: cfgfile = os.environ.get('JMAPP_CFGFILE')
        if not cfgfile: cfgfile = DEFAULT_CFGFILE
        cfgfile = abspath (cfgfile, p.dirname (__file__))
        print ("Using cfgfile: %s" % cfgfile, file=sys.stderr)
        os.environ['JMAPP_CFGFILE'] = cfgfile
          # The jmdictdb.jmapp import MUST be done after JMAPP_CFGFILE is set.
        from jmdictdb import jmapp
        App = jmapp.App
        App.jinja_env.auto_reload = True
        App.config['TEMPLATES_AUTO_RELOAD'] = True
        App.run (host='0.0.0.0', debug=True)

  #	FIXME: This function is a duplicate of config.abspath()
def abspath (path, relative_to=None):
          # Like os.path.abspath() but allows 'path' to be relative
          # to an arbitrary directory.
        if not relative_to: relative_to = os.getcwd()
        fn = p.normpath (p.join (p.abspath (relative_to), path))
        return fn
main()
