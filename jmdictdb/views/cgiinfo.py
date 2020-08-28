# Copyright (c) 2020 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# This web page will show some details about the CGI/Python execution
# environment and is useful for diagnosing library location confusions.
# NOTE: this view return raw HTML rather than data to be rendered
# via a Jinja template.

import sys, os, cgi, pdb
import flask
try: import pkgpath.py  # Make jmdictdb package available on sys.path.
except ImportError: pass

def view (params):
        try: import jmdictdb
        except ImportError:
            content = """\
                <h3>Failed to import jmdictdb</h3>
                Current directory is: %s<br>
                sys.path is: %r"""  % (os.getcwd(), sys.path)
            return Page % content
        from jmdictdb import jdb, config, dbver

        info = {};  def_svc = None
        svc = params.get ('svc')
        cfgloc = params.get ('cfgloc')
        info['API requires'] = ', '.join (("%0.6x"%x for x in dbver.DBVERS))
        info['cwd'] = os.getcwd()
        info['view location'] = os.path.dirname (os.path.abspath (__file__))
        info['jmdictdb location'] \
                = os.path.dirname (os.path.abspath (jdb.__file__))
        info['sys.path'] = '%r' % sys.path

        info['config location'] = repr (cfgloc)    # Use repr() in case value is None.
        try:
            cfg = config.cfgRead ('config.ini', 'config-pvt.ini', cfgloc)
        except OSError as e:
            info['config files'] = '<span class="err">%s</span>' % str(e)
            cfg = None
        else: 
            info['config files'] = cfg['status']['cfg_files']
            def_svc = cfg['web'].get ('DEFAULT_SVC', 'jmdict')
            if def_svc.startswith ('db_'): def_svc = def_svc[3:]

        if not svc: svc = def_svc
        info['svc'] = svc if svc else "svc not specified and default svc not available."
        if svc and cfg:
            cur = jdb.dbOpenSvc (cfg, svc, nokw=True, noverchk=True)
            cur.execute ("SELECT id FROM dbx WHERE active ORDER BY ts")
            rs = cur.fetchall()
            info['DB updates'] = ', '.join ((x[0] for x in rs))
        elif not cfg:
            info['DB updates'] = '<span class="err">Can\'t read database, no config file available.</span>'
        else:
            info['DB updates'] = '<span class="err">Cant read database, no \'svc\' available.</span>'
 
        order = ('cwd','sys.path','jmdictdb location','view location',
                 'config location','config files','svc','DB updates','API requires')

        row_tmpl = "    <tr><td>%s:</td><td>%s</td></tr>"
        rows = [row_tmpl % (key.replace(' ','&nbsp;'), info[key])
                for key in order]
        rows.extend ([row_tmpl % (key.replace(' ','&nbsp;'), info[key])
                      for key in info.keys() if key not in order])
        html = Page % '\n'.join (rows)
        return html

Page = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <title>JMdictDB - Configuration details</title>
  <style>.err {color:red} td {vertical-align: top;}</style>
  </head>
<body>
  <table>
    %s
    </table>'''
