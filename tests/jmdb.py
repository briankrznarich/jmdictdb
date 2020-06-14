import sys, os, subprocess, hashlib, re, pdb
from jmdictdb import jdb, db

# This module provides support for JMdictDB tests in two forms:
# - A _DBmanager class for loading tests databases.
# - A JEL parser for conveniently constructing Entr objects.

#-----------------------------------------------------------------------------
# Define a _DBmanager class and create a single
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
# already loaded in the Postgresql server by checking a hash value
# stored in the database when it was first loaded into the database
# server; it's value must match the hash of the filename we want to
# load here.  If it doesn't match we presume the database was loaded
# from some other file, drop the database and reload from our file.
# A failure when loading will result in an exception.

HASH_METHOD = 'sha1'

class _DBmanager():
    def __init__ (self): pass
    def use (self, dbname, filename, force_reload=False):
        if force_reload or not self.is_loaded (dbname, filename):
            print ('Loading database "%s" from %s' % (dbname, filename),
                   file=sys.stderr)
              # self.load() will raise CalledProcessError if it fails
              # which we let propagate up to our caller.
            self.load (dbname, filename)
        cur = jdb.dbOpen (dbname)
        return cur
    def is_loaded (self, dbname, filename):
        try:
            dbconn = db.connect (dbname)
            rs = db.query (dbconn, "SELECT * FROM testsrc;")
        except db.Error as e:
            if re.search ('database \S+ does not exist', str(e)):
                print ("jmdb: test database %s not found" % dbname,
                       file=sys.stderr)
                return False
            if re.search ('relation \S+ does not exist', str(e)):
                print ("jmdb: no signature table found", file=sys.stderr)
                return False
              # If there is some other error it will probabably reoccur
              # so re-raise it; since we were probably called from a
              # unittest setUpModule() method, the exception will pre-
              # emptively cancel any tests in that module.
            raise
        if len(rs) != 1 or len(rs[0]) != 3:
            print ("jmdb: unexpected signature data", file=sys.stderr)
            return False
          # Code below is commented out in order to ignore the testdb filename
          # and rely only on the hash to identify the expected test database.
          # The motivation is that tests are often run from repository clones
          # causing the filename difference to result in an unnecessary reload.
        #if rs[0][0] != os.path.abspath (filename):
        #    print ("jmdb: filename mismatch", file=sys.stderr)
        #    return False
        if rs[0][2] != self.hash (HASH_METHOD, filename):
            print ("jmdb: hash mismatch", file=sys.stderr)
            return False
        return True
    def load (self, dbname, filename):
          # Reload a fresh copy of a test database into the postgresql
          # database server.  After loading the database we store the
          # a hash of the load file's contents in a table, "testsrc",
          # in the database.  Subsequent requests to use the database
          # will call .is_loaded() to check the stored hash against the
          # actual file hash to confirm that the requested database is
          # already loaded and need not be reloaded.
          # For safely (to avoid accidently blowing away a production
          # database) we require the test database name to start with
          # "jmtest".
          # The user running this must:
          #  - have "create database" permission on the server.
          #  - have a suitable .pgpass set up that allows access to the
          #    server without needing to interactively supply a password.
        if not dbname.startswith ("jmtest"):
            raise RuntimeError ('jmdb: dbname must start with "jmtest"')
        absfn = os.path.abspath (filename)
        hash = self.hash (HASH_METHOD, filename)
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
                ' CREATE TABLE testsrc (filename TEXT, method TEXT, hash TEXT);'
                ' INSERT INTO testsrc VALUES(\'%s\', \'%s\', \'%s\');"'
                % (dbname, os.path.abspath (filename), HASH_METHOD, hash))
    def hash (self, method, filename):
        with open (filename, 'rb') as f:
            h = hashlib.new (method, f.read())
        return (h.digest()).hex()

  # Create a single instance of _DBmanager that will be shared by
  # all tests run in a single invocation of a unittest test program.
  # This allows any database(s) loaded to be reused by all tests,
  # regardless of the test class or module they are in.
DBmanager = _DBmanager()

#-----------------------------------------------------------------------------
# This is a JEL parser for use in creating Entr objects for
# tests.  Creating them using JEL is more convenient and concise
# then constructing them from the base objects by hand.

import jellex, jelparse
class JelParser:
    def __init__(self, dbcursor=None,
                       src=None, stat=None, unap=None, dfrm=None,
                       debug=False):
          # 'dbcursor' is an open JMdictDB cursor such as returned
          # by jdb.dbOpen() and used when resolving any xrefs in the
          # parsed entry.  It is not required if .parse() wil be
          # called with 'resolve' set to false.
          # 'src', 'stat' and 'unap' are defaults value to use in
          # the Entr objects if values weren't supplid in the JEL
          # text.
          # NOTE: while 'dbcursor' is optional here, jdb.dbOpen()
          # *must* be called prior to executing .parse() since the
          # latter requires the jdb.KW structure to be initialized,
          # which jdb.dbOpen() does.

        self.lexer, tokens = jellex.create_lexer ()
        self.parser = jelparse.create_parser (self.lexer, tokens)
        self.dbcursor,self.src,self.stat,self.unap,self.dfrm,self.debug\
           = dbcursor, src, stat, unap, dfrm, debug
    def parse (self, jeltext, resolve=True, augment=True, dbcursor=None,
               src=None, stat=None, unap=None, dfrm=None):
        jellex.lexreset (self.lexer, jeltext)
          #FIXME? why do we give the jeltext to both the lexer
          # and the parser?  One of the other should be sufficient.
        entr = self.parser.parse (debug=self.debug)
        if not entr.src: entr.src = src or self.src
        if not entr.stat: entr.stat = stat or self.stat
        if entr.unap is None:   # 'unap' may be False
            entr.unap = unap if unap is not None else self.unap
        if not entr.dfrm: entr.dfrm = dfrm or self.dfrm
        if resolve:
            if not dbcursor: dbcursor = self.dbcursor
            if not dbcursor: raise RuntimeError (
                "Xref resolution requested but no database available")
            #FIXME: temporary adjustment for different branches:
              # Use following line for branch 'xrslv".
            #jdb.xresolv (dbcursor, entr)
              # Use following line for branch "master".
            jelparse.resolv_xrefs (dbcursor, entr)
            if augment:     # Augment the xrefs...
                  # These calls attach additional info to the xrefs that
                  # is needed when when displaying them.  Without it some
                  # information like the target kanji/reading texts is not
                  # available.  Note that since 'entr' was created from
                  # JEL text it is not in the database and consequently
                  # cannot have any reverse xrefs yet; the reverse xref
                  # related calls that are usually used after reading an
                  # entry from the database are commented out for that
                  # reason.
                xrefs = jdb.collect_xrefs (entr)
                #xrers = jdb.collect_xrefs (entr, rev=True)
                jdb.augment_xrefs (dbcursor, xrefs)
                #jdb.augment_xrefs (dbcursor, xrers, rev=True)
                jdb.add_xsens_lists (xrefs)
                jdb.mark_seq_xrefs (dbcursor, xrefs)
        return entr
