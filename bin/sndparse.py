#!/usr/bin/env python3
# Copyright (c) 2008 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# Read sound clips from XML file and generate a Postgresql loadable
# dump file.

import sys, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import jdb, jmxml, pgi

def main (args, opts):
        m = {'vol':'sndvol', 'sel':'sndfile', 'clip':'snd'}
        inpf = jmxml.JmdictFile( open( args[0] ))
        workfiles = pgi.initialize (opts.tempdir)
        snd_iter = jmxml.parse_sndfile (inpf)
        for obj, typ, lineno in snd_iter:
            pgi._wrrow (obj, workfiles[m[typ]])
        pgi.finalize (workfiles, args[1], delfiles=(not opts.keep), transaction=True)

from optparse import OptionParser, OptionGroup

def parse_cmdline ():
        u = """\

        %prog xml-filename pgi-filename

%prog reads an XML file containing JMdict audio data and will
write a loadable Postgresql dump file.

Arguments:
        xml-filename -- Name of input XML file.
        pgi-filename -- Name of output postgresql dump file (typically
                        given a .pgi suffix)."""

        p = OptionParser (usage=u, add_help_option=False)

        p.add_option ("-k", "--keep", default=False,
            dest="keep", action="store_true",
            help="Do not delete temporary files after program exits.")

        p.add_option ("-t", "--tempdir", default=".",
            dest="tempdir", metavar="DIRPATH",
            help="Directory in which to create temporary files.")

        p.add_option ("--help",
            action="help", help="Print this help message.")

        opts, args = p.parse_args ()
        if len (args) != 2: p.error ("%d arguments given, expected two" % len(args))

        return args, opts


if __name__ == '__main__':
        args, opts = parse_cmdline()
        main (args, opts)
