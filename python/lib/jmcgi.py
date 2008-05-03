#######################################################################
#  This file is part of JMdictDB. 
#  Copyright (c) 2008 Stuart McGraw 
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
#  51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
#######################################################################

__version__ = ('$Revision$'[11:-2],
	       '$Date$'[7:-11]);

import sys, re, os, os.path
import jdb, tal

def args():
	"""
    Command-line argument processing for cgi scripts.

    Python's cgi module will process a commandline argument as though
    it had been received through the environment as it is when a script
    is run by a web server, which is very useful for debugging.  
    However, it expects only the url parameters (the part of the url
    that follows the "?", not the full url (starting with "http://...").
    Accepting the full url is convenient since it allows one to copy/-
    paste urls from a browser to a commendline invocation for debugging.
    This function will remove anything preceeding the url parameters so
    that the cgi module will be happy.
	""" 
	args = [];  opts = object()
	if len(sys.argv) > 1:
	    #args, opts = parse_cmdline()
	    args = sys.argv[1:]

	    if args:
		a1, x, a2 = args[0].partition ('?')
		if a2: sys.argv[1] = a2
	return args, opts

def clean (s):
	if not s: return '' 
	if not re.search ('^[0-9A-Za-z_]+$', s): 
	    raise ValueError ("clean(): Bad string received") 
	return s

def esc(s): #FIXME
	if not s: return ""
	else: return str(s)

def str2seq (q):
	KW = jdb.KW
	a = q.split ('.')
	try: n = int (a[0])
	except (ValueError, IndexError): 
	    raise ValueError("Invalid seq number '%s'." % (q,))
	if n <= 0: raise ValueError("Invalid seq number '%s'." % (q,))
	c = None
	if len(a) > 1: 
	    try: c = int (a[1])
	    except ValueError:
		try: c = KW.SRC[a[1]].id
		except KeyError: raise ValueError("Invalid seq number '%s'." % (q,))
	    if c <= 0: raise ValueError("Invalid seq number '%s'." % (q,))
	return n, c

def str2eid (e):
	n = int (e)
	if n <= 0: raise ValueError()
	return n

def safe (s):
	if not s: return ''
	if re.search (r'^[a-zA-Z_][a-zA-Z_0-9]*$', s): return s
	raise ValueError ()

def get_entrs (dbh, elist, qlist, errs):
	eargs = []; qargs = []; whr = []
        for x in elist:
	    try: eargs.append (str2eid (x))
	    except ValueError:
                errs.append ("Bad url parameter received: " + esc(x))
        if eargs: whr.append ("id IN (" + ','.join(['%s']*len(eargs)) + ")")

        for x in qlist:
	    try: args = str2seq (x)
	    except ValueError:
                errs.append ("Bad url parameter received: " + esc(x))
	    if args[1]:
                whr.append ("(seq=%s AND src=%s)"); qargs.extend (args)
	    else:
		whr.append ("seq=%s"); qargs.append (args[0])
        if not whr: errs.append ("No valid entry or seq numbers given.")
        if errs: return None 

        sql = "SELECT e.id FROM entr e WHERE " + " OR ".join (whr)
        entries, raw = jdb.entrList (dbh, sql, eargs + qargs, ret_tuple=True)
        if entries: 
	    jdb.augment_xrefs (dbh, raw['xref'])
	    jdb.augment_xrefs (dbh, raw['xrer'], rev=1)
 	return entries

def gen_page (tmpl, output=None, **kwds):
	httphdrs = kwds.get ('HTTP', None)
	if httphdrs: print httphdrs, "\n"
	else:
	    if not kwds.get ('NoHTTP', None):
		print "Content-type: text/html\n";
	  # FIXME: 'tmpl' might contain a directory component containing 
	  #  a dot which breaks the following.
	if tmpl.find ('.') < 0: tmpl = tmpl + '.tal'
	tmpldir = find_in_syspath (tmpl)
	if tmpldir == '': tmpldir = "."
	if not tmpldir: 
	    raise IOError ("File or directory '%s' not found in sys.path" % tmpl)
	html = tal.fmt_simpletal (tmpldir + '/' + tmpl, **kwds)
	if output: print >>output, html.encode ('utf-8')
	return html

def fmt_p (entrs):
	# Add a supplemantary attribute to each entr object in
	# list 'entrs', that has a boolean value indicating if 
	# any of its readings or kabji meet wwwjdic's criteria
	# for "P" status (have a freq tag of "ichi1", "gai1",
	# "spec1", or "news1").

	for e in entrs:
	    if jdb.is_p (e): e.IS_P = True
	    else: e.IS_P = False

def fmt_restr (entrs):

	# In the database we store the invalid combinations of readings
	# and kanji, but for display, we want to show the valid combinations.
	# So we subtract the former set which we got from the database from
	# from the full set of all combinations, to get the latter set for
	# display.  We also set a HAS_RESTR flag on the entry so that the 
	# display machinery doesn't have to search all the readings to 
	# determine if any restrictions exist for the entry.

	for e in entrs:
	    if not hasattr (e, '_kanj'): continue
	    nkanj = len (e._kanj)
	    for r in getattr (e, '_rdng', []):
		rs = getattr(r, '_restr', None)
		if not rs: continue
		e.HAS_RESTR = True
		if len (r._restr) == nkanj: r._RESTR= True
		else:
		    r._RESTR = [x.txt for x in 
			jdb.filt (e._kanj, ["kanj"], r._restr, ["kanj"])]

def fmt_stag (entrs): 

	# Combine the stagr and stagk restrictions into a single
	# list, which is ok because former show in kana and latter
	# in kanji so there is no interference.  We also change
	# from the "invalid combinations" stored in the database
	# to "valid combinations" needed for display.

	for e in entrs:
	    stag = []
	    for s in getattr (e, '_sens', []):
		sk = getattr (s,'_stagk', None)
		if sk: stag.extend ([x.txt for x in 
			jdb.filt (e._kanj, ['kanj'], sk, ['kanj'])])
		sr = getattr (s, '_stagr', None)
		if sr: stag.extend ([x.txt for x in
			jdb.filt (e._rdng, ["rdng"], s._stagr, ["rdng"])])
		if stag:
		    s._STAG = stag

def set_audio_flag (entrs): 

	# The display template shows audio records at the entry level 
	# rather than the reading level, so we set a HAS_AUDIO flag on 
	# entries that have audio records so that the template need not
	# sear4ch all readings when deciding if it should show the audio
	# block.
	# [Since the display template processes readings prior to displaying
	# audio records, perhaps the template should set its own global
	# variable when interating the readings, and use that when showing
	# an audio block.  That would eliminate the need for this function.]

	for e in entrs:
	    e.HAS_AUDIO = True
	    for r in getattr (e, '_rdng', []):
		if getattr (r, '_audio', None): break
	    else:
		e.HAS_AUDIO = False

def set_editable_flag (entrs): 

	# This is a conveniene function to avoid embedding this logic 
	# in the TAL templates.  This sets a EDITABLE flag on entries
	# that should have an "Edit" button is entr.tal. 
 
	KW = jdb.KW
	for e in entrs:
	    e.EDITABLE = (e.unap 
		or (e.stat == KW.STAT['N'].id) 
		or (e.stat == KW.STAT['A'].id))


class SearchItems (jdb.Obj):
    """Convenience class for creating objects for use as an argument
    to function so2conds() that prevents using invalid attribute 
    names.""" 

    def __setattr__ (self, name, val):
	if name not in ('idtyp','idnum','src','txts','pos','misc',
			'fld','freq','kinf','rinf','stat','unap',
			'nfval','nfcmp','gaval','gacmp'):
	    raise AttributeError ("'%s' object has no attribute '%s'" 
				   % (self.__class__.__name__, name))
	self.__dict__[name] = val

class SearchItemsTexts (jdb.Obj):
    """Convenience class for creating objects for use in the 'txts'
    attribute of SearchItems objects that prevents using invalid
    attribute names.""" 

    def __setattr__ (self, name, val):
	if name not in ('srchtxt','srchin','srchtyp','inv'):
	    raise AttributeError ("'%s' object has no attribute %s" 
				   % (self.__class__.__name__, name))
	self.__dict__[name] = val

def so2conds (o):
	"""
	Convert an object containing search criteria (typically
	obtained from a web search page or gui search form) into
	a list of search "conditions" suitable for handing to the
	jdb.build_search_sql() function.

	Attributes of 'o':
	  idtyp -- Either "id" or "seq".  Indicates if 'idnum'
		should be interpreted as an entry id number, or
		an entry sequence number.  If the former, all 
		other attributes other than 'idnum' are ignored.
		If the latter, all other attributes other than
		'idnum' and 'src' are ignored.
	  idnum -- An integer that is either the entry id number 
		or sequence number of the target entry.  Which it 
		will be interpreted is determined by the 'idtyp'
		attribute, which but also be present, if 'idnum'
		is present.  
	  src -- List of Corpus keywords.
	  txts -- A list of objects, each with the following
		   attributes:
	      srchtxt -- Text string to be searched for.
	      srchin --Integer indicating table to be searched:
		1 -- Determine table by examining 'srchtxt':
		2 -- Kanj table.
		3 -- rdng table
		4 -- Gloss table.
	      srchtyp -- Integer indicating hot to search for
		   'srchtxt': 
		1 -- 'srchtxt' must match entire text string in table
			(i.e. and "exact" match.)
		2 -- 'srchtxt' matches the leading text in table (i.e.
			anchorded at start).
		3 -- 'srchtxt' matches a substring of text in table
			(i.e. is contained anywhere in the table's text).
		4 -- 'srchtxt' matches the trailing text in table 
			(i.e. anchored at end).
	      inv -- If true, invert the search sense: find entries
		    where the text doesn't match according the the 
		    given criteria.
	  pos -- List of Part of Speech keywords.
	  misc -- List of Misc (sense) keywords.
	  fld -- List of Field keywords.
	  kinf -- List of Kanj Info keywords.
	  rinf -- List of Reading Info of Speech keywords.
	  stat -- List of Status keywords.
	  unap -- List of Unapproved keywords.  #FIXME
	  freq -- List of Frequency keywords.  #FIXME
		Note that an entry matches if there is either a 
		matching kanj freq or a matching rdng freq.  There
		is no provision to specify just one or the other.

	Since it is easy to mistype attrubute names, the classes
	jdb.SearchItems can be used to create an object to pass
	to so2conds.  It checks attribute names and will raise an
	AttributeError in an unrecognised one is used.  
	SearchItemsTexts is similar for the objects in the '.txts'
	list.

	Example:
	    # Create a criteria object that will look for in jmdict
	    # and the tanaka (examples) corpus for entries with
	    # a gloss (srchin=4) containing (srchtyp=2) the text 
	    # "helper". 

	  srch_criteria = jdb.SearchItems (
				 src=['jmdict','examples'], 
				 txts=[jdb.SearchItemsTexts (
				     srchtxt="helper", 
				     srchin=4, 
				     srchtyp=2)])

	    # Convert the criteria object into a "condition list".

	  condlist = so2conds (srch_criteria)

	    # Convert the condition list into the sql and sql arguments
	    # need to perform the search.

	  sql, sql_args = build_srch_sql (condlist)

	    # Give the sql to the entrList() function to retrieve 
	    # entry objects that match the search criteria.

	  entry_list = entrList (dbcursor, sql, sql_args)

	    # Now one can display or otherwise do something with
	    # the found entries.

	"""
	conds = []
	n = int(getattr (o, 'idnum', None) or 0)
	if n:
	    idtyp = getattr (o, 'idtyp')
	    if idtyp == 'id':    # Id Number
		conds.append (('entr','id=%s',[n]))
	    elif idtyp == 'seq':  # Seq Number
		conds.append (('entr','seq=%s',[n]))
		conds.extend (_kwcond (o, 'src',  "entr e", "e.src"))
	    else: raise ValueError ("Bad 'idtyp' value: %r" % idtyp)
	    return conds

	for n,t in enumerate (getattr (o, 'txts', [])):
	    conds.extend (_txcond (t, n))
	conds.extend (_kwcond (o, 'pos',  "pos",    "pos.kw"))
	conds.extend (_kwcond (o, 'misc', "misc",   "misc.kw"))
	conds.extend (_kwcond (o, 'fld',  "fld",    "fld.kw"))
	conds.extend (_kwcond (o, 'kinf', "kinf",   "kinf.kw"))
	conds.extend (_kwcond (o, 'rinf', "rinf",   "rinf.kw"))
	conds.extend (_kwcond (o, 'src',  "entr e", "e.src"))
	conds.extend (_kwcond (o, 'stat', "entr e", "e.stat"))
	conds.extend (_boolcond (o, 'unap',"entr e","e.unap", 'unappr'))
	conds.extend (_freqcond (getattr (o, 'freq', []),
				 getattr (o, 'nfval', None),
				 getattr (o, 'nfcmp', None),
				 getattr (o, 'gaval', None),
				 getattr (o, 'gacmp', None)))
	return conds

def _txcond (t, n):
	txt = t.srchtxt
	intbl  = getattr (t, 'srchin', 1)
	typ    = getattr (t, 'srchtyp', 1)
	inv    = getattr (t, 'srchnot', '')
	cond = jdb.autocond (txt, typ, intbl, inv, alias_suffix=n)
	return [cond]

def _kwcond (o, attr, tbl, col):
	vals = getattr (o, attr, None)
	if not vals: return []
	  # FIXME: following hack breaks if first letter of status descr
	  #  is not same as kw string.  
	if attr == 'stat': vals = [x[0] for x in vals]
	kwids, inv = jdb.kwnorm (attr.upper(), vals)
	if not kwids: return []
	cond = tbl, ("%s %sIN (%s)" % (col, inv, ','.join(str(x) for x in kwids))), []
	return [cond]

def _boolcond (o, attr, tbl, col, true_state):
	vals = getattr (o, attr, None)
	if not vals or len(vals) == 2: return []
	inv = ''
	if vals[0] != true_state: inv = 'NOT '
	cond = tbl, (inv + col), []
	return [cond]

def _freqcond (freq, nfval, nfcmp, gaval, gacmp):
	# Create a pair of 3-tuples (build_search_sql() "conditions")
	# that build_search_sql() will use to create a sql statement 
	# that will incorporate the freq-of-use criteria defined by
	# our parameters:
	#
	# $freq -- List of indexes from a freq option checkboxe, e.g. "ichi2".
	# $nfval -- String containing an "nf" number ("1" - "48").
	# $nfcmp -- String containing one of ">=", "=", "<=".
	# gaval -- String containing a gA number.
	# gacmp -- Same as nfcmp.

	# Freq items consist of a domain (such as "ichi" or "nf")
	# and a value (such as "1" or "35").
	# Process the checkboxes by creating a hash indexed by 
	# by domain and with each value a list of freq values.

	KW = jdb.KW
	x = {};  inv = ''
	if 'NOT' in freq:
	    freq.remove ('NOT')
	    inv = 'NOT '
	# FIXME: we really shouldn't hardwire this...
	if 'P' in freq:
	    freq.remove ('P')
	    freq = list (set (freq + ['ichi1','gai1','news1','spec1']))
	for f in freq:
	      # Split into text (domain) and numeric (value) parts.
	    match = re.search (r'^([A-Za-z_-]+)(\d*)$', f)
	    domain, value = match.group(1,2)
	    if domain == 'nf': have_nf = True
	    elif domain == 'gA': have_gA = True
	    else:
	          # Append this value to the domain list.
	        x.setdefault (domain, []).append (value)

	# Now process each domain and it's list of values...

	whr = []
	for k,v in x.items():
	      # Convert the domain string to a kwfreq table id number.
	    kwid = KW.FREQ[k].id

	      # The following assumes that the range of values are 
	      # limited to 1 and 2.

	      # As an optimization, if there are 2 values, they must be 1 and 2, 
	      # so no need to check value in query, just see if the domain exists.
	      # FIXME: The above is false, e.g., there could be two "1" values.
	      # FIXME: The above assumes only 1 and 2 are allowed.  Currently
	      #   true but may change in future.
	    if len(v) == 2: whr.append ("(freq.kw=%s)" % kwid)
	      # If there is only one value we need to look for kw with
	      # that value.
	    elif len(v) == 1: whr.append ("(freq.kw=%s AND freq.value=%s)" % (kwid, v[0]))
	      # If there are more than 2 values then we look for them explicitly
	      # using an IN() construct.
	    elif len(v) > 2: whr.append (
		"(freq.kw=%s AND freq.value IN (%s))" % (k, ",".join(v)))
	      # A 0 length list should never occur.
	    else: raise ValueError ("No numeric value in freq item")

	  # Handle any "nfxx" item specially here.

	if nfval:
	    kwid = KW.FREQ['nf'].id
	    # Build list of "where" clause parts using the requested comparison and value.
	    whr.append (
		"(freq.kw=%s AND freq.value%s%s)" % (kwid, nfcmp, nfval))

	  # Handle any "gAxx" item specially here.

	if gaval:
	    kwid = KW.FREQ['gA'].id
	      # Build list of "where" clause parts using the requested comparison and value.
	    whr.append (
		"(freq.kw=%s AND freq.value%s%s)" % (kwid, gacmp, gaval))

	  # If there were no freq related conditions...
	if not whr: return []

	# Now, @whr is a list of all the various freq related conditions that 
	# were  selected.  We change it into a clause by connecting them all 
	# with " OR".
	whr = ("%s(" + " OR ".join(whr) + ")") % inv
	
	# Return a triple suitable for use by build-search_sql().  That function
	# will build sql that effectivly "AND"s all the conditions (each specified 
	# in a triple) given to it.  Our freq conditions applies to two tables 
	# (rfreq and kfreq) and we want them OR'd not AND'd.  So we cheat and use a
	# strisk in front of table name to tell build_search_sql() to use left joins
	# rather than inner joins when refering to that condition's table.  This will
	# result in the inclusion in the result set of rfreq rows that match the
	# criteria, even if there are no matching kfreq rows (and visa versa). 
	# The where clause refers to both the rfreq and kfreq tables, so need only
	# be given in one constion triple rather than in each. 

	return [("freq",whr,[])]


def dbOpenSvc (svcname, svcdir=None):
	# This function will open a database connection.  It is
	# intended for the use of cgi scripts where we do not want
	# to embed the connection information (username, password,
	# etc) in the script itself, for both security and
	# maintenance reasons. 
	# It uses a Postgresql "service" file.  For more info
	# on the syntax and use of this file, see:
	#
	#   [Both the following are in Postgresql Docs, libpq api.]
	#   29.1. Database Connection Control Functions
	#   29.14. The Connection Service File
	#
	#   DBD-Pg / DBI Class Methods / connect() method
	#   The JMdictDB README.txt file, installation section.
	#
	# svcname -- name of a postgresql service listed 
	#	in the pg_service.conf file.  If not supplied,
	#	"jmdict" will be used.
	# svcdir -- Name of directory containing the pg_service.conf
	#	file.  If undefined, "../lib/" will be used.  If 
	#	an empty string (or other defined but false value)
	# 	is given, Postresql's default location will be
	#	used.

	if not svcdir: svcdir = find_in_syspath ("pg_service.conf")
	if not svcname: svcname = "jmdict"

	if svcdir: os.environ['PGSYSCONFDIR'] = svcdir

	dbh = jdb.dbOpen (None, dsn='service=%s' % svcname)
	return dbh

def find_in_syspath (fname):
	# Search the directories in sys.path for the first occurance
	# of a readable file or directory named fname, and return 
	# the sys.path directory in which it was found.

	for d in sys.path: 
	    if os.access (os.path.join (d, fname), os.R_OK):
		return d
	return None
