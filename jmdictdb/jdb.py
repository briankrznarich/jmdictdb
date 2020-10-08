# Copyright (c) 2006-2014 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, os, os.path, random, re, datetime, operator, csv, json
from time import time
from collections import defaultdict
from jmdictdb import db, fmtxml
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb.objects import *
from jmdictdb.restr import *

# Logging calls:
#   Level    Source
#    5      jdb.entr_data.db.sql
#    5      jdb.entr_data.db.time

  # Get the database version id number(s) required by this version
  # of the JMdictDB API.  When dbOpen() is called it will check that
  # all version id's in the DBVERS list are present in database table
  # "db" and marked as active.  If not dbOpen will raise a KeyError
  # exception.  Note that id's are integers conventionally expressed
  # in hexidecimal.
  # If "dbver" is empty no version check will be done.  This allows
  # for ignoring version numbers temporarily during development.
try: from jmdictdb.dbver import DBVERS
except ImportError: DBVERS = []

global KW
Debug = {}
NONE = object()  # Sentinel for missing fuction call args
                 # used in some functions and methods.

class AuthError (Exception): pass

def dbread (cur, sql, args=None, cols=None, cls=None, timeout=None):
        # Execute a result returning sql statement(s) and return the
        # result set as a list of 'cls' object, one object per row.
        #
        # cur -- Open DBAPI cursor object.
        # sql -- (str) SQL statement to execute.
        # args -- (optional) A list of args corresponding to parameter
        #       markers in the sql statement.  May be omitted, None, or
        #       an empty sequence if 'sql' contains no pmarks.
        # cols -- (optional) A list of column names to be used for each
        #       column of the results set.  If not given, the dbapi will
        #       be queried from the column names.
        # cls -- (optional) A class that will be used for row objects.
        #       Must be a class, not a factory function.  If not given,
        #       DbRow will be used.
        # timeout -- (optional) Timeout value (int) in milliseconds or None.
        #       If not None, runs the 'sql' statement after starting a
        #       transaction and setting Postgresql's 'statement_timeout'
        #       value to 'timeout'.  The 'set' is done with the "local"
        #       option so previous value is restored before returning.

          # If there are no args, set args (which might be [], or ())
          # to None to avoid bug in psycopg2 (at least version 2.0.7)
          # Specifically, if 'sql' contains a sql wildcard character,
          # '%', the psycopg2 DBAPI will interpret it as a partial
          # parameter marker (it uses "%s" as the parameter marker)
          # and will fail with an IndexError exception if sql_args is
          # an empty list or tuple rather than 'None'.
          # See: http://www.nabble.com/DB-API-corner-case-(psycopg2)-td18774677.html
        if not args: args = None
          # Execute the sql in a try statement to catch any errors.
        if timeout:
              # Note that this has to be executed separately from the
              # the sql statement subject to timeout since the timeout
              # is applied to the statement(s) that follow the "set
              # statement_timeout statement.  The "local" option
              # restricts the timeout to statement withing the containing
              # transaction, hence the "begin" statement.
            sqlsett = "BEGIN; SET LOCAL statement_timeout=%s" % timeout
            cur.execute (sqlsett);
        try: cur.execute (sql, args)
        except dbapi.Error as e:
              # If the execute failed, append the sql and args to the
              # error message.
            msg = e.args[0] if len(e.args) > 0 else ''
            msg += "\nSQL: %s\nArgs: %r" % (sql, args)
            e.args = [msg] + list(e.args[1:])
              # If a rollback is not done, all subsequent operations on this
              # cursor's connection will (with the psycopg2 DBAPI) result
              # in a InternalError("current transaction is aborted, commands
              # ignored until end of transaction block\n") error.
              # Catch any errors from this operation to prevent them from
              # being raised, rather than the original error.
            try: cur.execute ("ROLLBACK")
            except dbapi.Error: pass
            raise       # Re-raise the original error.
          # If not given column name by the caller, get them from the cursor.
        if not cols: cols = [x[0] for x in cur.description]
        v = []
        for r in cur.fetchall ():
              # For each row, create a generic DbRow object...
            x = DbRow (r, cols)
              # ...and coerce it to the desired type.
              # FIXME: is there a cleaner way?...
            if cls: x.__class__ = cls
            v.append (x)
        cur.connection.commit()
        return v

def dbinsert (dbh, table, cols, row, wantid=False):
        # Insert a row into a database table named by 'table'.
        # coumns that will be used in the INSERT statement are
        # given in list 'cols'.  The values are given in object
        # 'row' which is expected to contain attributes matching
        # the columns listed in 'cols'.

        args = None
        sql = "INSERT INTO %s(%s) VALUES(%s)" \
                % (table, ','.join(cols), pmarks(cols))
          #FIXME: we want to take column values from attributes of 'row'
          # if possible, or sequentially from seq elements if not (i.e.
          # assume a list, tuple, etc), but DbRow objects can be accessed
          # either way.  Access by attribute should assume None if attribute
          # missing so we can't rely on missing attributes to switch to seq
          # access.  For now we will test explicitly for Obj (DbRow is Obj
          # subclass) but this is obviously a hack.

        if isinstance (row, Obj):
            args = [getattr (row, x, None) for x in cols]
        else:
            if len(row) != len(cols): raise ValueError(row)
            args = row
        if not args: raise ValueError (args)
        if Debug.get ('prtsql'): print (repr(sql), repr(args))
        try: dbh.execute (sql, args)
        except Exception as e:
            e.sql = sql;  e.sqlargs = args
            if not hasattr (e, 'message'): e.message = ''
            e.message += "  %s [%s]" % (sql, ','.join(repr(x) for x in args))
            raise e
        id = None
        if wantid: id = dblastid (dbh, table)
        return id

def dblastid (dbh, table):
        # Need to make this work like Perl's DBD:Pg:last_insert_id()
        # but for now following is ok.
        dbh.execute ('SELECT LASTVAL()')
        rs = dbh.fetchone()
        return rs[0]

def dbexecsp (cursor, sql, args, savepoint_name="sp"):
        # Execute a sql statement with a savepoint.  If the statement succeeds,
        # the savepint is deleted.  If the statement fails, the database state
        # is rolled back to the savepoint and the failure exception reraised.
        cursor.execute ("SAVEPOINT %s" % savepoint_name)
        try:
            cursor.execute (sql, args)
        except dbapi.Error as e:
            cursor.execute ("ROLLBACK TO %s" % savepoint_name)
            raise e
        else:
            cursor.execute ("RELEASE %s" % savepoint_name)

def entrFind (cur, sql, args=None):
        if args is None: args = []
        tmptbl = Tmptbl (cur)
        tmptbl.load (sql, args)
        return tmptbl

def entrList (dbh, crit=None, args=None, ord='', tables=None, ret_tuple=False):

        # Return a list of database objects read from the database.
        #
        # dbh -- An open DBI database handle.
        #
        # crit -- Criteria that specifies the entries to be
        #   retrieved and returned.  Is one of three forms:
        #
        #   1. Tmptbl object returned from a call to Find()
        #   2. A sql statement that will give a results set
        #       with one column named "id" containing the entr
        #       id numbers of the desired entries.  The sql
        #       may contain parameter markers which will be
        #       replaced by items for 'args' by the database
        #       driver.
        #   3. None.  'args' is expected to contain a list of
        #       entry id numbers.
        #   3a. (Deprecated) A list of integers or parameter
        #       markers, each an entr id number of an entry
        #       to be returned.
        #
        # args -- (optional) Values that will be bound to any
        #   parameter markers used in 'crit' of forms 2 or 3.
        #   Ignored if form 1 given.
        #
        # ord -- (optional) An ORDER BY specification (without
        #   the "ORDER BY" text) used to order the entries in the
        #   returned list.  When qualifying column names by table,
        #   the entr table has the alias "x", and the 'crit' table
        #   or subselect has the alias "t".
        #   If using a Tmptbl returned by Find() ('crit' form 1),
        #   'ord' is ignored and internally forced to "t.ord".

        t = {}; entrs = []
        if args is None: args = []
        if not crit and not args: raise ValueError("Either 'crit' or 'args' must have a value.")
        if not crit:
            crit = "SELECT id FROM entr WHERE id IN (%s)" % pmarks(args)
        if isinstance (crit, Tmptbl):
            t = entr_data (dbh, crit.name, args, "t.ord")
        elif isinstance (crit, str):
            t = entr_data (dbh, crit, args, ord, tables)
        else:
            # Deprecated - use 'crit'=None and put a real list in 'args'.
            t = entr_data (dbh, ",".join([str(x) for x in crit]), args, ord, tables)
        if t:
            entrs = entr_bld (t)
        if ret_tuple: return entrs,t
        return entrs

OrderBy = {
        'rdng':"x.entr,x.rdng",          'kanj':"x.entr,x.kanj",
        'sens':"x.entr,x.sens",          'gloss':"x.entr,x.sens,x.gloss",
        'xref':"x.entr,x.sens,x.xref",   'hist':"x.entr,x.hist",
        'kinf':"x.entr,x.kanj,x.ord",    'rinf':"x.entr,x.rdng,x.ord",
        'pos':"x.entr,x.sens,x.ord",     'misc':"x.entr,x.sens,x.ord",
        'fld':"x.entr,x.sens,x.ord",     'dial':"x.entr,x.sens,x.ord",
        'lsrc':"x.entr,x.sens,x.ord",    'xresolv':"x.entr,x.sens,x.typ,x.ord",
        'restr':"x.entr,x.rdng,x.kanj",
        'stagk':"x.entr,x.sens,x.kanj",  'stagr':"x.entr,x.sens,x.rdng" }

def entr_data (dbh, crit, args=None, ord=None, tables=None):
        #
        # dbh -- An open JMdictDB database handle.
        #
        # crit -- A string that specifies the selection criteria
        #    for the entries that will be returned and is in one
        #    of the following formats.
        #
        #    1. Table name.  'crit' either starts with a double
        #       quote character or contains no space characters,
        #       and is not an id number list (#3 below).
        #       The table named must exist and contain at least a
        #       column named "id" containing entry id numbers of
        #       the entries to be fetched.
        #       jdb.entr.Find() is one way to create such a table.
        #
        #    2. Select statement (in parenthesis).  'crit' starts
        #       with a "(" character.
        #       It must produce a result set that includes a column
        #       named "id" that contains the entry id numbers of
        #       the entries to be fetched.  The select statement
        #       may contain parameter marks which will be bound to
        #       values from 'args'.
        #
        #    3. A list of entry id numbers.  'crit' is one or more
        #       of a number or parameter markers ("?" or "%s"
        #       depending on the DBI interface in use) separated
        #       by commas.  Parameter marks which will be bound to
        #       values from 'args'.
        #
        #    4. Select statement (not in parenthesis).  'crit'
        #       contains space characters and doesn't start with
        #       a double quote or left paren character.
        #       It must produce a result set that includes a column
        #       named "id" that contains the entry id numbers of
        #       the entries to be fetched.  The select statement
        #       may contain parameter marks which will be bound to
        #       values from 'args'.
        #
        #    Formats 1 and 2 above will be joined with a generic
        #    select to retrieve data from the entry object tables.
        #    Forms 3 and 4 will be used in a "WHERE ... IN()"
        #    clause attached the the generic retrieval sql.
        #    When a large number of results are expected, the
        #    latter two formats are likely to be more efficient
        #    than the former two.
        #
        #  args -- A list of values that will be bound to
        #    any parameters marks in 'crit'.
        #
        #  ord -- (optional) string giving an ORDER BY clause
        #    (without the "ORDER BY" text) that will be used
        #    to order the read of the entr rows and thus the
        #    order entries are placed in the returned list.
        #    When qualifying column names by table, the entr
        #    table has the alias "x", and the $crit table or
        #    subselect has the alias "t".
        #    If using the Tmptbl returned by Find(), $ord will
        #    usually be: "t.ord".
        #
        #  tables -- (optional) A list of table names from which
        #    to retrieve infomation for building the Entr objects.
        #    This is useful when not all information is needed in
        #    an entry (for example the abbreviated entries used
        #    to hold details of xref targets) and accomplished by
        #    by specifying a limited set of tables.  If not given
        #    the default is to use all tables.
        #
        #  Returns:
        #   A dict object where each key is a table name (or pseudo
        #   name like "xrer") given in 'tables' or in the default
        #   list below) and each value is a list of objects.* objects
        #   corresponding to the table type.  E.g., the value of the
        #   "entr" key is a list of objects.Entr objects.  Note that
        #   all the objects.* objects are subclasses of objects.DbRow.

        global Debug; time_start = time_last = time()

        if not tables: tables = (
            'entr','hist','rdng','rinf','kanj','kinf',
            'sens','gloss','misc','pos','fld','dial','lsrc',
            'restr','stagr','stagk','freq','xref','xrer',
            'rdngsnd','entrsnd','grp','chr','cinf','xresolv')
        if args is None: args = []
        if ord is None: ord = ''
        if re.search (r'^((\d+|\?|%s),)*(\d+|\?|%s)$', crit):
            typ = 'I'                           # id number list
        elif  (crit.startswith ('"')            # quoted table name
                or crit.find(' ')==-1           # no spaces: table name
                or crit.startswith ('(')):      # parenthesised sql
            typ = 'J'
        else: typ ='I'                          # un-parenthesised sql.

        if typ == 'I': tmpl = "SELECT x.* FROM %s x WHERE x.%s IN (%s) %s %s %s"
        else:          tmpl = "SELECT x.* FROM %s x JOIN %s t ON t.id=x.%s %s %s %s"

        t = {}
        for tbl in tables:
            key = iif (tbl == "entr", "id", "entr")

            if tbl == "entr": ordby = ord
            else: ordby = OrderBy.get (tbl, "")
            if ordby: ordby = "ORDER BY " + ordby

            if tbl == "xrer":
                  # Table "xrer' is a pseudo-table: it consists of rows
                  # from real table "xref" but using different criteria
                  # for selecting the rows.
                  # "xrer" selects rows for "reverse" xrefs: xrefs whos
                  # (xentr,xsens) values refer to the related entry rather
                  # than (entr,sens) as in normal "forward" xrefs.
                  # We select only rows not marked as "lowpri" (low priority)
                  # to avoid getting an excessively large of number of xrer
                  # rows in cases of words like "の" which could have hundreds
                  # of thousands of reverse xrefs to example sentences.
                tblx = "xref"; key = "xentr"
                if typ == 'I':           # We are adding to existing
                    wkeyword = "AND"     #  WHERE clause so "WHERE" not needed.
                else:  # typ='J', we need to add a full WHERE clause.
                    wkeyword = "WHERE"   # No existing WHERE clause so we
                whr = " %s not lowpri" % (wkeyword,)
                limit = ''  # Not currently used.
            else:
                tblx = tbl;  limit = '';  whr = ''
            # FIXME: cls should not be dependent on lexical table name.
            # FIXME: rename database table "xresolv" to "xrslv".
            if tblx == "xresolv": cls_name = "Xrslv"
            else: cls_name = tblx.title()
            cls = globals()[cls_name]

            if   typ == 'I': sql = tmpl % (tblx, key, crit, whr, ordby, limit)
            elif typ == 'J': sql = tmpl % (tblx, crit, key, whr, ordby, limit)
            else: assert False   # this should never happen.
            if tbl not in t: t[tbl] = []
            try:
                L('jdb.entr_data.db.sql').log(5,"sql: "+sql)
                L('jdb.entr_data.db.sql').log(5,"args: %r"%(args,))
                t[tbl].extend (dbread (dbh, sql, args, cls=cls))
                L('jdb.entr_data.db.time').log(5,"table %s read time: %s"%(tbl,round(time()-time_last,6)))
                time_last = time()
            except (psycopg2.ProgrammingError) as e:
                L('jdb.entr_data').error(str(e))
                L('jdb.entr_data.db.sql').error("  sql: "+sql)
                L('jdb.entr_data.db.sql').error("  args: %r"%(args,))
                dbh.connection.rollback()
        L('jdb.entr_data.db.time').log(5,"total time: %s"%(round(time()-time_start,6)))
        return t

def entr_bld (t):
        # Put rows from child tables into lists attached to their
        # parent rows, thus building the object structure that
        # application programs will work with.

        r = [t.get (x, []) for x in ('entr', 'rdng', 'kanj', 'sens', 'chr')]
        entr, rdng, kanj, sens, chr = r
        mup ('_kanj',  entr, ['id'],          kanj,              ['entr'])
        mup ('_rdng',  entr, ['id'],          rdng,              ['entr'])
        mup ('_sens',  entr, ['id'],          sens,              ['entr'])
        mup ('_hist',  entr, ['id'],          t.get('hist', []), ['entr'])
        mup ('_inf',   rdng, ['entr','rdng'], t.get('rinf', []), ['entr','rdng'])
        mup ('_inf',   kanj, ['entr','kanj'], t.get('kinf', []), ['entr','kanj'])
        mup ('_gloss', sens, ['entr','sens'], t.get('gloss',[]), ['entr','sens'])
        mup ('_pos',   sens, ['entr','sens'], t.get('pos',  []), ['entr','sens'])
        mup ('_misc',  sens, ['entr','sens'], t.get('misc', []), ['entr','sens'])
        mup ('_fld',   sens, ['entr','sens'], t.get('fld',  []), ['entr','sens'])
        mup ('_dial',  sens, ['entr','sens'], t.get('dial', []), ['entr','sens'])
        mup ('_lsrc',  sens, ['entr','sens'], t.get('lsrc', []), ['entr','sens'])
        mup ('_restr', rdng, ['entr','rdng'], t.get('restr',[]), ['entr','rdng'])
        mup ('_stagr', sens, ['entr','sens'], t.get('stagr',[]), ['entr','sens'])
        mup ('_stagk', sens, ['entr','sens'], t.get('stagk',[]), ['entr','sens'])
        mup ('_freq',  rdng, ['entr','rdng'], [x for x in t.get('freq',[]) if x.rdng],  ['entr','rdng'])
        mup ('_freq',  kanj, ['entr','kanj'], [x for x in t.get('freq',[]) if x.kanj],  ['entr','kanj'])
        mup ('_xref',  sens, ['entr','sens'], t.get('xref', []), ['entr','sens']);
        mup ('_xrer',  sens, ['entr','sens'], t.get('xrer', []), ['xentr','xsens'])
        mup ('_snd',   entr, ['id'],          t.get('entrsnd',[]), ['entr'])
        mup ('_snd',   rdng, ['entr','rdng'], t.get('rdngsnd',[]), ['entr','rdng'])
        mup ('_grp',   entr, ['id'],          t.get('grp',[]),     ['entr'])
        mup ('_xrslv', sens, ['entr','sens'], t.get('xresolv',[]), ['entr','sens'])
          # For assigning to entr.chr, we reverse the roles of the mup()
          # "parent" and "child" arguments ('entr' is passed as child,
          # 'chr' as parent) in order that the assignment to entr.chr
          # will be a single 'chr' object, not a list.
        mup (None,     chr,  ['entr'],        entr,                ['id'],  'chr')
        mup ('_cinf',  chr,  ['entr'],        t.get('cinf',[]),    ['entr'])
        mup ('_krslv', entr, ['id'],          t.get('krslv',[]),   ['entr'])
        return entr     # 'entr' is a list of Entr instances.

def filt (parents, pks, children, fks):
        # Return a list of all parents (each a hash) in 'parents' that
        # are not matched (in the 'pks'/'fks' sense of lookup()) in
        # 'children'.
        # One use of filt() is to invert the restr, stagr, stagk, etc,
        # lists in order to convert them from the "invalid pair" form
        # used in the database to the "valid pair" form typically needed
        # for display (and visa versa).
        # For example, if 'restr' contains the restr list for a single
        # reading, and 'kanj' is the list of kanji from the same entry,
        # then
        #        filt (kanj, ["kanj"], restr, ["kanj"]);
        # will return a list of kanj hashes that do not occur in 'restr'.

        list = []
        for p in parents:
            if not lookup (children, fks, p, pks): list.append (p)
        return list

def lookup (parents, pks, child, fks, multpk=False):
        # 'parents' is a list of hashes and 'child' a hash.
        # If 'multpk' if false, lookup will return the first
        # element of 'parents' that "matches" 'child'.  A match
        # occurs if the hash values of the parent element identified
        # by the keys named in list of strings 'pks' are "="
        # respectively to the hash values in 'child' corresponding
        # to the keys listed in list of strings 'fks'.
        # If 'multpk' is true, the matching is done the same way but
        # a list of matching parents is returned rather than the
        # first match.  In either case, an empty list is returned
        # if no matches for 'child' are found in 'parents'.

        results = []
        for p in parents:
            if matches (p, pks, child, fks):
                if multpk: results.append (p)
                else: return p
        return results

def matches (parent, pks, child, fks):
        # Return True if the values of the attributes of object 'parent'
        # listed in 'pks' (a list of strings) are equal to the attributes
        # of object 'child' listed in 'fks' (a list of strings).  Otherwise
        # return False.  'pks' and 'fks' should have the same length.

        for pk,fk in zip (pks, fks):
            if getattr (parent, pk) != getattr (child, fk): return False
        return True

def mup (attr, parents, pks, childs, fks, pattr=None):
        # Assign each element of list 'childs' to its matching parent
        # and/or "assign" each parent to each matching child.
        # A parent item and child item "match" when the values of the
        # parent item attributes named in list 'pks' are equal to the
        # child item attributes named in list 'fks'.
        #
        # The child is "assigned" to the parent by adding it to the
        # list in the parent's attribute 'attr', if attr is not None.
        # Alternatively (or in addition) the parent will be "assigned"
        # to each matching child by setting the child's attribute named
        # by pattr, to the parent, if 'pattr' is not None.
        #
        # Note that if both 'attr' and 'pattr' are not None, a reference
        # cycle will be created.  Refer to the description of reference
        # counting and garbage collection in the Python docs for the
        # implications of that.

          # Build an index of the keys of parents, to speed up lookups.
        index = dict();
        for p in parents:
            pkey = tuple ([getattr (p, x) for x in pks])
            index.setdefault (pkey, []).append (p)
            if attr: setattr (p, attr, [])

          # Go through the childs, for each looking up the parent with
          # a pk matching the child's fk, and adding the child to that
          # parent's list, in attribute 'attr'.
        for c in childs:
            ckey = tuple ([getattr (c, x) for x in fks])
              # We prevent KeyErrors by using .get() below so that we can build
              # an Entr object even if some of the constitutent records are
              # bad.  That can happen in jmedit.py for example when an Entr
              # object is built from records that are only partially complete
              # of have been changed so that a foreign key refers to rows that
              # are not in the parent row set.
              # The downside is that we do not detect unintentionally bad data
              # rows -- they simply will not appear in the result object.
              # FIXME: why do we skip error checking for the benefit of a
              #   single app?
            for p in (index.get (ckey, [])):
                if attr: getattr (p, attr).append (c)
              # Assign parent link to child if requested via 'pattr'.
            if pattr:
                  # There should be either 0 or 1 matching parent.  If 0 then
                  # we assign None since the policy for the Entr and child
                  # objects is to have all attributes present, even if empty.
                parents = index.get (ckey, [None])
                if len (parents) > 1:
                    raise ValueError ("jdb.mup: more than 2 parents")
                setattr (c, pattr, parents[0])

#-------------------------------------------------------------------
# The following functions deal with freq objects.
#-------------------------------------------------------------------

def freq2txts (freqs, tt=False):
        flist = []
        for f in freqs:
            kwstr, descr = KW.FREQ[f.kw].kw, KW.FREQ[f.kw].descr
            fstr = ('%s%02d' if kwstr=='nf' else '%s%d') % (kwstr, f.value)
            if tt: fstr = '<span class="abbr" title="%s">%s</span>' % (descr, fstr)
            if fstr not in flist: flist.append (fstr)
        return sorted (flist)

def copy_freqs (old_entr, new_entr):
        # Copy the freq objects on the ._rdng and ._kanj lists of
        # Entr object 'old_entr', to Entr object 'new_entr'.  Any
        # preexisting freq items in 'new_entr' are removed.
        #
        # Reading and kanji items are matched between the old
        # and new entries based in their .txt attribute, not
        # their indexed position.
        #
        # The Freq items added to 'new_entr' are freshly created and
        # will have no values for .entr, .rdng or .kanj attributes.

        for rto in new_entr._rdng:
            rfrom = _find_matching_rk (old_entr._rdng, rto.txt)
            _copy_freqs (rfrom, rto)
        for kto in new_entr._kanj:
            kfrom = _find_matching_rk (old_entr._kanj, kto.txt)
            _copy_freqs (kfrom, kto)

def _find_matching_rk (rklist, txt):
          # Find and return the Rdng or Kanj object in list 'rklist'
          # whose .txt value is the same as 'txt'.  If no matching
          # object is found return None.
          #   rklist -- A list of objects.Rdng or objects.Kanj objects 
          #     (typically from Entr._rdng or Entr._kanj).
          #   txt -- Reading of 
        for o in rklist:
            if o.txt == txt: return o
        return None

def _copy_freqs (from_, to_):
          # from_, to_ -- Both are objects.Rdng or objects.Kanj objects.
        to_._freq = []          # Discard any preexisting ._freq items.
        if not from_: return   # If no 'from_' item, nothing to copy.
        for f in from_._freq:
            to_._freq.append (Freq (kw=f.kw, value=f.value))

#-------------------------------------------------------------------
# The following four functions deal with xrefs.
#-------------------------------------------------------------------
        # An xref (in the jdb api) is an object that represents
        # a record in the "xref" table (or "xresolv" table in the
        # case of unresolved xrefs).  The database xref records
        # in turn represent a <xref> or <ant> element in the
        # JMdict xml file, although there are some differences:
        #
        #  * Database xref records can have other type besides
        #    "xref" and "ant".
        #  * Database xref records always point to a specific sense
        #    in the target entry; jmdict xrefs/ants can point to a
        #    specific sense, or no sense (i.e. the entire entry.)
        #  * Database xrefs always point to (a sense in) a specific
        #    entry; jmdict xrefs identify the target entry with a
        #    kanji text, reading text, or both, and may not uniquely
        #    identify a single entry.
        #
        # Each xref object links two two entries (or more acurately,
        # specific senses of two entries) identified by their id
        # numbers in the attributes .entr and .xentr.  We view an
        # xref as being "from" .entr and "to" .xentr.  A "forward"
        # xref (with respect to an entry) is one whose .entr value
        # is equal to the entry's .id value.  A "reverse" xref is
        # one whose .xentr value is the same as the entry's .id.
        #
        # There are actually three flavours of xref objects:
        #
        # "ordinary" (or unqualified) xrefs represent only the info
        # stored in the database xref table where each row represents
        # an xref from an existing entry's sense to another existing
        # entry's sense.  It will have attributes 'typ' (attribute type
        # id number as defined in table kwxref), 'xentr' (id number of
        # target entry), 'xsens' (sense number of target sense), and
        # optionally 'kanj' (kanj number of the kanji whose text will
        # be used when displaying the xref textually), 'rdng' (like
        # 'kanj' but for reading), 'notes'.  When jdb.entrList() reads
        # an entry object, it creates ordinary xrefs.
        #
        # "augmented" xrefs are provide additional information about
        # the xref's target entry that are useful when presenting the
        # xref textually to an end-user.  The additional information
        # is in the form of an "abbreviated" entry object found in the
        # xref attribute "TARG".  The entry object is "abbreviated" in
        # that it contains only data from the rdng, kanj, sens, and
        # gloss tables, but not from kinfo, lsrc, etc that are not
        # relevant when providing only a summary of an entry.
        # ordinary xrefs can be turned into augmented xrefs with the
        # function jdb.augment_xrefs().  Note that augmented xrefs
        # are a superset of ordinary xrefs and should work wherever
        # ordinary xrefs are accepted.
        #
        # "unresolved" xrefs represent xref information read from a
        # textual source and correspond to database records in table
        # "xresolv".  They have attributes 'typ' (attribute type id
        # number as defined in table kwxref), 'ktxt' (target kanji),
        # 'rtxt' (reading text), and optionally, 'notes', 'xsens'
        # (target sense), 'ord' (ordinal position within a set of
        # related xrefs).  These xrefs have not been verified and
        # and a unique entry with the given kanji or reading texts
        # may not exist in the database or it may not have the given
        # target senses.  The api function jdb.resolv_xrefs() can be
        # used to turn unresolved xrefs into ordinary xrefs.

def collect_xrefs (entrs, rev=False):
        # Given a list of Entr objects, 'entrs', collect all the
        # Xref's on their Sens' _xref lists (or _xrer if 'rev' is
        # true) into a single list which is returned, typically so
        # the caller can call augment_xrefs() on them.
        # (The _xref or _xrer lists are not changed.)

        attr = '_xrer' if rev else '_xref'
        xrefs = []
        for e in entrs:
           for s in getattr (e, '_sens', []):
                xrefs.extend (getattr (s, attr, []))
        return xrefs

def augment_xrefs (dbh, xrefs, rev=False):
        # Augment a set of xrefs with extra information about the
        # xrefs' targets.  After augment_xrefs() returns, each xref
        # item in 'xrefs' will have an additional attribute, "TARG"
        # that is a reference to an entr object describing the xref's
        # target entry.  Unlike ordinary entr objects, the TARG objects
        # have only a subset of sub items: they have no _inf, _freq,
        # _hist, _lsrc, _pos, _misc, _fld, _xrer, _restr,
        # _stagr, _stagk, _entrsnd, _edngsnd, lists.
        #
        # If <rev> is false, the .TARG entr object will be for the
        # "forward" xref; that is, its id will be the same as the xref's
        # .xentr value.  If <rev> is true then .TARG's entr object will
        # be for the reverse xref; its id will be the same as the xref's
        # .entr value.

        global Debug; start = time()

        tables = ('entr','rdng','kanj','sens','gloss','xref')
        if rev: attr = 'entr'
        else: attr = 'xentr'
        ids = set ([getattr(x,attr) for x in xrefs])
        if len (ids) > 0:
            elist = entrList (dbh, list(ids), tables=tables)
            mup (None, elist, ['id'], xrefs, [attr], 'TARG')

        Debug['Xrefsum2 retrieval time'] = time() - start

def add_xsens_lists (xrefs, rev=False):
        # Add a ._xsens attribute to the first xref in each
        # set of xrefs with the same .entr, .sens, .typ, .xentr
        # and .notes, that contains a list of all xsens numbers
        # of the xrefs in that set.  A ._xsens attribute with a
        # value of [] is added to the second and subsequent xrefs
        # of each set.

        index = {}
        for x in xrefs:
            if not rev:
                key = (x.entr,  x.sens, x.typ, x.xentr, x.notes)
                var = x.xsens
            else:
                key = (x.xentr, x.xsens, x.typ, x.entr,  x.notes)
                var = x.sens
            p = index.get (key, None)
            if p is None:
                x._xsens = [var]
                index[key] = x
            else:
                x._xsens = []
                p._xsens.append (var)

def mark_seq_xrefs (cur, xrefs):
        # Go through the list of xrefs and add a '.SEQ' attribute
        # to any that can be displayed as a seq-type xref, that is
        # the xref group (common entr, sens, typ, note, values)
        # contains xrefs to every active entry of the target's
        # seq number, and the list of target senses for each of
        # those target entries is the same.

          # Get a list of all target xref seq numbers, categorized
          # by corpus (aka src).
        srcseq = defaultdict (set)
        try:
            for x in xrefs: srcseq[x.TARG.src].add (x.TARG.seq)
        except AttributeError:
              # Assume attribute error is due to missing .TARG, presumably
              # because jdb,augment_xrefs() was not called on xrefs.  In
              # this case bail since we can't group by seq number if seq
              # numbers (which are in .TARG entries) aren't available.
            return

          # Get a count of all the "active" entries for each (corpus,
          # seq-number) pair and put in dict 'seq_count' keyed by (corpus,
          # seq) with values being the corresponding counts.
        seq_counts = {};  args = []
        for src,seqs in list(srcseq.items()):
            sql = "SELECT src,seq,COUNT(*) FROM entr " \
                  "WHERE src=%%s AND seq IN(%s) AND stat=%%s GROUP BY src,seq" \
                  % ",".join (["%s"]*len(seqs))
            args.append (seqs)
            cur.execute (sql, [src]+list(seqs)+[KW.STAT['A'].id])
            rs = cur.fetchall()
            for r in rs: seq_counts[(r[0],r[1])] = r[2]
            # 'seq_counts' is now a dict, keyed by (src,seq) 2-tuple and
            # values being the number of active entries with that src,seq.

          # Categorize each xref by source (.entr, .sens, .typ, .notes),
          # then target (corpus, seq), then, sense list.  Gather a count
          # of the number of xrefs per category in dict 'collect'.
          # Don't count any non-active (rejected or deleted) ones,
        collect = defaultdict(lambda:defaultdict(set))
        for x in xrefs:
              # JEL only represents xrefs to stat=A entries.
            if not hasattr (x, 'TARG'): continue
            if x.TARG.stat != KW.STAT['A'].id: continue
            key1 = (x.entr,x.sens,x.typ,x.notes)
            key2 = (x.TARG.src,x.TARG.seq)
            collect[key1][key2].add (x.TARG.id)

          # Go through the xrefs again, skipping non-active ones, and re-
          # categorizing as above, compare to number of xrefs for that
          # category set (counts are in 'collect') with the total number
          # of potential target entries in the database.  If the numbers
          # are equal, there is an xref to every target and we can use a
          # seq-style xref for that set of xrefs and we mark (only) the
          # first xref of each set with a .SEQ attribute.
        marked = defaultdict(lambda:defaultdict(lambda:defaultdict(bool)))
        for x in xrefs:
            if not hasattr (x, 'TARG'): continue
            if x.TARG.stat != KW.STAT['A'].id: continue
            #if getattr (x, 'SEQ', None) is None:
            key1 = (x.entr,x.sens,x.typ,x.notes)
            key2 = (x.TARG.src,x.TARG.seq)
            if len (collect[key1][key2]) == seq_counts[key2]:
                key3 = tuple (getattr (x, '_xsens', (x.xsens,)))
                if marked[key1][key2][key3]:
                    x.SEQ = False
                else:
                    marked[key1][key2][key3] = x.SEQ = True

def xresolv (dbh, entr):
        # Try to resolve any unresolved xrefs (in the ._xrslv list for each
        # sense) in Entr object 'entr'.  Those that can be resolved will be
        # removed from the ._xrslv list and corresponding xrefs added to the
        # ._xref list on the same sense.

        errs = []
        for ns, s in enumerate (entr._sens, start=1):
            unsuccessful = []
            for nx, xr in enumerate (s._xrslv):
                slist = None if not xr.tsens else [xr.tsens]
                seq = xr.vseq
                corpid = xr.vsrc
                  # 'corpid' may be a corpus name, corpus id number,
                  #  or None (resolve to an entry in the same corpus).
                if corpid is None: corpid = entr.src
                elif corpid != None:
                    try: corpid = int(corpid)
                    except ValueError: corpid = KW.SRC[corpid].id
                try:
                    xrefs = resolv_xref (dbh, xr.typ, xr.rtxt, xr.ktxt, slist,
                                         seq, corpid)
                except ValueError as e:
                   #print("jdb.xresolv: %s[%s][%s]: %s"%(entr.seq, ns, nx, e),
                   #      file=sys.stderr)
                    unsuccessful.append (xr)
                    errs.append ((ns, nx, str(e)))
                else:
                    s._xref.extend (xrefs)
            s._xrslv = unsuccessful
        return errs

def resolv_xref (dbh, typ, rtxt, ktxt, slist=None, enum=None, corpid=None,
                 one_entr_only=True, one_sens_only=False, krdetect=False):

        # Find entries and their senses that match 'ktxt','rtxt','enum'.
        # and return a list of augmented xref records that points to
        # them.  If a match is not found (because nothing matches, or
        # the 'one_entr_only' or 'one_sens_only' criteria are not satisfied),
        # a ValueError is raised.
        #
        # dbh (dbapi cursor) -- Handle to open database connection.
        # typ (int) -- Type of reference per table kwxref.
        # rtxt (string or None) -- Cross-ref target(s) must have this
        #   reading text.  May be None if 'ktxt' is non-None, or if
        #   'enum' is non-None.
        # ktxt (string or None) -- Cross-ref target(s) must have this
        #   kanji text.  May be None if 'rtxt' is non-None, or if
        #   'enum' is non-None.
        # slist (list of ints or None) -- Resolved xrefs will be limited
        #   to these target senses.  A Value Error is raised in a sense
        #   is given in 'slist' that does not exist in target entry.
        # enum (int or None) -- If 'corpid' (below) value is non-None
        #   then this parameter is interpreted as a seq number.  Other-
        #   wise it is interpreted as an entry id number.
        # corpid (int or None) -- If given search for target will be
        #   limited to the given corpus, and 'enum' if given will be
        #   interpreted as a seq number.  If None, 'enum' if given
        #   will be interpreted as an entry id number, otherwise,
        #   all entries will be searched for matching ktxt/rtxt.
        # one_entr_only (bool) -- Raise error if xref resolves to more
        #   than one set of entries having the same seq number.  Regard-
        #   less of this value, it is always an error if 'slist' is given
        #   and the xref resolves to more than one set of entries having
        #   the same seq number.
        # one_sens_only (bool) -- Raise error if 'slist' not given and
        #   any of the resolved entries have more than one sense.
        #
        # resolv_xref() returns a list of augmented xrefs (see function
        # augment_xrefs() for description) except each xref has no {entr},
        # {sens}, or {xref} elements, since those will be determined by
        # the parent sense to which the xref will be attached.
        #
        # Prohibited conditions such as resolving to multiple seq sets
        # when the 'one_entr_only' flag is true, are signaled by raising
        # a ValueError.  The caller may want to call resolv_xref() within
        # a "try" block to catch these conditions.

        #FIXME: Use a custom error rather than ValueError to signal
        # resolution failure so the caller can distinguish failure
        # to resolve from a parameter error that causes a ValueError.

        if not rtxt and not ktxt and not enum:
            raise ValueError ("No rtxt, ktxt, or enum value, need at least one.")

          # If there is only one of 'ktxt', 'rtxt', and if 'krdetect' is true,
          # we take it that whichever of 'ktxt', 'rtxt' was given could be
          # be either kanji or reading and we will test and reassign correctly
          # to 'ktxt' or 'rtxt' according to the result.
        if krdetect and (ktxt or rtxt) and not (ktxt and rtxt):
            if ktxt and not jstr_keb (ktxt): ktxt, rtxt = rtxt, ktxt
            if rtxt and     jstr_keb (rtxt): ktxt, rtxt = rtxt, ktxt

          # Build a string for use in error messages.
          #FIXME: ktst and rtxt should be quoted if jel would require
          # quotes to avoid a confusing message when ktxt or rtxt has
          # middot character since middot also used to join them.
        krtxt = (ktxt or '') + ('\u30fb' if ktxt and rtxt else '') + (rtxt or '')

          # Build a SQL statement that will find all entries
          # that have a kanji and reading matching 'ktxt' and
          # 'rtxt'.  If further restrictions are necessary (such
          # as limiting the search to entries in a specific
          # corpus), they are given the the 'whr' and 'wargs'
          # parameters.

        condlist = []
        if ktxt: condlist.append (('kanj k', "k.txt=%s", [ktxt]))
        if rtxt: condlist.append (('rdng r', "r.txt=%s", [rtxt]))
          # Exclude Deleted and Rejected entries from consideration.
        condlist.append (('entr e', 'e.stat=%d' % (KW.STAT['A'].id), []))
        if enum and not corpid:
            condlist.append (('entr e', 'e.id=%s', [enum]))
        elif enum and corpid:
            condlist.append (('entr e', 'e.seq=%s AND e.src=%s', [enum,corpid]))
        elif not enum and corpid:
            condlist.append (('entr e', 'e.src=%s', [corpid]))

        sql, sql_args = build_search_sql (condlist)
        tables = ('entr','rdng','kanj','sens','gloss')
        entrs = entrList (dbh, sql, sql_args, tables=tables)

        if not entrs: raise ValueError ('No entry found for cross-reference "%s".' % krtxt)
        seqcnt = len (set ([x.seq for x in entrs]))
        if seqcnt > 1 and (one_entr_only or slist):
            raise ValueError ('Xref "%s": Multiple entries found.' % krtxt)

        # For every target entry, get all it's sense numbers.  We need
        # these for two reasons: 1) If explicit senses were targeted we
        # need to check them against the actual senses. 2) If no explicit
        # target senses were given, then we need them to generate erefs
        # to all the target senses.
        # The code currently assumes that sense numbers of database entries
        # are always sequential and start at 1.

        if slist:
              # The submitter gave some specific senses that the xref will
              # target, so check that they actually exist in the target entry(s).
            for e in entrs:
                snums = len (e._sens); nosens = []
                for s in slist:
                    if s<1 or s>snums:
                        raise ValueError ('Xref "%s": Sense %s not in target id %d.'
                                          % (krtxt, s, e.id))
        else:
              # No specific senses given, so this xref(s) should target every
              # sense in the target entry(s), unless $one_sens_only is true
              # in which case all the xrefs must have only one sense or we
              # raise an error.
            entr_multsens = first (entrs, lambda x: len(x._sens)>1)
            if one_sens_only and entr_multsens:
                raise ValueError ('Xref "%s": Target entry id %d has more than one sense.'
                                  % (krtxt, entr_multsens.id))

          # Create an xref object for each entry/sense.

        xrefs = []
        for e in entrs:
              # All xrefs require an .rtxt and/or.ktxt value which is the
              # position (indexed from 1) of a reading or kanji in the target
              # entry's reading of kanji lists, of the reading or kanji to
              # to be used when displaying the xref.  'nrdng' and 'nkanj'
              # will be set to these positions.

            nrdng = nkanj = None
            if not rtxt and not ktxt:
                  # If no rtxt or ktxt received from caller, then call
                  # headword() which will find reasonable values taking
                  # things like "nokanji", "uk", and other restrictions
                  # into account.  headword() returns rdng/kanj positions
                  # (ints, base-1).
                  # FIXME: 'e' here is an abbreviated Entr without restr
                  #  or misc data, which headword() needs to generate good
                  #  results.  So currently it will just return the numbers
                  #  for the first rdng/kanj.
                nrdng, nkanj = headword (e)

              # If the caller did provide explicit rtxt and/or ktxt strings,
              # find their position in the entry's rdng or kanj lists.
            if rtxt:
                try: nrdng = [x.txt for x in e._rdng].index (rtxt) + 1
                except ValueError: raise ValueError ("No reading '%s' in entry %d" % (rtxt, e.id))
            if ktxt:
                try: nkanj = [x.txt for x in e._kanj].index (ktxt) + 1
                except ValueError: raise ValueError ("No kanji '%s' in entry %d" % (ktxt, e.id))

              # Create an augmented xref for each target sense.
            for s in e._sens:
                if not slist or s.sens in slist:
                    x = Xref (typ=typ, xentr=e.id, xsens=s.sens, rdng=nrdng, kanj=nkanj)
                    x.TARG = e
                    xrefs.append (x)
        return xrefs

def headword (entr):
        # Return a 2-tuple giving the rdng / kanj numbers (base-1)
        # or reading-kanji pair that represents the entry and which
        # takes into consideration restrictions and 'uk' sense
        # tags.  Either element of the 2-tuple, but not both,
        # may be None if a reading of kanji element is not available
        # or not appropriate.
        # FIXME: I don't know how to pick headword.  Since there is
        #  is no mention of "headword" in the JMdict DTD, I am not
        #  even sure what a headword is.  Code below is just a guess.

        global KW
        rdngs = getattr (entr, '_rdng', [])
        kanjs = getattr (entr, '_kanj', [])
        if not rdngs and not kanjs:
            raise ValueError ("Entry has no readings and no kanji")
        if not rdngs: return None, 1
        if not kanjs: return 1, None

          # If the first reading is "nokanji", return only it.
        if rdngs and len(getattr (rdngs[0], '_restr', [])) \
                  == len(getattr (entr, '_kanj', [])):
            return 1, None

          # If first sense is 'uk', return only first reading.
        uk = KW.MISC['uk'].id in [x.kw for x in
                getattr (getattr (entr, '_sens', [None])[0], '_misc', [])]
        if uk:
            stagr = getattr (entr._sens[0], '_stagr', [])
            for n, r in enumerate (rdngs):
                if not isin (r, stagr): return n+1, None

          # Otherwise return the first reading-kanji pair allowed
          # by restrs, ordering by kanji before selection.
          # FIXME: does not consider stagr, stagk.
        rk = list (restr_expand (entr))
        rk.sort (key=lambda x: (x[1],x[0]))
        nr, nk = rk[0]
        return nr+1, nk+1

#-------------------------------------------------------------------
# The following functions deal with history lists.
#-------------------------------------------------------------------

def add_hist (
    entr,       # Entry object (.stat, .unap, .dfrm must be correctly set).
    pentr,      # Parent of 'entr' (an Entr object) or None if no parent.
    userid,     # Userid from session or None.
    name,       # Submitter's name.
    email,      # Submitter's email address.
    notes,      # Comments for history record.
    refs,       # Reference comments for history record.
    use_parent): # If false, return 'entr' with updated hist including diff.
                # If true, return 'pentr' (or raise error) with updated
                # hist and diff=''.  Latter is used when we want to ignore
                # any changes to the entry made by the submitter, as in when
                # he/she has requested deletion of the entry.
        # Attach history info to an entry.  The history added is the
        # history from entry 'pentr' to which a new history record,
        # generated from the parameters to this function, is appended.
        # Any existing hist on the 'entr' is ignored'.
        # If 'use_parent' is true, the history list is attached to the
        # 'pentr' entry object, and that object returned.  If
        # 'use_parent' is false, the history list is attached to the
        # 'entr' object, and that object returned.

        if pentr and (pentr.id is None or pentr.id != entr.dfrm):
            raise ValueError ("Entr 'drfm' (%s) does not match parent entr id (%s)"
                              % (entr.dfrm, pentr.id))
        if not pentr:
            if entr.dfrm: raise ValueError ("Entr has parent %s but no 'pentr' arg given." \
                                            % (entr.dfrm))
            if use_parent: raise ValueError ("'use_parent' requested but no 'pentr' arg given.")

        h = Hist (dt= datetime.datetime.utcnow().replace(microsecond=0),
                stat=entr.stat, unap=entr.unap, userid=userid, name=name,
                email=email, diff=None, notes=notes, refs=refs)

        e = entr
        if use_parent:
            e = pentr
            e.stat, e.unap, e.dfrm = entr.stat, entr.unap, entr.dfrm
        if pentr:
            e._hist = getattr (pentr, '_hist', [])
        else:
            e._hist = []
        if pentr:
            h.diff = fmtxml.entr_diff (pentr, e, n=0) \
                        if pentr is not e \
                        else ''
        e._hist.append (h)
        return e

#-------------------------------------------------------------------
# The following functions deal with writing entries to a database.
#-------------------------------------------------------------------

def addentr (cur, entr):
        # Write the entry, 'entr', to the database open on connection
        # 'cur'.
        # WARNING: This function will modify the values of some of the
        # attributes in the entr object: entr.id, entr.seq (if None),
        # all the sub-object pk attributes, e.g., rdng.entr, rdng.rdng,
        # gloss.entr, gloss.sens, gloss.gloss, etc.

        # Note the some of the values in the entry object ignored when
        # writing to the database.  Specifically:
        #   entr.id -- The database entr record is written to database
        #     ignoring the entr.id value in the entr object.  This
        #     results in the database assigning the next auto-sequence
        #     id number to the id column in the entr row.
        #     This id number is read back, and the entr object's .id
        #     attribute updated with it.  All sub-object foreign key
        #     .entr attributes (e.g. rdng.entr, gloss.entr, etc) are
        #     also set to that value.
        #   sub-object id's (rdng.rdng, etc) -- Are rewritten as the
        #      object's index position in it's list, plus one.  That
        #      number is also used when writing to the database.
        #   entr.seq -- Used if present and not false, but otherwise,
        #      the entr record is written without a seq number causing
        #      the database's entr table trigger to assign an appropriate
        #      seq number.  That number is read back and the entr object's
        #      .seq attribute updated with it.
        # The caller is responsible for starting a transaction prior to
        # calling this function, and doing a commit after, if an atomic
        # write of the complete entry is desired.

          # Insert the entr table row.  If 'seq' is None, an appropriate
          # seq number will be automatically generated by a trigger on the
          # entr table, using a sequence table named in the kwsrc table row
          # corresponding to 'src'.
        dbinsert (cur, "entr", ['src','stat','seq','dfrm','unap',
                                'srcnote','notes','idx'], entr)
          # Postgresql function lastval() will contain the auto-assigned
          # seq number if one was generated.  We need to get the auto-
          # assigned id number directly from its sequence.
        if not getattr (entr, 'seq', None):
            cur.execute ("SELECT LASTVAL()")
            entr.seq = cur.fetchone()[0]
        cur.execute ("SELECT CURRVAL('entr_id_seq')")
        eid = cur.fetchone()[0]
          # Update all the foreign key attributes in the entr object to
          # match the real entr.id  setkeys() will also set the relative
          # part of each row object's pk (rdng.rdng, gloss.sens, gloss.gloss,
          # etc.) to the objects position (0-based) in it's list plus one,
          # overwriting any preexisting values.
        setkeys (entr, eid)
          # Walk through the entr object tree writing each row object to
          # a new database row.
        for h in entr._hist:   dbinsert (cur, "hist", ['entr','hist','stat','unap','dt','userid',
                                                       'name','email','diff','refs','notes'], h)
        for k in entr._kanj:
            dbinsert (cur, "kanj", ['entr','kanj','txt'], k)
            for x in k._inf:   dbinsert (cur, "kinf",  ['entr','kanj','ord','kw'], x)
            for x in k._freq:  dbinsert (cur, "freq",  ['entr','rdng','kanj','kw','value'], x)
        for r in entr._rdng:
            dbinsert (cur, "rdng", ['entr','rdng','txt'], r)
            for x in r._inf:   dbinsert (cur, "rinf",  ['entr','rdng','ord','kw'], x)
            for x in r._restr: dbinsert (cur, "restr", ['entr','rdng','kanj'], x)
            for x in r._freq:  dbinsert (cur, "freq",  ['entr','rdng','kanj','kw','value'], x)
            for x in r._snd:   dbinsert (cur, "rdngsnd", ['entr','rdng','ord','snd'], x)
        for s in entr._sens:
            dbinsert (cur, "sens", ['entr','sens','notes'], s)
            for g in s._gloss: dbinsert (cur, "gloss", ['entr','sens','gloss',
                                                        'lang','ginf','txt'], g)
            for x in s._pos:   dbinsert (cur, "pos",   ['entr','sens','ord','kw'], x)
            for x in s._misc:  dbinsert (cur, "misc",  ['entr','sens','ord','kw'], x)
            for x in s._fld:   dbinsert (cur, "fld",   ['entr','sens','ord','kw'], x)
            for x in s._dial:  dbinsert (cur, "dial",  ['entr','sens','ord','kw'], x)
            for x in s._lsrc:  dbinsert (cur, "lsrc",  ['entr','sens','ord','lang','txt',
                                                        'part','wasei'], x)
            for x in s._stagr: dbinsert (cur, "stagr", ['entr','sens','rdng'], x)
            for x in s._stagk: dbinsert (cur, "stagk", ['entr','sens','kanj'], x)
            for x in s._xref:  dbinsert (cur, "xref",  ['entr','sens','xref','typ','xentr',
                                                        'xsens','rdng','kanj','notes'], x)
            for x in s._xrer:  dbinsert (cur, "xref",  ['entr','sens','xref','typ','xentr',
                                                        'xsens','rdng','kanj','notes'], x)
            for x in s._xrslv: dbinsert (cur,"xresolv",['entr','sens','typ','ord','rtxt','ktxt',
                                                        'tsens','vsrc','vseq','notes','prio'], x)
        for x in entr._snd:    dbinsert (cur, "entrsnd", ['entr','ord','snd'], x)
        for x in entr._grp:    dbinsert (cur, "grp",     ['entr','kw','ord'], x)
        if entr.chr:
            c = entr.chr
            dbinsert (cur, "chr", ['entr','chr','bushu','strokes','freq','grade','jlpt','radname'], c)
            for x in c._cinf:  dbinsert (cur, "cinf",  ['entr','kw','value','mctype'], x)
        return eid, entr.seq, entr.src

def setkeys (e, id=0):
          # Set the foreign and primary key values in each record
          # in the entry, 'e'.  If 'id' is provided, it will be used
          # as the entry id number.  Otherwise, it is assumed that
          # the id number has already been set in 'e'.
          # Please note that this function assumes that items with
          # multiple parents such as '_freq', '_restr', etc, are
          # listed under both parents.
        if id!=0: e.id = id
        else: id = e.id
        for n,r in enumerate (e._rdng):
            n += 1;                          r.entr, r.rdng = id, n
            for p,x in enumerate (r._inf):   x.entr, x.rdng, x.ord = id, n, p+1
            for x in r._freq:                x.entr, x.rdng = id, n
            for x in r._restr:               x.entr, x.rdng = id, n
            for m,x in enumerate (r._snd):   x.entr, x.rdng, x.ord = id, n, m+1
        for n,k in enumerate (e._kanj):
            n += 1;                          k.entr, k.kanj = id, n
            for p,x in enumerate (k._inf):   x.entr, x.kanj, x.ord = id, n, p+1
            for x in k._freq:                x.entr, x.kanj = id, n
        for n,s in enumerate (e._sens):
            n += 1;                          s.entr, s.sens = id, n
            for m,x in enumerate (s._gloss): x.entr,x.sens,x.gloss = id, n, m+1
            for p,x in enumerate (s._pos):   x.entr, x.sens, x.ord = id, n, p+1
            for p,x in enumerate (s._misc):  x.entr, x.sens, x.ord = id, n, p+1
            for p,x in enumerate (s._fld):   x.entr, x.sens, x.ord = id, n, p+1
            for p,x in enumerate (s._dial):  x.entr, x.sens, x.ord = id, n, p+1
            for p,x in enumerate (s._lsrc):  x.entr, x.sens, x.ord = id, n, p+1
            for x in s._stagr:               x.entr, x.sens = id, n
            for x in s._stagk:               x.entr, x.sens = id, n
            for m,x in enumerate (s._xrslv): x.entr, x.sens, x.ord  = id, n, m+1
            for m,x in enumerate (s._xref):  x.entr, x.sens, x.xref = id, n, m+1
            for x in s._xrer:                x.xentr, x.xsens = id, n
        for n,x in enumerate (e._snd):       x.entr, x.ord = id, n+1
        for n,x in enumerate (e._hist):      x.entr, x.hist = id, n+1
          # Note: do not set grp.ord; order is based on position in grp
          #  table, not entr._grp list.
        for x in e._grp:                     x.entr = id
        if e.chr:
            c = e.chr;  c.entr = id
            for x in c._cinf:                x.entr = id
        for x in e._krslv:                   x.entr = id

#-------------------------------------------------------------------
# The following functions deal with searches.
#-------------------------------------------------------------------

def build_search_sql (condlist, disjunct=False, allow_empty=False):

        # Build a sql statement that will find the id numbers of
        # all entries matching the conditions given in <condlist>.
        # Note: This function does not provide for generating
        # arbitrary SQL statements; it is only intended to support
        # limited search capabilities that are typically provided
        # on a search form.
        #
        # <condlist> is a list of 3-tuples.  Each 3-tuple specifies
        # one condition:
        #   0: Name of table that contains the field being searched
        #     on.  The name may optionally be followed by a space and
        #     an alias name for the table.  It may also optionally be
        #     preceded (no space) by an asterisk character to indicate
        #     the table should be joined with a LEFT JOIN rather than
        #     the default INNER JOIN.
        #     Caution: if the table is "entr" it *must* have "e" as an
        #     alias, since that alias is expected by the final generated
        #     sql.
        #   1: Sql snippet that will be AND'd into the WHERE clause.
        #     Field names must be qualified by table.  When looking
        #     for a value in a field.  A sql parameter marker ("%s" for
        #     the Postgresql psycopg2 adapter) may (and should) be used
        #     where possible to denote an exec-time parameter.  The value
        #     to be used when the sql is executed is provided in the
        #     3rd member of the tuple (see #2 next).
        #   2: A sequence of argument values for any exec-time parameters
        #     ("%s") used in the second value of the tuple (see #1 above).
        #
        # Example:
        #     [("entr e","e.stat=4", ()),
        #      ("gloss", "gloss.txt LIKE %s", ("'%'+but+'%'",)),
        #      ("pos","pos.kw IN (%s,%s,%s)",(8,18,47))]
        #
        #   This will generate the SQL statement and arguments:
        #     "SELECT e.id FROM (((entr e INNER JOIN sens ON sens.entr=entr.id)
        #       INNER JOIN gloss ON gloss.entr=entr.id)
        #       INNER JOIN pos ON pos.entr=entr.id)
        #       WHERE e.stat=4 AND (gloss.txt=%s) AND (pos IN (%s,%s,%s))"
        #     ('but',8,18,47)
        #   which will find all entries that have a gloss containing the
        #   substring "but" and a sense with a pos (part-of-speech) tagged
        #   as a conjunction (pos.kw=8), a particle (18), or an irregular
        #   verb (47).

        # The following check is to reduce the effect of programming
        # errors that pass an empty condlist, which in turn will result
        # in generating sql that will attempt to retrieve every entry
        # in the database.  It does not guarantee reasonable behavior
        # though: a condlist of [('entr', 'NOT unap', [])] will produce
        # almost the same results.

        if not allow_empty and not condlist:
            raise ValueError ("Empty condlist parameter")

        # 'fclause' will become the FROM clause of the generated sql.  Since
        # all queries will require table "entr" to be included, we start off
        # with that table in the clause.

        fclause = 'entr e'
        regex = re.compile (r'^([*])?(\w+)(\s+(\w+))?$')
        wclauses = [];  args = [];  havejoined = {}

        # Go through the condition list.  For each 3-tuple we will add the
        # table name to the FROM clause, and the where and arguments items
        # to their own arrays.

        for tbl,cond,arg in condlist:

            # To make it easier for code generating condlist's allow
            # them to generate empty cond elements that we skip here.

            if not cond: continue

            # The table name may be preceded by a "*" to indicate that
            # it is to be joined with a LEFT JOIN rather than the usual
            # INNER JOIN".  It may also be followed by a space and an
            # alias name.  Unpack these things.

            mg = regex.search (tbl)
            jt,tbl,alias = mg.group (1,2,4)
            if jt: jointype = 'LEFT JOIN'
            else: jointype = 'JOIN'

            # Add the table (using the desired alias if any) to the FROM
            # clause (except if the table is "entr" which is aleady in
            # the FROM clause).

            tbl_w_alias = tbl
            if alias: tbl_w_alias += " " + alias
            if tbl != 'entr' and tbl_w_alias not in havejoined:
                fclause += ' %s %s ON %s.entr=e.id' \
                           % (jointype,tbl_w_alias,(alias or tbl))
                havejoined[tbl_w_alias] = True
            else:
                # Sanity check...
                if tbl == 'entr' and alias and alias != 'e':
                    raise ValueError (
                        "table 'entr' in condition list uses alias other than 'e': %s" % alias)

            # Save the cond tuple's where clause and arguments each in
            # their own array.

            wclauses.append (cond)
            args.extend (arg)

        # AND all the where clauses together.

        if disjunct: conj = ' OR '
        else: conj = ' AND '
        where = conj.join ([x for x in wclauses if x])
          # If 'condlist' was empty, 'where' will be empty.
        if not where: where = "True"

        # Create the sql we need to find the entr.id numbers from
        # the tables and where conditions given in the @$condlist.

        sql = "SELECT DISTINCT e.id FROM %s WHERE %s" % (fclause, where)

        # Return the sql and the arguments which are now suitable
        # for execution.

        return sql, args

def autocond (srchtext, srchtype, srchin, inv=None, alias_suffix=''):
        #
        # srchtext -- The text to search for.
        #
        # srchtype: where to search of 'srchtext' in the txt column.
        #   1 -- "Is", exact (and case-sensitive) match required.
        #   2 -- "Starts", 'srchtext' matched a leading substring
        #        of the target string.
        #   3 -- "Contains", 'srchtext' appears as a substring anywhere
        #        in the target text.
        #   4 -- "Ends", 'srchtext' matches at the end of the target text.
        #
        # srchin: table to search in
        #   1 -- auto (choose table based on presence of kanji or kana
        #        in 'srchtext'.
        #   2 -- kanj
        #   3 -- kana
        #   4 -- gloss
        #
          # The following generates implements case insensitive search
          # for gloss searches, and non-"is" searches using the sql LIKE
          # operator.  The case-insensitive part is a work-around for
          # Postgresql's lack of support for standard SQL's COLLATION
          # feature.  We can't use ILIKE for case-insensitive searches
          # because it won't use an index and thus is very slow (~25s
          # vs ~.2s with index on developer's machine.  So instead, we
          # created two functional indexes on gloss.txt: "lower(txt)"
          # and "lower(txt) varchar-pattern-ops".  The former will be
          # used for "lower(xx)=..." searches and the latter for
          # "lower(xx) LIKE ..." searches.  So when do a gloss search,
          # we need to lowercase the search text, and generate a search
          # clause in one of the above forms.
          #
          # To-do: LIKE 'xxx%' doesn't use index unless the argument value
          # is embedded in the sql (which we don't currently do).  When
          # the 'xxx%' is supplied as a separate argument, the query
          # planner (runs when the sql is parsed) can't use index because
          # it doesn't have access to the argument (which is only available
          # when the query is executed) and doesn't know that it is not
          # something like '%xxx'.

        sin = stype = m = 0
        try: sin = int(srchin)
        except ValueError: pass
        try: stype = int(srchtype)
        except ValueError: pass

        if sin==1: m = jstr_classify (srchtext)
        if   sin==3 or (sin==1 and jstr_reb (m)):  tbl,col = 'rdng r%s',  'r%s.txt'
        elif sin==4 or (sin==1 and jstr_gloss(m)): tbl,col = 'gloss g%s', 'g%s.txt'
        elif sin==2 or sin==1:                     tbl,col = 'kanj k%s',  'k%s.txt'
        else:
            raise ValueError ("autocond(): Bad 'srchin' parameter value: %r" % srchin)
        tbl %= alias_suffix;  col %= alias_suffix
        if tbl.startswith("gloss "):
            srchtext = srchtext.lower();
            col = "lower(%s)" % col
        if   stype == 1: whr,args = '%s=%%s',      [srchtext]
        elif stype == 2: whr,args = '%s LIKE %%s', [srchtext + '%']
        elif stype == 3: whr,args = '%s LIKE %%s', ['%' + srchtext + '%']
        elif stype == 4: whr,args = '%s LIKE %%s', ['%' + srchtext]
        else:
            raise ValueError ("autocond(): Bad 'srchtype' parameter value: %r", srchtype)
        if inv: whr = "NOT %s" % whr
        return tbl, (whr % col), args

def kwnorm (kwtyp, kwlist, inv=None):
        """
        Return either the given 'kwlist' or its complement
        (and the string "NOT"), whichever is shorter.

        Given as list of kw's all from the same domain, see if
        it is longer than half the length of all kw's in the domain.
        If so, return the shorter complement of the given list, along
        with an inversion string, "NOT", which can be used to build
        a short SQL WHERE clause that will produce the same results
        as the longer given kw list.
        """
        global KW
        if inv is None:
            if 'NOT' in kwlist: kwlist.remove ('NOT'); inv = True
            else: inv = False
        nkwlist = []
        for x in kwlist:
            try: x = int(x)
            except ValueError: pass
            try: v = getattr (KW, kwtyp)[x].id
            except KeyError as e:
                raise ValueError ("'%s' is not a known %s keyword" % (x, kwtyp))
            nkwlist.append (v)
        kwall = KW.recs(kwtyp)
        inv_is_shorter = len (nkwlist) > len (kwall) / 2
        if inv_is_shorter:
            nkwlist = [x.id for x in kwall if x.id not in nkwlist]
        invrv = 'NOT ' if inv_is_shorter != bool(inv) else ''
        return nkwlist, invrv

def is_p (entr):
        """
        Return a bool value indicating whether or not an entry
        object 'entr' meets the wwwjdic criteria for a "P"
        (popular) marker.  Currently true if any of the entry's
        kanji or readings have a FREQ tag of "ichi1", "gai1",
        "spec1", "spec2" or "news1".
        Ref: http://www.edrdg.org/jmdict/edict_doc.html#IREF05 (sec. E)
        """
        for r in getattr (entr, '_rdng', []):
            for f in getattr (r, '_freq', []):
                if is_pj (r): return True
        for k in getattr (entr, '_kanj', []):
            for f in getattr (k, '_freq', []):
                if is_pj (k): return True
        return False

def is_pj (kr):
        """
        Return True if the Kanj or Rdng object, 'kr', meets the
        wwwjdic criteria for a "P" (popular) marker.  Currently
        true if the object has a FREQ tag of "ichi1", "gai1",
        "news1", "spec1" or "spec2".
        """
        for f in getattr (kr, '_freq', []):
              # ichi=1, gai=2, spec=4, 7=news
            if f.kw==4 or (f.kw in (1,2,7) and f.value==1): return True
        return False

#-------------------------------------------------------------------
#   The following functions are for accessing entry and reading
#   audio clips.
#-------------------------------------------------------------------

class Snds:
    def __init__ (self, cur):
        self.cur = cur
        sql = "SELECT * FROM sndvol"
        self.vols = dbread (cur, sql)
        sql = "SELECT * FROM sndfile"
        self.sels = dbread (cur, sql)
        mup (None, self.vols,  ['id'], self.sels, ['vol'],  'VOL')

    def augment_snds (sndrecs):
        augment_snds (self.cur, sndrecs, self.sels)

def collect_snds (entrs):
        # Given a list of Entr objects, 'entrs', collect all the
        # snd's on their Entr and Rdng ._snd lists into a single
        # list which is returned, typically so the caller can call
        # augment_snds() on them, for example:
        #   augment_snds (dbh, collect_snds (entrs))
        # (The Entr._snd and Rdng._snd lists are not changed.)

        snds = []
        for e in entrs:
           snds.extend (getattr (e, '_snd', []))
           for r in getattr (e, '_rdng', []):
                snds.extend (getattr (r, '_snd', []))
        return snds

def augment_snds (dbh, snds):
        # Augment a set of snds with extra information about the
        # snds' clips.  After augment_snds() returns, each snd
        # item in 'snds' will have an additional attribute, "CLIP"
        # that is a reference to a Clip object describing the snd's
        # clip information.

        if not snds: return
        sql = "SELECT * FROM vsnd WHERE id IN (%s)" % ','.join(['%s']*len(snds))
        args = [x.snd for x in snds]
        data = dbread (dbh, sql, args,
                       ('id','strt','leng','sfile','sdir','iscd','sdid','trns'))
        mup (None, data, ['id'], snds, ['snd'], 'CLIP')

def xx_augment_snds (cur, sndrecs, sels=None):
        """
        Augments entrsnd or rdngsnd records ('sndrecs') with sound
        objects that describe the sound clip identified in each sndrec
        only by id number.  The augmenting object is attached to each
        sndrec items in attribute 'CLIP'.

        cur -- An open DBAPI cursor to the jmdict database containing
            the sound records of interest.
        sndrecs -- A list of entrsnd or rdngsnd records.
        sels -- If provided, is a list of sound selection (aka file)
            records that have already matched it with volume records.
            If None, the appropriate selection and volume records will
            be read from the database.
        """
        ids = [x.snd for x in sndrecs]
        snds = get_recs (cur, 'snd', ids)
        if sels is not None:
            sels = get_recs (cur, 'sndfile', [x.file for x in t['snd']])
            vols  = get_recs (cur, 'sndvol',  [x.vol  for x in t['sndfile']])
            mup (None, vols,  ['id'], sels, ['vol'],  'VOL')
        mup (None, sels, ['id'], snds, ['file'], 'FILE')
        mup (None, snds, ['id'], sndrecs, ['snd'],  'CLIP')

#@memoize
def get_recs (cur, table, ids):
        s = set (ids)
        sql = "SELECT * FROM %s WHERE id IN (%s)" % (table, ','.join(['%s'] * len (s)))
        rs = dbread (cur, sql, list (s))
        return rs

def iter_snds (cur):
        sql = "SELECT * FROM sndvol"
        vols = dbread (cur, sql)
        sql = "SELECT * FROM sndfile"
        sels = dbread (cur, sql)
        sql = "SELECT * FROM snd"
        snds = dbread (cur, sql)
        mup ('_snd',  sels, ['id'], snds, ['file'], None)
        mup ('_file', vols, ['id'], sels, ['vol'],  None)
        return vols, sels, snds

class Kwds:
    """
    This class stores data from the jmdictdb kw* tables.  The
    data in these tables are typically static and small in size,
    so it is efficient to read them once when an app starts.
    This class allows the data to be read either from a jmdictdb
    database, or from kw*.csv files in a directory.  After
    initialization, an instance will have a set of attributes,
    each corresponding to a table.  The value of each will be
    a mapping containing keys that are the tables row's 'id'
    numbers and 'kw' strings.  The keys are distinguishable
    because the former will always be int's and the latter,
    str's.
    The value associated with of each key is a DbRow object
    containing a table row.  Note that because each row in
    indexed under both it's id and kw, there will appear to be
    twice as many rows are there actually are in the corresponding
    table.  Use method .recs() to get a single set of rows.

    Typical use of this class in an app:

        KW = jdb.Kwds (cursor)  # But note this is done by dbOpen().
        KW.POS['adj-na'].id     # => The id number of PoS 'adj-na'.
        KW.DIAL[dialect].descr  # => The description string for
                                #  'dialect'. 'dialect' may be
                                #  either an int id number or kw
                                #  string.

    For the special (but common) case of mapping a kw to an id number,
    each row in a Kwds instance also creates an attribute of the form,
    XXX_kw where XXX of the table identifier, and kw is the kw string.
    The attribute's value is the kw's id number.  For example,

        KW.POS_vt       # => 50.

    If the kw string contains a "-", it is changed to a "_" in the
    attribute:

        KW.POS_adj_na   # => 2
    """

    Tables = {'DIAL':"kwdial", 'FLD' :"kwfld",  'FREQ':"kwfreq", 'GINF' :"kwginf",
              'KINF':"kwkinf", 'LANG':"kwlang", 'MISC':"kwmisc", 'POS'  :"kwpos",
              'RINF':"kwrinf", 'STAT':"kwstat", 'XREF':"kwxref", 'CINF' :"kwcinf",
              'SRC' :"kwsrc",  'SRCT':"kwsrct", 'GRP' :"kwgrp",  'COPOS':"vcopos"}
    # Re COPOS, see comments in pg/conj.sql:vcopos, jmcgi.add_pos_flag() and IS-226.

    def __init__( self, cursor_or_dirname=None ):
        # Create and optionally load a Kwds instance.  If
        # 'cursor_or_dirname' is None, an empty instance is
        # created and may be loaded later using the methods
        # loadcsv() or loaddb().  Otherwise 'cursor_or_dirname'
        # should be an open DBI cursor to a jmdictdb database,
        # or a string giving the path to a directory containing
        # kw table csv files.  In the former case, the instance
        # will be loaded from the database's kw tables.  In the
        # latter, from the directory's csv files.
        # You may find function jdb.std_csv_dir() useful for
        # providing a path to call this method with.
        # As a convenience, using an empty string ("") for
        # 'cursor_or_dirname' is equivalent to std_csv_dir().

          # Add a set of standard attributes to this instance and
          # initialize each to an empty dict.
        failed = []
        for attr,table in list(self.Tables.items()):
            setattr (self, attr, dict())

          # 'cursor_or_dirname' may by a directory name, a database
          # cursor, or None.  If a string, assume the former.
        if isinstance (cursor_or_dirname, str):
            failed = self.loadcsv (cursor_or_dirname)

          # If not None, must be a database cursor.
        elif cursor_or_dirname is not None:
            failed = self.loaddb (cursor_or_dirname)

        if len (failed) >= len (self.Tables):
              # Raise error if no tables were loaded.
            raise IOError ("Unable to load any tags")

          # Otherwise 'cursor_or_dirname' is None, and we won't
          # load anything, just return the empty instance.

    def loaddb( self, cursor, tables=None ):
        # Load instance from database kw* tables.

        failed = []
        if tables is None: tables = self.Tables
        for attr,table in list(tables.items()):
              # For item in Tables is a attribute name, database table
              # name pair.  Read the table from the database and use
              # method .add() to store the records in attribute 'attr'.
              # If there is a exception (typically because the table
              # does not exist or is not readable due to permissions)
              # catch it and add the table name to the 'failed' list.
            try: recs = dbread (cursor, "SELECT * FROM %s" % table, ())
            except dbapi.ProgrammingError as e:
                failed.append (table)
            else:
                for record in recs: self.add (attr, record)
        return failed

    def loadcsv( self, dirname=None, tables=None ):
        # Load instance from the csv files in directory 'dirname'.
        # If 'dirname' is not supplied or is None, it will default
        # to "../../pg/data/" relative to the location of this module.

        Converts = \
            {'SRC':{'sinc':cvint, 'smin':cvint, 'smax':cvint},
            'DIAL':{'ents':cvjson}, 'FLD':{'ents':cvjson},
            'KINF':{'ents':cvjson}, 'MISC':{'ents':cvjson},
            'POS':{'ents':cvjson}, 'RINF':{'ents':cvjson},
            'RAD':{'var':cvint,'strokes':cvint, 'loc':cvint},}

        if not dirname: dirname = std_csv_dir ()
        if tables is None: tables = self.Tables
        if dirname[-1] != '/' and dirname[-1] != '\\' and len(dirname) > 1:
            dirname += '/'
        failed = []
        dialect = {'delimiter':'\t', 'quoting':csv.QUOTE_NONE}
        for attr,table in list(tables.items()):
            fname = dirname + table + ".csv"
            try: f = open (fname)
            except IOError:
                f = None;  failed.append (table);  continue
            else:
                csvrdr = csv.reader (f, **dialect)
                fields = next (csvrdr)
                if fields[0].isdigit():
                    raise ValueError ("Missing header line: %s" % fname)
                for row in csvrdr:
                    row[0] = int(row[0])  # First item is always int id number.
                    for i,itm in enumerate (fields):
                          # Convert strings received from csv into expected
                          # data types.
                        if attr not in Converts: continue
                        cvtfunc = Converts.get(attr).get (itm, None)
                        if cvtfunc: row[i] = cvtfunc(row[i])
                    dbrow = db.DbRow (row, fields)
                    self.add (attr, dbrow)
            finally:
                if f: f.close()
        return failed

    def add( self, attr, row ):
        # Add the row object to the set of rows in the dict in
        # attribute 'attr', indexed by its numeric id and its
        # name (kw).  'row' may be either a DbRow object (such
        # as returned by DbRead), or a seq.  In the latter case
        # only the first three items will be used and they will
        # taken as the 'id', 'kw', and 'descr' values.
        #
        # Additionally, every row added results in the creation
        # of an additional attribute with a name based on 'attr'
        # and the row.kw value separated by a "_" and assigned
        # a value 'row.id'.
        # For example, if 'attr' is "POS", 'row.id' is 50, and
        # 'row.kw' is "vt", then attribute "POS_vt" is created
        # with a value of 50.
        # If the kw string contains a "-" character it is changed
        # to "_" in the attribute name: POS kw "adj-i" results
        # in attribute self.POS_adj_i.

        v = getattr (self, attr)
        if not isinstance (row, (Obj, DbRow)):
            row = DbRow (row[:3], ('id','kw','descr'))
        v[row.id] = row;  v[row.kw] = row;
        shortname = '%s_%s' % (attr, row.kw.replace ('-', '_'))
        setattr (self, shortname, row.id)

    def upd (self, attr, id_or_kw, kw=NONE, descr=NONE, ents=NONE):
        # Update or delete a row.
        #   attrs -- Identifies the keyword set (eg, 'DIAL', 'POS', etc.
        #   is_or_kw -- Identifies the row in the keyword set.
        #   kw, descr, ents -- New value for the given field.  If none
        #     are given the row will be deleted.
        kwtab = getattr (self, attr)
        r = kwtab[id_or_kw]
        if (kw, descr, ents) == (NONE,NONE,NONE):
            del kwtab[r.id]; del kwtab[r.kw]
            return
        if descr is not NONE and descr != r.descr:
            kwtab[r.id].descr = descr
        if ents is not NONE and ents != r.ents:
            kwtab[r.id].ents = ents
        if kw is not NONE and kw != r.kw:
            del kwtab[r.kw]
            kwtab[r.id].kw = kw
            kwtab[kw] = kwtab[r.id]

    def attrs( self ):
        # Return list of attr name strings for attributes that contain
        # non-empty sets of rows.  Note that this instance will
        # contain every attribute listed in .Tables but some of them
        # may be empty if they haven't been loaded (because the
        # corresponding .csv file of table was missing or empty.)

        return sorted([x for x in list(self.Tables.keys()) if getattr(self, x)])

    def attrsall( self ):
        # Like .attrs() but returns all the attr name strings, whether
        # the value is empty or not.
        #FIXME: need a rethink on both .attr() and this method and what
        # they should return.
        return set ([x for x in list(self.Tables.keys())])

    def recs( self, attr ):
        # Return a list of DbRow objects representing the rows on the
        # table identified by 'attr'.  Note that the naive way of attempting
        # to get the same results, e.g., "KW.POS.values()", will return two
        # instances of each row (because each row is keyed by both id and
        # keyword.)
        #
        # Example (assuming 'KW' is an initialized Kwds instance):
        #    # Get the rows of the kwpos table:
        #    pos_recs = KW.recs ('POS')

        vt = getattr (self, attr)
        r = [v for k,v in list(vt.items()) if isinstance(k, int)]
        return r

def cvint (s): return None if s is None or s=='' else int(s)
def cvjson (s): return None if s is None or s=='' else json.loads(s)

def std_csv_dir ():
        ''' Return the path to the directory containing the
            kw table csv data files.  We use the location of
            of our own module as a reference point. '''

          #FIXME: should rename to data_dir() since the directory
          # now contains more than csv files.
        our_dir, _ = os.path.split (__file__)
        data_dir = os.path.normpath (os.path.join (our_dir, 'data'))
        return data_dir

class Tmptbl:
    def __init__ (self, cursor, tbldef=None, temp=True):
        """Create a temporary table in the database.

        cursor -- An open DBAPI cursor that identifies the data-
            base in which the temporary table will be created.
        tbldef -- If 'tbldef' is given, it is expected to be a
            string that gives the SQL for the table definition
            after the "create table xxx (" part.  It should not
            include the closing paren.
            If not given, the table will be created with a single
            integer primary key column named "id" and a counter
            (autonumber) column named "ord".
        temp -- If not true, table will be created with the "TEMPORARY"
            option.  If true, it will be created without this option.
            "TEMPORARY" causes the table to not be visible from
            other connections and to be automatically deleted when
            the connection it was created on is closed.  Setting the
            'temp'parameter to False can be useful when debugging or
            testing.  Note that the table will be explicitly deleted
            when a Tmptbl instance is deleted, whether 'temp' is True
            or False.

        When a Tmptbl instance is deleted (due to explicit deletion
        or because no other objects are referencing it and it is
        being garbage collected) it will explicitly delete it's
        database table."""

          # The 'ord' column's purpose is to preserve the order
          # that 'id' values were inserted in.
        if not tbldef: tbldef = "id INT, ord SERIAL PRIMARY KEY"
        nm = self.mktmpnm()
        tmp = 'TEMPORARY ' if temp else ''
        sql = "CREATE %s TABLE %s (%s)" % (tmp, nm, tbldef)
        cursor.execute (sql)
        self.name = nm
        self.cursor = cursor

    def load (self, sql=None, args=[]):
        # FIXME: this method is too specific, assumes column name
        #  is 'id', when sql is None, args is list of ints (why not
        # strings if tmptbl was defined so?)
        cur = self.cursor
        if sql:
            s = "INSERT INTO %s(id) (%s)" % (self.name, sql)
            cur.execute (s, args)
        elif args:
            vallist = ','.join(["(%d)"%x for x in args])
            s = "INSERT INTO %s(id) VALUES %s" % (self.name, vallist)
            cur.execute (s)
        else: raise ValueError ("Either 'sql' or 'args' must have a value")
        self.rowcount = cur.rowcount
        cur.connection.commit ()

          # We have to vacuum the table, or queries based on joins
          # with it may run extrordinarily slowly.  AutoCommit must
          # be on to do this.
        ac = cur.connection.isolation_level         # Save current AutoCommit setting.
        cur.connection.set_isolation_level (0)      # Turn AutoCommit on
        cur.execute ("VACUUM ANALYZE " + self.name) # Do the vacuum.
        cur.connection.set_isolation_level (ac)     # Restore original setting..

    def delete (self):
        #print >>sys.stderr, "Deleting temp table", self.name
        sql = "DROP TABLE %s;" % self.name
        self.cursor.execute (sql)
        self.cursor.connection.commit ()

    def __del__ (self):
        self.delete ()

    def mktmpnm (self):
        cset = "abcdefghijklmnopqrstuvwxyz0123456789"
        t =''.join (random.sample(cset,10))
        return "_T" + t


#=======================================================================
# Bits used in the return value of function jstr_classify() below.
KANA=1; KANJI=2; KSYM=4; LATIN=16; OTHER=32


def jstr_classify (s):
        """\
        Returns an integer with bits set according to whether
        the certain types of characters are present in string <s>.
        The bit settings are given by constants above.

        See IS-26 and Edict email list posts,
          2008-06-27,"jmdict/jmnedict inconsistency"
          2009-02-26,"Tighter rules for reading fields"
        and followups for details of distinguishing reb text strings,
        and latter particularly for the rationale for the use of
        u+301C (WAVE DASH) rather than u+FF5E (FULLWIDTH TILDE)
        in the JMdict XML file.
          2010-08-14, "keb vs reb (again)" for the justification for
        treating KATAKANA MIDDLE DOT (U+30FB) as a keb rather than
        reb character."""

        r = 0
        for c in s:
            n = uord (c)
            if    n >= 0x0000 and n <= 0x02FF:       r |= LATIN
            elif (n >= 0x3040 and n <= 0x30FF                   # Hiragana/katakana
                  and n != 0x30FB                               #  but excl. MIDDOT
                  or n == 0x301C):                   r |= KANA  #  but incl. WAVE DASH.
            elif (n >= 0x3000 and n <= 0x303F                   # CJK Symbols
                  and n != 0x3006                               #  but excl. IDEO CLOSE
                  or n == 0x30FB):                   r |= KSYM  #  but incl. MIDDOT.
            elif (n >= 0x4E00 and n <= 0x9FFF                   # CJK Unified,
                  or n >= 0xFF00 and n <= 0xFF5F                #  Fullwidth ascii,
                  or n >= 0x20000 and n <= 0x2FFFF              #  CJK Unified ExtB+Supl,
                  or n == 0x3006):                   r |= KANJI #  IDEO CLOSE.
            else:                                    r |= OTHER
        return r

def jstr_reb (s):
        # Return a true value if the string 's' is a valid string
        # for use in an XML <reb> element or 'rdng' table.
        # It must consist exclusively of characters marked as KANA
        # by jstr_classify.

        if isinstance (s, str):
            b = jstr_classify (s)
        else: b = s
        if b == 0: return True  # Empty string.
          # Must not have any characters other than kana and ksyms
          # and must have at least one kana.  (Following expression
          # also used in jstr_keb(); if changed here, change there
          # too.)
        return (b & KANA) and not (b & ~(KANA | KSYM))

def jstr_gloss (s):
        # Return a true value if the string 's' consists only
        # of LATIN characters.
        # FIXME: this won't work in a multi-lingual corpus when we
        #  may have cryllic, or korean, or chinese, etc, glosses.

        if isinstance (s, str):
            b = jstr_classify (s)
        else: b = s
        if b == 0: return True  # Empty string.
          # Must be exclusively latin characters.
        return not (b & ~LATIN)

def jstr_keb (s):
        # Return a true value if the string 's' is acceptable
        # for use in a <keb> element.  This is any string that
        # is not usable as a reb or a gloss.

        if isinstance (s, str):
            b = jstr_classify (s)
        else: b = s
        if b == 0: return True  # Empty string.
          # Any string that does not qualify as a gloss or a
          # reb.  (Expression below intentionally not simplified
          # to facilitate visual verification.)
        return not (
                 (not (b & ~LATIN))     # gloss
                 or
                 ((b & KANA) and not (b & ~(KANA | KSYM)))) #reb

BOMle, BOMbe = '\uFFFE', '\uFEFF'
BOM_STRIP_TAB = {ord(BOMle):None, ord(BOMbe):None}
def bom_strip (s):
      # Check string 's' for presence of a unicode BOM (Byte Order
      # Mark) character in either of the two forms.  If not found
      # return None; if found return a copy of the string 's' with
      # all occurances of the BOM character(s) deleted.
    if not s: return s
    if BOMle not in s and BOMbe not in s: return None
    return s.translate (BOM_STRIP_TAB)

def bom_fixn (lst):
      # Remove BOM characters from the .txt atribute of the objects
      # in list 'lst' (typically a Kanj, Rdng or Gloss object but
      # can be any object which has a '.txt' atrribute pointing to
      # a string or None.)
      # Return a count of the total number of characters removed
      # in all the strings.
    count = 0
    for o in lst:
       s = bom_strip (o.txt)
       if s: o.txt, count = s, count+1
    return count

def bom_fixall (e):
      # Remove BOM character from an entry object ('e') rdng and
      # kanj text strings.  We don't check or fix gloss, lsrc,
      # hist or other text fields since experience to date has
      # not shown a problem with BOM characters in those fields.
    count = 0
    count += bom_fixn (e._kanj)
    count += bom_fixn (e._rdng)
    #for s in e._sens: count += bom_fixn (s._gloss)
    return count

#=======================================================================
import psycopg2
import psycopg2.extensions
dbapi = psycopg2

def dbopen (dburi, allow_params=False, **kwds):
        "Replacement for dbOpen() that accepts a database URI."

        opts = parse_pguri (dburi, allow_params)
        dbname = opts.pop('database')
          # keys in 'kwds' should overwrite those in 'opts'. 
        opts_ = {}; opts_.update (opts);  opts_.update (kwds)
        cur = dbOpen (dbname, **opts_)
        return cur

def dbOpen (dbname_, **kwds):
        """\
        Open a DBAPI cursor to a jmdict database and initialize
        a Kwds instance with the global name KW.

        dbOpen() accepts all the same keyword arguments that the
        underlying Psycopg2 connect() call takes ('database', 'user',
        'password', 'host', 'port' in Psycopg2 version 2.4.2 and earlier
        or any keyword args accepted by Postgresql's libpq C library
        (see http://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-PARAMKEYWORDS)
        in Pyscopg2 version 2.4.3 and later.

        There are four additional acceptable keyword parameters that
        are used only within this function:

            autocommit -- If true puts the connection in "autocommit"
                mode.  If false or not given, the connection is opened
                in the dbapi or driver default mode.  For psycopg2,
                "autocommit=True" is the same as "isolation=0".

            isolation -- if given and not None, connection is opened
                at the isolation level given.  Choices are:
                  0 -- psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
                  1 -- psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED
                    or psycopg2.extensions.ISOLATION_LEVEL_READ_UNCOMMITTED
                  2 -- psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ
                    or psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE
                Note that the last two levels (1, 2) correspond to
                Postgresql's isolation levels but the first (0) is
                implemented purely within psycopg2.

            Only one of autocommit and isolation may be non-None.

            noverchk -- Don't check that the database update version
                matches DBVER.

            nokw -- Suppress the reading of keyword data from the
                database and the creation of the jdb.KW variable.
                Note that many other api functions refer to this
                variable so if you suppress it's creation you are
                responsible for creating it yourself, or not using
                any api functions that use it."""

          # Copy kwds dict since we are going to modify the copy.
        kwargs = dict (kwds)

          # Extract from the parameter kwargs those which are strictly
          # of local interest, then delete them from kwargs to prevent
          # them from being passed on to the dbapi.connect() call
          # which may object to parameters it does not know about.
        autocommit = kwargs.get('autocommit');
        if 'autocommit' in kwargs: del kwargs['autocommit']
        isolation = kwargs.get('isolation');
        if 'isolation' in kwargs: del kwargs['isolation']
        nokw = kwargs.get('nokw');
        if 'nokw' in kwargs: del kwargs['nokw']
        noverchk = kwargs.get('noverchk')
        if 'noverchk' in kwargs: del kwargs['noverchk']
        if isolation is not None and autocommit:
            raise ValueError ("Only one of 'autocommit' and 'isolation' may be given.")
        if dbname_: kwargs['database'] = dbname_

          # Remove kwds with None values since psycopg2 doesn't
          # seem to like them.
        nonekwds = [k for k,v in list(kwargs.items()) if v is None]
        for k in nonekwds: del kwargs[k]

        conn = psycopg2.connect (**kwargs)

          # Magic psycopg2 incantation to ask the dbapi gods to return
          # a unicode object rather than a utf-8 encoded str.
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

        if autocommit: isolation = 0    # 0 = ISOLATION_LEVEL_AUTOCOMMIT
        if isolation is not None:
            conn.set_isolation_level(isolation)

          # Most of the the jdb api expects jdb.KW to point to a
          # jdb.Kwds() object (not to be confused with the kwds
          # (lowercase "k") parameter of this function) initialized
          # from the current database connection.
          # Since KW is so widely used a global seemed like the best,
          # although still poor, solution.  Do it here to eliminate a
          # small piece of boilerplate code in every application program.
          # For those few that don't need/want it, conditionalize with
          # a parameter.  If connecting to a database in which the kw*
          # tables don't exist (e.g. for testing or in tools that will
          # create the database)` ignore the error that will result
          # when Kwds.__init_() tries to read non-existent tables.

          # FIXME? Make nokw the default?
        if not nokw:
            global KW
            KW = Kwds (conn.cursor())
        if DBVERS and not noverchk:
            dbrequire (conn, DBVERS)
        L('jdb.dbOpen').debug("Opened db '%s', KW %sinitialized" % (conn.dsn,('NOT ' if nokw else '')))
        return conn.cursor()

def dbrequire (dbconn, require):
          # require -- A list of ints (typically given  in hexidecimal)
          #              of db update numbers required by the calling
          #              application.
        if not require: return
        from jmdictdb import db   # We import inside function to avoid
                                  # importing if this function is not called.
        missing = db.require (dbconn, require)
          #FIXME: include database name or URI in error message.
        if missing: raise KeyError ("Database missing required update(s): %s"
                                    % ','.join(["%06.6x"%r for r in missing]))

import urllib.parse

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

        result = urllib.parse.urlsplit (uri_string)
        query = urllib.parse.parse_qs (result.query)
        scheme = result.scheme
        if not scheme: scheme = 'postgresql'
        if scheme not in ('pg', 'postgresql','postgres'):
            raise ValueError ("Bad scheme name ('%s') in URI: %s" % (result.scheme, uri_string))
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
        Convert dict of connection arguments such as is returned from jdb.parse_pguri()
        into a URI string.   The result will always have a scheme, "postgresql:"
        '''
        # Postgresql URI syntax:
        #   postgresql://[user[:password]@][netloc][:port][/dbname][?param1=value1&...]

        # Why, oh why, does urllib not provide better support for this??
        # Its urlunsplit() function does not seem to have any way to accept username
        # password, port, etc.
        auth = connargs.get('user','')
        if auth and connargs.get ('password'): auth += ':' + connargs['password']
        host = connargs.get('host','')
        if connargs.get('port'): host += ':' + str(connargs['port'])
        if auth: host = auth + '@' + host
        q = []
        for k,v in connargs.items():
            if k in ('user','password','database','host','port',): continue
            if not isinstance (v, (list,tuple)): v = [v]
            for vx in v: q.append ("%s=%s" % (k,vx))
        query = '&'.join (q)
        uri = urllib.parse.urlunsplit (('postgresql',host,connargs.get('database',''),query,''))
        return uri

def dbexecute (cur, sql, sql_args):
        # Use this funtion rather than cur.execute() directly.
        # If 'sql' contains a sql wildcard character, '%', the
        # psycopg2 DBAPI will interpret it as a partial parameter
        # marker (it uses "%s" as the parameter marker) and will
        # fail with an IndexError exception if sql_args is '[]'
        # rather than 'None'.  This bug exists in at least
        # psycopg2-2.0.7.
        # See: http://www.nabble.com/DB-API-corner-case-(psycopg2)-td18774677.html
        if not sql_args: sql_args = None
        return cur.execute (sql, sql_args)

def dbopts (opts):
        # Convenience function for converting database-related
        # OptionParser options to the keyword dictionary required
        # by dbOpen().  It is typically used like:
        #
        #   jdb.dbOpen (opts.database, **jdb.dbopts (opts))
        #
        # where opts is a optparse.Options object that may
        # have .database, .host, .user, or .password attributes
        # in addition to other application options.

        openargs = {}
        if opts.user: openargs['user'] = opts.user
        if opts.password: openargs['password'] = opts.password
        if opts.host: openargs['host'] = opts.host
        return openargs

def _extract_hostname (connection):
        # CAUTION: Specific to pyscopg2 DBI cursors.
        dsn = connection.dsn
        dsns = dsn.split()
        strs = [x for x in dsns if x.startswith ('host=')]
        if len (strs) == 0: return ""
        elif len (strs) == 1: return strs[0][5:].strip()
        raise ValueError ("Multiple host specs in dsn: '%s'" % dsn)

def pmarks (sqlargs):
        "Create and return a string consisting of N comma-separated "
        "parameter marks, where N is the number of items in sequence"
        "'sqlargs'.  "

        return ','.join (('%s',) * len (sqlargs))

def getSvc (cfg, svcname, readonly=False, session=False):
        # Get the authentication values from config.Config
        # instance 'cfg' for a specific database service
        # identified name name 'svcname'.
        # *** CAUTION ***
        # The options returned by this function are specific
        # to the psycopg2 DBAPI.

        if not svcname.startswith ('db_'): svcname = "db_" + svcname
        cfgsec = cfg[svcname]
        if session: cfgsec = cfg[cfgsec['session_db']]
        if readonly: user, pw = 'sel_user', 'sel_pw'
        else: user, pw = 'user', 'pw'
        dbopts = {}
        dbopts['database'] = cfgsec['dbname']
        if cfgsec.get (user):   dbopts['user']     = cfgsec[user]
        if cfgsec.get (pw):     dbopts['password'] = cfgsec[pw]
        if cfgsec.get ('host'): dbopts['host']     = cfgsec['host']
        return dbopts

def dbOpenSvc (cfg, svcname, readonly=False, session=False, **kwds):
        # Open the database identified by 'svcname' getting the
        # authenication values from 'cfg' which may be either a
        # config.Config instance or configuration filename.
        # The authenication values are looked for in section
        # "db_"+'svcname'.
        # If 'readonly' is true, open with the read-only user.
        # Otherwise, open the database with the full-access user.
        # If 'session' is true open the session database given in
        # the svcname section rather than the 'svcname' database
        # itself.

        if isinstance (cfg, str): cfg = cfgOpen (cfg)
        dbopts = getSvc (cfg, svcname, readonly, session)
        dbopts.update (kwds)
        cur = dbOpen (None, **dbopts)
        return cur

def iif (c, a, b):
        """Stupid Python! at least prior to 2.5"""
        if c: return a
        return b

def uord (s):
        """More stupid Python!  Despite the fact that Python-2.5's
        unichr() function produces unicode surrogate pairs (on Windows)
        it's ord() function throws an error when given such a pair!"""

        if len (s) != 2: return ord (s)
        s0n = ord (s[0]); s1n = ord (s[1])
        if (s0n < 0xD800 or s0n > 0xDBFF or s1n < 0xDC00 or s1n > 0xDFFF):
            raise TypeError ("Illegal surrogate pair")
        n = (((s0n & 0x3FF) << 10) | (s1n & 0x3FF)) + 0x10000
        return n

def first (seq, f, nomatch=None):
        for s in seq:
            if f(s): return s
        return nomatch

_sentinal = object()
def isin (object, seq):
        """Returns True if 'object' is "in" 'seq', when "in" is
        based on object identity (i.e. the "is" operator) rather
        thn equality ("==") as is used by the "in" operator.
        Returns False otherwise.  'object' may be None."""

        return _sentinal is not first (seq, lambda x: x is object, _sentinal)

def del_item_by_ident (list, item):
        """Remove first occurance of 'item' from 'list'.  'item'
        is identified in 'list' by an "is" comparison rather
        than the usual "==" comparison."""

        for i in range (len (list)):
              # We can't use list.index() or the like to find
              # 'f' in 'list' because such method use equality
              # comparisions and we need 'is' to be sure we
              # identify the right object.
            if item is list[i]:
                del list[i]
                break

def unique (key, dupchk):
        """
        key -- A hashable object (i.e. usable as a dict key).
        dupchk -- An (initially empty) mapping object.

        """
        if key in dupchk: return False
        dupchk[key] = 1
        return True

def rmdups (recs, key=None):
        """
        recs -- A list of objects
        key -- None, or a one-parameter function that will be
          called with objects of 'recs' and is expected to return
          an immutable value that identifies "same" objects of
          'recs'.
        Returns: a 2-tuple:
          [0] -- List of unique objects in 'recs' (order preserved).
          [1] -- List of duplicate objects in 'recs'.
        """
        uniq=[]; dups=[]; dupchk={}
        for x in recs:
            if key: k = key (x)
            else: k = x
            if unique (k, dupchk): uniq.append (x)
            else: dups.append (x)
        return uniq, dups

def reset_encoding (file, encoding='utf-8'):
        # As of Python-3.3, this seems to be the best (if still
        # ugly) way to change the encoding on an already-opened
        # file such as sys.stdout that python has kindly determined
        # that we want some other unwanted encoding on.

        if file.encoding == encoding: return
        file.__init__(file.detach(),
                      line_buffering=file.line_buffering,
                      encoding=encoding)

if __name__ == '__main__':
        pdb.set_trace()
        kw = Kwds('')
        print (kw)
