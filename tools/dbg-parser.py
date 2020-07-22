#!/usr/bin/env python3
# Copyright (c) 2018 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# Run the JEL lexer or parser using input read from stdin
# and print the results.

import sys, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, jelparse, jellex

def main():
        args = parse_cmdline()
        logger.log_config (level=args.level)
        jdb.dbOpen (args.database)   # Initializes jdb.KW which is needed
                                     #  by the lexer and parser.
        if args.jel:
            run (args.action, args.jel, args.trace, args.brk)
            return
        while True:
            print ("Enter text (can be multi-line), ^D to parse, ^C to exit")
            try: intxt = sys.stdin.read()
            except KeyboardInterrupt: break
            run (args.action, intxt, args.trace, args.brk)
        print()

def run (action, intxt, trace, brk):  
        if not intxt: return
        intxt = ffify (intxt)
        if action == 'lex':       # Run lexer
            lex (intxt)
        elif action == 'parse':   # Run parser
            try: entr = parse (intxt, trace)
            except Exception as excp:
                print (excp)
                if hasattr (excp, 'loc'):
                    print (excp.loc.replace('\f','')) 
            else: 
                print (entr)
                if brk: pdb.set_trace()
        else: raise ValueError ("Bad 'action' value")

def lex (intxt):
        lexer, tokens = jellex.create_lexer()
        jellex.lexreset (lexer, intxt)
        while True:
            tok = lexer.token()
            if not tok: break      # No more input
            print (tok)
        print ("done")
        return None

def parse (intxt, trace):
        entr = None; errs = []
        lexer, tokens = jellex.create_lexer ()
        parser = jelparse.create_parser (lexer, tokens)
        jellex.lexreset (lexer, intxt)
        entr = parser.parse (tracking=True, debug=trace)
          #FIXME: need something that shows the full contents of the entry.
        return entr

def ffify (intxt):
        # Formfeed-ify the input text string.
        # The jel lexer and parser, as of rev 180523-472f52fa, require
        # the kanji, reading , and sense sections to be separated with
        # form-feed characters, not \n's as previously.  Because
        # form-feed characters are hard to enter interactively, we
        # allow the two character sequence "\f" or "^L" and replace
        # any occurances of them with real formfeeds ("\f").
        # If there are no formfeeds in 'intxt' at all (after the
        # above replacements), we replace the first two \n's with
        # formfeeds.
        #FIXME: replacing first two '\n's doesn't work with the
        # experimental "extended jel" metainfo proposal since the 
        # metainfo preceeds the reading/kanji text and can have
        # newline characters in it.  

        if "\\f" in intxt: intxt = intxt.replace ("\\f", "\f")
        if "\f" in intxt: return intxt
        return intxt.replace ("\n", "\f", 2)

def parse_cmdline():
        import argparse
        p = argparse.ArgumentParser (description=
            'Run the JEL lexer or parser on arbitrary text to view '
            'or debug its output.  '
            'If a second argument is given on the command line, it '
            'will be used as the JEL text to lex or parse.  If a second '
            'argument is not given you will be repeatedly promped to '
            'enter the text to be lexed/parsed; multiline JEL entries '
            'can also be entered in this mode.  '
            'If formfeeds aren\'t used at least three lines should be '
            'entered with the kanji text on the first line, the reading '
            'text on the second, and the sense text on the third and '
            'subsequent lines.  '
            'Alternatively the input text can be entered in raw form '
            'using form-feed characters to separate the reading, kanji '
            'and senses sections.  If the two character sequence "\\f" '
            'or the two character sequence "^L" are entered, they will '
            'be converted to a form-feed character.  ' 
            'Type ^D when input in complete.  Type ^C to exit.')
        p.add_argument ('action', choices=['lex','parse'],
            help="Action to perform.")
        p.add_argument ('jel', nargs='?', default=None,
            help="JEL text to lex or parse.  If not given you will be "
                "prompted to enter the JEL text.")
        p.add_argument ('--break', '-b',
            dest='brk',  # "break" is a Python reserved word. 
            default=False, action='store_true',
            help="Start the Python debugger after a successful parse "
                "to allow detailed examination of the resulting Entr "
                "object.  Has no effect when action is \"lex\".")
        p.add_argument ('--level', '-l', default='debug',
            help="Logging message level.  One of: \"debug\", \"warn\" or "
                "\"error\".  Default is \"debug\".")
        p.add_argument ('--trace', '-t', default=False, action='store_true',
            help="Print parser actions by running the parse with Ply's "
                "debug option.  Has no effect when action is \"lex\".")
        p.add_argument ('--database', '-d', default='jmdict',
            help="URL for a JMdictDB database that will be used as "\
                "the source for keyword values.  Default is \"jmdict\".")
        args = p.parse_args ()
        return args

if __name__ == '__main__': main()
