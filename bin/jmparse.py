#!/usr/bin/env python3
# Copyright (c) 2008-2012 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, os, inspect, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import jdb, jmxml, pgi, fmt
from jmdictdb.pylib import progress_bar

def main (args, opts):
        global KW

        if opts.database:
            jdb.dbOpen (opts.database, **jdb.dbopts (opts))
            KW = jdb.KW
        else:
            jdb.KW = KW = jdb.Kwds ('')

        xlang = None
        if opts.lang:
            xlang = [KW.LANG[x].id for x in opts.lang.split(',')]

        pbar = None
        if opts.progbar:
            total_items = opts.count \
                    or progress_bar.count_items (args[0],'<entry>')
            pbar = progress_bar.InitBar (
                    title=args[0], size=total_items, offset=2)

        xmltype = None
        if opts.xml_type: xmltype = opts.xml_type
        else: xmltype = jmxml.sniff( args[0] )
        if not xmltype: error ("Unable to determine DTD type,"
                               " please use the - option.")
        inpf = jmxml.JmdictFile( open( args[0] ))
        tmpfiles = pgi.initialize (opts.tempdir)
        if not opts.logfile: logfile = sys.stderr
        else: logfile = open (opts.logfile, "w")
        eid = 0
        jmparser = jmxml.Jmparser (KW, xmltype, logfile=logfile)
        for typ, entr in jmparser.parse_xmlfile (inpf, opts.begin, opts.count,
                                                 xlang, toptag=True,
                                                 seqnum_init=opts.sequence[0],
                                                 seqnum_incr=opts.sequence[1]):
            if typ == 'entry':
                eid += 1
                if pbar: pbar (eid)
                if not getattr (entr, 'src', None): entr.src = corpid
                jdb.setkeys (entr, eid)
                pgi.wrentr (entr, tmpfiles)
            elif typ == 'corpus':
                pgi.wrcorp (entr, tmpfiles)
            elif typ == 'grpdef':
                pgi.wrgrpdef (entr, tmpfiles)
            elif typ == 'root':
                  # Note that 'entr' here is actually the tag name of the
                  # top-level element in the xml file, typically either
                  # "JMdict" or "JMnedict".
                try: corpid, corprec \
                        = pgi.parse_corpus_opt (opts.corpus, entr, inpf.created, kw=KW)
                except KeyError: pass
                else:
                    if corprec: pgi.wrcorp (corprec, tmpfiles)

        sys.stdout.write ('\n')
        pgi.finalize (tmpfiles, opts.output, not opts.keep)

def parse_seq_opt (s):
        q = [int(x or 1) for x in s.split (',')]
        if len (q) < 2: q.append (1)
        return q[:2]
 
from optparse import OptionParser, OptionGroup
from jmdictdb.pylib.optparse_formatters import IndentedHelpFormatterWithNL

def parse_cmdline ():
        u = \
"""\n\t%prog [options] [filename]

%prog will read a jmdict XML file such as JMdict or JMnedict and
create a file that can be subsequently loaded into a jmdict Postgresql
database (usually after pre-processing by jmload.pl).

Arguments:
        filename -- Name of input jmdict xml file.  Default is
        "JMdict"."""

        p = OptionParser (usage=u, add_help_option=False,
                formatter=IndentedHelpFormatterWithNL())

        p.add_option ("--help",
            action="help", help="Print this help message.")

        p.add_option ("-o", "--output", default="JMdict.pgi",
            dest="output", metavar="FILENAME",
            help="Name of output postgresql rebasable dump file.  "
                "By convention this is usually given the suffix \".pgi\".")

        p.add_option ("-x", "--xml-type", default=None,
            help="XML DTD type: either: \"jmdict\" or \"jmnedict\".  "
                "This is usually not needed since jmparse.py will "
                "guess the type from the file contents.")

        p.add_option ("-b", "--begin", default=0,
            dest="begin", type="int", metavar="SEQNUM",
            help="Sequence number of first entry to process.  If not "
                "given or 0, processing will start with the first entry.")

        p.add_option ("-c", "--count", default=0,
            dest="count", type="int", metavar="NUM",
            help="Number of entries to process.  If not given or 0, "
                "all entries in the file will be processed.")

        p.add_option ("-s", "--corpus",
            dest="corpus", default=None,
            help="""\
        CORPUS defines a corpus record (in table kwsrc) to which all
        entries in the input file will be assigned.  It consists of
        up to seven comma separated items.  Spaces are not permitted
        within the string.  Items can be left out with two adjacent
        commas.

        The CORPUS items are:

          id -- Id number of the corpus record.

          kw -- A short string used as an identifier for the corpus.
             Must start with a lowercase letter followed by zero or
             more lowercase letters, digits, or underscore ("_")
             characters.  Must not already be used in the database.

          dt -- The corpus' date in the form: "yyyy-mm-dd".

          sinc -- The increment value of the Postgresql sequence
              associated with this corpus.  (The seqence will be 
              created automatically with the name "seq_"+<kw>.

          smin -- The minimum value of the Postgresql sequence
              associated with this corpus.

          smax -- The maximum value of the Postgresql sequence
              associated with this corpus.

        [N.B. the database corpus record has an additional field,
        "srct" that identifies the type of the corpus entries (eg
        "jmdict", "jmnedict", etc) but that is supplied automatcally
        by jmparse.py.]

        [N.B. that the corpus table ("kwsrc") also has two other columns,
        'descr' and 'notes' but jmparse provides no means for setting
        their values.  They can be updated in the database table after
        kwsrc is loaded, using standard Postgresql tools like "psql".]

        Unless only 'id' is given in the CORPUS string, a corpus record
        will be written to the output .pgi file.  A record with this 'id'
        number or 'kw' must not exist in the database when the entries
        are later loaded.

        If only 'id' is given in CORPUS, a new corpus record will not
        be created; rather, all enties will be assigned the given corpus
        id number and it will be assumed that a corpus record with that
        id number already exists when the entries are later loaded.

        If this option is not given at all, jmparse will examine the
        name of the top-level element in the input file.  If it is
        "JMdict", jmparse will use "1", "jmdict", and "jmdict_seq"
        for 'id', 'kw', and 'seq' respectively.  If it is "JMnedict",
        jmparse will use "2", "jmnedict", and "jmnedict_seq" for 'id',
        'kw', and 'seq' respectively.  In both cases it will use the
        date extracted from the "date comment" in the input XML file
        if available for 'dt'.
        If the top-level element name is neither "JMdict" or "JMnedict"
        an error will be reported.

        Examples:

            <no option>

                Will create a new corpus record based on information
                extracted from the XML input file as described above.
                This is the usual choice when processing the JMdict
                or jmnedict files downloaded from Monash.

            -s 6,jmdict_2,2008-03-15,jmdict_seq

                Will create a new corpus (kwsrc table) record with
                an id of 6, and name of "jmdict_2", a date of "2008-
                03-15.  It will use the same sequence generator as
                the jmdict corpus (should that also be loaded).

            -s 15,,,myseq

                Will create a new corpus (kwsrc table) record with
                an id of 15.  The name will be taken from the top-
`               level element in the input file, and the date from
                the date comment in the file if it exists.  The corpus
                record will specify sequence "myseq" (which you must
                create sometime before later attempting to add an entry
                with no sequence number).

            -s 5

                Will give all entries produced by this execution
                of jmparse.py a corpus id (entr.src value) of 5 but
                will not generate any kwsrc record in the output
                .pgi file.  When these entries are loaded into the
                database a kwsrc table record with id=5 must already
                exist or an integrity error will occur.""")

        p.add_option ("-g", "--lang", default=None,
            dest="lang",
            help="Include only gloss tag with language code LANG.  "
                "If not given default is to include all glosses regardless "
                "of language.")

        p.add_option ("-q", "--sequence", default='1,1',
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

        p.add_option ("-k", "--keep", default=False,
            dest="keep", action="store_true",
            help="Do not delete temporary files after program exits.")

        p.add_option ("-l", "--logfile", default="jmparse.log",
            dest="logfile", metavar="FILENAME",
            help="Name of file to write log messages to.")

        p.add_option("--no-progress",
            dest="progbar", action="store_false", default=True,
            help="Don't show the progress bar.")

        p.add_option ("-T", "--tempdir", default=".",
            dest="tempdir", metavar="DIRPATH",
            help="Directory in which to create temporary files.")

        p.add_option ("-d", "--database", default=None,
            help="""Name of the database to load keywords from.  If
                not given, static keyword data will read from the file
                .csv files in the standard location.""")

        g = OptionGroup (p, "Database access options",
                """If the --database (-d) option was given, the following
                options determine how to connect to that database.

                Caution: On many systems, command line option contents
                may be visible to other users on the system.  For that
                reason, you should avoid using the "--user" and "--password"
                options below and use a .pgpass file (see the Postgresql
                docs) instead. """)
        g.add_option ("-h", "--host", default=None,
            help="Name or ip address of machine database resides on.")
        g.add_option ("-u", "--user", default=None,
            help="Connect to database with this username.")
        g.add_option ("-p", "--password", default=None,
            help="Connect to database with this password.")
        p.add_option_group (g)

        opts, args = p.parse_args ()
        if len (args) > 1: p.error ("%d arguments given, expected at most one" % len(args))
        if len (args) < 1: args = ["JMdict"]
        try: opts.sequence = parse_seq_opt (opts.sequence)
        except (ValueError, IndexError, TypeError): p.error ("Bad --sequence (-q) option value.") 
        return args, opts

if __name__ == '__main__':
        args, opts = parse_cmdline()
        main (args, opts)

