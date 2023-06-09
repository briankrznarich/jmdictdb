# Copyright (c) 2019 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, datetime, pdb
import psycopg2, psycopg2.extras
from psycopg2.extras import DictCursorBase
  # The following are imported so that db.py consumers can access them
  # via the db.py module without needing to import psycopg2 directly.
from psycopg2.extras import DictCursor, NamedTupleCursor
from psycopg2 import Error, Warning, InterfaceError, DatabaseError, \
    DataError, OperationalError,IntegrityError, InternalError, \
    ProgrammingError, NotSupportedError
from psycopg2.extensions import QueryCanceledError

dbapi = psycopg2

class DbRowCursor (DictCursorBase):
    # We can use the DictCursorBase class even though we are not
    # implementing any sort of "dict" cursor because all it really
    # does is to call ._build_index() to create a column name to
    # index mapping after any .execute() calls, which is all we need.
    # We do require that the mapping exist before any row objects
    # are created in the fetch* methods and setting ._prefetch to 0
    # will force that to occur.

    def __init__(self, *args, **kwargs):
        kwargs['row_factory'] = DbRow
        super(DbRowCursor, self).__init__(*args, **kwargs)
        self._prefetch = 0

    def execute(self, query, vars=None):
        self.index = {}
        self._query_executed = 1
        return super(DbRowCursor, self).execute(query, vars)

    def callproc(self, procname, vars=None):
        self.index = {}
        self._query_executed = 1
        return super(DbRowCursor, self).callproc(procname, vars)

    def _build_index(self):
        if self._query_executed == 1 and self.description:
            self.index = [x[0] for x in self.description]
            self._query_executed = 0

def open (dburi, cursor_factory=DbRowCursor):
        if isinstance (dburi, str): dbargs = parse_pguri (dburi)
        else: dbargs = dburi
        dbconn = dbapi.connect (cursor_factory=cursor_factory, **dbargs)
        return dbconn
connect = open

def ex (dbconn, sql, args=(), cursor_factory=None):
        cur = dbconn.cursor (cursor_factory=cursor_factory)
        cur.execute (sql, args)
        return cur

def query (dbconn, sql, args=(), one=False, cursor_factory=None):
        cur = ex (dbconn, sql, args, cursor_factory=cursor_factory)
        if one: rs = cur.fetchone()
        else: rs = cur.fetchall()
        cur.close()
        return rs

def query1 (dbconn, sql, args=(), cursor_factory=None):
        return query (dbconn, sql, args, one=True,
                      cursor_factory=cursor_factory)

class Obj(object):
    # This creates "bucket of attributes" objects.  That is,
    # it creates a generic object with no special behavior
    # that we can set and get attribute values from.  One
    # could use a keys in a dict the same way, but sometimes
    # the attribute syntax results in more readable code.
    def __init__ (self, **kwds):
        for k,v in list(kwds.items()): setattr (self, k, v)
    def __repr__ (self):
        return self.__class__.__name__ + '(' \
                 + ', '.join([k + '=' + _p(v)
                              for k,v in list(self.__dict__.items())
                              if k != '__cols__']) + ')'

class DbRow (Obj):
    def __init__ (self, values=None, cols=None):
        if isinstance(values, DbRowCursor):
            self.__cols__ = values.index
        elif values is not None:
            if cols is not None:
                self.__cols__ = tuple(cols)
                for n,v in zip (cols, values): setattr (self, n, v)
            else:
                self.__cols__ = tuple(values.keys())
                for n,v in values.items(): setattr (self, n, v)
    def __getitem__ (self, idx):
        return getattr (self, self.__cols__[idx])
    def __setitem__ (self, idx, value):
        name = self.__cols__[idx]
        setattr (self, name, value)
    def __len__(self):
        return len(self.__cols__)
    def __iter__(self):
        for n in self.__cols__: yield getattr (self, n)
    def __eq__(self, other): return _compare (self, other)
    def copy (self):
        c = self.__class__()
        c.__dict__.update (self.__dict__)
        return c
    def new (self):
        c = self.__class__()
        c.__init__ ([None]*len(self.__cols__), self.__cols__)
        return c
    def _tolist(self): return [getattr(self, x) for x in self.__cols__]
    def _totuple(self): return tuple((getattr(self,x) for x in self.__cols__))
    def _todict(self): return dict((x,getattr(self,x)) for x in self.__cols__)

def _p (o):
        if isinstance (o, (int,str,bool,type(None))):
            return repr(o)
        if isinstance (o, (datetime.datetime, datetime.date, datetime.time)):
            return str(o)
        if isinstance (o, list):
            if len(o) == 0: return "[]"
            else: return "[...]"
        if isinstance (o, dict):
            if len(o) == 0: return "{}"
            else: return "{...}"
        else: return repr (o)

class _Nothing: pass
def _compare (self, other):
        try: attrs = set (list(self.__dict__.keys())
                          + list(other.__dict__.keys()))
        except AttributeError: return False
        for a in attrs:
            if a == '__cols__': continue
            s, o = getattr (self, a, _Nothing), getattr (other, a, _Nothing)
            if s is _Nothing or o is _Nothing or s != o:
                return False
        return True

  # When passed as sql argument to a sql statement executed by psycopg2,
  # DEFAULT will result in a postgresql DEFAULT argument.
  # See https://www.postgresql.org/message-id/CA+mi_8ZQx-vMm6PMAw72a0sRATEh3RBXu5rwHHhNNpQk0YHwQg@mail.gmail.com:
class Default(object):
    def __conform__(self, proto):
        if proto is psycopg2.extensions.ISQLQuote: return self
    def getquoted(self): return 'DEFAULT'
DEFAULT = Default()

if sys.version_info.major == 2: import urlparse
else: import urllib.parse as urlparse

def dburi_norm (dburi, scheme='postgres'):
        o = urlparse.urlsplit (dburi, scheme=scheme)
        scheme, netloc, path, query, fragment = o
        if scheme == 'pg': o = o._replace (scheme='postgres')
        if not netloc:
              # The following is to work around another Python PITA:
              # urllib treats a "netloc" value of '//' as empty and
              # normalizes it away when it reconstructing the URI.
              # That is,
              #   >>> urlunsplit (urlsplit('postgres://localhost/jmdict'))
              #   'postgres://localhost/jmdict'
              # returns what one would expect but,
              #   >>> urlunsplit (urlsplit('postgres:///jmdict'))
              #   'postgres:/jmdict'
              # removes the netloc part completely resulting in an invalid
              # Postgresql URI.  To preserve the "//" in the reconstructed
              # URI, there has to be something following it.  We create a
              # random text string (in order to avoid both unintentional
              # and intentional collisions with text in the URI) for this
              # purpose and remove it later to leave the "//" part.
            placeholder = "%012.12x"%random.randint(0,16777215)
            o = o._replace (netloc=placeholder)
        else: placeholder = None
          # Postgresql URI path value may not be relative.  We allow it
          # and change it to absolute here, so that "dbname" is valid and
          # results in "postgres:///dbname".
        if o.path and not o.path.startswith ('/'):
            o = o._replace (path='/' + o.path)
        newuri = o.geturl()
        if placeholder:
            newuri = newuri.replace (placeholder, '')
        return newuri

def dburi_sanitize (dburi):
        '''
        Remove the username and password parts (if either is present)
        from a postgresql database URI string.
        WARNING: UNTESTED
        '''
        scheme, netloc, path, query, frags = urlparse.urlsplit (dburi)
          # Note that this:
          #   o =  urlparse.urlsplit (dburi)
          #   o._replace(netloc'=...)
          # doesn't work.  The 'o' object keeps the username and password
          # as (AFAIK unchangable) attribute values and happily reinserts
          # them when reconstructing the URI, no matter what the netloc
          # value was changed to.
        if '@' in netloc:
              # Use 'rfind' rather than 'find' since the password might
              # contain a '@' character.
            netloc = netloc[1+netloc.rfind ('@'):]
        parts = [scheme, netloc, path, query, frags]
        newuri = urlparse.urlunsplit (parts)
        return newuri

def parse_pguri (uri_string, allow_params=False):
        '''
        Parse a Postgresql URI connection string and return a dict() suitable
        for use as the **kwds argument to psycopg2,connect() or jdb.dbOpen()
        functions.
        For URI syntax see the Postgresql libpq docs for "Connection URIs" in:
          http://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-PARAMKEYWORDS

        Examples:
          postgresql:///jmdict
          pg://localhost:5678/jmdict
        (Note: Allowing "pg" as an abbreviation for "postgresql" on the URI
        scheme designator is our own local enhancement.)

        If <allow_params> is true, any query string in the URI will also be
        parsed and the keyword,value pairs included in the output dict and
        will subsequently be interpreted as additional Postgresql libpq
        keyword,value pairs when passed to Pssycopg2's connect() function
        bt dbOpen().  This in general should only be done if the URI is
        from a trusted source as such parameters can affect things like
        connection timeouts and ssl modes.
        If <allow_params> is false, any query string part of the URI will be
        ignored.
        '''

        result = urlparse.urlsplit (uri_string)
        query = urlparse.parse_qs (result.query)
        scheme = result.scheme
        if not scheme: scheme = 'postgresql'
        if scheme not in ('pg', 'postgresql','postgres'):
            raise ValueError ("Bad scheme name ('%s') in URI: %s"
                              % (result.scheme, uri_string))
          # Add query items to results dict first so that uri parameters added
          #  sencond will overwrite if there are duplicates.
        connargs = query if allow_params else {}
        if result.username: connargs['user']     = result.username
        if result.password: connargs['password'] = result.password
        if result.path:     connargs['database'] = result.path.lstrip('/')
        if result.hostname: connargs['host']     = result.hostname
        if result.port:     connargs['port']     = result.port
        return connargs

def make_pguri (connargs):
        '''
        Convert dict of connection arguments such as is returned from
        jdb.parse_pguri() into a URI string.   The result will always
        have a scheme, "postgresql:"
        '''
        # Postgresql URI syntax:
        #   postgresql://[user[:password]@][netloc][:port][/dbname][?param1=value1&...]

        # Why, oh why, does urllib not provide better support for this??
        # Its urlunsplit() function does not seem to have any way to
        # accept username password, port, etc.
        auth = connargs.get('user','')
        if auth and connargs.get ('password'):
            auth += ':' + connargs['password']
        host = connargs.get('host','')
        if connargs.get('port'): host += ':' + str(connargs['port'])
        if auth: host = auth + '@' + host
        q = []
        for k,v in connargs.items():
            if k in ('user','password','database','host','port',): continue
            if not isinstance (v, (list,tuple)): v = [v]
            for vx in v: q.append ("%s=%s" % (k,vx))
        query = '&'.join (q)
        uri = urlparse.urlunsplit (('postgresql',
                                    host,connargs.get('database',''),
                                    query,''))
        return uri

  # Note: psycopg2 contains some attributes and functions related
  # to Postgresql connection strings (as an alternative to URIs).
  #   extensions.make_dsn() -- Turn a set of connection parameters
  #     into a connection string.
  #     arguments into a conection string.
  #   extensions.parse_dsn() -- Turn a connection string into a
  #     set of connection parameters.
  #   Connection.get_dsn_parameters() -- Return a connection's
  #     connection parameters.
  #   Connection.dsn -- Return a connection's connection string.

def require (dbconn, want, ret_dbver=False):
        ''' Given a list of update id numbers, return a subset of
        those numbers that are *not* present in the "db" table.
        These will usually represent database updates that the
        application requires to run correctly but which haven't
        been applied to the database.  If all the required updates
        are present in the database (ie, the software and database
        are compatible), an empty set is returned.

        want -- A list or set of update numbers that we require
            to be in the database's "db" table and have the
            "active" value set.  May be either 6-digit hexadecimal
            strings or ints.
        ret_dbver -- Determines return value, see below.
        Returns:
          If 'ret_dbver' is false (default): A set of update id (int)
            numbers in <want> that are not in the database "db" table.
          If 'ret_dbver' is true: A 2-tuple where the first item is
            as described above for the ret_dbver==false case, and the
            second item is the set of all active update is's in the
            database.'''

        cursor = dbconn.cursor()
        want_i = [v if isinstance(v, str) else "%.6x"%v for v in want]
        have = updates (dbconn)
        missing = set(want_i) - set(have)
        if ret_dbver: return missing, have
        return missing

def updates (dbconn, want_inactive=False, want_ts=False):
        '''-------------------------------------------------------------------
        Return a list of update ids (in hex format) for a database.
        Parameters:
          dbconn -- A psycopg2 connection object to JMdictDB database.
          want_inactive -- (bool) Return updates marked inactive as well
            as active ones.  If false, only active ones are returned.
          want_ts -- (bool) Items in returned list will be 3-tuples of
            (update-id, time-stamp, active).  If false, the list items
            will be update id's only.
        Returns:
          If both 'want_inactive' and 'want_ts' are false, the return
            value is a list of active update ids.
          If either 'want_inactive' or 'want_ts' are true, the return
            value is a list of 3-tuples of (update-id, time-stamp, active).
          In both cases update ids are a six-character str representing
            the id value in hexadecimal (lowercase with no prefix).
          Timestamps are in the form of datetime.dateime instances.
          The list will be ordered by descending value of timestamp,
            whether or not timestamps were requested with 'want_ts'.
        -------------------------------------------------------------------'''
        cursor = dbconn.cursor()
        cols = "id" + (",ts,active" if want_ts or want_inactive else "")
        whr = "" if want_inactive else " WHERE active"
        sql = "SELECT %s FROM db %s ORDER BY ts DESC" % (cols, whr)
        try: cursor.execute (sql)
        except dbapi.ProgrammingError as e:
            raise ValueError ("Can't read 'db' table, wrong database?")
        fmt = "%.6x"
        if want_ts or want_inactive:
            results = [(fmt%r[0],r[1],r[2]) for r in cursor.fetchall()]
        else: results = [fmt%r[0] for r in cursor.fetchall()]
        return results

def is_jmdictdb (dbconn):
         '''------------------------------------------------------------------
         Return True if database is a JMdictDB database, else False.
         ------------------------------------------------------------------'''
           # Test for JMdictDB database by looking for presence of
           # a set of tables.
         sql = "SELECT count(*) "\
               "FROM information_schema.tables "\
               "WHERE table_schema='public' "\
                 "AND table_name in ('db','entr','kanj','kinf','stagr')"
         rs = query (dbconn, sql)
         return bool (rs and rs[0][0] == 5)

def rowget (dbconn, tblname, pkey, cols=None):
    # Get a single row selected by primry key from a named table.
        whr = " AND ".join ([('%s=%%s' % k) for k in pkey.keys()])
        sqlargs = list (pkey.values())
        cols = ','.join (cols) if cols else '*'
        sql = "SELECT %s FROM %s WHERE %s" % (cols, tblname, whr)
        rs = db.query (dbconn, sql, sqlargs)
        if len (rs) > 1:  raise KeyError()
        if len (rs) == 0: return None
        return rs[0]

def rowop (dbconn, tblname, pkey, values, minupd=False,
                   autokey=None, returning=True):
    # Perform a basic IUD (Insert, Update or Delete) operation on
    # a single row identified by primary key on a single table.
    # 'pkey' is a dict whose keys are column names and values
    # identify the row wanted.
    #   dbconn -- Open DBAPI connection obbject.
    #   tblname -- Name of table.
    #   pkey -- A dict whose key(s) are the name(s) of primary key
    #      column(s) for table 'tblname' and the values identify the
    #      row to be updated.
    #   values -- A dict whose keys are the names of the columns to
    #      be updated and the values the give the values to update to.
    #   minupd -- If false (default), all column mentioned in values
    #      will be updated, whether or not the current value in the
    #      database is the same.  In 'minupd' is true, the current row
    #      row will be retrieved for comparison and only those columns
    #      that are different will be updated.  Please be aware of the
    #      possible concurrency implications of this.
    #   autokey -- Allows insert of new rows with an auto-increment of
    #      of a 2-part composite integer primary key.  A 2-item sequence
    #      comprised of:
    #        - The name of the first column of the primary key.
    #        - The name of the second column of the primary key.
    #      The first column must also be present in 'values'.
    #      The mechanism used is to insert the 1+MAX value of the second
    #      primary key column over the rows matching the first column.
    #      This may result in IntegrityError failures and performance
    #      issues in an environment with many concurrent operations or
    #      high insert rates.
    #   returning -- (bool) if true (default) return

    ##  The following explict conversion is not needed if dicts are
    ##  registered with psycopg2 to be automatically adapted to json
    ##  as is currently done in lib/db.py.  See also the ## comments
    ##  in two "sqlargs =" statements below.
    ##    def A(x): return db.Json(x) if isinstance(x,dict) else x

        if pkey and values:            # Update
            diffs = values
            if minupd:
                currentrow = rowget (dbconn, tblname, pkey)
                if not currentrow:
                    raise KeyError('No row to update in table "%s", pk=%r'
                                   % pkey)
                diffs = rowchanges (values, currentrow)
            cols = ','.join(["%s=%%s"%x for x in diffs.keys()])
            sqlargs = list (diffs.values())  ## = [A(x) for x in diffs.values()]
            whr = " AND ".join ([("%s=%%s"%x) for x in pkey.keys()])
            ret = " RETURNING *" if returning else ""
            sqlargs.extend (pkey.values())
            sql = "UPDATE %s SET %s WHERE %s%s" % (tblname, cols, whr, ret)
            if not cols or not whr: sql = None

        elif pkey and not values:      # Delete
            whr = " AND ".join ([("%s=%%s"%x) for x in pkey.keys()])
            sqlargs = list (pkey.values())
            sql = "DELETE FROM %s WHERE %s RETURNING *" % (tblname, whr)
            if not whr: sql = None

        elif not pkey and values:      # Insert
            cols = ','.join(list (values.keys()))
            sqlargs = list(values.values())  # =[A(x) for x in values.values()]
            pmarks = ','.join (['%s'] * len (sqlargs))
            akexpr = ''
            if autokey:
                pk1, pk2 = autokey    # Names of the primary key columns.
                if pk1 not in values.keys():  # We must have a value for
                    raise KeyError (pk1)      #  the first part of the pk.
                akexpr = ',(SELECT 1+COALESCE(MAX(%s),0) FROM %s WHERE %s=%%s)'\
                         % (pk2, tblname, pk1)
                  # 'akexpr', when executed, will be like:
                  #   SELECT 1+MAX(pk2) FROM tblname WHERE pk1=values[pk1]
                  # This is added onto the end of VALUES items.
                cols += ',' + pk2
                sqlargs.append (values[pk1])
            sql = "INSERT INTO %s(%s) VALUES(%s%s) RETURNING *"\
                   % (tblname, cols, pmarks, akexpr)
            if not cols: sql = None

        else:                           # No pkey and no values
            raise ValueError ()

        if not sql: return {}, 0
        cursor = db.sqlex (dbconn, sql, sqlargs)
        rowcount = cursor.rowcount
        if not returning: return rowcount

        rs = cursor.fetchall()
          # If caller specifed a 'pk' that was not in fact a primary
          # key, more than one record could be affect, which for safety
          # we complain about.
        if len(rs) > 1: raise KeyError ((tblname, pkey))
        if len(rs) == 0: return {}, rowcount
        return rs[0], rowcount

def rowdiff (a, b, raise_missing=False):
        diff = {}; amissing = set(); bmissing = set()
        for k,v in a.items():
            if k not in b: bmissing.add (k)
            else:
                if b[k] != v: diff[k] = (v,b[k])
        for k,v in b.items():
            if k not in a: amissing.add (k)
        if raise_missing and (amissing or bmissing):
            raise KeyError ((amissing, bmissing))
        if raise_missing: return diff
        return diff, amissing, bmissing

def rowchanges (new, old, raise_missing=False):
          # Return a dict consisting of those items in 'new' that
          # have a value different than in 'old' or don't occur in
          # 'old'.  If 'raise_missing is true, the latter condition
          # will result in an exception instead.
        diff = {}
        for k,v in new.items():
            if k not in old and raise_missing: raise KeyError (k)
            if k not in old or old[k] != v: diff[k] = v
        return diff
