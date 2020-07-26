#!/usr/bin/env python3
# Copyright (c) 2008-2020 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# Read entries from database and write to XML file.  Run with
# --help option for details.

  #FIXME? The --compat=jmex option was originally intended for serializing
  # an entire jmdictdb database to XML but it is no longer useful for that
  # because of the single corpus restriction and that it no longer includes
  # non-active or unappoved entries.  (Not sure where/how the latter
  # inability came about.)  However there seems little need any more to
  # seralize a full database since Postgresql's pg_dump command does that
  # better than we can.  It still has value as a development aid/tool
  # since "jmex" formatted XML is used in generating the diff's used
  # in history records.

import sys, os, re, time, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, fmt, fmtxml
from jmdictdb.pylib import progress_bar

def main():
        global Debug
        opts = parse_cmdline()
        Debug = opts.debug
        cur = jdb.dbOpen (None, **jdb.parse_pguri(opts.dburi))

        seqlist = []
          # opts.seqnums and opts.seqfile won't both be true (although
          # both may be false); prohibited in parse_cmdline().
        if opts.seqnums: seqlist = opts.seqnums
        if opts.seqfile:
            seqlist = read_seqfile (opts.seqfile)

          # Get compatibility info based on user request and corpus type.
        corpid, dtd, compat, dtd_root, dtd_date, appr, warn \
            = compat_info (opts.corpus, opts.compat)
        if warn and not opts.force: sys.exit (
            "The --compat option you requested (%s) incompatible with "\
            "the requested --corpus (%s).  To continue anyway, use the "\
            "--force option." % (opts.compat, opts.corpus))
        if dtd is None: opts.nodtd = True
        if not opts.root: opts.root = dtd_root

          # Get a sql statement that will select all the entries to be
          # extracted, or in the case of a seq# file, the pool of entries
          # containing the seq#s.
        sql_base = select_entries (corpid, opts.begin, opts.count, appr)

          # Following sets 'pbar' to None if no progress indicator wanted,
          #  to "" if 'blocks (aka dots) wanted, or to a progress_bar object
          #  for "percent" (the default).
        if Debug: pbar = None
        else: pbar = setup_progbar (cur, opts.progress, sql_base, seqlist)

          # Open the output file and also write the DTD to it if needed.
          # We wait as late as possible to do this to avoid creating the
          # file if there is some error in the command line arguments that
          # can be detected above.
        outname = opts.output if opts.output else None
        outf = open_output (outname, dtd, opts.root, dtd_date)

          # Read the entries in blocks of 'opts.blocksize', format them
          # as XML, and write them to the output file.
        done = 0
        for entries,raw in read_entries (cur, sql_base, seqlist,
                                         opts.count, opts.blocksize):
            done += len(entries)
            write_entrs (cur, outf, entries, raw, compat)
            if pbar: pbar (done)
            elif pbar == '': sys.stderr.write ('.');  sys.stderr.flush()
            if Debug: print ("%d entries written" % done, file=sys.stderr)

        if not opts.nodtd: outf.writelines ('</%s>\n' % opts.root)
        if not Debug: sys.stderr.write ('\n')
        print ("Wrote %d entries" % done, file=sys.stderr)

def read_entries (cur, sql_base, seqlist, count, blksize):
    # This is a generator that reads and yields successive blocks of entries.
    # Prior to rev 200120-0c649f6 this program allowed extracting entries
    # in different corpora together.  In the aforementioned revision that
    # feature was removed, but primarily from the UI; this function retains
    # the ability to process entries with different 'src' (corpora) values
    # should the desire to restore that ability reappear.

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
                if Debug: print (sql, sql_args, file=sys.stderr)
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
                if Debug: print (sql, sql_args, file=sys.stderr)
                start = time.time()
                tmptbl = jdb.entrFind (cur, sql, sql_args)
            mid = time.time()
            entrs, raw = jdb.entrList (cur, tmptbl, None,
                                       ord="src,seq,id", ret_tuple=True)
            end = time.time()
            if Debug: print ("read %d entries" % len(entrs), file=sys.stderr)
            if Debug: print ("Time: %s (entrFind), %s (entrList)"
                             % (mid-start, end-mid), file=sys.stderr)
            if not entrs : break
            yield entrs, raw
              # Update the 'last*' variables for the next time through
              # the loop.  Also, decrement 'count', if we are counting.
            lastsrc, lastseq, lastid \
                = entrs[-1].src, entrs[-1].seq, entrs[-1].id + 1
            if count is not None: count -= blksize

def select_entries (corpid, begin, count, appr):
    # Based on the entry selection criteria given on the command line
    # (and available here in 'opts'), create a SQL statement that will
    # select the entire set of entries that we will extract from the
    # database.  In the case of a seq# file, the sql will select the
    # pool of entries containing the sequence numbers.
    # Ordering and retrieving these entries in blocks will be done
    # later using the sql generated here as a subselect.

        whr_terms = ["src=%s" % corpid]
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

def write_entrs (cur, outf, entrs, raw, compat, corpora=set()):
          # To format xrefs in xml, they must be augmented so that the
          # the target reading and kanji text will be available.
        jdb.augment_xrefs (cur, raw['xref'])
          # Generate xml for each entry and write it to the output file.
        start = time.time()
        for e in entrs:
            if not compat:
                if e.src not in corpora:
                    txt = '\n'.join (fmtxml.corpus ([e.src]))
                    outf.write (txt + "\n")
                    corpora.add (e.src)
                grp = getattr (e, '_grp', [])
                for g in grp:
                    gob = jdb.KW.GRP[g.kw]
                    if not hasattr (gob, 'written'):
                        gob.written = True
                        txt = '\n'.join (fmtxml.grpdef (gob))
                        outf.write (txt + "\n")
            txt = fmtxml.entr (e, compat=compat, genhists=True)
            outf.write (txt + "\n")
        if Debug: print ("Time: %s (fmt)"%(time.time()-start),file=sys.stderr)

def open_output (filename, dtd, dtd_root, dtd_date):
    # Create and open the output file and write the DTD to it if
    # 'dtd' (the name of the dtd template file) has a non-false
    # str value.
        if not filename: outf = sys.stdout
        else: outf = open (filename, "w")
          # Write the dtd if requested (via a 'dtd_fn' value with the name
          # of the dtd template file to use.  If 'dtd_fn' is false, skip the
          # dtd; the output file will be list <entry> and maybe <corpus>
          # elements.
        if dtd:
            dtdtxt= fmtxml.get_dtd (jdb.KW, dtd)
            outf.write (dtdtxt)
            if dtd_date:
                today = time.strftime ("%Y-%m-%d", time.localtime())
                outf.write ("<!-- %s created: %s -->\n" % (dtd_root, today))
            outf.write ('<%s>\n' % dtd_root)
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

def compat_info (corpus, compat):
        data = {
          # Values:
          #   0 dtd filename:  Name of the DTD template file to use.
          #   1 fmtxml-compat:  Value of 'compat' to pass to fmtxml.entr().
          #   2 root:  Text to use in the XML root element.
          #   3 date: (bool) Include a "created" timestamp in the XML.
          #   4 appr: (bool) Included only active approved entries.
          #   5 srcts: List of compatible corpus types.
          #
          #    dtd name  fmtxml-compat  root       date  appr   srct's
          #    0           1            2          3     4      5
            'jmdict':
              ["jmdict",   'jmdict',    'JMdict',  True, True, ['jmdict']],
            'jmnedict':
              ["jmnedict", 'jmnedict',  'JMnedict',True, True, ['jmnedict']],
            'jmex':
              [None,        None,       'JMdict',  False,False,['jmdict','jmnedict']],
            }
          # Note: when adding/changing/deleting compat entries above, be
          # sure to reflect any key changes in the --compat option choices
          # in parse_cmdline().
          # Note: dtd-filename of "None" will suppress dtd like --nodtd.

        corpid = corpus
        if corpid.isdigit(): corpid = int (corpid)
        corpid = jdb.KW.SRC[corpid].id
        srct = jdb.KW.SRC[corpid].srct
        srctkw = jdb.KW.SRCT[srct].kw
        if not compat: compat = srctkw
        warn = srctkw not in data[compat][5]
        return [corpid] + data[compat][:5] + [warn]

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

                All entries come from a single corpus given by -s/--corpus.
                 All active, approved entries in that corpus are output
                 (but see --compat=jmex) unless a subset are selected by
                 sequence number in the command's arguments, in a file
                 with --seqfile, or with the -b/--begin and -c/--count
                 options.  Entries are written out in sequence number
                 order with duplicates eliminated.
                 The particular XML format and DTD used is automatically
                 chosen based on --corpus but may be overridden with
                 --compat."""\
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

        p.add_argument ("-s", "--corpus", required=True,
            help="Extract entries belonging to this corpus.  May be "
                "given as either a corpus name or id number.  This "
                "option is REQUIRED.")

        p.add_argument ("-o", "--output", default=None,
            help="Filename to write XML to.  If not given, output is "
                "to stdout.")

        p.add_argument ("--compat", default=None,
            choices=['jmdict','jmnedict','jmex'],
            help="""If not given, an appropriate compat value is
                 chosen automatically based on the corpus type.
                 You only need to use this option to generate
                 specalized XML output.

                If given, COMPAT must have one of the following values:

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

        p.add_argument ("--root", "-r",
            help="Name to use as the root element in the output XML file.  "
                "It is normally chosen automatically based "
                "on --compat but can be overridden with this option.  "
                "Will have no effect obviously if --nodtd is given.")

        p.add_argument ("--nodtd", default=None,
            action="store_true",
            help="Do not write a DTD.")

        p.add_argument ("--blocksize", "-B", default=1000,
            type=int, metavar="NUM",
            help="Read and write entries in blocks of NUM entries.  "
                "A larger blocksize will speed up processing substantially "
                "but require more memory.  Default is 1000.")

        p.add_argument ("--progress", default="percent",
            help="""Show progress while running.  Choices are:\n
                * none: no progress indicator.\n
                * percent (default): show a percentage progress bar.\n
                * blocks: print a dot for each block of entries.\n
                Progress bar output is written to stderr.
                 Note when sequence number arguments or --seqfile is
                 given, the program may finish before the progress
                 bar indicates it will since not all entries requested
                 may exist."""\
                .replace("\n"+(" "*16),''))  # See Note-1 below.

        p.add_argument ("-d", "--dburi", default="jmdict",
            help="URI of the database to use.  If the database is local "
                "(on the same machine) and no additional connection "
                "information (username, etc) is needed, this can be "
                "simply the database name.  Default is \"jmdict\".")

        p.add_argument ("-D", "--debug", default="0",
            dest="debug", type=int,
            help="If given a value greater than 0, print debugging information "
                "while executing.  See source code for details.")

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
                     "with --seqfile")
        return args

if __name__ == '__main__': main()
