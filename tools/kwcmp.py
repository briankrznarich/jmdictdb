#!/usr/bin/env python3
# Copyright (c) 2020 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# Compare kw* tables in a database with the standard kw*.csv files.
# Output is in the form of SQL statements that would, in an ideal
# world, bring the database tables into conformance with the csv
# files.  But see the caveats and further details in the --help
# output.

import sys,  difflib, io, os.path, re, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import jdb, db
from jmdictdb.dbver import DBVERS

def main():
        args = parse_cmdline()
        if args.csvdir is None: args.csvdir = jdb.std_csv_dir()
        tables = []
        for t in args.tables:
            tables.append (t.upper());
        if not tables:
            tables = 'DIAL FLD GINF KINF MISC POS RINF XREF'.split()

          # Open a connection to initialize jdb.KW.  Check for database/api
          # version incompatability and report it but don't abort.
        dbcur = jdb.dbopen (args.dburi, noverchk=True)
        reqver, dbver = db.require (dbcur.connection, DBVERS, ret_dbver=1)
        if reqver: print ("WARNING: expected database at update: %s\n"
                          "  but database is at %s"
                          % (','.join(["%06.6x"%r for r in DBVERS]),
                             ','.join(["%06.6x"%r for r in dbver])),
                          file=sys.stderr)

          # The processing for the sql diffs and csv diffs has almost 
          # nothing in common.  The sql diffs are generated from jdb.Kwds
          # instances initialized from the database and csv files.
          # The csv diffs are generated from CSV exported directly from
          # the database and textually diffed directly against the csv
          # files.

        if args.format.startswith ('sql'):
            do_sql (dbcur, args.csvdir, args.format, tables, args.verbose)
        else:
            do_csv (dbcur, args.csvdir, args.format, tables, args.verbose)

#------ Code for generating 'sql' format output ------------------------------

def do_sql (dbcur, csvdir, format, tables=[], verbose=False):
        '''------------------------------------------------------------------
        Generate a sql script that will:
        - Update the given database to match the csv files (if 'format'=="sql")
        - Update a database conformant with the csv files to match the given
          database (if 'format'=="sqlx").
        Parameters:
          dbcur -- Database cursor to database providing the tag tables.
          cvsdir -- Path to directory containing the kw*.csv files.  If '' 
            or None, the package's kw*.csv files will be used.
          format -- Output format: either 'sql' or 'sqlx'.
          tables -- A list of tables to limit processing to.  Tables are
            given without te "kw" prefix and in uppercase.  E.g., "DIAL", 
            not "kwdial".  If empty all tables wil be processed.
          verbose -- Print extra information to stderr.
        -------------------------------------------------------------------'''
          # Read the kw* tables from the csv files and the database.
        kwstd, kwdb = jdb.Kwds(csvdir or ''), jdb.KW
        if verbose:
            print ("Using CSV files from %s" % kwstd.source, file=sys.stderr)

          # The union of the kw table name abbreviations (we call them
          # "domains" in comments below).
        attrs = set (kwstd.attrsall()) | set (kwdb.attrsall())
        diffs = {}
        for domain in sorted (attrs):
              # Skip these tables; they are not really static kw* tables.
            if domain not in tables: continue
            if verbose:
                print ("Comparing %s (kw%s.csv): " % (domain, domain.lower()),
                       end='', file=sys.stderr)
            a, b = getattr (kwstd, domain), getattr (kwdb, domain) 
            if format=='sqlx': a, b = b, a
            added, deltd, chngd = sql_compare (a, b)
            if verbose:
                print ("%s" % "differences found"
                              if (added or deltd or chngd) else "ok",
                              file = sys.stderr)
            diffs[domain] =  added, deltd, chngd
        sql = gen_sql (diffs)
        if sql: print ("\n".join (sql))

def sql_compare (refkw, dbkw):
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

#------ Code for generating 'diff' and 'csv' format output ------------------

def do_csv (dbcur, csvdir, format, tables=[], verbose=False):
        '''------------------------------------------------------------------
        If 'format'=="diff", generate a Unix "diff" file that if given
        to the 'patch' utility will update the kw*csv files to be conformant
        with the database.  If 'format'=="csv" no comparison with the
        existing kw*.csv is done but instead they are rewritten from scratch
        with data from the database tag tables.
        Parameters:
          dbcur -- Database cursor to database providing the tag tables.
          cvsdir -- Path to directory containing the kw*.csv files.  If '' 
            or None, the package's kw*.csv files will be used.
          format -- Output format: either 'diff' or 'csv'.
          tables -- A list of tables to limit processing to.  Tables are
            given without te "kw" prefix and in uppercase.  E.g., "DIAL", 
            not "kwdial".  If empty all tables wil be processed.
          verbose -- Print extra information to stderr.
        -------------------------------------------------------------------'''
          # Read the database tables and save as csv data in indexed by
          # table name in 'dbdata'.
          # The table data is extracted in CSV form using Postgresql's
          # "copy" command.  Postgresql will enclose some fields in quote
          # characters even though they are unnecessary and while the quote
          # character can be changed, it has to be exactly one character
          # (not an empty string).  So we set it to a backspace character
          # since no such characters occur in the kw table data and will
          # post-process the returned data to remove all backspace characters.
        sql = "COPY %s TO STDOUT WITH (FORMAT csv, HEADER TRUE, " \
                "DELIMITER E'\\t', NULL '', QUOTE E'\\b')"
          # Define local function, fix(), used to process each csv text
          # row retrieved from database.  Specifically, it removes the
          # backspaces mentioned above.  It also removes space characters
          # between JSON keys and values (how Postgresql formats formats
          # JSON) but existing cvs files don't have those spaces so removing
          # them here eliminates textual but functionally spurious differences
          # between existing files and our generated versions).   
        def fix(s): return s.replace ('\b', '').replace ('": ', '":')
        dbdata = {}
        for tbl in tables:
            fakefile = io.StringIO()       # Create an "in memory" file.
            s = sql % ('kw' + tbl.lower())
              # We use Psycopg2's copy_expert() function to export the table
              # data in csv format rather than copy_to() because the latter
              # has no way to request a header line in the output.
            dbcur.copy_expert (s, fakefile)
            data = fakefile.getvalue().splitlines (keepends=True)
              # Sort the data lines (all but the first, first is a header
              # line) by id number.
            d = sorted (data[1:], key=lambda x: int(x.split('\t')[0]))
              # Final data is the header line with each data line, processed
              # by fix() (removes '\b's and tweaks json fields), appended.
            dbdata[tbl] = data[0:1] + [fix(x) for x in d]

          # At this point...
          # 'dbdata' is a dict, with each item has a key that is a table
          # name in uppercase with no initial "KW".  Each value is a
          # list of text strings for each row, with the first being a
          # header line.  The lines are sorted by id number.

        if format == 'diff':
              # Do the same for the csv files.
            csvdata = {}
            for tbl in tables:
                fname = "kw%s.csv" % tbl.lower()
                with open (os.path.join (csvdir, fname)) as f:
                    #next (f)    # Skip the header line.
                    csvdata[tbl] = f.readlines()
              # At this point 'csvdata' is a dict with the same format
              # as 'dbdata' above.
            diffs = csv_compare (dbdata, csvdata)
            print (diffs)

        elif format == 'csv':
            for k in sorted (dbdata.keys()):
                fname = 'kw' + k.lower() + '.csv'
                if csvdir:
                    fname = os.path.join (csvdir, fname)
                with open (fname, 'w') as f:
                    if verbose:
                        print ("writing file %s" % fname, file=sys.stderr)
                    f.write (''.join (dbdata[k]))

        else: raise RuntimeError ("Bad 'format' value: %r" % format)

def csv_compare (dbdata, csvdata):
        diffs = []
        for k in sorted (dbdata.keys()):
            fname = '%s/jmdictdb/data/kw' + k.lower() + '.csv'
            old, new = (fname % 'old'), (fname % 'new')
            diff = difflib.unified_diff (csvdata[k], dbdata[k], old, new)
            diffs.append (''.join(diff))
        return ''.join (diffs)

#------ Command line argument parsing ----------------------------------------

import argparse
from jmdictdb.pylib.argparse_formatters import FlexiFormatter

def parse_cmdline():
        p = argparse.ArgumentParser (formatter_class=FlexiFormatter,
                                     description=
            "This script compares the contents of the kw* tables in the "
            "given reference database with the contents of the standard "
            "kw*.csv files and if there are differences, generates various "
            "scripts (as requested by the --format/-f option) to bring one "
            "into conformance with the other."
            "The --tables/-t option can be used to limit comparison to "
            "specific tables.")
        p.add_argument ('dburi',
            help="URL for the reference database to use as the source for "
                "the kw* tag tables.")
        p.add_argument ('-f', '--format', default='sql', 
                choices=['sql','sqlx','diff','csv'],
            help="Specifies output format, one of: "
                "sql, sqlx, diff or csv.\n"
                "* sql: Output is a SQL script that will bring the database "
                "  tag tables into conformity with the CSV files.\n"
                "* sqlx: Output is a SQL script that will bring a set of "
                "  hypothetical database tag tables created from the CSV "
                "  files into conformity with the database.  This "
                "  is useful for producing a database update script given "
                "  a database whos tags have been updated by hand.\n"
                "* diff: a diff file that can be applied to the kw*.csv "
                "  files in --csvdir and will bring them into conformance "
                "  with the database tag tables.\n"
                "* csv: new CSV files are created in --csvdir from the "
                "  tag tables in the database.  In this case no "
                "  comparison is done and any existing kw*.csv files in "
                "  --csvdir are overwritten.\n"
                "WARNING! 'csv' will result in the overwriting of kw*.csv "
                "files in --csvdir. "
                "Output from the 'sql', 'sqlx' and 'diff' formats is to "
                "stdout.")
        p.add_argument ('--csvdir', default=None, metavar='DIR',
            help="Path to a directory containing the kw*.csv files that "
                "the database will be compared to.  If not given, the "
                "set of kw*.csv files in the JMdictDB package will be "
                "used (<pkg-root>/jmdictdb/data/kw*.csv).  ")
        p.add_argument ('--tables', '-t', nargs='+',default=[],metavar='TABLE',
            help="List of tables to limit comparison or generation to.  "
                "Table names may be in either case and with or without "
                "the initial \"kw\".")
        p.add_argument ('-v', '--verbose', default=False,action='store_true',
            help="Print more details about kwcheck's operation to stderr.  "
               "Currently this is only the path to the CSV files used.")
        args = p.parse_args ()
        args.tables = \
          [re.sub ('(?i)^kw', '', x).upper() for x in args.tables]
        return args

main()
