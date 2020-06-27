#!/usr/bin/env python3
# Copyright (c) 2008 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# Read sound clips from database and write to an XML file.
# Currently, quite incomplete.
# To-do:
# * Add command line args and options output encoding.
#   dtd file selection, xml roor name, sound clips subset, etc.

import sys, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import jdb, fmtxml

def main (args, opts):
        jdb.reset_encoding (sys.stdout, opts.encoding)
        dir = jdb.std_csv_dir()
        dtd = jdb.get_dtd (dir + "/" + "dtd-audio.xml", "JMaudio", opts.encoding)
        print (dtd); print ("<JMaudio>")
        cur = jdb.dbOpen (opts.database, **jdb.dbopts (opts))
        vols = jdb.dbread (cur, "SELECT * FROM sndvol")
        for v in vols:
            print ("\n".join (fmtxml.sndvols ([v])))
            sels = jdb.dbread (cur, "SELECT * FROM sndfile s WHERE s.vol=%s", [v.id])
            for s in sels:
                print ("\n".join (fmtxml.sndsels ([s])))
                clips = jdb.dbread (cur, "SELECT * FROM snd c WHERE c.file=%s", [s.id])
                for c in clips:
                    print ("\n".join (fmtxml.sndclips ([c])))
        print ('</JMaudio>')


from optparse import OptionParser, OptionGroup
from jmdictdb.pylib.optparse_formatters import IndentedHelpFormatterWithNL

def parse_cmdline ():
        u = \
"""\n\t%prog [options]

%prog will read audio clip data from a jmdictdb database and write
them in XML form to stdout.

Arguments: none"""

        p = OptionParser (usage=u, add_help_option=False,
                formatter=IndentedHelpFormatterWithNL())

        p.add_option ("--help",
            action="help", help="Print this help message.")
        p.add_option ("-e", "--encoding", default="utf-8",
            help="Encoding for the output XML file.  Default is \"utf-8\".")

        g = OptionGroup (p, "Database access options",
                """The following options are used to connect to a
                database in order to read the entries.

                Caution: On many systems, command line option contents
                may be visible to other users on the system.  For that
                reason, you should avoid using the "--user" and "--password"
                options below and use a .pgpass file (see the Postgresql
                docs) instead. """)

        g.add_option ("-d", "--database", default="jmdict",
            help="Name of the database to load.  Default is \"jmdict\".")
        g.add_option ("-h", "--host", default=None,
            help="Name host machine database resides on.")
        g.add_option ("-u", "--user", default=None,
            help="Connect to database with this username.")
        g.add_option ("-p", "--password", default=None,
            help="Connect to database with this password.")
        p.add_option_group (g)

        opts, args = p.parse_args ()
        if len (args) != 0: p.error ("%d arguments given, expected at most one" % len(args))
        return args, opts

if __name__ == '__main__':
        args, opts = parse_cmdline()
        main (args, opts)
