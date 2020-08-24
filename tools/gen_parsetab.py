#!/usr/bin/env python3
""" Program to generate parser tables from the jelparse module. """

import sys, os, inspect, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import jdb, jellex, jelparse

def main():
        jdb.KW = jdb.Kwds (jdb.std_csv_dir())
        lexer, tokens = jellex.create_lexer (debug=0>>8)
        jelparse.create_parser (lexer, tokens, module=jelparse,
                                tabmodule='jelparse_tab',
                                write_tables=1, optimize=0, debug=1)

if __name__ == '__main__': main()
