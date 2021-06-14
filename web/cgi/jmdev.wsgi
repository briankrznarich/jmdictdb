# This wsgi script will run the jmapp package from the
# development directory rather than from installed jmdictdb
# package as jmapp.wsgi does.

import sys, os
  # We are (expected to be) located in the development jmdictdb
  # in web/cgi/ so two levels up is our root directory.  Add our
  # root directory to the front of sys.path so our (development
  # version) of the jmdictdb package will be found first when
  # importing.
our_root = os.path.normpath (os.path.dirname (__file__) + '/../..')
if our_root not in sys.path: sys.path[0:0] = [our_root]

  # The default location of the jmapp config file, if not
  # explicitly specified by the environment variable JMAPP_CFGFILE,
  # is in ../lib/cfgapp.ini relative to the cgi directory (were we
  # live).  Unfortunate neither apache, mod_wsgi, or flask seem to
  # provide a means of locating our directory.  So we do so here...

if not os.environ.get('JMAPP_CFGFILE'):
    default_cfgfile = os.path.normpath (os.path.join (
                          our_root, 'web/lib/cfgapp.ini'))
    os.environ['JMAPP_CFGFILE'] = default_cfgfile

from jmdictdb.jmapp import App as application
