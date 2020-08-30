#!/usr/bin/env python3
# Copyright (c) 2020 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, os, inspect, re, subprocess, time, pdb
import psycopg2
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, db

def main():
        args = parse_cmdline()
        logger.log_config (level=args.loglevel)
          # User to run DDL statements as.  Running consistently with the
          # the same user that created other database objects outside of
          # this script is important to prevent failures due to ownership
          # and permissions.  The only DDL statements executed here where 
          # 'user' is used is the execution of the imptabs.sql script
          # which creates the import schema.
        user = '-U'+args.user if args.user else ''

        dbconn = db.connect (args.dburi)
          # Read the import kwsrc table from the .pgi file because
          # we want to catch some obvious problems right away without
          # te long time it takes to import first.
        pubcorp = kwsrc_from_db (dbconn)
        impcorp = kwsrc_from_file (args.filename)
          # We assign kwsrc id numbers starting from the highest id
          # already in the table but by default databases are set up 
          # with a test corpus at id=99.  We don't want to consider 
          # that id because otherwise all new ids would be 100+.
          # So we ignore that id when finding the next id and skip
          # over it when the next id would be 99.
          #FIXME: shouldn't be hardwired obviously.
        TEST_ID = 99
        max_srcid = max ([x[0] for x in pubcorp if x[0]!=TEST_ID] or [0])
        impcorp = remap (impcorp, args.map)
        if args.show:
            showsrc (pubcorp, "database %s:" % args.dburi)
            showsrc (impcorp, "file %s:" % args.filename)
        conflicts = set ([x[1] for x in pubcorp])\
                    & set ([x[1] for x in impcorp])
        if conflicts:
             sys.exit ("Conflicting corpus names: %s\n"
                       "Please use the -m option to remap these."
                       % ", ".join (sorted (conflicts)))
        if args.show: sys.exit(0)

          # We will need the path to scripts in the db/ directory so
          # figre out the prefix path here. 
        p = os.path
        dbdir = p.normpath (p.join (p.dirname (__file__), '../db/'))
        if dbdir == '': dbdir = '.'

          # Create fresh copy of the import schema.  Although the "imp"
          # schema can be reused (and was in the past), recreating it
          # ensures that the object defintions are current since database
          # updates are not routinely also applied to the "imp" schema. 
        cmd = "psql %s -d %s -f %s/imptabs.sql" % (user, args.dburi, dbdir)
        run (cmd)

        sql = "ALTER TABLE imp.kwsrc\n"\
              " ADD COLUMN IF NOT EXISTS newid INT;\n"\
              "ALTER TABLE imp.entr\n"\
              " DROP CONSTRAINT IF EXISTS entr_dfrm_fkey;"
        L().info("Ex:\n %s" % sql)
        db.ex (dbconn, sql); dbconn.commit()

          # Import the raw entry data into the "imp" schema.
        cmd = "PGOPTIONS=--search_path=imp,public psql -e -d %s -f %s"\
                                    % (args.dburi, args.filename)
        run (cmd)

          # Update the imported kwsrc table data.

        L('pgload').info("Updating table imp.kwsrc")
        sql = "UPDATE imp.kwsrc SET kw=%s,newid=%s WHERE id=%s"
        for n, (srcid, corp, ctype, oldcorp) in enumerate (impcorp):
            newid = max_srcid + 1 + n
            if newid == TEST_ID: newid += 1
            L().info("Ex:\n%s" % (sql % (corp, newid, srcid)))
            db.ex (dbconn, sql, (corp, newid, srcid))
        dbconn.commit()

          # Run the import.sql script which will add the rows in the
          # imported kwsrc table to the public kwsrc table, adjusting
          # the id's to avoid conflicts.  Then it will copy the imported
          # entry data into the public schema, again adjusting entry id
          # numbers to avoid conflict with existing entries.  This needs
          # to be run by the -U user since sequence objects are created 
          # when rows are added to table "kwsrc" and they need to be owned
          # by the same user that owns the other database objects.
        cmd = "psql %s -d %s -f %s/import.sql" % (user, args.dburi, dbdir) 
        run (cmd)

def run (cmd):
        L().info("Run: " + cmd)
        subprocess.run (cmd, shell=True, check=True)

def remap (kwsrc, map):
        result = []
        for srcid, corp, ctype in kwsrc:
            newcorp = corp
            try: newcorp = map[corp]
            except KeyError: pass
            result.append ((srcid, newcorp, ctype, corp))
        return result

def kwsrc_from_db (dbconn):
        rs = db.query (dbconn, "SELECT * FROM public.kwsrc")
        results = []
        for r in rs:
            srcid,corp,_,_,_,_,_,_,_,ctype = r._tolist()
            results.append ((srcid,corp,ctype))
        return results

def kwsrc_from_file (fname):
        with open (fname) as f:
            results = [];  intable = False
            for lnnum, ln in enumerate (f):
                ln = ln.strip ('\r\n')
                if ln.startswith ("COPY kwsrc("):
                    intable = True; continue
                if ln.startswith ('\\.') or lnnum > 50: break
                if intable:
                    srcid,corp,_,_,_,_,_,_,_,ctype = ln.split ('\t')
                    results.append ((srcid,corp,ctype))
            if not intable:
                raise KeyError ("kwsrc table not found in %s" % fname)
        return results

def showsrc (kwsrc, title):
        print (title)
        print ("  id   corp     type  ")
        print ("  ---- -------- --------")
        for srcid, corp, ctype, *_ in sorted (kwsrc):
            print ("  %s %s %s"
               % (str(srcid).ljust(4), corp.ljust(8), ctype.ljust(8)))
        print()
#-----------------------------------------------------------------------
from argparse import ArgumentParser
from jmdictdb.pylib.argparse_formatters import ParagraphFormatter

def parse_cmdline():
        u = \
"Bulkupd.py will edit and submit changes to multiple entries " \
"based on an input file that describes the entries to be modified " \
"and the modifications to be made to them."

        p = ArgumentParser (description=u, formatter_class=ParagraphFormatter)

        p.add_argument ("filename",
            help="Name of file containing entry data to load.  By "
                "convention usually has a .pgi extension.  If omitted, "
                "input will be read from stdin.")

        p.add_argument ("-d", "--dburi", required=True,
            help="URI for database to load pgi data into.")

        p.add_argument ("--show", default=False, action='store_true',
            help="List the corpus names and id numbers present in the input "
                "file and database, then exit.  No data will be loaded.  "
                "This is useful to determine what corpora are in the "
                "pgi file and database and thus how to remap the pgi "
                "corpora to avoid conflicts.")

        p.add_argument ("--map", "-m", nargs='*',
            help="Corpus map pair.  MAP is two corpus names "
                "separated by a colon with no whitepace.  Occurances of "
                "the first corpus name in the pgi file will be changed "
                "to the second during import.  This option may be given "
                "multiple times to remap multiple corpora.")

        p.add_argument ("-l", "--loglevel", default='info',
                        choices=['error','summary','warn','info','debug'],
            help="Logging level for messages: only mesages at or above"
               "this level will be printed.")

        p.add_argument ("--user", "-U",
            help="The Postgresql user to create the import schema as.")

        args = p.parse_args()
        t = {}
        for x in args.map or []:
            try: k,v = x.split (':')
            except ValueError: p.error ("Bad -m/--map value: %s" % x)
            t[k] = v
        args.map = t
        return args

if __name__ == '__main__': main()
