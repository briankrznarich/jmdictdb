The files in this subdirectory are an implementation of the
JMdictDB web server using the Flask framework rather than CGI.
It currently will run directly from the development directories
(i.e. requires no "installation").

To run with Flask's internal development sever:
===============================================
  $ cd <jmdictdb-root-dir>/app/
  $ python3 jmapp.py

The server will then be available at http://localhost:5000
Please note that the server started in "debug" mode and is
not secure -- access should be limited to trusted users.

To run with Apache2 and mod_wsgi:
===============================================
The site's Apache2 web server is assumed to have the mod_wsgi
module installed and enabled.

Create an Apache2 configuration, either added to the site's
main Apache2 configuration file or as a separate file in a
configuration directory:

  WSGIDaemonProcess jmapp processes=1 threads=5
  WSGIProcessGroup jmapp

  WSGIScriptAlias /jmapp <jmdictdb-root-dir>/app/jmapp.wsgi
  <Directory <jmdictdb-root-dir>/app>
      Require all granted
      </Directory>

Replace the two occurances of "<jmdictdb-root-dir>" above
with the actual path to the jmdictdb software root directory.
The "processes and "threads" settings can be adjusted to meet
site requirements.

After a change is made to the jmapp code, the wsgi daemon
process(es) can be restarted to make the server aware of the
changes (without the need to restart the entire server) by
'touch'ing jmapp.wsgi.

The Flask server code is incomplete and under active development
and has not been checked for security holes -- use at your own
risk.
