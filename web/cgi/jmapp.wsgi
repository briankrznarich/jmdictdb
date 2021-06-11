# This is the wsgi shim between web server server and the jmapp app.
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
# Note that the directory must be configured in Apache to allow
# access just like any other script directory to avoid a 403 (permission
# denied) error.

# When mod_wsgi starts a jmapp Python process, it imports a callable
# named "application" from us.  Our job is to provide an application
# object for it to import.  We get one from the system-installed
# jmdictdb package.

import jmdictdb
from jmdictdb.jmapp import App as application
