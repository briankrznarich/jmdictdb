#!/usr/bin/env python3
# Copyright (c) 2008-2020 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# Read entries from database and write to XML file.  Run with
# --help option for details.

import sys, os, collections, re, time, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, fmt, fmtxml
from jmdictdb.pylib import progress_bar

# Logging calls:
#  Level     Source
#   8       read_entries
#   9       read_entries.seqlist.sql
#   9       read_entries.all.sql
#   D,I	    (root)

def main():
        opts = parse_cmdline()
        loglvl = logger.levelnum (opts.loglevel)
        logfmt = "%(message)s" if loglvl > 10 else None
        logger.config (level=loglvl, fmt=logfmt)

        cur = jdb.dbOpen (None, **jdb.parse_pguri(opts.dburi))

        seqlist = []
          # opts.seqnums and opts.seqfile won't both be true (although
          # both may be false); prohibited in parse_cmdline().
        if opts.seqnums: seqlist = opts.seqnums
        if opts.seqfile: seqlist = read_seqfile (opts.seqfile)

        corps, ctypes = parse_corpopt (opts.corpus, opts.xml)
        details = compat_details (opts.xml, ctypes)
        compat, dtd, root, datestamp, appr, _, warn = details
        if warn and not opts.force: sys.exit (
            "The --xmlt option you requested:\n"
            "  %s\n"
            "is incompatible with the types of the copora you requested:\n"
            "  %s\n"
            "To continue anyway, please rerun with the --force option."\
            % (opts.compat, ctypes))
        L().info("Writing '%s' compatible XML" % compat)

          # 'dtd' was set above to the default dtd name.
        if dtd: dtd = '\x01' + dtd      # Mark as a dtd name (vs filename).
        if opts.dtd: dtd = opts.dtd     # Override if --dtd was given.
        if opts.no_dtd: dtd = None      # Override if --no-dtd was given.
          # 'root' was set above to the default root name.
        rootpart = "+-"
        if opts.root and opts.root[-1] in ("+-"):
            opts.root, rootpart = opts.root[:-1], opts.root[-1]
        if opts.root: root = opts.root  # Override if --root was given.
        if opts.no_root: root = None    # Override if --no-root was given.

          # Get a sql statement that will select all the entries to be
          # extracted, or in the case of a seq# file, the pool of entries
          # containing the seq#s.
        sql_base = select_entries (corps, opts.begin, opts.count, appr)

          # Following sets 'pbar' to None if no progress indicator wanted,
          #  to "" if 'blocks (aka dots) wanted, or to a progress_bar object
          #  for "percent" (the default).
        if L().level<=10 or not opts.progress or opts.progress=='none':
            pbar = None
        else: pbar = setup_progbar (cur, opts.progress, sql_base, seqlist)

          # Open the output file and also write the DTD to it if needed.
          # We wait as late as possible to do this to avoid creating the
          # file if there is some error in the command line arguments that
          # can be detected above.
        outname = opts.output if opts.output else None
        root_open = root if root and '+' in rootpart else None
        try: outf = open_output (outname, dtd, root_open)
        except OSError as e: sys.exit (str(e))

          # Read the entries in blocks of 'opts.blocksize', format them
          # as XML, and write them to the output file.
        done = 0; counters = collections.Counter()
        for entries,raw in read_entries (cur, sql_base, seqlist,
                                         opts.count, opts.blocksize):
            done += len(entries)
            write_entrs (cur, outf, entries, raw, compat, counters)
            if pbar: pbar (done)
            elif pbar == '': sys.stderr.write ('.');  sys.stderr.flush()
            L().debug("main: block of %d entries written" % done)

        if root and '-' in rootpart:
            outf.writelines ('</%s>\n' % root)
        if opts.progress: sys.stderr.write ('\n')
        L().info("Wrote %d entries %r" % (done, dict(counters)))

def read_entries (cur, sql_base, seqlist, count, blksize):
    # This is a generator that reads and yields successive blocks of entries.

        seqlist_loc, lastsrc, lastseq, lastid = 0, 0, 0, 0
        while count is None or count > 0:
            if seqlist:
                seqnums = tuple (seqlist[seqlist_loc : seqlist_loc+blksize])
                if not seqnums: break
                seqlist_loc += blksize
                  #FIXME: need detection of non-existent seq#s.
                sql = "SELECT id FROM (%s) AS s "\
                      "WHERE seq IN %%s ORDER BY src,seq,id LIMIT %d"\
                      % (sql_base, blksize)
                sql_args = [seqnums]
                L('read_entries.seqlist.sql').log(8,"sql: %s" % sql)
                L('read_entries.seqlist.sql').log(8,"args: %s" % sql_args)
                start = time.time()
                tmptbl = jdb.entrFind (cur, sql, sql_args)
            else:
                  # In this loop we read blocks of 'blksize' entries.  Each
                  # block read is ordered by entr src (i.e. corpus), seq, and
                  # id.  The block to read is specified in WHERE clause which
                  # is effectively:
                  #   WHERE ((e.src=lastsrc AND e.seq=lastseq AND e.id>=lastid+1)
                  #           OR (e.src=lastsrc AND e.seq>=lastseq)
                  #           OR e.src>lastsrc)
                  # and (lastsrc, lastseq, lastid) are from the last entry in
                  # the last block read.
                L('read_entries.start').log(9,"Reading %d entries after src=%s,"
                            " seq=%s, id=%s" % (blksize,lastsrc,lastseq,lastid))
                sql = "SELECT id FROM (%s) AS e "\
                      "WHERE ((e.src=%%s AND e.seq=%%s AND e.id>=%%s) "\
                              "OR (e.src=%%s AND e.seq>%%s) "\
                              "OR e.src>%%s)"\
                      "ORDER BY src,seq,id LIMIT %d"\
                      % (sql_base, blksize)
                  # The following args will be substituted for the "%%s" in
                  # the sql above, in jbd.findEntr().
                sql_args = [lastsrc, lastseq, lastid, lastsrc, lastseq, lastsrc]

                  # Create a temporary table of id numbers and give that to
                  # jdb.entrList().  This is an order of magnitude faster than
                  # giving the above sql directly to entrList().
                L('read_entries.all.sql').log(8,"sql: %s" % sql)
                L('read_entries.all.sql').log(8,"args: %s" % sql_args)
                start = time.time()
                tmptbl = jdb.entrFind (cur, sql, sql_args)
            mid = time.time()
            entrs, raw = jdb.entrList (cur, tmptbl, None,
                                       ord="src,seq,id", ret_tuple=True)
            end = time.time()
            L('read_entries').log(9,"Read %d entries" % len(entrs))
            L('read_entries').log(9,"Time: %s (entrFind), %s (entrList)"
                      % (mid-start, end-mid))
            if not entrs : break
            yield entrs, raw
              # Update the 'last*' variables for the next time through
              # the loop.  Also, decrement 'count', if we are counting.
            lastsrc, lastseq, lastid \
                = entrs[-1].src, entrs[-1].seq, entrs[-1].id + 1
            if count is not None: count -= blksize

def select_entries (corpids, begin, count, appr):
    # Based on the entry selection criteria given on the command line
    # (and available here in 'opts'), create a SQL statement that will
    # select the entire set of entries that we will extract from the
    # database.  In the case of a seq# file, the sql will select the
    # pool of entries containing the sequence numbers.
    # Ordering and retrieving these entries in blocks will be done
    # later using the sql generated here as a subselect.

        if not corpids: whr_terms = ["TRUE"]
        else: whr_terms = ["src IN (%s)"
                           % (",".join([str(x) for x in corpids]))]
        if appr:
            whr_terms.append ("NOT unap")
            whr_terms.append ("stat=%s" % str(jdb.KW.STAT['A'].id))
        if begin:
            whr_terms.append ("seq>=%s" % begin)
        sql_base = "SELECT id,seq,src FROM entr WHERE %s"\
                   % " AND ".join (whr_terms)
        if count:
              # If LIMIT is used, we also require an ORDER BY to
              # make sure the desired subset of entries is selected
              # rather than an arbitrary subset.
            sql_base += " ORDER BY src,seq,id"
            sql_base += " LIMIT %s" % int (count)
        return sql_base

def parse_corpopt (corpspec, compat):
        '''-------------------------------------------------------------------
        corpspec -- (str) A comma separated list to corpus names or id
          numbers to include in the output.  If prefixed with a "!" the
          output will include entries from corpora other than the listed
          ones.  If nil, default value is determined by 'compat'.
        compat -- (str) Compatibility name.  Must be one of: "jmdict",
          "jmnedict", "jmex" or nil.  Denotes the form of the output
          XML and DTD.
        If 'corpspec' is nil and 'compat' is "jmex", all corpora will be
        included.  If 'compat' is other than "jmex", only the corpus with
        the same name as 'compat' will be output.
        If both 'corpspec' and 'compat' are nil a ValueError is raised.
        -------------------------------------------------------------------'''

        if not corpspec and not compat:
            raise ValueError ("'corpspec' and 'compat' both nil.")
        exclude = False
        if not corpspec:
            if compat != 'jmex': corpspec = compat
            else: corpspec, exclude = "!", True    # All corpora.
        if corpspec.startswith('!'): exclude, corpspec = True, corpspec[1:]
        corpspecs = corpspec.split (',')
        corps = set();  nfg = set()
        for corp in corpspecs:
            if not corp: continue  # Ignore blank resulting from .split().
            try: corp = int (corp)
            except ValueError: pass
            try: corpid = jdb.KW.SRC[corp].id
            except KeyError:
                nfg.add (corp);  continue
            corps.add (corpid)
        if nfg: raise KeyError ("Non-existent corpora: %s" % ", ".join(nfg))
        if exclude: corps = {x.id for x in jdb.KW.recs('SRC')} - corps
        ctypes = {jdb.KW.SRC[x].srct for x in corps}
        return corps, ctypes

def write_entrs (cur, outf, entrs, raw, compat, counters=None):
          # To format xrefs in xml, they must be augmented so that the
          # the target reading and kanji text will be available.
        jdb.augment_xrefs (cur, raw['xref'])
          # Generate xml for each entry and write it to the output file.
        start = time.time()
        for e in entrs:
            if not compat or compat == 'jmex':
                grp = getattr (e, '_grp', [])
                for g in grp:
                    gob = jdb.KW.GRP[g.kw]
                    if not hasattr (gob, 'written'):
                        gob.written = True
                        txt = '\n'.join (fmtxml.grpdef (gob))
                        outf.write (txt + "\n")
            txt = fmtxml.entr (e, compat=compat, genhists=True)
            outf.write (txt + "\n")
            if counters is not None: counters[jdb.KW.SRC[e.src].srct] += 1
        L().debug ("write_entries: time: %s (fmt)" % (time.time()-start))

def open_output (filename, dtd, root, datestamp=True):
        '''-------------------------------------------------------------------
        Create and open the output file and optionally write a DTD, a
        datestamp, and the opening tag of the root element to it.

        Parameters:
          filename -- (str) The name of the file to write to.  If None
            or an empty string, output will be written to stdout.
          dtd -- (str) The name of a file or the name of a DTD recognized
            by fmtxml.get_dtd().  If the latter it must be prefixed with
            a '\x01' character.  If None or an empty string no DTD will
            be written.
          root -- (str) Name of an XML root element which will enclose
            the rest of the XML elements.  The opening tag this element
            will be written here.  If None or an empty string, no opening
            tag will be written.
          datestamp -- (bool) If true, and if 'root' is also true, an
            XML comment containing a date stamp for the current date (in
            local time) will be written immediately before the root tag.

        Returns: the file instance for the opened output file.
        -------------------------------------------------------------------'''

        if not filename: outf = sys.stdout
        else: outf = open (filename, "w")
          # Write the dtd if requested (via a 'dtd_fn' value with the name
          # of the dtd template file to use.  If 'dtd_fn' is false, skip the
          # dtd; the output file will be list <entry> and maybe <corpus>
          # elements.
        if dtd:
            if dtd[0] == '\x01':
                dtdtxt= fmtxml.get_dtd (jdb.KW, dtd[1:])
            else:
                with open (dtd) as f: dtdtxt = f.read()
            outf.write (dtdtxt)
        if root and datestamp:
            today = time.strftime ("%Y-%m-%d", time.localtime())
            outf.write ("<!-- %s created: %s -->\n" % (root, today))
        if root: outf.write ('<%s>\n' % root)

        return outf

def read_seqfile (seqfilename):
        if seqfilename == '-': f = sys.stdin
        else:
            f = open (seqfilename)
        seqlist = []
        for lnnum, ln in enumerate (f):
            lnnum += 1
            ln = re.sub (r'\s*#.*', '', ln)
            if not ln: continue
            try: seqlist.extend ([int(x) for x in ln.split()])
            except ValueError as e:
                print ("Bad value in %s at line %s:\n  %s"
                       % (seqfilename, lnnum, str(e)), file=sys.stderr)
        if f != sys.stdin: f.close()
        return seqlist

def compat_details (compat, ctypes):
        '''-------------------------------------------------------------------
        Returns a 7-item list with details for compatibility mode 'compat'
        or details for a recommented mode based on 'ctypes' (a set of corpus
        types) if 'compat' is None.  The last item indicates if the selected
        compat mode if compatible with 'ctypes' ("") or not ("warn").
        -------------------------------------------------------------------'''
        data = {
          # Keys: compat mode.
          # Values:
          #   0 dtd name:  Name of the DTD template file to use (must be
          #       a name recognized by fmtxml.get_dtd().
          #   1 root:  Text to use in the XML root element.
          #   2 date: (bool) Include a "created" datestamp in the XML.
          #   3 appr: (bool) Included only active approved entries.
          #   4 srcts: Set of compatible corpus types.
          #
          #              dtd name    root       date  appr   srct's
          #              0           1          2     3      4
            'jmdict':   ("jmdict",   'JMdict',  True, True, {'jmdict'}),
            'jmnedict': ("jmnedict", 'JMnedict',True, True, {'jmnedict'}),
            'jmex':     ("jmex",     'JMex',    False,False,{'jmdict',
                                                             'jmnedict',
                                                             'kanjidic',
                                                             'examples'}), }
          # Note: when adding/changing/deleting compat entries above, be
          # sure to reflect any key changes in the --compat option choices
          # in parse_cmdline().
          # Note: dtd name of "None" will suppress dtd like --no-dtd.

        if compat: data = {compat: data[compat]}
        for c,(_,_,_,_,srct) in data.items():
            if not (ctypes - srct): return (c,) + data[c] + ('',)
        return (compat,) + data[compat] + ('warn',)

def setup_progbar (cur, prog_type, sql_base, seqlist):
    # Return a value that will be used when displaying a progress indicator:
    #   None: no progress indication wanted.
    #   "":  use "blocks" (print one "." per block) indicator.
    #   progress_bar instance:  use a "percent" indicator.

        if not prog_type or prog_type == 'none': return None
        if prog_type == 'blocks': return ''
          # For the "percent" progress indicator we need an estimate
          # of the total number of entries we'll be processing.
        if seqlist:
              # This estimate may not be accurate since there may be
              # seq#'s in 'seqlist' that are not in the database or
              # duplicates that will produce only one actual entry.
              # But it is about the best we can do conveniently and
              # should at worst overestimate the number of results.
            estimate = len (seqlist)
        else:
              # Get a count of the number of entries that will be
              # retrieved.
            sql = "SELECT COUNT(*) FROM (%s) AS s" % sql_base
            estimate = jdb.dbread (cur, sql)[0][0]

        pbar = progress_bar.InitBar (
                title="", size=estimate, offset=2)
        return pbar

import argparse
from jmdictdb.pylib.argparse_formatters import FlexiFormatter

def parse_cmdline ():
        p = argparse.ArgumentParser (formatter_class=FlexiFormatter,
            description=\
                """%(prog)s will read entries from a JMdictDB database and
                 write them in XML form to a file.\n

                All entries come from a single corpus given by the
                 mandatory option -s/--corpus.
                 All active, approved entries in that corpus are output
                 (but see --compat=jmex) unless a subset are selected by
                 sequence number in the command's arguments, in a file
                 with --seqfile, or with the -b/--begin and -c/--count
                 options.  Entries are written out in sequence number
                 order with duplicates eliminated.
                 The particular XML format and DTD used is automatically
                 chosen based on --corpus but may be overridden with
                 --compat.  The DTD and/or root element may be changed
                 or supressed with --dtd, --no-dtd, --root, --no-root."""\
                .replace("\n"+(" "*16),''))   # See Note-1 below.

        p.add_argument ("seqnums", nargs='*', type=int,
            help="Sequence numbers of entries (in the corpus specified "
                "by --corpus) to be written to the XML output file.  "
                "No notification is currently given for sequence numbers "
                "with non-existent entries, they are effectively ignored.  "
                "If no arguments are given (nor the --seqfile option), "
                "all the entries in the corpus will be written.  "
                "Sequence numbers may be given on the command line "
                "or in the file specified by --seqfile but not both.")

        p.add_argument ("-s", "--corpus",
            help="One or more comma-separated corpus names or id numbers "
                "to output.  May be prefixed with \"!\" to output all "
                "corpora except the ones given.")

        p.add_argument ("-o", "--output", default=None,
            help="Filename to write XML to.  If not given, output is "
                "to stdout.")

        p.add_argument ("-x", "--xml", "--compat", default=None,
              # --compat is for backward compatibility.
            choices=['jmdict','jmnedict','jmex'],
            help="""Determines the format of the output XML and
                 the default DTD used. If not given, an appropriate
                 compat value is chosen automatically based on the
                 corpus type.  If given, COMPAT must have one of
                 the following values:

                * jmdict: generate XML that uses the standard
                  JMdict DTD (rev 1.09).  This is the standard
                  JMdict XML and usually need not be specified.

                * jmnedict: generate XML that uses the standard
                  (post Oct.2014) JMnedict DTD that includes seq
                  numbers and xrefs.  This is the standard JMnedict
                  XML and usually need not be specified.

                * jmex: extended form of XML that can represent
                  multiple corpora including both "jmdict" and
                  "jmnedict".  In this mode deleted and rejected
                  and unapproved entries are included in the output."""\
                .replace("\n"+(" "*16),''))   # See Note-1 below.

        p.add_argument ("--force", action='store_true', default=False,
            help="Continue even if the --compat option chosen is "
                "incompatible with corpus being processed.")

        p.add_argument ("--begin", "-b", default=0,
            type=int, metavar="SEQNUM",
            help="Sequence number of first entry to process.  If not "
                "given or 0, processing will start with the entry "
                "with the smallest sequence number in the requested "
                "corpus.  Mutually exclusive with the --seqfile option "
                "or sequence number arguments.")

        p.add_argument ("--count", "-c", default=None,
            type=int, metavar="NUM",
            help="Number of entries to process.  If not given, all "
                "entries in the requested corpus will be processed.  "
                "Mutually exclusive with the --seqfile option "
                "or sequence number arguments.")

        p.add_argument ("--seqfile", default=None,
            help="Name of a file that contains a sequence numbers "
                "to be processed.  A line may contain multiple sequence "
                "numbers separated by spaces.  A # character indicates a "
                "comment and it and any text to the end of line will be "
                "ignored, as will blank lines.  "
                "No notification is currently given for sequence numbers "
                "with non-existent entries, they are effectively ignored.  "
                "Mutually exclusive with sequence numbers arguments "
                "and the --begin and --count options.")

        p.add_argument ("--root", default=None,
            help="Name to use as the root element in the output XML file.  "
                "If not given the root element will be chosen automatically "
                "based on --compat.  The name may be suffixed with a \"+\" "
                "in which case only the opening tag of the root element "
                "will be output.  A \"-\" suffix will will cause only the "
                "closing tag to be written.  A \"+\" or \"-\" alone will "
                "have the same effect for the default root element name.  "
                "The \"+\" and \"-\" actions are useful when appending the "
                "results of several consecutive executions into a single "
                "file: a \"+\" is used with the first, --no-root with the "
                "middle ones, and \"-\" with the last.  "
                "--root is incompatible with --no-root.")

        p.add_argument ("--no-root", default=False, action="store_true",
            help="Do not generate a root element in the output XML; the "
                "non-DTD output will be an un-enclosed list of <entry> "
                "elements.  Incompatible with --root.")

        p.add_argument ("--dtd", default=None,
            help="Gives the name of a file containing the DTD to use.  "
                "If not given the DTD  will be chosen automatically "
                "based on --compat.  Incompatible with --no-dtd.")

        p.add_argument ("--no-dtd", default=False, action="store_true",
            help="Do not write a DTD.  Incompatible with --dtd.")

        p.add_argument ("--blocksize", "-B", default=1000,
            type=int, metavar="NUM",
            help="Read and write entries in blocks of NUM entries.  "
                "A larger blocksize will speed up processing substantially "
                "but require more memory.  Default is 1000.")

        p.add_argument ("--progress", "-p", nargs='?',
                        default="percent", const=None,
            help="""Show progress while running.  Choices are:\n
                * none (or no value): no progress indicator.\n
                * percent (default): show a percentage progress bar.\n
                * blocks: print a dot for each block of entries.\n
                Progress bar output is written to stderr.
                 Note when sequence number arguments or --seqfile is
                 given, the program may finish before the progress
                 bar indicates it will since not all entries requested
                 may exist."""\
                .replace("\n"+(" "*16),''))  # See Note-1 below.

        p.add_argument ("-d", "--dburi", default='jmdict',
            help="URI of the database to use.  If the database is local "
                "(on the same machine) and no additional connection "
                "information (username, etc) is needed, this can be "
                "simply the database name.  Default is \"jmdict\".")

        p.add_argument ("-L", "--loglevel", default='info',
            help="""Determines logging level with lower numerical values
                 producing more details.  Also accepts keywords.
                   warn (30) -- Show only warning and error messages.
                   info (20) -- Show info and summary messages in addition
                     to the above.  This is the default level.
                   debug (10) -- Debugging messages in addition to the above.
                   9, 8 -- Yet more debuggign messages including SQL used
                     to read entries from the database."""\
                .replace("\n"+(" "*16),''))  # See Note-1 below.)

          # Note-1: Help text in triple quotes contains the embedded
          # leading space characters.  These are removed with the
          # '.replace("\n"+" "*16)' method call applied to the string.
          # Lines of text that will be reflowed by the help formatter
          # need to be indented an extra space to prevent them from
          # being appended to the last word on the preceeding line.

        args = p.parse_args ()
        if  (args.seqfile or args.seqnums) and (args.begin or args.count):
            p.error ("--begin or --count option is incompatible "
                     "with sequence number arguments or --seqfile.")
        if  args.seqfile and args.seqnums:
            p.error ("Sequence number arguments are incompatible "
                     "with --seqfile.")
        if args.root and args.no_root:
            p.error ("Options --root and --no-root are incompatible.")
        if args.root and args.no_root:
            p.error ("Options --dtd and --no-dtd are incompatible.")
        return args

if __name__ == '__main__': main()
