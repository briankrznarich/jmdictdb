#!/usr/bin/env python3
# Copyright (c) 2021 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later
#!/usr/bin/env python3
# Run the JMdictDB WSGI/Flask app under Flask's built-in debug server.

import sys, os, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
p = os.path     # For brevity

  # Following should be defined relative to the JMdictDB root directory.
DEFAULT_CFGFILE = 'web/lib/jmdictdb.ini'

def main():
        args = parse_cmdline()
        cfgfile = args.cfgfile or DEFAULT_CFGFILE
        cfgfile = abspath (cfgfile, p.join (p.dirname (__file__), '..'))
        print ("Using cfgfile: %s" % cfgfile, file=sys.stderr)
        os.environ['JMDICTDB_CFGFILE'] = cfgfile
          # The jmdictdb.flaskapp import MUST be done after
          # JMDICTDB_CFGFILE is set.
        from jmdictdb import flaskapp
        App = flaskapp.App
        App.jinja_env.auto_reload = True
        App.config['TEMPLATES_AUTO_RELOAD'] = True
        App.run (host=args.ip, port=args.port, debug=args.debug)

def abspath (path, relative_to=None):
          # Like os.path.abspath() but allows 'path' to be relative
          # to an arbitrary directory.
          #FIXME: This function is a duplicate of config.abspath()
        if not relative_to: relative_to = os.getcwd()
        fn = p.normpath (p.join (p.abspath (relative_to), path))
        return fn

import argparse
def parse_cmdline():
        p = argparse.ArgumentParser (description=
            "Run JMdictDB with the Flask development server.")
        p.add_argument ('cfgfile', nargs='?',
            help="JMdictDB configuration file to use (relative to the root "
                "of the JMdictDB directory).  If not given a default value "
                "of %s will be used." % DEFAULT_CFGFILE)
        p.add_argument ('-p', '--port', type=int, default=5000,
            help="Port number (default is 5000).")
        p.add_argument ('-i', '--ip', default='127.0.0.1',
            help="IP address for server to listen on.  Default is 127.0.0.1 "
                "(localhost).  Use 0.0.0.0 to listen on all public IP "
                "addresses.")
        p.add_argument ('-d', '--debug', action='store_true', default=False,
            help="Run in 'debug' mode: if an exception occurs an interactive "
                "debugging traceback page will be displayed")
        args = p.parse_args()
        return args

main()
