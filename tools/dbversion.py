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
             dbconn, have = db.open (dbname), None
             if not db.is_jmdictdb (dbconn): continue
             missing, have = db.require (dbconn,dbver.DBVERS,ret_dbver=True)
             missing = set (need) - set (have)
             has_txt = ", ".join(have)
             if missing:
                 print ("%s: incompatible, missing updates: %s"
                        % (dbname, ", ".join (missing)), end=', ')
             else: print ("%s: compatible" % dbname, end=', ')
             print ("has updates: %s" % has_txt)

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
