#!/usr/bin/env python3
#
# This script compares the entities in an XML DTD file with
# the corresponding values in the JMdictDB kw* tables (from
# either the pg/data/*.csv files or a loaded database) and
# reports any discrepancies.

import sys, re, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import jdb, db
from jmdictdb.dbver import DBVERS

def main():
        args = parse_cmdline()
        if args.dburi: 
            dbcursor = jdb.dbOpen (args.dburi, noverchk=True)
            missing = db.require (dbcursor.connection, DBVERS)
            if missing: print ("WARNING: database missing updates: %s"
                               % ','.join(missing), file=sys.stderr)
        else: jdb.KW = jdb.Kwds (jdb.std_csv_dir())
        kwds = get_kwds (jdb.KW)
        entities = read_dtd_file (args.dtdfile)
        compare (entities, kwds)

def compare (entities, kwds):
        entkeys, kwkeys = set(entities.keys()), set(kwds.keys())
        if entkeys - kwkeys:
            err ("DTD entities not in kw tables:\n"
                 " %s" % (', '.join (sorted (entkeys - kwkeys)))) 
        if kwkeys - entkeys:
            err ("DTD kw table items not in DTD:\n"
                 " %s" % (', '.join (sorted (kwkeys - entkeys)))) 
        for k in entkeys & kwkeys:
            if entities[k] != kwds[k]:
                err ("Mismatch on entity '%s'\n"
                     "  DTD:    %s\n"
                     "  Tables: %s" % (k, entities[k], kwds[k]))
def get_kwds (KW):
        kwitems = {}
        for table in "DIAL FLD KINF MISC POS RINF".split():
            for row in KW.recs (table):
                kwitems[row.kw] = row.descr
        return kwitems

def read_dtd_file (filename):
        f = open (filename)
        entities = {}
        for lnnum, ln in enumerate (f, start=1):
            if not ln.startswith ('<!ENTITY'): continue
            mo = re.match (r'<!ENTITY (\S+) "(.*)">', ln)
            if not mo:
                err ("%d: bad ENTITY line: %s" % (lnnum, ln))
                continue
            entity, descr = mo.group (1,2)
            if entity in entities:
                err ("%d: duplicate entity: %s" % (lnnum, entity)) 
            entities[entity] = descr
        return entities

def parse_cmdline():
        import argparse
        p = argparse.ArgumentParser (description=
            "This script compares the entities in an XML DTD file with "
            "the corresponding values in the JMdictDB kw* tables (from "
            "either the pg/data/*.csv files or a loaded database) and "
            "reports any discrepencies.")
        p.add_argument ('dtdfile',
            help="Path to the DTD file to check.")
        p.add_argument ('--dburi', '-d', default=None,
            help="URL for a database to use as the source for the kw* "
                "tables.  If not given, the kw* table data will be read "
                "from the JMdictDB pg/data/*.csv files.")
        args = p.parse_args ()
        return args

def err (*args):
        print (*args)

if __name__ == '__main__': main()

