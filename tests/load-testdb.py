#! /usr/bin/python3
# Tool to manually load a test database.

import sys, os, re, unittest, signal, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import jdb
from jmdb import DBmanager

def main():
         args = parse_cmdline()
         if args.dbname: dbname = args.dbname
         else:
             fn = os.path.basename (args.dbfile)
             dbname = os.path.splitext(fn)[0]
         DBmanager.use (dbname, args.dbfile, force_reload=True)

import argparse
def parse_cmdline ():
        p = argparse.ArgumentParser (description=\
            "Load a test database")

        p.add_argument ('dbfile', default=None,
            help="Name of file containing the database dump to load.")

        p.add_argument ('-d', '--dbname', 
            help="Name of database to create and load.  If not given, "
                "a name derived from the basename of the filename will "
                "be used.")

        args = p.parse_args ()
        return args

if __name__ == '__main__': main()
