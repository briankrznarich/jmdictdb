# This is the wsgi shim between the app and the server.
# The Apache server should be configured to point to this file
# with something like the following in it's configuration file(s).
#
#  WSGIDaemonProcess jmapp processes=1 threads=5
#  WSGIProcessGroup jmapp
#  WSGIScriptAlias /jmapp /home/stuart/devel/jdb/jmapp/app/jmapp.wsgi
#  <Directory /home/stuart/devel/jdb/jmapp/app/>
#    Require all granted
#    </Directory>
#
# The two instances of the directory:
#   /home/stuart/devel/jdb/jmapp/app/
# shown ABOVE should be changed to the directory where this
# jmapp.wsgi file actually resides.

import sys, os
appdir, _ = os.path.split (os.path.abspath(__file__))
sys.path.insert (0, appdir)
from jmapp import App as application
