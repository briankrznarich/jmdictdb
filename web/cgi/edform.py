#!/usr/bin/env python
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
	       '$Date$'[7:-11])

import sys, cgi
sys.path.extend (['../lib','../../python/lib','../python/lib'])
import jdb, jmcgi, fmtjel

def main (args, opts):
	errs = []
	try: form, svc, host, cur, sid, sess, parms, cfg = jmcgi.parseform()
	except Exception, e: errs = [str (e)]
	is_editor = jmcgi.is_editor (sess)
	if not errs:
	    elist = form.getlist ('e')
	    qlist = form.getlist ('q')
	    if elist or qlist:
	        entrs = jmcgi.get_entrs (cur, elist, qlist, errs)
	    else: entrs = []
	    cur.close()
	if not errs:
	    if len (entrs) > 1: 
	        errs.append ("Can\'t edit more than one entry at a time<br>\n"
			 "Note: q=... url parameters may need to qualified<br/>\n"
			 "by a specific corpus, e.g. q=1037440.jmdict")
	if not errs:
	    srcs = sorted (jdb.KW.recs('SRC'), key=lambda x: x.kw)
	    srcs.insert (0, jdb.Obj (id=0, kw='', descr=''))
	    if entrs:
		entr = entrs[0]
		if not is_editor: remove_freqs (entr)
		ktxt = fmtjel.kanjs (entr._kanj)
		rtxt = fmtjel.rdngs (entr._rdng, entr._kanj)
		stxt = fmtjel.senss (entr._sens, entr._kanj, entr._rdng)
		isdelete = (entr.stat == jdb.KW.STAT['D'].id) or None
	    else:
		entr = None; isdelete = None
		ktxt = rtxt = ''
		stxt = "[1][n]"
	    jmcgi.gen_page ('tmpl/edform.tal', macros='tmpl/macros.tal', e=entr, 
			     ktxt=ktxt, rtxt=rtxt, stxt=stxt, parms=parms, 
			     srcs=srcs, is_editor=is_editor, isdelete=isdelete,
			     svc=svc, host=host, sid=sid, session=sess, cfg=cfg, 
			     method='get', output=sys.stdout, this_page='edform.py')
	else:
	    jmcgi.gen_page ('tmpl/url_errors.tal', output=sys.stdout, errs=errs)

def remove_freqs (entr):
	for r in getattr (entr, '_rdng', []): r._freq = []
	for k in getattr (entr, '_kanj', []): k._freq = []

if __name__ == '__main__': 
	args, opts = jmcgi.args()
	main (args, opts)
