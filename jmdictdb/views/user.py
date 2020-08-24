#######################################################################
#  This file is part of JMdictDB.
#  Copyright (c) 2018 Stuart McGraw
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

import sys, pdb
sys.path.extend (['../lib','../../python/lib','../python/lib'])
import logger; from logger import L
import jdb, jmcgi

def view (svc, cfg, user, cur, params):
        errs = []; chklist = {}
        fv = params.get; fl = params.getlist
        L('cgi.user').debug("user=%r" % user)
        L('cgi.user').debug("u=%r, new=%r" % (fv('u'), fv('new')))
          # If 'user' evaluates false, user is not logged in in which
          # case we go directly to the "user" page which will say that
          # one has to be logged in.  We do this instead of using an
          # error page because the notes on the users.jinja page inform
          # the user about the requirements for access.
          # If user is logged in but is not an Admin user, we ignore
          # the "u=..." url parameter and show user info only for
          # the logged in user.
          # If the user is an Admin user, we show info for the user
          # requested by the "u=..." parameter if any, or the logged
          # in user if not.
          # There may still be no user due to "u=..." for non-existant
          # or some corner-case but that's ok, page will show a "no user
          # found" message.
        subject = subjectid = new = None
        if user:  # I.e., if logged in...
            if user.priv == 'A':
                subjectid, new = fv ('u'), fv('new')
            if not new and not subjectid: subjectid = user.userid
            L('cgi.user').debug("subjectid=%r, new=%r" % (subjectid, new))
            if subjectid:
                subject = jmcgi.get_user (subjectid, svc, cfg)
                L('cgi.user').debug("read user data: %s" % (sanitize_o(subject),))
        L('cgi.user').debug("rendering template, new=%r" % new)
        return dict(subject=subject, new=new, result=fv('result')), []

def sanitize_o (obj):
        if not hasattr (obj, 'pw'): return obj
        o = obj.copy()
        if o.pw: o.pw = '***'
        return o
