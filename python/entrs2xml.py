#!/usr/bin/env python3
#######################################################################
#  This file is part of JMdictDB.
#  Copyright (c) 2008-2020 Stuart McGraw
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

# Read entries from database and write to XML file.  Run with
# --help option for details.

import sys, os, inspect, pdb
_ = os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])
_ = os.path.join (os.path.dirname(_), 'python', 'lib')
if _ not in sys.path: sys.path.insert(0, _)

import time, re
import pylib.progress_bar
import jdb, fmt, fmtxml

def main():
        global Debug
        opts = parse_cmdline()
        Debug = opts.debug
        cur = jdb.dbOpen (None, **jdb.parse_pguri(opts.dburi))

          # If no "--root" option was supplied, choose a default based
          # on the value of the "--compat" option.
        if not opts.root:
            if opts.compat in ('jmnedict','jmneold'): opts.root = 'JMnedict'
            else: opts.root = 'JMdict'

        seqlist = []
          # opts.seqnums and opts.seqfile won't both be true (although
          # both may be false); prohibited in parse_cmdline().
        if opts.seqnums: seqlist = opts.seqnums
        if opts.seqfile:
            seqlist = read_seqfile (opts.seqfile)

          # Get a sql statement that will select all the entries to be
          # extracted, or in the case of a seq# file, the pool of entries
          # containing the seq#s.
        sql_base = select_entries (opts)

          # Following sets 'pbar' to None if no progress indicator wanted,
          #  to "" if 'blocks (aka dots) wanted, or to a progress_bar object
          #  for "percent" (the default).
        if Debug: pbar = None
        else: pbar = setup_progbar (cur, opts.progress, sql_base, seqlist)

          # Open the output file (which also writes the DTD to it if needed).
          # We wait as late as possible to do this to avoid creating the
          # file if there is some error in the command line arguments that
          # can be detected above.
        outname = opts.output if opts.output else None
        outf = open_output (outname, opts.nodtd, opts.compat, opts.root)

          # Read the entries in blocks of 'opts.blocksize', format them
          # as XML, and write them to the output file.
        done = 0
        for entries,raw in read_entries (cur, sql_base, seqlist,
                                         opts.count, opts.blocksize):
            done += len(entries)
            write_entrs (cur, entries, raw, [], opts.compat, outf)
            if pbar: pbar (done)
            elif pbar == '': sys.stderr.write ('.');  sys.stderr.flush()
            if Debug: print ("%d entries written" % done, file=sys.stderr)

        if not opts.nodtd: outf.writelines ('</%s>\n' % opts.root)
        if not Debug: sys.stderr.write ('\n')
        print ("Wrote %d entries" % done, file=sys.stderr)

def read_entries (cur, sql_base, seqlist, count, blksize):
    # This is a generator that reads and yields successive blocks of entries.
        seqlist_loc = 0;  corpora = set()
        lastsrc, lastseq, lastid = 0, 0, 0

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

def select_entries (opts):
    # Based on the entry selection criteria given on the command line
    # (and available here in 'opts'), create a SQL statement that will
    # select the entire set of entries that we will extract from the
    # database.  In the case of a seq# file, the sql will select the
    # pool of entries containing the sequence numbers.
    # Ordering and retrieving these entries in blocks will be done
    # later using the sql generated here as a subselect.

        corpid = opts.corpus
        if corpid.isdigit(): corpid = int (corpid)
        corpid = jdb.KW.SRC[corpid].id

        whr_terms = ["src=%s" % corpid]
        if opts.compat:
            whr_terms.append ("NOT unap")
            whr_terms.append ("stat=%s" % str(jdb.KW.STAT['A'].id))
        if opts.begin:
            whr_terms.append ("seq>=%s" % opts.begin)
        sql_base = "SELECT id,seq,src FROM entr WHERE %s"\
                   % " AND ".join (whr_terms)
        if opts.count:
              # If LIMIT is used, we also require an ORDER BY to
              # make sure the desired subset of entries is selected
              # rather than an arbitrary subset.
            sql_base += " ORDER BY src,seq,id"
            sql_base += " LIMIT %s" % int (opts.count)
        return sql_base

def write_entrs (cur, entrs, raw, corpora, compat, outf):
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

def open_output (filename, nodtd, compat, root):
    # Create and open the output file and write the DTD to it if requested.
        if not filename: outf = sys.stdout
        else: outf = open (filename, "w")
        if not nodtd: write_dtd (outf, compat, root)
          # Add an enclosing root element only if we are also including
          # a DTD (ie, producing a full XML file).  Otherwise, the file
          # generated will just be a list of <entr> elements.
        if not nodtd:
            if compat:  # Add a date comment...
                today = time.strftime ("%Y-%m-%d", time.localtime())
                outf.write ("<!-- %s created: %s -->\n" % (root, today))
            outf.write ('<%s>\n' % root)
        return outf

def write_dtd (outf, compat, root):
          # Choose a dtd to use based on the "--compat" option.
          # The dtd file is expected to be located somewhere in the
          # pythonpath (sys.path) directories.
        if   compat == 'jmdict':     dtd = "dtd-jmdict.xml"
        elif compat == 'jmdicthist': dtd = "dtd-jmdict.xml"
        elif compat == 'jmnedict':   dtd = "dtd-jmnedict.xml"
        elif compat == 'jmneold':    dtd = "dtd-jmneold.xml"
        else:                        dtd = "dtd-jmdict-ex.xml"
        dir = jdb.find_in_syspath (dtd)
        dtdfn = dir + "/" + dtd             # Fully qualified dtd file name.
          # jdb.get_dtd() reads the dtd text and replaces the root
          # element name name.
        dtdtxt= jdb.get_dtd (dtdfn, root)
        outf.write (dtdtxt)
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

        pbar = pylib.progress_bar.InitBar (
                title="", size=estimate, offset=2)
        return pbar

import argparse
from pylib.argparse_formatters import FlexiFormatter

def parse_cmdline ():
        p = argparse.ArgumentParser (description=
            "%(prog)s will read entries from a JMdictDB database and "
            "write them in XML form to a file.",
            formatter_class=FlexiFormatter)

        p.add_argument ("seqnums", nargs='*', type=int,
            help="Sequence numbers of entries (in the corpus specified "
                "by --corpus) to be written to the XML output file.  "
                "Entries are written to the output file in the same order "
                "as given.  "
                "No notification is currently given for sequence numbers "
                "with non-existent entries, they are effectively ignored.  "
                "If no arguments are given (nor the --seqfile option), "
                "all the entries in the corpus will be written.  "
                "Sequence numbers may be given on the command line "
                "or in the file specified by --seqfile but not both.")

        p.add_argument ("-o", "--output", default=None,
            help="Filename to write XML to.  If not given, output will "
                "be to stdout.")

        p.add_argument ("-s", "--corpus", default="jmdict",
            help="Extract entries belonging to this corpus.  May be "
                "given as either a corpus name or id number.  Default is "
                "\"jmdict\".")

        p.add_argument ("--compat", default=None,
            choices=['jmdict','jmnedict','jmneold','jmdicthist'],
            help="""If given, COMPAT must have one of the following values:

                * jmdict: generate XML that uses the standard
                  JMdict DTD (rev 1.09).

                * jmnedict: generate XML that uses the standard
                  (post 2014-10) JMnedict DTD that includes seq
                  numbers and xrefs.

                * jmneold: generate XML that uses the old-style
                  (pre 2014-10) JMnedict DTD that does not include
                  seq numbers and xrefs.

                * jmdicthist: generate XML that uses the standard
                  JMdict DTD (rev 1.09) but includes an <info> element
                  with the entry's full history.

                If not given: generate XML that completely
                 describes the entry using an enhanced version
                 of the jmdict DTD."""\
                .replace("\n"+(" "*16),''))   # See Note-1 below.

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
                "Entries are written to the output file in the same order "
                "as given.  "
                "No notification is currently given for sequence numbers "
                "with non-existent entries, they are effectively ignored.  "
                "Mutually exclusive with sequence numbers arguments "
                "and the --begin and --count options.")

        p.add_argument ("--root", "-r",
            help="Name to use as the root element in the output XML file.  "
                "It is normally chosen automatically based "
                "on --compat but can be overridden with this option." )

        p.add_argument ("--nodtd", default=None,
            action="store_true",
            help="Do not write a DTD or root element. If this option "
                "is given, --root is ignored.")

        p.add_argument ("--blocksize", "-B", default=1000,
            type=int, metavar="NUM",
            help="Read and write entries in blocks of NUM entries.  "
                "Default is 1000.")

        p.add_argument ("--progress", default="percent",
            help="""Show progress while running.  Choices are:

                * none: no progress indicator.

                * percent (default): show a percentage progress bar.

                * blocks: print a dot for each block of entries.

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
