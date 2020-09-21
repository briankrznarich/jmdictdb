#!/usr/bin/env python3
# Compare db updates required by code with updates in database.

import sys, os, re, unittest, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import jdb, db, dbver

#FIXME: update doc/src/dev.asc, has example output of dbversion.py.

def main():
         args = parse_cmdline()
         need = ["%0.6x"%v for v in dbver.DBVERS]
         print ("code expects updates: %s" % (", ".join(need)))

         if len (args.dbnames) == 0:
              dbnames = get_dblist()
         else: dbnames = args.dbnames
         for dbname in dbnames:
             try: have = db_has (dbname)
             except Exception as e:
                 print ("%s: %s" % (dbname, e))
                 continue
             if have is None: continue
             missing = set (need) - set (have)
             has_txt = ", ".join(have)
             if missing:
                 print ("%s: incompatible, missing updates: %s"
                        % (dbname, ", ".join (missing)), end=', ')
             else: print ("%s: compatible" % dbname, end=', ')
             print ("has updates: %s" % has_txt)

def db_has (dbname):
         dbconn = db.connect (dbname)
         sql = "SELECT count(*) "\
               "FROM information_schema.tables "\
               "WHERE table_schema='public' "\
                 "AND table_name in ('db','entr','kanj','kinf','stagr')"
         rs = db.query (dbconn, sql)
         if not rs or rs[0][0] != 5: return None;
         rs = db.query (dbconn, "SELECT * FROM db WHERE active")
         have = ["%0.6x"%v[0] for v in rs]
         dbconn.close()
         return have

def get_dblist():
        sql = "SELECT datname FROM pg_database WHERE NOT datistemplate"
        dbconn = db.connect ("postgres")
        results = [r[0] for r in db.query (dbconn, sql)]
        dbconn.close()
        return results

import argparse
def parse_cmdline():
        p = argparse.ArgumentParser (description=
            "Check each database named.")
        p.add_argument ('dbnames', nargs='*',
            help="Names of database to check.  If none give, all databases "
                "will be checked.")
        args = p.parse_args ()
        return args

if __name__ == '__main__': main()
