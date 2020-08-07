#!/usr/bin/env python3
# Copyright (c) 2008-2012 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, os, inspect, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, jmxml, pgi, fmt
from jmdictdb.pylib import progress_bar

def main():
        global KW
        args = parse_cmdline()
        if args.logfile:
            open (args.logfile, 'w').close()  # logger needs file to pre-exist.
            logger.log_config (filename=args.logfile)
        if args.database:
            jdb.dbopen (args.database)
            KW = jdb.KW
        else: jdb.KW = KW = jdb.Kwds ('')

        xlang = None
        if args.lang:
            xlang = [KW.LANG[x].id for x in args.lang.split(',')]

        pbar = None
        if args.progress:
            total_items = args.count \
                    or progress_bar.count_items (args.filename,'<entry>')
            pbar = progress_bar.InitBar (
                    title=args.filename, size=total_items, offset=2)

        xmltype = None
        if args.xml_type: xmltype = args.xml_type
        else: xmltype = jmxml.sniff( args.filename )
        if not xmltype: error ("Unable to determine DTD type,"
                               " please use the - option.")
        inpf = jmxml.JmdictFile( open( args.filename ))
        tmpfiles = pgi.initialize (args.tempdir)
        eid = 0
        jmparser = jmxml.Jmparser (KW, xmltype)
        for typ, entr in jmparser.parse_file (
                            inpf, args.begin, args.count,
                            xlang, toptag=True,
                            seqnum_init=args.sequence[0],
                            seqnum_incr=args.sequence[1]):
            if typ == 'entry':
                eid += 1
                if pbar: pbar (eid)
                if not getattr (entr, 'src', None): entr.src = corpid
                jdb.setkeys (entr, eid)
                pgi.wrentr (entr, tmpfiles)
            elif typ == 'grpdef':
                pgi.wrgrpdef (entr, tmpfiles)
            elif typ == 'root':
                  # Note that 'entr' here is actually the tag name of the
                  # top-level element in the xml file, typically either
                  # "JMdict" or "JMnedict".
                pass
          #FIXME! 2nd, 3rd parms hardwaired below for test.
        pgi.wrcorpora (jmparser.corpora, 'jmdict', 'jmdict', tmpfiles)
        sys.stdout.write ('\n')
        pgi.finalize (tmpfiles, args.output, not args.keep)

def parse_seq_opt (s):
        q = [int(x or 1) for x in s.split (',')]
        if len (q) < 2: q.append (1)
        return q[:2]
 
from argparse import ArgumentParser
from jmdictdb.pylib.argparse_formatters import FlexiFormatter

def parse_cmdline():
        u = """\
%(prog)s will read a jmdict XML file such as JMdict or JMnedict and
create a file that can be subsequently loaded into a jmdict Postgresql
database."""

        p = ArgumentParser (description=u, formatter_class=FlexiFormatter)

        p.add_argument ("filename",
            help="Name of output postgresql rebasable dump file.  "
                "By convention this is usually given the suffix \".pgi\".")

        p.add_argument ("-o", "--output", default="JMdict.pgi",
            help="Name of output postgresql rebasable dump file.  "
                "By convention this is usually given the suffix \".pgi\".")

        p.add_argument ("-x", "--xml-type",
            help="XML DTD type: either: \"jmdict\" or \"jmnedict\".  "
                "This is usually not needed since jmparse.py will "
                "guess the type from the file contents.")

        p.add_argument ("-b", "--begin", type=int, default=0,
            help="Sequence number of first entry to process.  If not "
                "given or 0, processing will start with the first entry.")

        p.add_argument ("-c", "--count", type=int, default=0,
            help="Number of entries to process.  If not given or 0, "
                "all entries in the file will be processed.")

        p.add_argument ("-s", "--corpus",
            help="""\

            ."""\
        .replace("\n"+(" "*8),''))   # See Note-1 below.

        p.add_argument ("-g", "--lang",
            dest="lang",
            help="Include only gloss tag with language code LANG.  "
                "If not given default is to include all glosses regardless "
                "of language.")

        p.add_argument ("-q", "--sequence", default='1,1',
            dest="sequence",
            help="If the input XML does not contain entry sequence numbers "
                "in <ent_seq> tags, sequence numbers will be be generated "
                "based on this option with should consist of two comma-"
                "separated numbers with no spaces.  The first is the sequence "
                "number to be used for the first entry.  The second is the "
                "increment between entries.  Either or both may be omitted "
                "in which case the missing number will be taken as 1.  This "
                "option has no effect on entries with a sequence number in "
                "the XML.  ")

        p.add_argument ("-k", "--keep", default=False, action="store_true",
            help="Do not delete temporary files after program exits.")

        p.add_argument ("-l", "--logfile", default="jmparse.log",
            help="Name of file to write log messages to.  If not given, "
                "log mesages will be written stderr.")

        p.add_argument ("-p", "--progress", nargs='?',
                        default="percent", const=None,
            help="""Show progress while running.  Choices are:\n
                * none (or no value): no progress indicator.\n
                * percent (default): show a percentage progress bar.\n
                Because the absence of a value is equivalent to "none",
                 -p alone will disable the progress bar.
                 Progress bar output is written to stderr."""\
                .replace("\n"+(" "*16),''))  # See Note-1 below.

        p.add_argument ("-T", "--tempdir", default=".",
            help="Directory in which to create temporary files.")

        p.add_argument ("-d", "--database",
            help="URI for a JMdictDB database to get tag infomation "
                "from.  If not given, the standard built-in tags will "
                "be used.")

        # Note-1: Help text in triple quotes contains the embedded
        # leading space characters.  These are removed with the
        # '.replace("\n"+" "*16)' method call applied to the string.
        # Lines of text that will be reflowed by the help formatter
        # need to be indented an extra space to prevent them from
        # being appended to the last word on the preceeding line.

        args = p.parse_args ()
        try: args.sequence = parse_seq_opt (args.sequence)
        except (ValueError, IndexError, TypeError):
            p.error ("Bad --sequence (-q) option value.")
        return args

if __name__ == '__main__': main()

