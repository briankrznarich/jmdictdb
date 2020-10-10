#!/usr/bin/env python3
# Copyright (c) 2020 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# Compare kw* tables in a database with the standard kw*.csv files.
# Output is in the form of SQL statements that would, in an ideal
# world, bring the database tables into conformance with the csv
# files.  But see the caveats and further details in the --help
# output.

import sys, re, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import jdb, db
from jmdictdb.dbver import DBVERS

def main():
        args = parse_cmdline()

          # Open a connection to initialize jdb.KW.  Check for database/api
          # version incompatability and report it but don't abort.
        dbcur = jdb.dbopen (args.dburi, noverchk=True)
        reqver, dbver = db.require (dbcur.connection, DBVERS, ret_dbver=1)
        if reqver: print ("WARNING: expected database at update: %s\n"
                          "  but database is at %s"
                          % (','.join(["%06.6x"%r for r in DBVERS]),
                             ','.join(["%06.6x"%r for r in dbver])),
                          file=sys.stderr)

          # Read the kw* tables from the csv files and the database.
        kwstd, kwdb = jdb.Kwds(args.csvdir or ''), jdb.KW
        if args.verbose:
            print ("Using CSV files from %s" % kwstd.source, file=sys.stderr)


          # The union of the kw table name abbreviations (we call them
          # "domains" in comments below).
        attrs = set (kwstd.attrsall()) | set (kwdb.attrsall())
        diffs = {}
        for domain in sorted (attrs):
              # Skip these tables; they are not really static kw* tables.
            if domain in ('COPOS','GRP','SRC'): continue
            if args.verbose:
                print ("Comparing %s (kw%s.csv): " % (domain, domain.lower()),
                       end='', file=sys.stderr)
            added, deltd, chngd = compare (getattr (kwstd,domain),
                                           getattr (kwdb,domain))
            if args.verbose:
                print ("%s" % "differences found"
                              if (added or deltd or chngd) else "ok",
                              file = sys.stderr)
            diffs[domain] =  added, deltd, chngd
        sql = gen_sql (diffs)
        if sql: print ("\n".join (sql))

def compare (refkw, dbkw):
        refids, dbids = set ([r.id for r in refkw.values()]),\
                        set ([r.id for r in dbkw.values()])
        kf = lambda x: x.id     # Key function for sorting records by 'id'.
        added_recs =   sorted ([dbkw[i]  for i in dbids - refids], key=kf)
        deltd_recs = sorted ([refkw[i] for i in refids - dbids], key=kf)
        common_ids = refids & dbids
        chngd_recs = []
        for id in common_ids:
           if refkw[id] == dbkw[id]: continue
           chngd_recs.append ((refkw[id], dbkw[id]))
        return added_recs, deltd_recs, chngd_recs

def gen_sql (diffs):
        sql = []
        for domain, (added, deltd, chngd) in diffs.items():
            sql.extend (gen_deletes (domain, added))
            sql.extend (gen_inserts (domain, deltd))
            sql.extend (gen_updates (domain, chngd))
        return sql

def gen_deletes (domain, rows):
        if not rows: return []
        table = "kw" + domain.lower()
        sql = []
        for r in rows:
            sql.append ("-- %r" % (r,))
        sql.append ("DELETE FROM %s WHERE id IN (%s);" % (table,
                    ",".join([str(r.id) for r in rows])))
        return sql

def gen_inserts (domain, rows):
        if not rows: return []
        table = "kw" + domain.lower()
        sql = []
        for r in rows:
            nargs = 4 if hasattr (r, 'ents') else 3
            s = "INSERT INTO %s VALUES(%s);" % (table,','.join(['%s']*nargs))
            args = (r.id, r.kw, r.descr)
            if nargs == 4: args += (r.ents,)
            sql.append (qvn (s, args))
        return sql

def gen_updates (domain, rowpairs):
        if not rowpairs: return []
        table = "kw" + domain.lower()
        sql = []
        for rref, rdb in rowpairs:
            upds = []
            if rdb.id != rref.id:
                upds.append ("id=%s" % qv(rref.id))
            if rdb.kw != rref.kw:
                upds.append ("kw=%s" % qv(rref.kw))
            if rdb.descr != rref.descr:
                upds.append ("descr=%s" % qv(rref.descr))
              # Not all kw* tables have an 'ents' column.  Further, in
              # older database versions, none of tables had 'ents' columns.
              # Generate an update term for 'ents' only is it is present in
              # at least one of the rows.
            rdb_ents = getattr (rdb, 'ents', None)
            rref_ents = getattr (rref, 'ents', None)
            if rdb_ents != rref_ents:
                upds.append ("ents=%s"% qv(rref.ents))
            setclause = ','.join ([term for term in upds])
            if not setclause: continue
            sql.append ("UPDATE %s SET %s WHERE id=%s;" % (table,
                        setclause, rdb.id))
        return sql

# Following is modified version of code at:
#   https://web.archive.org/web/20100206013223/http://brotchie.org/?p=101
# Example usage (as given on that site):
#   >>> from datetime import datetime
#   >>> sql = 'INSERT INTO users (name, age, last_login) VALUES (%s,%s,%s);'
#   >>> qvn (sql, ('James', 24, datetime.now()))
#   "INSERT INTO users (name, age, last_login) \
#      VALUES ('James',24,'2009-08-28T07:26:58.311175');"
#
# qv() will apply the appropriate transformations and escaping to its
# argument to make it suitable for direct insertion into a SQL statement
# string.

import psycopg2
from psycopg2.extensions import adapt, register_adapter
register_adapter (dict, psycopg2.extras.Json)
def qv (value):
        adapted = adapt (value)
        if hasattr (adapted, 'getquoted'):
            if hasattr (adapted, 'encoding'):
                adapted.encoding = 'utf-8'
            adapted = adapted.getquoted()
        if type (adapted) == type(b''):
            adapted = adapted.decode ('utf-8')
        return adapted
def qvn (sql, values):
    return sql % tuple (qv(value) for value in values)

def parse_cmdline():
        import argparse
        p = argparse.ArgumentParser (description=
            "This script compares the contents of the kw* tables in "
            "the given database with the contents of the standard "
            "kw*.csv files.  "
            "Output is in the form of a sql script that will bring "
            "the database kw tables into conformance with the kw*.csv "
            "files.  "
            "The output sql may not be runnable for several reasons: "
            "1) the database schema may not be at the current update "
            "level and the schema may not support the changes; 2) "
            "changes to 'kw' values may be in an order that conflicts "
            "(eg, a row in added before a row with the same 'kw' value "
            "is deleted.)"  )
        p.add_argument ('-d', '--dburi', required=True,
            help="URL for the database to use as the source for the kw* "
                "tables.  This option is required.")
        p.add_argument ('--csvdir', default=None,
            help="Path to a directory containing the kw*.csv files that "
                "the database will be compared to.  If not given, the "
                "set of kw*.csv files in the JMdictDB package will be "
                "used.")
        p.add_argument ('-v', '--verbose', default=False,action='store_true',
            help="Print more details about kwcheck's operation to stderr.  "
               "Currently this is only the path to the CSV files used.")
        args = p.parse_args ()
        return args

if __name__ == '__main__': main()
