#!/usr/bin/env python3
# Copyright (c) 2020 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# This web page will show some details about the CGI/Python execution
# environment and is useful for diagnosing library location confusions.

# WARNING: The page generated by this view will show all items from the
# config.ini files, including those in the config-pvt.ini file (other
# than the db_* sections what are optionally supressed).

# NOTE: this view returns raw HTML rather than data to be rendered
# via a Jinja template.
# Note that unlike CGI scripts which read the jmdictdb config file on
# every html request, the jmapp script reads the config file only once
# when the webserver starts its Python subinterpreter and that configuration
# is used for all following html requests including this one.
# A restart of the Python subinterpreter can be requested without a full
# webserver restart by 'touch'ing the jmapp.wsgi file.

import sys, configparser, html, os, pdb
try: import pkgpath.py  # Make jmdictdb package available on sys.path.
except ImportError: pass

Row_tmpl = "    <tr><td>%s</td><td>%s</td></tr>"

jmdictdb = jdb = config = jmcgi = None
Failed_import = None
  # Following imports are in order of depencies: if import of jmdictdb fails,
  # a the following ones will fail too; if jdb fails, so won't config ands
  # jmcgi.  So no point trying a later import if earlier one fails and we
  # need only record the name of the first to fail.
try: import jmdictdb
except ImportError: Failed_import = 'jmdictdb'
if not Failed_import:
    try: from jmdictdb import jdb
    except ImportError: Failed_import = 'jdb'
if not Failed_import:
    try: from jmdictdb import config
    except ImportError: Failed_import = 'config'
if not Failed_import:
    try: from jmdictdb import jmcgi
    except ImportError: Failed_import = 'jmcgi'

def main():
        ex_rows = gen_ex_section()
        cfg_rows = gen_cfg_section()
        env_rows = gen_env_section()
        htmltxt = Page % (ex_rows, cfg_rows, env_rows)
        print ("Content-type: text/html\n\n", htmltxt)

  # NOTE: Be mindful of the distinction between cfg.get()
  # and cfg_get() below.

def gen_ex_section():
        exdata = []
        exdata.append (('cwd', os.getcwd()))
        exdata.append (('cgi location',
                     os.path.dirname (os.path.abspath (__file__))))
        exdata.append (('python version', '%r' % sys.version))
        exdata.append (('sys.path', '%s' % sys.path))
        if jdb is not None:
            try: pkg_loc = os.path.dirname (os.path.abspath (jdb.__file__))
            except Exception as e: pkg_loc = e.__class__.__name__+": "+str(e)
            exdata.append (('pkg location', pkg_loc))
        else: exdata.append (('pkg location', "- (import of %s module failed)" % Failed_import))
        if jmdictdb is not None:
            try: pkg_ver =  getattr (jmdictdb, '__version__', '<none>')
            except Exception as e: pkg_ver = e.__class__.__name__+": "+str(e)
            exdata.append (('pkg version', pkg_ver))
        else: exdata.append (('pkg version', "- (import of %s module failed)" % Failed_import))
        ex_rows = '\n'.join ([Row_tmpl % (key.replace(' ','&nbsp;'), html.escape(value))
                              for key,value in exdata])
        return ex_rows

def gen_cfg_section ():
        cfgdata = []
        if Failed_import:
            cfgdata.append (('', "- (import of %s module failed)" % Failed_import))
        else:
              # The canonical definition the CGI config file location is
              # defined by the variable CONFIG_FILE in module jmcgi.
            try: cfg = config.cfgRead (jmcgi.CONFIG_FILE)
            except Exception as e:
                cfgdata.append ((jmcgi.CONFIG_FILE, e.__class__.__name__+": "+str(e)))
            else:
                cfgdata.append (('config dir', cfg.get ('status', 'cfg_dir')))
                cfgdata.append (('config files',
                                cfg.get ('status', 'cfg_files')))
                cfgdata.append (cfg_get (cfg, 'logging', 'LOG_FILENAME'))
                cfgdata.append (cfg_get (cfg, 'web', 'STATUS_DIR'))
                cfgdata.extend (cfg_svcs (cfg))
        cfg_rows = '\n'.join ([Row_tmpl % (key.replace(' ','&nbsp;'),
                                           html.escape(value).replace("\n","<br>"))
                              for key,value in cfgdata])
        return cfg_rows

def gen_env_section ():
        env_rows = '\n'.join ([Row_tmpl % (key.replace(' ','&nbsp;'), html.escape(value))
                              for key,value in sorted (os.environ.items())])
        return env_rows

def cfg_get (cfg, section, key):
        tag = "[%s] %s" % (section, key)
        try: value = cfg.get (section, key)
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            return tag, str(e)
        return tag, value

def cfg_svcs (cfg):
        results = [];  warns = []
        default_svc = cfg.get ('web', 'DEFAULT_SVC')
        results.append (('[web] DEFAULT_SVC', default_svc))
        svcs = [x[3:] for x in cfg.sections() if x.startswith ('db_')]
          # Report if 'db_session is missing but don't explicitly report
          # its presence.
        if 'session' in svcs: svcs.remove ('session')
        else: warns.append (('WARNING', "'session' not in svc's"))
        if default_svc not in svcs:
            warns.append (('WARNING', "default svc not in svc's"))
        results.append (("services", (', '.join(svcs))))
        return results + warns

  # Don't forget to double "%" characters below.
Page = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <title>JMdictDB - Configuration details</title>
  <style>
    body         {font-family: arial;}
    .item        {background: #E8FFF0;
                 border-style: solid; border-width: thin;
                 margin: 5px; padding: 10px}
    .notes      {font-size: 75%%;}
    .err {color:red;} td {vertical-align: top;} .pre {white-space: pre;}
    </style>
  </head>
<body>
  <p>Execution info:
  <table class="item">
    %s
    </table>
  <p>Config info:<br>
  <table class="item">
    %s
    </table>
    <span class="notes">Note: No <b>LOG_FILENAME</b> value means log
      output to stderr.</span>
  <p>Environment info:<br>
  <table class="item">
    %s
    </table>
'''
main()
