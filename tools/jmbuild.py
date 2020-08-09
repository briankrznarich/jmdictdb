#!/usr/bin/env python3
# Copyright (c) 2008-2012,2020 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# This program builds a complete XML file by combining a DTD
# with a number of files containing one or more XML elements.
# It is used by the jmdictdb testing framework to generate
# test files from components.
# See also: jmextract.py -- Pulls subset of elements out of
#   a jmdict or jmnedict file.

import sys, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import jdb, fmtxml

def main():
        KW = jdb.Kwds('')
        args = parse_cmdline()
        root = None
        if args.dtd: root = args.dtd[0:2].upper() + args.dtd[2:]
        dtd = fmtxml.get_dtd (KW, args.dtd)
        outf = open (args.output, 'w') if args.output else sys.stdout
        outf.write (dtd)
        if root and args.date:
            if args.date == 'now':
                args.date = datetime.date.today().isoformat()
            outf.write ("<!-- %s created: %s -->\n" % (root, args.date))
        if root: outf.write ("<%s>\n" % root)
        for fname in args.filenames:
            with open (fname) as f:
                outf.write (f.read())
        if root: outf.write ("</%s>\n" % root)

from argparse import ArgumentParser
def parse_cmdline ():
        p = ArgumentParser (description="""\
%(prog)s will create a full JMdict/JMnedict XML file by combining
a DTD and the contents of zero or more XML file containing <entry>
elements.  Note that the entities used in the DTD are from the
standard kw*.csv file in jmdicttdb/data/, not from a database.""")

        p.add_argument ('dtd',
            help="Type of DTD to include: jmdict, jmnedict or jmex")
        p.add_argument ('filenames', nargs='*',
            help="Filename(s) of the xml snippets to be included.")
        p.add_argument ('--date', '-d', default='2020-01-01',
            help="Date to use in the datestamp comment line.  A "
                "specific date can be given in the form: YYYY-MM-DD.  "
                "May be \"now\" to use today's date or \"none\" to "
                "suppress the datestamp line altogether.  The default "
                "is \"2020-01-01\".")
        p.add_argument ('--output', '-o',
            help="Output file name.  If not given outpuut is to stdout.")
        args = p.parse_args ()
        return args

if __name__ == '__main__': main()
