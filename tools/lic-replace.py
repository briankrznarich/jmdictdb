#!/usr/bin/python3

# Tool to replace GPL license text embedded in JMdictDB files with
# an SPDX id.  `tools.lic-replace.py --help` for usage details.

# FIXME: often blows up with UnicodeDecodeError when given binary files.

import sys, os, pdb

def main():
        args = parse_cmdline()
        for fname in args.files:
            if args.verbose: print ("processing %s" % fname, file=sys.stderr)
            result = process_file (fname, args.noaction)
            if result:
                print (fname)
            else:
                print ("no license found, skipped: %s" % fname,
                       file=sys.stderr)
        if args.noaction:
            print ("no files changed due to --noaction option")

def process_file (fname, noaction):
        with open (fname) as infile:
            newfn = process_content (infile, noaction)
        if not newfn: return False
        if not noaction: os.rename (newfn, fname)
        return True

def process_content (infile, noaction):
        spdxid = "# SPDX-License-Identifier: GPL-2.0-or-later"
        key1 = '#' * 70
        key2 = "#  This file is part of JMdictDB."
        key3 = "#  Copyright (c) "
        state = 0;  buffer = [];  outfile = None;  newfn = None
        for lnnum, ln in enumerate (infile):
            if state == 0:         # Before license comments.
                if lnnum > 2:
                      # If we haven't seen any sign of the license comments
                      # in the first few lines, assume it's not present.
                    break
                if ln.startswith (key1): state = 1
                else: buffer.append (ln)
            elif state == 1:       # Comment bar seen.
                if ln.startswith (key2): state = 2
                else:
                      # If the comment bar was not immediately followed by
                      # the "part of JMdictDB line", assume no license text.
                    state = 0;  break
            elif state == 2:       # JMdictDB affiliation line seen.
                if ln.startswith (key3):
                   copyright = ln.replace('#  ', '# ');  state = 3
                else:
                     # If JMdictDB line was not followed by copyright line
                     # then signal something's wrong by breaking in state==3.
                   break
            elif state == 3:       # Copyright line seen.
                if not ln.startswith (key1):
                      # Assume everything up to next comment bar is license.
                    pass
                else:              # Comment bar seen.
                      # This is end of license text, we know we'll write a
                      # a replacement file so open it now.
                    newfn = infile.name + "-licupd"
                    if not noaction:
                        outfile = init_newfile (newfn, buffer,
                                                copyright, spdxid)
                    state = 4
            elif state == 4:
                  # We've skipped the license text, from now on just copy
                  # the source file lines verbatim to the replacement file. 
                if not noaction: print (ln, end='', file=outfile)
            else: assert False, "Bad 'state' value: %s" % state
        if outfile:
            mode = os.stat (infile.fileno()).st_mode
            os.chmod (outfile.fileno(), mode)
            outfile.close()
        if state not in (0, 4):
              # This generally means EOF before end of license comments
              # or unexpected license text (see state==2 above).
            raise RuntimeError ("Unexpected 'state' value: %s" % state)
        return None if state==0 else newfn

def init_newfile (newfn, buffer, copyright, spdxid):
        outfile = open (newfn, 'w');
        for ln in buffer: print (ln, end='', file=outfile)
        print (copyright, end='', file=outfile)
        print (spdxid, file=outfile)
        return outfile

import argparse
def parse_cmdline():
        p = argparse.ArgumentParser(description=
            "In each file replace GPL license text with SPDX IDs.  "
            "Each file will be examined for the presence of the standard "
            "JMdictDB GPL license text, and if found, it will be replaced "
            "with the original copyright line and an SPDX ID line.  The " 
            "name of each file undergoing such replacement is written "
            "to stdout.  A message is written to stderr for each file "
            "that underwent no replacement.  Note that only the file's "
            "mode is preserved; other attributes like owner, group, etc "
            "aren't.")
        p.add_argument ('files', nargs='*')
        p.add_argument ('--noaction', '-n', action="store_true", default=False,
            help="Check all input files for replacable license text and "
                "produce the normal messages but do not create a replacement "
                "file and leave original file unchanged.")
        p.add_argument ('--verbose', '-v', action="store_true", default=False,
            help="Print name of file about to be processed.  Useful to "
               "find a problem file when processing multiple files.")
        args = p.parse_args()
        return args

if __name__ == '__main__': main()
