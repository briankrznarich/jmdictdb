#!/usr/bin/env python3
# Copyright (c) 2020 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# This web page will show some details about the CGI/Python execution
# environment and is useful for diagnosing library location confusions.

import sys, cgi, cgitb, html, os
try: import pkgpath.py  # Make jmdictdb package available on sys.path.
except ImportError: pass

try: import jmdictdb
except ImportError:
        print ("Content-type: text/plain\n")
        print ("Failed to import jmdictdb")
        print ("Current directory is: %s" % os.getcwd())
        print ("sys.path is: %r" % sys.path)
        sys.exit(0)
from jmdictdb import jdb, config, jmcgi, dbver

def main():
        errs = []; data = {}
          # The canonical definition the CGI config file location is
          # defined by the variable CONFIG_FILE in module jmcgi.
        CONFIG_FILE = jmcgi.CONFIG_FILE
        cfg = config.cfgRead (CONFIG_FILE)
        def_svc = cfg['web'].get ('DEFAULT_SVC', 'jmdict')
        if def_svc.startswith ('db_'): def_svc = def_svc[3:]
        form = cgi.FieldStorage()
        svc = form.getfirst ('svc') or def_svc
        cur = jdb.dbOpenSvc (cfg, svc, nokw=True, noverchk=True)
        cur.execute ("SELECT id FROM dbx WHERE active ORDER BY ts")
        rs = cur.fetchall()
        data = [('svc', svc),
            ('DB updates',   ', '.join ((x[0] for x in rs))),
            ('API requires', ', '.join (("%0.6x"%x for x in dbver.DBVERS))),
            ('cwd',          os.getcwd()),
            ('CGI location', os.path.dirname (os.path.abspath (__file__))),
            ('Pkg location', os.path.dirname (os.path.abspath (jdb.__file__))),
            ('sys.path',     '%r' % sys.path), ]
        row_tmpl = "    <tr><td>%s:</td><td>%s</td></tr>"
        rows = [row_tmpl%(title.replace(' ','&nbsp;'),html.escape(value))
                         for title, value in data]
        htmltxt = Page % (CONFIG_FILE, '\n'.join (rows))
        print ("Content-type: text/html\n\n", htmltxt)

Page = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <title>JMdictDB - Configuration details</title>
  </head>
<body>
  Using config file %s<br><br>
  <table>
    %s
    </table>'''

if __name__ == '__main__': main()
