#!/usr/bin/env python3
# Copyright (c) 2008-2012 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# WARNING --  this file has only been partially converted to Python3.

# This program build a complete XML file by combining a DTD
# with a number of files containing one ot more XML elements.
# It is used by the jmdictdb testing framework to generate
# test files from components.
# See also: jmextract.py -- Pulls subset of elements out of
#   a jmdict or jmnedict file.

import sys, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'

def main (args, opts):
        if sys.stdout.encoding != opts.encoding:
            sys.stdout = open (sys.stdout.fileno(), 'w', encoding=opts.encoding)
        parts = []
        dtdfname = args.pop(0)
        dtd = get_dtd (dtdfname, opts.orig_root, opts.root, opts.encoding)
        sys.stdout.write (dtd)
        sys.stdout.write ("<%s>\n" % opts.root)
        for fname in args:
            sec = open (fname, 'r', encoding='utf-8').read()
            if sec[0] == '\uFEFF': sec = sec[1:]
            sys.stdout.write (sec)
        sys.stdout.write ("</%s>\n" % opts.root)

def get_dtd (dtdfname, origroot, newroot, newenc):
        dtd = open (dtdfname, 'r').read()
        if dtd[0] == '\uFEFF': dtd = dtd[1:]
        if newenc != "UTF-8":
            a = dtd.replace ('<?xml version="1.0" encoding="UTF-8"?>',
                             '<?xml version="1.0" encoding="%s"?>' % newenc, 1)
            if a == dtd:
                a = dtd.replace ('<?xml version="1.0">',
                                 '<?xml version="1.0" encoding="%s"?>' % newenc, 1)
            if a == dtd:
                print ("Unable to replace DTD encoding", file=sys.stderr)
                sys.exit (1)
            dtd = a
        if newroot != origroot:
            a = dtd.replace ('\n<!DOCTYPE %s [\n' % origroot,
                             '\n<!DOCTYPE %s [\n' % newroot, 1)
            if a == dtd:
                print ("Unable to replace DTD doctype root declaration", file=sys.stderr)
                sys.exit (1)
            dtd = a
            a = dtd.replace ('\n<!ELEMENT %s' % origroot,
                             '\n<!ELEMENT %s' % newroot, 1)
            if a == dtd:
                print ("Unable to replace DTD root entity declaration", file=sys.stderr)
                sys.exit (1)
            dtd = a
        return dtd

from optparse import OptionParser, OptionGroup
from jmdictdb.pylib.optparse_formatters import IndentedHelpFormatterWithNL

def parse_cmdline ():
        u = \
"""\n\t%prog [options] dtd-file [elements-file [elements-file [...]]

%prog will combine a DTD file and a number of files containing xml
elements into a single xml file that is written to stdout.
The ENC and ROOT values given in the --encoding and --root options
are substituted into the DTD, and all the elements read from the
input files are wrapped in a root element with tag ROOT.  Note the
input DTD is not actually parsed; rather the new ROOT and ENV values
are replaced by string substitution, so the DTD must be formatted
identically (including whitespace) to the stndard Monash JMdict or
JMnedict XML files.

Arguments:
        dtd-file -- DTD file with substitutable encoding and root
            (such as python/lib/dtd-jmdict.xml.)  You can also
            use a dtd file with hardcoded encoding or root tag but
            the output xml file will not be valid unless the values
            given in --encoding and --root agree.
        elements-file -- A file containing xml elements that will
            be included under the root element in the output files.
            All input files are assumed to be utf-8 encoded.
            Caution: Some jmdictdb tools expect entry elements to
            be in seq-number order.  This program simply concatentates
            the input file entries so it is the user's responsibility
            to provide appropriate input files in the right order
            if ordered entries in the output file are wanted.
            """

        p = OptionParser (usage=u)

        p.add_option ("-e", "--encoding", default="UTF-8",
            metavar="ENC",
            help="""Enoding to use in the output xml file (including
                the encoding declaration in the DTD).  All input files
                are presumed to be utf-8.)""")

        p.add_option ("-r", "--root", default="JMdict",
            help="""Name of root element to use in the output DTD.""")

        p.add_option ("--orig-root", default="JMdict",
            help="""Name of root element to be replaced in the input DTD.""")

        opts, args = p.parse_args ()
        if len(args) < 1: p.error ("Expected at least one input file.")
        return args, opts

if __name__ == '__main__':
        args, opts = parse_cmdline()
        main (args, opts)

