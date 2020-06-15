#!/usr/bin/python3
#######################################################################
#  This file is part of JMdictDB.
#  Copyright (c) 2019 Stuart McGraw
#
#  JMdictDB is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published
#  by the Free Software Foundation; either version 2 of the License,
#  or (at your option) any later version.
#
#  JMdictDB is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with JMdictDB; if not, write to the Free Software Foundation,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#######################################################################

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
