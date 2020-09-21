#!/usr/bin/env python3
# Copyright (c) 2019 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import jdb, jel

def main (cmdline=sys.argv):
        args = cmdparse (cmdline)
        dbcursor = jdb.dbOpen (args.dbname)
        file = open (args.filename)
        added, errs = jel.dbload (file, dbcursor)
        if errs:
            dbcursor.connection.rollback()
            print ('\n'.join (errs), file=sys.stderr)
        else:
            dbcursor.connection.commit()
            print ("Added following entries to database:")
            print ("+--- eid --+-- seq --+-src-+")
            for eid, seq, src in added:
                print (" %9.9s %9.9s %5.5s" % (eid, seq, src))

import argparse
def cmdparse (cmdline):
        p = argparse.ArgumentParser (
            description='Load entries into database from JEL file.')
        p.add_argument('dbname', default=None,
            help='Name of database on localhost to load.')
        p.add_argument('filename', default=None,
            help='Name of file containing the JEL entries.')
        args = p.parse_args()
        return args

if __name__ == '__main__': main()
