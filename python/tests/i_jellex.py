from __future__ import print_function, absolute_import, division
from future_builtins import ascii, filter, hex, map, oct, zip 
import sys
import jellex, jdb, fmtjel

def main (args, opts):
	global KW, tokens

	encoding = opts.encoding or sys.getdefaultencoding()
        lexer, tokens = jellex.create_lexer (debug=opts.debug)
	if opts.seq:
	    instr = _get_text_from_database (opts.seq, 1)
	    print (instr)
	    print ("----------")
	    test (lexer, instr)
	else:
	    while 1:
	        instr = _get_text_interactively(encoding)
	        if not instr: break
		test (lexer, instr)

def test (lexer, instr):
	jellex.lexreset (lexer, instr)
	while 1:
	    tok = lexer.token()
	    if not tok: break
	    print (tok)

def _get_text_from_database (seq, src):
	cur = jdb.dbOpen ('jmdict')
	KW = jdb.KW
	sql = "SELECT id FROM entr WHERE seq=%s AND src=%s"
	elist = jdb.entrList (cur, sql, [seq, src])
	if not elist:
	    print ("Entry %s not found" % seq)
	    return
	entr = elist[0]
	for s in entr._sens:
	    jdb.augment_xrefs (cur, getattr (s, '_xref', []))
	txt = fmtjel.entr (entr)
	txt = txt.partition('\n')[2]
	return txt

def _get_text_interactively (enc='sjis'):
	instr = '';  cnt = 0;  prompt = 'test> '
	while cnt < 1:
            try: s = raw_input(prompt).decode(enc)
            except EOFError: break
	    prompt = ''
            if s: cnt = 0
	    else: cnt += 1
	    if cnt < 1: instr += s + '\n'
	return instr.rstrip()


def _parse_cmdline ():
	from optparse import OptionParser 
	u = \
"""\n\tpython %prog [-d n][-q SEQ]
	
  This is a simple test/exerciser for the JEL parser.  It operates
  in two different modes depending on the presence or absense of 
  the --seq (-q) option.  

  When present it will read the entry with the given seq number
  from the jmdict corpus in the database, format it as a JEL text 
  string, and parse it.  It prints both the input text and the
  object generated from the parse in the same format, and both
  should be functionally identical.  (There may be non-significant
  differences such as tag order.)

  If the --seq (-q) option is not given, this program will read 
  text input interactively until a blank line is entered, feed the 
  text to the parser, and print the resulting object. 

Arguments: (None)
"""
	p = OptionParser (usage=u)
	p.add_option ("-q", "--seq", type="int", default=None,
            help="Parse text generated by reading jmdict seq SEQ from" 
		" database rather than the default behavior of prompting" 
		" interactively for input text.")
	p.add_option ("-E", "--encoding", default=None,
            help="Encoding to assume when reading input.  "
	        "Default is the default system encoding.")
	p.add_option ("-d", "--debug", type="int", default=0,
            help="Debug value to pass to parser:"
		" 1: Lexer tokens")
	opts, args = p.parse_args ()
	#...arg defaults can be setup here...
	return args, opts

if __name__ == '__main__': 
	args, opts = _parse_cmdline ()
	main (args, opts)
