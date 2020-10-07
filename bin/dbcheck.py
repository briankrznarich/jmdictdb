#!/usr/bin/env python3
# Copyright (c) 2010,2020 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# This runs some checks on the data in a jmdictdb database.
# Run 'python3 dbcheck.py --help' for details.

import sys, os, re, textwrap, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import jdb

CHECKS = [
      # Each check is a 4-tuple of:
      #  0 - Check id number.  This is the number used to select
      #    or exclude checks on the command line.  They do not
      #    have to be in order or contiguous.
      #  1 - Short description.  A brief one-line description
      #    of the check.
      #  2 - A long description of the check that is printed in
      #    failure reports and with --list if -v is also given.
      #    If more than entry ids are reported for failures this
      #    description show give the meaning of the reported
      #    values.
      #  3 - A SQL statement that is run to execute the check.
      #    It must return the entry id numbers of failing
      #    entries in a column named "id" and possibly other
      #    details in additional columns.

    (1, "Approved but edit of another entry",
      "Entries that are \"approved\" (entr.unap is FALSE)"
        " but have a non-NULL entr.dfrm value indicating they"
        " are edits of another entry.  Approved entries should"
        " always have a NULL entr.dfrm value.",
      "SELECT e.id "
        "FROM entr e "
        "WHERE NOT e.unap AND e.dfrm IS NOT NULL "
        "ORDER BY e.id"),

    (2, "Dfrm cycles",
      "Entries that are part of a dfrm cycle.  The entr.dfrm"
        " value of an unapproved entr points to the entry"
        " it is an edit of, which may in turn be an edit of"
        " some other entry.  No entry may have a .frm value"
        " that, directly or through a chain of other entries,"
        " refers back to itself.",
      "WITH RECURSIVE wt (id, dfrm, depth, path, cycle) AS ("
             "SELECT e.id, e.dfrm, 1, ARRAY[e.id], false "
             "FROM entr e "
               "UNION ALL "
             "SELECT e.id, e.dfrm, wt.depth+1, path||e.id, e.id=ANY(path) "
             "FROM entr e, wt "
             "WHERE e.id = wt.dfrm AND NOT cycle) "
          "SELECT DISTINCT wt.id FROM wt WHERE cycle"),

    (3, "Multiple active entries",
      "More that one approved and active entry exists with the"
        " same sequence number in a corpus.  Only one should exist."
        " Results are the entry id of the first entry of the"
        " multiple ones, the common seq number and the corpus name.",
      "SELECT MIN(e.id) AS id, c.kw, e.seq "
          "FROM entr e JOIN kwsrc c ON c.id=e.src "
          "WHERE NOT unap and stat=2 "
          "GROUP BY c.kw,e.seq HAVING count(*)>1 "
          "ORDER BY MIN(e.id)"),

    (4, "Multiple seq#s in edit set",
      "Some entries in the edit tree have different corpus or seq"
        " numbers.  Normally all the entries in a tree of edits will"
        " have the same seq# and corpus.  This may not be a problem"
        " if an edit changed an entry's seq# or corpus but it is"
        " unusual enough to report.",
      "SELECT e1.id AS id, e2.id AS id2 "
          "FROM entr e1 "
          "JOIN entr e2 ON e2.dfrm=e1.id "
          "WHERE e1.src!=e2.src OR e1.seq!=e2.seq "
          "ORDER BY e1.id,e2.id"),

    (5, "JIS semicolon in gloss",
      "Entries with a JIS semicolon in a gloss.  Gloss text should"
         " not contain any Japanese characters but JIS semicolons"
         " are sometimes entered by mistake instead of an ASCII "
         " semicolon.",
        # Hex string is unicode codepoint of JIS semicolon.
      "SELECT entr AS id FROM gloss WHERE txt LIKE '%%\uFF1B%%' "
          "ORDER BY entr"),

    (6, "JIS space in gloss",
      "Entries with a JIS space in a gloss.  Gloss text should"
         " not contain any Japanese characters but JIS space"
         " characters are sometimes entred by mistake instead"
         " of an ASCII space.",
        # Hex string is unicode codepoint of JIS space.
      "SELECT entr AS id FROM gloss WHERE txt LIKE '%%\u3000%%' "
          "ORDER BY entr"),

    (7, "No readings or kanji",
      "Every non-deleted, non-rejected entry must have at least"
        " one reading or kanji.",
      "SELECT e.id FROM entr e WHERE stat=2 "
          "AND NOT EXISTS (SELECT 1 FROM rdng r WHERE r.entr=e.id) "
          "AND NOT EXISTS (SELECT 1 FROM kanj k WHERE k.entr=e.id) "
          "ORDER BY e.id"),

    (8, "No readings",
      "Every non-deleted, non-rejected entry in a jmdict or jmnedict"
        " corpus must have at least one reading.  This is not true"
        " for the examples or kanjdic corpora so those are excluded"
        " from this check.",
      "SELECT e.id FROM entr e "
          "JOIN kwsrc c ON c.id=e.src "
          "WHERE stat=2 AND c.srct IN ('jmdict','jmnedict') "
            "AND NOT EXISTS (SELECT 1 FROM rdng r WHERE r.entr=e.id) "
          "ORDER BY e.id"),

    (9, "No senses",
      "Every entry other than those in the kanjidic corpus must have"
        " at least one sense.",
      "SELECT e.id FROM entr e "
          "JOIN kwsrc c ON c.id=e.src "
          "WHERE c.srct NOT IN ('kanjidic') "
            "AND NOT EXISTS (SELECT 1 FROM sens s WHERE s.entr=e.id) "
          "ORDER BY e.id"),

    (10, "No glosses",
      "Every sense must have at least one gloss.",
      "SELECT e.id, s.sens FROM entr e JOIN sens s ON s.entr=e.id "
          "WHERE NOT EXISTS "
          "(SELECT 1 FROM gloss g WHERE g.entr=s.entr AND g.sens=s.sens) "
          "ORDER BY e.id,s.sens"),

    (11, "No part-of-speech",
      "Each sense in a jmdict corpus entry, by convention, must have"
        " at least one part-of speech tag.",
        # We report only the entry id numbers.  To report the sens
        # numbers too use ""SELECT e.id,s.sens FROM..."
      "SELECT DISTINCT e.id FROM entr e JOIN sens s ON s.entr=e.id "
          "JOIN kwsrc c ON c.id=e.src "
          "WHERE c.srct='jmdict' AND NOT EXISTS "
          "(SELECT 1 FROM pos p WHERE p.entr=s.entr AND p.sens=s.sens) "
          "ORDER BY e.id"),

    (12, "Non-sequential kanj numbers",
      "Entries with kanj.kanj numbers that are not sequential or do "
        "not start at one.",
      "SELECT entr AS id FROM kanj "
          "GROUP BY entr HAVING MIN(kanj)!=1 OR COUNT(*)!=MAX(kanj) "
          "ORDER by entr"),

    (13, "Non-sequential rdng numbers",
      "Entries with rdng.rdng numbers that are not sequential or do "
        " not start at one.",
      "SELECT entr AS id FROM rdng "
          "GROUP BY entr HAVING MIN(rdng)!=1 OR COUNT(*)!=MAX(rdng) "
          "ORDER by entr"),

    (14, "Non-sequential sens numbers",
      "Entries with sens.sens numbers that are not sequential or do "
        " not start at one.",
      "SELECT entr AS id FROM sens "
          "GROUP BY entr HAVING MIN(sens)!=1 OR COUNT(*)!=MAX(sens) "
          "ORDER by entr"),

    (15, "Non-sequential gloss numbers",
      "Entries with gloss.gloss numbers that are not sequential or do "
        " not start at one.  Numbers reported are (entr.id, sens.sens)"
        " of the sense containing the problematic gloss.",
      "SELECT entr AS id, sens FROM gloss "
          "GROUP BY entr,sens HAVING MIN(gloss)!=1 OR COUNT(*)!=MAX(gloss) "
          "ORDER by entr,sens"),

    (16, "Deleted or rejected without history",
      "Deleted or rejected entries with no history will not be "
        " expunged by the usual maintenance scripts because with no "
        " history they have no \"age\".",
      "SELECT e.id FROM entr e WHERE stat IN (4,6)"
          "AND NOT EXISTS (SELECT 1 FROM hist h WHERE h.entr=e.id) "
          "ORDER by e.id"),

    (17, "Xref to same seq#",
      "Xrefs must not point to an entry with the same seq# and corpus. "
        " Results are reported as (entr.id, target-entr.id).",
      "SELECT e.id, ex.id AS id2 FROM entr e "
          "JOIN sens s ON s.entr=e.id "
          "JOIN xref x ON x.entr=s.entr AND x.sens=s.sens "
          "JOIN entr ex ON ex.id=x.xentr "
          "WHERE e.seq=ex.seq AND e.src=ex.src "
          "ORDER by e.id"),

    (18, "Nosens xref points to sense other than 1",
      "JMdictDB represents a non-sense specific xref (ie, one to"
        " to an entire entry) by setting the xref's .nosens flag"
        " to True and the target sense (.xsens) to 1.  Entries"
        " reported by this check have .xsens set to something"
        " other than 1.",
      "SELECT e.id FROM entr e "
          "JOIN sens s ON s.entr=e.id "
          "JOIN xref x ON x.entr=s.entr AND x.sens=s.sens "
          "WHERE x.nosens AND x.xsens!=1 "
          "ORDER by e.id"),

    (19, "Seq#s with both deleted and active entries.",
      "When an entry is deleted, all non-rejected versions should be "
        "replaced with a single version marked as deleted.  It is ok "
        "to have coexisting rejected entries after an entry is deleted "
        "but there should be no coexisting active entries.  Results show "
        "seq#s with both an active and deleted entry (deleted-entry-id, "
        "corpus-id, seq-number).",
      "SELECT e.src,e.seq,e1.id "
        "FROM (SELECT id,src,seq FROM entr WHERE stat=4 AND not unap) AS e "
        "JOIN entr e1 ON e1.src=e.src AND e1.seq=e.seq AND e1.id!=e.id "
        "WHERE e1.stat=2 ORDER BY e1.id,src,e.seq"),

    (20, "Seq#s with multiple deleted entries.",
      "When an entry is deleted, all non-rejected versions should be "
        "replaced with a single version marked as deleted.  It is ok "
        "to have coexisting rejected entries after an entry is deleted "
        "but there should be only one deleted version.  Results are "
        "reported as (deleted-entry-id, corpus-id, seq-number).",
      "SELECT e1.id,e.src,e.seq "
        "FROM (SELECT id,src,seq FROM entr WHERE stat=4 AND not unap) AS e "
        "JOIN entr e1 ON e1.src=e.src AND e1.seq=e.seq AND e1.id!=e.id "
        "WHERE e1.stat=4 ORDER BY e1.id,src,e.seq"),

    (21, "Postgresql counter value less than seq#s in corpus.",
      "Entry sequence numbers are automatically assigned on submission "
        "using Postgresql counters confusingly also called sequences.  "
        "These (one for each corpus) will generally have a value that is "
        "the same as the last entry seq# assigned to an entry in the "
        "corpus (since it was from the PG sequence that the entry's seq# "
        "came from).  If there are entries with a seq# greater than the "
        "PG sequence, a duplicate key error will occur when the PG "
        "sequence eventually reaches that value and gives a new entry "
        "the same seq# as the existing entry.  Results are: "
        "(corpus-name, max-entry-seq#, pgseq-value).  'pgseq-value' "
        "should have the same value as 'max-entry-seq#'.",
          # Note: the following checks only for a pgseq value that is less
          # than the corpus' max seq#.  It could also easily check for a
          # pgseq value excessively larger than the max corpus seq# on the
          # grounds that such a condition will produce an undesireably
          # large gap in the entry seq#s and may be the result of an error
          # when manually resetting the pgseq.  But such a condition will
          # last only until a new entry is created.  Since this check
          # program will run periodically, perhaps once a day, it is very
          # likely to miss the short interval when the gap between pgseq
          # and max seq# exists.  So we don't check for it here.
          #FIXME? no column returning an entr.id number...we bad?
      "SELECT kw,seq,last_value AS pg_seq "
        "FROM (SELECT kw,MAX(e1.seq) AS seq "
          "FROM entr e1 JOIN kwsrc k ON k.id=e1.src "
          "GROUP BY kw) AS e "
        "JOIN pg_sequences s ON s.sequencename='seq_'||kw "
        "WHERE seq>last_value"),

    (22, "Large gaps in entry sequence numbers.",
      "It is normal to have small gaps in entry sequence numbers as "
        "entries are removed for various reasons but a large gap may "
        "indicate a problem with automatic seq# assignments or an error "
        "when manually assigning a seq#.  Results are shown as: "
        "(gap, corpus-id, seq#, previous-seq#).",
          #FIXME? no column returning an entr.id number...we bad?
      "SELECT seq-previous AS gap, * "
        "FROM ("
          "SELECT src,seq,"
            "lag(seq) OVER (PARTITION BY src ORDER BY src,seq) AS previous "
          "FROM entr) AS e "
        "WHERE seq-previous >= 150 "
        "ORDER BY src,seq"),
      ]

def main():
        args = parse_cmdline()
        if args.list:
            list_checks (CHECKS, args.verbose);  sys.exit (0);
        cur = jdb.dbOpen (None, **jdb.parse_pguri (args.database))
        errs = ok = 0
        for check in CHECKS:
            chknum, descr, msg, sql = check
            skip = (chknum not in args.chknum) != args.exclude
            if args.chknum and skip: continue
            bad = run_check (cur, check, args.limit, args.corpus,
                             args.verbose)
            if bad: errs += 1
            else: ok += 1
        if args.verbose: print ("%d ok" % ok)
        if args.verbose and errs: print ("%d errors" % errs)
        if errs: sys.exit(1)

def run_check (cur, check, limit, corpus, verbose):
        chknum, descr, msg, sql = check
        name = "Check %d: %s" % (chknum, descr)
        if corpus:
            sql = "SELECT w.* FROM (%s) AS w "\
                  "JOIN entr e ON e.id=w.id WHERE e.src=%s"\
                  % (sql, jdb.KW.SRC[corpus].id)
        if limit: sql += " LIMIT %s" % limit
        cur.execute (sql)
        rs = cur.fetchall()
        if rs:
            print ("\nFailed: %s\n--------" % name, file=sys.stderr)
            print (textwrap.fill(msg), file=sys.stderr)
            print (', '.join ([str(r) for r in rs]
                             + ['more...' if len(rs) >= limit else '']),
                   file=sys.stderr)
            return 1
        if verbose:
            print ("\nPassed: %s" % name, file=sys.stderr)
        return 0

def list_checks (checks, verbose):
        for c in checks:
            chknum, descr, msg, sql = c
            print ("Check %d: %s" % (chknum, descr))
            if verbose: print (textwrap.fill(msg), "\n")

#=====================================================================
from argparse import ArgumentParser
from jmdictdb.pylib.argparse_formatters import ParagraphFormatter

def parse_cmdline ():
        u = """\
Run a number of checks on the database that look for data problems.  If no
errors are found, no output is produced (if -v not given) and %(prog)s
will exit with a status of 0.  If there are errors messages will be written
to stderr and %(prog)s will exit will a status of 1."""

        p = ArgumentParser (description=u, formatter_class=ParagraphFormatter)

        p.add_argument ("chknum", nargs='*', type=int, default=None,
            help="Optional list of check numbers to run, or if -x was given, "
               "to not run.  If omitted, all checks are run.")

        p.add_argument ("-x", "--exclude", action="store_true", default=False,
            help="If given, the chknum arguments are the numbers of "
                "checks not to run.")

        p.add_argument ("-l", "--list", action="store_true", default=False,
            help="List a brief summary of each available test and exit.")

        p.add_argument ("-s", "--corpus", default=None,
            help="Limit checks to one particular corpus.")

        p.add_argument ("--limit", type=int, default=30,
            help="Maximum number of failures to report for a failing "
               "check.  Use \"--limit 0\" to disable any limit. ")

        p.add_argument ("-v", "--verbose", default=False, action='store_true',
            help="Report successful checks as well a failed ones in output.")

        p.add_argument ("-d", "--database", default="pg:///jmdict",
            help="URI for database to open.  The general form is: \n"
                " pg://[user[:password]@][netloc][:port][/dbname][?param1=value1&...] \n"
                "Examples: \n"
                " jmnew \n"
                " pg://remotehost/jmdict \n"
                " pg://user:mypassword@/jmtest \n"
                " pg://remotehost.somewhere.org:8866 \n"
                "For more details see \"Connection URIs\" in the \"Connections Strings\" "
                "section of the Postgresql \"libq\" documentation. ")

        args = p.parse_args()
        return args

if __name__ == '__main__': main()
