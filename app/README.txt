The files in this subdirectory are an implementation of the
JMdictDB web server using the Flask framework rather than CGI.
It currently will run directly from the development directories
in either of two modes: using Flask's built-in server or using
a WSGI server such as Apache with mod-wsgi.  The former mode
is appropriate  only for development and testing; the latter
should be used for production deployments.

The Flask server code is incomplete and under active development.


To run with Flask's internal development server:
===============================================
  $ cd <jmdictdb-root-dir>/app/
  $ python3 jmapp.py

<jmdictdb-root-dir> is the path to the jmdictdb software root
directory.  The server will be available at:

  http://localhost:5000

Please note that the development server is not suitable for
production use and is started in "debug" mode which is not
secure -- access should be limited to trusted users.

By default the jmapp server will look for its configuration
file(s) in web/lib/cfgapp.ini and web/lib/cfgapp-pvt.ini.
The location (the web/lib/ part) can be changed with the
environment variable JMAPP_CFGDIR.
There is currently no way to change the config file(s) name.
If a log file is not specified in the config file, logging
output will be written to srderr.


To run with Apache-2.4 and mod_wsgi:
===============================================
The site's Apache web server is assumed to have the mod_wsgi
module installed and enabled.

Create an Apache2 configuration, either added to the site's
main Apache2 configuration file or as a separate file in a
configuration directory:

  WSGIDaemonProcess jmapp processes=2 threads=4 \
                          display-name=apache2-jmapp
  WSGIProcessGroup jmapp
  WSGIScriptAlias /jmapp /home/stuart/devel/jdb/jb/app/jmapp.wsgi \
                  process-group=jmapp
  <Directory /home/stuart/devel/jdb/jb/app>
      Require all granted
      </Directory>
    # Serve static files directly without using the app.
  Alias "/jmapp/static/" "/home/stuart/devel/jdb/jb/app/static/"
  <Directory /home/stuart/devel/jdb/jb/app/static/>
      DirectoryIndex disabled
      Require all granted
      </Directory>

Replace the four occurances of "<jmdictdb-root-dir>" above
with the actual path to the jmdictdb software root directory.
The "processes and "threads" settings can be adjusted to meet
site requirements.

After restarting the Apache web server, the jmapp service
will be available at:

  http://localhost/jmapp/

After a change is made to the jmapp code, the wsgi daemon
process(es) can be restarted to make the server aware of the
changes (without the need to restart the entire server) by
'touch'ing jmapp.wsgi.

When run by a WSGI server, jmapp looks for its configuration
file(s) in /usr/local/etc/jmdictdb/cfgapp.ini and cfgapp-pvt.ini.
The location of the config files (the /usr/local/etc/jmdictdb/
part) can be changed with the environment variable JMAPP_CFGDIR.
There is currently no way to change the config file(s) name.
If a log file is not specified in the config file, logging output
will be written to srderr which generally means it will end up
in the web server's error log file.
