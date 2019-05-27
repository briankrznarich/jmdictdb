import sys, os, subprocess, re, pdb
import jdb, db

# This module defines a _DBmanager class and creates a single
# global instance of it that test modules may import and use in
# order to share a common database(s) without reloading it for
# each test.  This matters because the "jmtest01" database takes
# some 15+ seconds to reload... way too long to do in each of
# hundreds of tests.
# Sharing a database between tests requires some displine on the
# part of the tests not to make any changes that will affect other
# tests and even with that goal there is some risk it will happen
# inadvertently.  But it seems a fair tradeoff given the complexity
# of database interactions and the difficultly of mocking them as
# well as the situation that many tests are more functional tests
# than pure unit tests.
#
# The main user callable method of DBmanager is
#
#    .use (dbname, filename)
#
#    dbname -- Name of a test database.
#    filename -- Name of a file containing sql commands needed to
#      create the database.  This is typically produced by running
#      Postgresql's 'pg_dump' command on a prototype test database.
#
# When .use() is called it will check if the database 'dbname' is
# already loaded in the Postgresql server by:
# 1) Checking whether a database named 'dbname' was loaded from
#    file 'filename' previously in this invocation of the test
#    program.
# 2) If (1) is not true, it will check if as database named 'dbname'
#    exists on the server, and if so, if it has a table, created by
#    DBmanager, that contains that name of 'filename'.
# If (1) and (2) are both true, .use() assumes the existing 'dbname'
# database is the desired one and will return a jdb.dbOpen() cursor
# to it.  If either (1) or (2) is false, .use() will drop any existing
# 'dbname' database and create it by restoring from 'filename' (which
# should be a "plain" sql dump produced by 'pg_dump' of the virgin
# test database.)
# Check (2) allows a database to be reused between invocations of the
# test program.
# A failure when loading will result in an exception.

class _DBmanager():
    def __init__ (self): self.loaded = {}
    def use (self, dbname, filename, force_reload=False):
        if force_reload or not self.is_loaded (dbname, filename):
            print ('Loading database "%s" from %s' % (dbname, filename),
                   file=sys.stderr)
              # self.load() will raise CalledProcessError if it fails
              # which we let propagate up to our caller.
            self.load (dbname, filename)
            self.loaded[dbname] = filename
        cur = jdb.dbOpen (dbname)
        return cur
    def is_loaded (self, dbname, filename):
        if dbname in self.loaded and self.loaded[dbname]==os.path.abspath:
            return True
        try:
            dbconn = db.connect (dbname)
            rs = db.query (dbconn, "SELECT * FROM testsrc;")
        except db.Error as e:
            if not re.search ('(relation|database) \S+ does not exist',
                              str(e)):
                print ("jmdb: validate failed: %s" % e, file=sys.stderr)
            return False
        if len(rs) != 1 or len(rs[0]) != 1: return False
        return rs[0][0] == os.path.abspath (filename)
    def load (self, dbname, filename):
          # Reload a fresh copy of a test database into the postgresql
          # database server.
          # For safely (to avoid accidently blowing away a production
          #  database) we require the test database name to start with
          #  "jmtest".
          # The user running this must:
          #  - have "create database" permission on the server.
          #  - have a suitable .pgpass set up that allows access to the
          #    server without needing to interactively supply a password.
        if not dbname.startswith ("jmtest"):
            raise RuntimeError ('reloaddb: dbname must start with "jmtest"')
        absfn = os.path.abspath (filename)
        def run (cmd):
              # The "stdout" argument will send stdout to /dev/null; we
              # want to supress all the notice-level messages from psql
              # but errors will be written to stderr so they will be shown.
            subprocess.run (cmd, shell=True, check=True,
                                 stdout=subprocess.DEVNULL)
          # The PGOPTIONS environment variable used below supresses some
          # Postgresql NOTICE messages that would otherwise appear.
        run ('PGOPTIONS="--client-min-messages=warning" '
               'dropdb --if-exists %s' % dbname)
        run ('createdb %s' % dbname)
          # The -v option tells psql to stop immediately and exit with
          # status 3 if there is an error.  Without it, psql will trudge
          # on, exiting with status 0 unless the error is fatal.
        run ("psql -d %s -f %s -v 'ON_ERROR_STOP=1'" % (dbname, absfn))
        run ('PGOPTIONS="--client-min-messages=warning" '
                'psql -d %s -c '
                '"DROP TABLE IF EXISTS testsrc;'
                ' CREATE TABLE testsrc (filename TEXT);'
                ' INSERT INTO testsrc VALUES(\'%s\');"'
                % (dbname, os.path.abspath (filename)))

  # Create a single instance of _DBmanager that will be shared by
  # all tests run in a single invocation of a unittest test program.
  # This allows any database(s) loaded to be reused by all tests,
  # regardless of the test class or module they are in.
DBmanager = _DBmanager()
