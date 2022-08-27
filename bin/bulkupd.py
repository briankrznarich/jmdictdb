#!/usr/bin/env python3
# Copyright (c) 2014-2022 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, os, inspect, re, time, pdb
import psycopg2
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb
from jmdictdb.submit import submission

  # The following text will be automatically appended to the history
  # comments field of every entry updated by a bulk update operation.
  # This text should match the corresponding value in cgi/updates.py.
BULKUPD_TAG = '-*- via bulkupd.py -*-'

pgm = "bulkupd.py"
def F(*args, **kwargs): L(pgm).critical(*args, **kwargs) or sys.exit(1)
def E(*args, **kwargs): L(pgm).error(*args, **kwargs)
def S(*args, **kwargs): L(pgm).log(logger.SUMMARY,*args, **kwargs)
def W(*args, **kwargs): L(pgm).warning(*args, **kwargs)
def I(*args, **kwargs): L(pgm).info(*args, **kwargs)
def D(*args, **kwargs): L(pgm).debug(*args, **kwargs)

def main (cmdargs=sys.argv):
          # Parse command line arguments.
        global Args

        Args = args = parse_cmdline (cmdargs)
        msg_filters = [r'!Dlib.jdb.entr_data\.db']
        if args.loglevel != "debug": msg_filters.append ('!I^submit')
        logger.log_config (level=args.loglevel, filters=msg_filters)

          # Default into for entries' history records.
        hist = dict (name=args.name or '', email=args.email or '',
                     userid=args.userid or '',
                     notes=args.comment or '', refs=args.refs or '')

          # Open a database connection.
        cur = jdb.dbOpen (None, **jdb.parse_pguri (args.database))

          # Parse the input command file.  The result is a list of
          #  3-tuples of seqnums, src, edits.  'edits' in turn is a list
          #  of Cmd() instances that describe a sequence of changes to be
          #  made to the entry identified by seq,src.
          #  parse_cmdfile() returns None if any errors occured.
        if not args.filename: f = sys.stdin
        else:
            try: f = open (args.filename)
            except OSError as e: F(str(e))
        cmds = parse_cmdfile (f, args.corpus)
        if f != sys.stdin: f.close()
        if cmds is None: F("Exiting due to errors in input file")

          # Now go through 'cmds' and make the requested
          # change to each entry.  Changes are commited individually
          # and any failed attempts will result in some flavor of
          # UpdateError, which we catch and print, then continue
          # with the next entry.
        tdone = tskipped = tfailed = trolledback = 0
        for n, (seqnums, src, edits) in enumerate (cmds, start=1):
            I("\nProcessing directive set #%d" % n)
            done,skipped,failed,rolledback \
              = apply (cur, edits, src, seqnums, hist)
            I("Directive set #%d results: %d updated, %d skipped, %d failed"
                    % (n, done, skipped, failed))
            tdone+=done;  tskipped+=skipped;
            tfailed+=failed; trolledback+=rolledback
        S("Total results: %d updated, %d skipped, %d failed"
                % (tdone,tskipped,tfailed))
        if rolledback:
            S("%d updates rolled back due to --noaction" % trolledback)

def apply (cur, edits, src, seqnums, hist):
        '''
          Apply each change in 'edits' to each entry in 'seqnum'.'''

        done = skipped = failed = rolledback = 0
        entries = getentries (cur, seqnums, src)
        skipped += len(seqnums) - len(entries)
        for entr in entries:
            for edit in edits:
                try: doedit (entr, hist, edit)
                except UpdateError as e:
                    E("Entry %s (id %s): %s" % (entr.seq, entr.id, e));
                    skipped += 1;  break
            else: # Executed if the for-loop exits normally (not via 'break').
                   # Pause between updates to database if --delay was
                   # given (in order to lighten load on server for large
                   # updates) but skip delay first time through loop.
                if Args.delay is not None:
                    D("pausing for %s mS")
                    time.sleep (Args.delay/1000.0)
                try: stat = submit (cur, entr, Args.approve, Args.userid,
                                               Args.noaction)
                except UpdateError as e:
                    E(e);  failed += 1
                else:
                    done += 1;
                    if not stat: rolledback += 1
        return done, skipped, failed, rolledback

def parse_cmdfile (cmdfile, initial_corpus):
        # Read and parse the file 'cmdfile' and return None is any errors were
        # encountered or a list of 3-tuples representing the parsed contents if
        # not.  Each 3-tuple consists of:
        #   seqnums -- A list of (int) sequence numbers of entry to be edited.
        #   corpus-number -- (int) id number of corpus containing entry.
        #   cmds -- A list cof Cmd() instances that are the edits to be
        #     applied to the entry.
        errors = 0
        try: src = jdb.KW.SRC[initial_corpus].id
        except KeyError:
            E("Unknown corpus: '%s'" % initial_corpus)
            return None
        cmds = [];  seqnums = [];  edits = [];  cmdtxt = None
        for lnnum, ln in enumerate (cmdfile, start=1):
            ln = ln.strip()
            if not ln: continue                 # Skip blank lines.
            if re.match (r'\s*#', ln): continue # Skip comment lines.
            if ln[0] in "0123456789":
                if cmdtxt not in ('seq', 'id'): cmdtxt = 'seq'
                rest = ln
            else:
                try: cmdtxt, rest = ln.split (maxsplit=1)
                except ValueError:
                    E("line %d: Invalid directive line" % (lnnum))
                    errors += 1; continue
            if cmdtxt in ('corpus', 'seq', 'id'):
                  # A "seq", "id" or "corpus" command ends the previous batch
                  # of edits and starts a new one.  Save the seqence numbers
                  # and edits already collected.
                if edits:
                    cmds.append ([seqnums, src, edits])
                    edits = [];  seqnums = []
                if cmdtxt == 'corpus':
                    try: src = jdb.KW.SRC[rest].id
                    except KeyError:
                        E("line %d: Unknown corpus: '%s'" % (lnnum, rest))
                        errors += 1; corpus = None
                else:  # cmdtxt == 'seq' or cmdtxt == 'id'
                    typ = cmdtxt[0]
                    for seqtxt in rest.split():
                        try: seq = int (seqtxt)
                        except ValueError:
                            E("line %d: Bad %s number: '%s'" % (lnnum, cmdtxt, seqtxt))
                            errors += 1; seq = None
                        else: seqnums.append ((typ, seq))

            else: #'cmdtxt' is other than "corpus' or "seq".
                try: cmd = Cmd (cmdtxt, rest)
                except ParseError as e:
                    E("line %d: %s" % (lnnum, e))
                    errors += 1; continue
                else: edits.append (cmd)
        if edits: cmds.append ([seqnums, src, edits])
        if errors: return None
        return cmds

class Cmd:
      # add/repl/del kanj/rdng [oldtxt] [newtxt]
      # add/repl/del kinf/rinf[kr#/krtxt] [oldtag] [newtag]
      # add/repl/del gloss[sens#] [oldtxt] [newtxt]
      # add/repl/del pos/misc/fld/dial[sens#] [oldkw] [newtag]
      # del entr junktxt
    def __init__ (self, cmd, txt):
        # cmd -- The command directive: one of "add", "repl", "del".
        # txt -- remainder of input file line after removing directive.

        if cmd not in ('add', 'repl', 'del'): raise DirectiveError (cmd)
        self.cmd = cmd
        self.operand = None     # Part of entry to edit ('kanj', 'pos', etc).
        self.sens = None        # Sense number (base 1).
        self.new = None         # Value to add or use for replacement in entry.
        self.old = None         # Value to delete or replace in entry.
        pattern = r'''
          ((?:entr)|(?:kanj)|(?:kinf)|(?:rdng)|(?:rinf)|(?:gloss)|(?:pos)|(?:misc)|(?:fld)|(?:dial)|(?:comment)|(?:refs))
          \s*
          (?:\[([^\]]+)\])?     # Optional sense# or krtext in square brackets.
          \s+
          ((?:[^"][^\s]*)              # Unquoted or...
          |(?:"(?:(?:\\")|[^"])*"))    #  quoted string.
          (?:\s+
          ((?:[^"][^\s]*)              # Optional unquoted...
          |(?:"(?:(?:\\")|[^"])*")))?  #  or quoted string.
          \s*
          $
          '''
        mo = re.match (pattern, txt, re.I|re.X)
        if not mo: raise ArgumentsError (cmd)
        self.operand = mo.group(1).lower()
        self.sens = mo.group(2)
        try: self.sens = int (mo.group(2))    # If sense#, convert to int,
        except (ValueError, TypeError): pass  #  otherwise leave unchanged.
        if self.cmd != 'repl':
            if mo.group(4): raise ReplValError (self.operand)
            if self.cmd == 'add': self.new = clean_quoted_string (mo.group(3))
            else: self.old = clean_quoted_string (mo.group(3))
        else:
            self.old = clean_quoted_string (mo.group(3))
            self.new = clean_quoted_string (mo.group(4))
        if self.operand in ('kanj','rdng','comment','refs'):
            if self.sens:
                raise SensError (self.operand)  # No sense# allowed.
        else:   # self.sens value required.
            if not self.sens: self.sens = 1  # If none was given, use 1.
            if self.operand not in ('kinf', 'rinf'):
                  # kinf, rinf allow text, all others must be an int.
                if type (self.sens) is not int:
                    raise BadSensError (self.operand)
        if self.operand in ('comment','refs'):
            if cmd != 'add': raise NotAddError (cmd)
        if self.operand == 'entr':
            if cmd != 'del': raise NotDelError (cmd)
        if self.operand in ('pos','misc','fld','dial'):
            kwds = getattr (jdb.KW, self.operand.upper())
            for kw in self.old, self.new:
                if not kw: continue
                try: kwds[kw]
                except KeyError: raise KwError (kw, self.operand)

def clean_quoted_string (s):
        if not s.startswith ('"'): return s
          # Remove enclosing quotes and unescape internal quotes.
        s = (s.replace (r'\"', '"'))[1:-1]
        return s

def getentries (cur, numlist, src):
        seqnums, idnums = [], []
        for t, num in numlist:
            if t == 'i': idnums.append (num)
            elif t == 's': seqnums.append (num)
            else: raise ValueError ("Bad value in 'numlist': %s" % t)
        entrs1 = getentries_by_seq (cur, seqnums, src)
        entrs2 = getentries_by_id (cur, idnums)
        return entrs1 + entrs2
        #filtered = []
        #for e in entrs1 + entrs2:
        #    if not e.dfrm: filtered.append (e)
        #    else: E("Entry %s (id=%s) has dependent edited entry"
        #            % ((e.seq, e.id)))
        #return filtered

def getentries_by_seq (cur, seqnums, src):
        # cur -- An open DBAPI cursor to a JMdictDB database.
        # seqnums -- List of sequence number of entries to retrieve.
        # src -- Corpus id number of entry to retrieve.

        if not seqnums: return []
          # Read the entries.  We only get entries that are active-approved
          # or deleted-unapproved.
        KW = jdb.KW
        sql = "SELECT id FROM entr WHERE seq IN %%s AND src=%%s "\
                "AND ((stat=%s and NOT unap) OR (stat=%s and unap))"\
                % (KW.STAT['A'].id, KW.STAT['D'].id)
        entries, raw = jdb.entrList (cur, sql, (tuple(seqnums), src),
                                     ret_tuple=True)
        if len (entries) > len (seqnums):
            raise RetrievalError (
              "More entries received (%s) than requested (%s)"
              % (len(entries), len(seqnums)))
        missing = set (seqnums) - set ([e.seq for e in entries])
        D("Read %d entries, expected %d, %d missing"
                 % (len(entries), len(seqnums), len(missing)))
        if missing:
               # Print missing entries in same order they occur in 'seqnums'.
            for seq in seqnums:
                if seq in missing:
                    W("Entry %s not found" % seq)
        jdb.augment_xrefs (cur, raw['xref'])
        return entries

def getentries_by_id (cur, idnums):
        # cur -- An open DBAPI cursor to a JMdictDB database.
        # idnums -- List of sequence number of entries to retrieve.

        if not idnums: return []
        KW = jdb.KW
        entries, raw = jdb.entrList (cur, None, (tuple(idnums)),
                                     ret_tuple=True)
        if len (entries) > len (idnums):
            raise RetrievalError (
              "More entries received (%s) than requested (%s)"
              % (len(entries), len(seqnums)))
        missing = set (idnums) - set ([e.id for e in entries])
        D("Read %d entries, expected %d, %d missing"
                 % (len(entries), len(idnums), len(missing)))
        if missing:
               # Print missing entries in same order they occur in 'idnums'.
            for id in idnums:
                if id in missing:
                    W("Entry id %s not found" % id)
        jdb.augment_xrefs (cur, raw['xref'])
        return entries

def doedit (entr, hist, cmd):
        # entr -- A jdb.Entr() instance to be edited.
        # hist --  A dict with default info for the edited entry's history
        #   record.  The keys should correspond to Hist init parameters.
        # cmd -- A Cmd instance that describes changes to be made to entry.
        #
        # Apply the change described by <cmd> to <entr> and /or <hist>.
        #
        # Should return True if <entr> or <hist> were actually changed,
        # False if not, but currently always retuns True.

        h = jdb.Hist (**hist)
        entr._hist.append (h)
        new = None
          # The name "operand" here corresponds to "item" in the help text.
        if cmd.operand in ('kanj', 'rdng'):
            tlist = getattr (entr, '_'+cmd.operand)
            if cmd.new:
                if cmd.operand == 'kanj': new = jdb.Kanj (txt=cmd.new)
                else: new = jdb.Rdng (txt=cmd.new)
            edit (tlist, 'txt', cmd.old, new or cmd.new, cmd.operand, cmd.old, cmd.new)
        elif cmd.operand in ('kinf', 'rinf'):
            krlist = getattr (entr, '_'+('kanj' if cmd.operand=='kinf' else 'rdng'))
            krtype = "kanji" if cmd.operand=='kinf' else "reading"
            if type (cmd.sens) is int:
                try: use = krlist[cmd.sens-1]
                except IndexError: raise NoKRError (krtype, cmd.sens)
            else:  # we expect a kanji/kana str, find matching list item.
                use = jdb.first (krlist, lambda kr: kr.txt==cmd.sens, [])
                if not use: raise NoKRError (krtype, cmd.sens)
              #FIXME: what if 'use' is empty?  error? warning? ignore?
            tlist = getattr (use, '_inf')
            new, old = kw2id (cmd.operand, cmd.new, cmd.old)
            edit (tlist, 'kw', old, new, cmd.operand, cmd.old, cmd.new)
        elif cmd.operand == 'gloss':
            try: tlist = getattr (entr._sens[cmd.sens-1], '_'+cmd.operand)
            except IndexError: raise NoSenseError (cmd.sens)
            if cmd.new: new = jdb.Gloss (txt=cmd.new, lang=jdb.KW.LANG['eng'].id,
                                                      ginf=jdb.KW.GINF['equ'].id)
            edit (tlist, 'txt', cmd.old, new or cmd.new, cmd.operand, cmd.old, cmd.new)
        elif cmd.operand in ('pos','misc','fld','dial'):
            try: tlist = getattr (entr._sens[cmd.sens-1], '_'+cmd.operand)
            except IndexError: raise NoSenseError (cmd.sens)
            new, old = kw2id (cmd.operand, cmd.new, cmd.old)
            edit (tlist, 'kw', old, new, cmd.operand, cmd.old, cmd.new)
        elif cmd.operand == 'entr':
            if cmd.cmd == 'del':
                I("Marking entry for deletion")
                entr.stat = jdb.KW.STAT['D'].id
        elif cmd.operand == 'comment': h.notes = cmd.new
        elif cmd.operand == 'refs': h.refs = cmd.new
        else: raise ValueError (cmd.operand)

        return True #FIXME: how to determine if no change was made to entry?

def edit (tlist, srchattr, old, new, operand,  t_old, t_new):
        # tlist -- A _kanj, _kinf, _rdng, _rinf, _gloss, _pos, _misc,
        #   _fld, or _dial list from an entry.
        # srchattr -- Name of attribute to use when searching 'tlist'
        #   for item matching 'old', ie 'txt' for _kanj, _rdng, _gloss,
        #   or 'kw' for _pos, _misc, _fld, _dial, _kinf, _rinf.
        # old -- None or text string or id number that identifies item
        #   to replace or delete in 'tlist'.
        # new -- None or an instance of appropriate type (Kanj(), Pos()
        #   etc.) to replace 'old' in, or append to, 'tlist'.
        # operand -- Used only as text in log messages.
        # t_old -- text form of <old> for use in log messages.
        # t_new -- text form of <new> for use in log messages.
        #
        # If old and not new: delete item from 'tlist' that matches 'old'.
        # If not old and new: add 'new' (should be of correct type) to
        #   end of 'tlist'.
        # If old and new: replace item in 'tlist' that matches 'old'
        #   with 'new' (should be of correct type).

        if old:
            srch = [getattr (t, srchattr) for t in tlist]
            try: index = srch.index (old)
            except ValueError as e:
               raise NoItemError (t_old, operand)
            if not new:
                I("Deleting '%s' from '%s' list" % (t_old, operand))
                del tlist[index]
        if new:
            if not old:
                I("Appending '%s' to '%s' list" % (t_new, operand))
                tlist.append (new)
            else:
                I("Replacing '%s' with '%s' in '%s' list" % (t_old, t_new, operand))
                tlist[index] = new

def kw2id (operand, new, old):
        # Convert keyword str 'new' to a JMdictDB object that can go
        # into an Entr structure, and keyword str 'old' to a keyword
        # id number.
          # Get the right section of KW to allow keyword lookups.  E.g.,
          # if 'operand' is "pos", then get KW.POS so that later we can
          # lookup the id number of a POS key like "v5k" using
          #   kwsect['v5k'].id  (equiv to KW.POS["v5k"].id)
        kwsect = getattr (jdb.KW, operand.upper())
        if new:	    # Convert kw str to an JMdictDB object.
              # Get the class object corresponding to 'operand'; e.g.
              # if 'operand' is "pos", get a jdb.Pos() class object.
            obj = getattr (jdb, operand.capitalize())
              # Create a new instance of the class with an id number
              # corresponding to original value of 'new'.  (The id
              # number is assigned to attribute 'kw' for historical
              # reasons.)
            try: new = obj (kw=kwsect[new].id)
            except KeyError: raise UnknownTagError (operand, new)
        if old:     # Convert kw str to id number.
            try: old = kwsect[old].id
            except KeyError: raise UnknownTagError (operand, old)
        return new, old

def submit (cur, entr, appr, userid, noaction):
        # cur -- An open DBAPI cursor to a JMdictDB database.
        # entr -- Modified entry that will replace current db version
        #    of entry.  We assume that any desired Hist() record has
        #    already been appended.
        # appr -- One of None, True, False:
        #    None: submit with same approval state as orioginal entry.
        #    False: submit as unapproved.
        #    True: submit as approved.
        #    If 'userid' (below) is not provided, 'appr' is ignored and
        #    the entry always submitted as unapproved.
        # userid -- Userid string of an editor listed in jmsess or None.
        #    If this is not provided (is None), the entry will be submitted
        #    as unapproved.  Otherwise the approval status will be controlled
        #    by 'appr' (above).  Note that 'userid' is not valiated or
        #    checked against the jmsess database.
        # noaction -- Boolean which if true will rollback any changes.

          # Add the bulk update tag to the end of the history comments.
        entr._hist[-1].notes += ('\n' if entr._hist[-1].notes else '') \
                               + BULKUPD_TAG

          # Maintain the same approval state in the updated entry
          # as existed in the original entry.
          #FIXME: I don't think this is right for rejected entries.
        if appr is None:
            disp = '' if entr.unap or not bool (userid) else 'a'
        else:
            disp = 'a' if appr else ''
        entr.dfrm = entr.id   # This tells submission() that we are editing an
                              #  existing entry, not creating a new entry.

          # Call the submission() function to make the change to the entry
          # in the database.  This will take care of generating the history
          # record and removing the superceded entry properly.

        I("Submitting %s entry %s (%s) with userid='%s'"
                % ("approved" if disp=='a' else "unapproved",
                   entr.seq, jdb.KW.SRC[entr.src].kw, userid))
        errs = []
        cur.execute ("BEGIN")
        entrid = "(none)"    # In case submission fails.
        try: entrid,_,_ = submission (cur, entr, disp, errs,
                                      is_editor=bool(userid), userid=userid)
        except psycopg2.DatabaseError as e: errs.append (str(e))
        if entrid: D("Added entry id=%s" % entrid)
        if errs:
            E("Submission failed, rolling back")
            cur.execute ("ROLLBACK")
            errmsg = ('\n'.join (errs)).rstrip()
            raise SubmitError (entr.seq, errmsg)
        if noaction:
            D("Rolling back transaction in noaction mode")
            cur.execute ("ROLLBACK")
            stat = 0
        else:
            stat = 1
            D("Doing commit")
            cur.execute("COMMIT")
        return stat   # Return 1 if committed, 0 if noaction rollback.

class RetrievalError(Exception): pass

  # Errors that occur during parsing of the command list.
class ParseError (Exception): pass
class DirectiveError (ParseError):
    def __str__(self): return "Unrecognised directive: '%s'" % self.args[0]
class ArgumentsError (ParseError):
    def __str__(self): return "Unparsable arguments to '%s' directive" % self.args[0]
class SensError (ParseError):
    def __str__(self): return "Sense number not allowed with '%s' directive" % self.args[0]
class BadSensError (ParseError):
    def __str__(self): return "Sense number must be number, not text with '%s' directive" % self.args[0]
class ReplValError (ParseError):
    def __str__(self): return "Replacement value not allowed with '%s' directive" % self.args[0]
class NotAddError (ParseError):
    def __str__(self): return "Can only 'add' comments or refs, '%s' not allowed" % self.args[0]
class NotDelError (ParseError):
    def __str__(self): return "Can only 'del' entries, '%s' not allowed" % self.args[0]
class KwError (ParseError):
    def __str__(self): return "'%s' not a valid value for '%s'" % self.args

  # Errors that occur when excuting the commands.
class UpdateError (Exception): pass
class NoItemError (UpdateError):
    def __str__(self): return "no '%s' item in %s list" % (self.args[0], self.args[1])
class SubmitError (UpdateError):
    def __str__(self): return "%s: %s" % (self.args[0], self.args[1])
class NoSenseError (UpdateError):
    def __str__(_): return "has no sense %s" % (_.args[0])
class NoKRError (UpdateError):
    def __str__(_): return "has no %s '%s'" % (_.args[0],_.args[1])
class UnknownTagError (UpdateError):
    def __str__(_): return "unknown %s tag: '%s'" % (_.args[0],_.args[1])
#-----------------------------------------------------------------------

from argparse import ArgumentParser
from jmdictdb.pylib.argparse_formatters import ParagraphFormatter

def parse_cmdline (cmdargs):
        u = \
"Bulkupd.py will edit and submit changes to multiple entries " \
"based on an input file that describes the entries to be modified " \
"and the modifications to be made to them."

        p = ArgumentParser (description=u, formatter_class=ParagraphFormatter)

        p.add_argument ("filename", nargs='?', default=None,
            help="Name of file containing bulk update commands.  If omitted, "
                "the commands will be read from stdin.")

        p.add_argument ("-n", "--noaction", default=False,
            action="store_true",
            help="Perform the actions including updating the entries in the "
                "database but roll back the transaction so the changes are undone. "
                "This allows doing a trial run to find errors but without making "
                "any permanent changes.")

        p.add_argument ("--corpus", default='jmdict',
            help="Name of corpus that entries will be looked for in, until "
                "overridden by a \"corpus\" directive in the command file.  "
                "If not given the default is \"jmdict\".")

        p.add_argument ("-c", "--comment", default=None,
            help="Text that will be used for a comment for all updated entries "
                "that don't have entry-specific comments in the command file.  "
                "Note that an additional line will be added automatically that "
                "indicates this was a bulk update so that infomation need not "
                "be included in this option's value.")

        p.add_argument ("-r", "--refs", default=None,
            help="Text that will be used for references for all updated entries "
                "that don't have entry-specific references in the command file.")

        p.add_argument ("-s", "--name", default='',
            help="Name to be used for submitter.")

        p.add_argument ("-e", "--email", default='',
            help="Submitter's email address.")

        p.add_argument ("-u", "--userid", default='',
            help="User id of editor.  If not given, the modified entries will "
                "be created in an unapproved state.  If given, the modified "
                "entries will be created in the same approval state that the "
                "original entries were in or as requested by --approve.  "
                "This argument is not validated in any way -- write access "
                "to the database by the user executing this program is "
                "sufficient to allow any changes including approval of the "
                "updated entry.  ")

        p.add_argument ("--approve", default=None, choices=['yes','no'],
            help="Set the updated entries to approved or unapproved as "
                "indicated.  If this option is not given at all, approval "
                "status of the updated entries will remain the same as each "
                "parent entry if --userid was also given or will be set to "
                "unapproved if --userid was not given.  Giving --approve "
                "without --userid is an error.")

        p.add_argument ("--delay", type=int, default=None,
            help="Pause for this number of milliseconds between each update"
                "operation.  This allows for lightening the load on the "
                "database server.")

        p.add_argument ("-d", "--database", default="pg:///jmdict",
            help="URI for database to open.  The general form is: \n"
                " pg://[user[:password]@][netloc][:port][/dbname][?param1=value1&...] \n"
                "Examples: \n"
                " jmnew \n"
                " pg://remotehost/jmdict \n"
                " pg://user:mypassword@/jmtest \n"
                " pg://remotehost.somewhere.org:8866 \n"
                "For more details see the "
                "\"Connection URIs\" in the \"Connections Strings\" "
                "section of the Postgresql \"libq\" documentation. ")

        p.add_argument ("-l", "--loglevel", default="info",
                        choices=['error','summary','warn','info','debug'],
            help="Logging level for messages: only mesages at or above"
               "this level will be printed.")

        p.epilog = """\
Input file syntax:

The input file is a text file and each line contains a directive followed
by arguments.  The number and meaning of the arguments depends on the
directive.  Blank lines and comments (lines starting with a # character,
possibly preceeded with whitespace) are ignored.

Directives:
    corpus <name>
        Set the "current" corpus to <name>.  This determines what corpus
        will be searched for entries given by subsequent "seq" directives.
        A corpus can be also be specified with the --corpus command line
        option and it will remain in effect until a "corpus" directive
        is encountered in the input file.
    [seq] <seq-number> [<seq-number>...]
        Set the current entry set to given sequence numbers.  The directives
        following will apply to these entries.  The "seq" text is optional;
        a line starting with a number is assumed to be a "seq" line.  Multiple
        seq lines can occur in succession and the following edit directives
        will apply to all of given entries.
    id <entry-id-number> [<entry-id-number>...]
        Set the current entry set to given entry id numbers.  The directives
        following will apply to these entries.  Multiple id lines can occur
        in succession and the following edit directives will apply to all of
        given entries.  The 'corpus' value is ignored when processing entries
        identified by id number.
    add <item> [<ownid>] <new-value>
        <item> is one of:
          kanj, kinf, rdng, rinf, gloss, pos, misc, fld, dial, comment, refs.
        [<ownid>] (square brackets required) tells bulkupd which, of possible
          multiple items the item could belong to, are to be used.  For items
          associated with a sense (gloss, pos, misc, fld, dial), it is a sense
          number and if not provided will be assumed to be 1.
          For kinf or rinf items it must be the text of the owning kanji or
          reading item or the kanji/reading ordinal number.  If not provided
          the first kanji or reading item will be assumed.
          For other items (comment, refs) an ownid must not be given.
        <new-value> If item is kanj, rdng, gloss, comment or refs, this is
          the text for the item to be added.  If it contains any whitespace,
          the entire string should be enclosed in doublequote (") characters.
          If such a quoted string also contains any doublequote (") characters
          they should be escaped with as backslash (\) character.
          If item is kinf, rinf, pos, misc, fld or dial, <new-value> is the
          keyword that is to be added.
        Note that a comment line indicating the entry was modified by a bulk
        update will be added to the entry automatically; any comment added
        with a "comment" item will be prepended to that generated text.
    del <item> [<ownid>] <old-value>
        <item> and <ownid> have the same meanings as for the "add"
        directive except that "comment" and "refs" are not valid.
        <old_value> is either text or a keyword that will searched for
        in the current entry and removed.  An error will be generated and
        no changes made to the current entry if no text or keyword matching
        <old-value> is found.
    del entr xxx
        The entry with the current seq number will be deleted. "xxx" is
        any arbitrary text (required to keep the parser happy.)
    repl <item> [<ownid>] <old-value> <new-value>
        <item> and <ownid> have the same meanings as for the "add"
        directive except that "comment" and "refs" are not valid.
        <old_value> is either text or a keyword and will be replaced by
        <new-value>.  An error will be generated and no change made to
        the current entry if no text or keyword matching <old-value> is
        found.

Usage examples:
    python3 bulkupd.py -u jwb -c 'Update per edict maillist discussion' \\
        -s 'Jim Breen' -e 'jimbreen@gmail.com'
      # Following entry is 呉れる（くれる）
    seq 1269130
    repl pos v1 v1-ik
      # Following entry is だ
    2089020
    add pos cop-da
      # Following is 良い（いい）
    seq 1605820
    repl pos[1] adj-i adj-ix
    repl pos[2] adj-i adj-ix
    repl pos[3] adj-i adj-ix
    repl pos[4] adj-i adj-ix
      # Multiple seq numbers can be given
    seq 1882070 1901840 1901860 1927550
    add comment "deleted because ..."
    del entr x
      # Multiple sequence numbers can also occur on separate
      # lines.  The following does the same as the preceding
      # example.
    1882070
    1901840
    1901860
    1927550
    add comment "deleted because ..."
    del entr x
      # ... or any combination of the above.
    1882070 1901840
    1901860
    seq 1927550
    add comment "deleted because ..."
    del entr x

Missing capabilities:
There is no way at present to do the following:
  * Add/repl/del an entire sense.
  * Add/repl/del lsrc, freq, stagk, stagr, restr, xref, ginf, lang elements.
  * Reorder elements.
  * Use multi-line comments or refs in the command file.
"""
        args = p.parse_args (cmdargs[1:])
        if args.approve and not args.userid:
            p.error ("--approve requires --userid")
          # 'args.approve' will be either None, "yes", or "no".
          # Convert the latter two to True and False respectively.
        if args.approve is not None:
            args.approve = args.approve == 'yes'
        return args

if __name__ == '__main__': main()
