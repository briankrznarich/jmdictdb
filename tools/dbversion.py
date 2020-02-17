#! /usr/bin/python3
# Compare db updates required by code with updates in database.

import sys, os, re, unittest, signal, pdb
sys.path.insert (0, os.path.join(os.path.dirname(__file__),'./lib'))
import jdb, db, dbver

def main():
         if len(sys.argv) != 2:
             sys.exit("Usage: %s dbname" % (sys.argv[0]))
         dbconn = db.connect (sys.argv[1])
         rs = db.query (dbconn, "SELECT * FROM db WHERE active")
         have = ["%0.6x"%v[0] for v in rs]
         need = ["%0.6x"%v for v in dbver.DBVERS]
         missing = set (need) - set (have)
         if missing:
             print ("incompatible, missing updates: %s"
                    % (", ".join (missing)))
         else: print ("compatible")
         print ("code expects updates: %s" % (", ".join(need)))
         print ("database has updates: %s" % (", ".join(have)))

if __name__ == '__main__': main()
