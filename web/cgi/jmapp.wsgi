# This is the wsgi shim between the web server server and the jmapp app.
# The Apache server should be configured to point to this file
# with something like the following in it's configuration file(s).
#
#   WSGIDaemonProcess jmapp processes=2 threads=4 \
#                       display-name=apache2-jmapp \
#                       locale=en_US.UTF-8 lang=en_US.UTF-8
#   WSGIProcessGroup jmapp
#   WSGIScriptAlias /jmapp  <<directory>>\
#                   process-group=jmapp
#
# <<directory>> should be replaced the full path to this (jmapp.wsgi)
# file, e.g., /srv/jmdictdb/cgi-bin/jmapp.wsgi.
# Note that the directory must be configured in Apache to allow access
# just like any other script directory to avoid a 403 (permission denied)
# error.  That configuration in not shown here as we assume this script
# will live in the cgi scripts directory which has presumably already
# been configured.  Note that this script will not execute if requested
# as a cgi script in a url (produces a "bad format" error.)

# When mod_wsgi starts a jmapp Python process, it imports a callable
# named "application" from us.  Our job is to provide an application
# object for it to import.  We get one from the system-installed
# jmdictdb package.

import sys, os
import jmdictdb

  # The default location of the jmapp config file, if not
  # explicitly specified by the environment variable JMAPP_CFGFILE,
  # is in ../lib/cfgapp.ini relative to the cgi directory (were we
  # live).  Unfortunate neither apache, mod_wsgi, or flask seem to
  # provide a means of locating our directory.  So we do so here...

if not os.environ.get('JMAPP_CFGFILE'):
    our_directory = os.path.dirname (__file__)
    default_cfgfile = os.path.normpath (os.path.join (
                          our_directory, '../lib/cfgapp.ini'))
    os.environ['JMAPP_CFGFILE'] = default_cfgfile

from jmdictdb.jmapp import App as application
