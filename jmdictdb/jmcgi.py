# Copyright (c) 2008-2019 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, os, os.path, re, cgi, html
import urllib.request, urllib.parse, urllib.error
import random, time, http.cookies, datetime, time, copy
from jmdictdb import jdb, config, fmt
from jmdictdb import jinja; from markupsafe import Markup, escape as Escape
from jmdictdb import logger; from jmdictdb.logger import L

  # Path to the config file relative to the current working directory
  # of the web server (which for Apache2/CGI is the web/cgi/ directory.)
CONFIG_FILE = "../lib/config.ini"

def initcgi (cfgfile):
        """
        Does three things:
        1. Fixes any url command line argument so that it is usable by
          the cgi module (see the args() function).
          Currently the only argument accepted is a url used when this
          script run interactively for debugging.  In the future it may
          also accept an option giving the location of a configuration
          file.
        2. Reads the configuration file and optional auth file.  (The
          database authorization details can be set in either the main
          configuration file or in a separate file for only those details
          allowing permissions on the former to be broader than on the
          latter.)
        3. Initializes the Python logging system so log messages will have
          a consistent format. JMdictDB developers should not call the
          logger.L function() until after this function is called.
        """

          # Adjust any url argument so that the cgi module can use it.
        args()
          # If the .ini filename below has no directory separator in it,
          # it is looked for in a directory on sys.path.  If it does have
          # a separator in it it is treated as a normal relative or
          # absolute path.
        cfg = config.cfgRead (cfgfile)
        logfname = cfg.get ('logging', 'LOG_FILENAME')
        loglevel = cfg.get ('logging', 'LOG_LEVEL')
        filters = parse_cfg_logfilters (
                   cfg.get ('logging', 'LOG_FILTERS'))
          # Logfile path is relative to the config file directory.
          # If 'logfname' is an absolute path, os.path.join() will
          # ignore the preceeding directory so no need for us to check.
          # Access the cfg in dict form because we want a KeyError if
          # the cfg_dir info is unexpectedly not present.
        if logfname:
            logfname = os.path.join (cfg['status']['cfg_dir'], logfname)
        logger.log_config (level=loglevel, filename=logfname, filters=filters)
        return cfg

    #FIXME: parseform() and other functions raise standard Python errors
    # (e.g. ValueError) for many detected problems such as a bad entry
    # or sequence number.  Unexpected internal errors of course will
    # also produce Python exceptions.  Currently the cgi scripts catch
    # any exceptions and display them on an error page or via the
    # logger.handler uncaught exception handler.  Showing exceptions
    # that are potentially correctable by a user is ok.  But showing
    # all exceptions is dangerous -- a failure to connect to a database
    # could reveal a url containing a password for example.  Unexpected
    # exceptions should go only into the log file and the error page
    # sgould report something generic ("Oops, something went wrong").
    # Perhaps we should use a separate error class for user-relevant
    # exceptions?

def parseform (readonly=False):
        """\
    Do some routine tasks that are needed for (most) every page,
    specifically:
    * Call cgi.FieldStorage to parse parameters.
    * Extract the svc parameter, validate it, and open the requested database.
    * Get session id and handle log or logout requests.
    Return an 8-tuple of:
        form (cgi.FieldStorage obj)
        svc (string) -- Checked svc value.
        dbg (int) -- true if "dbg" url param has true value, else 0.
        cur (dbapi cursor) -- Open cursor for database defined by 'svc'.
        sid (string) -- session.id in hexidecimal form or "".
        sess (Session inst.) -- Session for sid or None.
        params (dict) -- Received and decoded form parameters.
        cfg (Config inst.) -- Config object from reading config.ini.
        """

          # Read config files and initialize logging.
          #FIXME: ini file names shouldn't be hardwired, maybe an
          #  environment variable or something?
        cfg = initcgi (CONFIG_FILE)
        L('lib.jmcgi.parseform').debug("called in %s" % sys.modules['__main__'].__file__)
        errs=[]; sess=None; sid=''; cur=None; svc=None
        def_svc = cfg['web'].get ('DEFAULT_SVC', 'jmdict')
        if def_svc.startswith ('db_'): def_svc = def_svc[3:]
        check_server_status (cfg.get ('web', 'STATUS_DIR'),
                                      os.environ.get('REMOTE_ADDR'))

        form = cgi.FieldStorage()
        L('lib.jmcgi').debug("query_string: %s" % os.environ.get('QUERY_STRING'))
        for k in form.keys():
          v = ['***']*len(form.getlist(k)) if k in ('password','pw1','pw2') \
                                           else form.getlist(k)
          L('lib.jmcgi.parseform').debug("form key %s=%r" % (k,v))
        dbg = int (form.getfirst ('dbg') or '0')
        svc = form.getfirst ('svc') or def_svc
        #L('lib.jmcgi.parseform').debug("svc=%s" % svc)
        usid = form.getfirst ('sid') or ''    # No SID is "", not None.
        try: svc = safe (svc)
        except ValueError: errs.append ('svc=' + svc)
        if not errs:
            try: cur = jdb.dbOpenSvc (cfg, svc)
            except KeyError as e: errs.append ('svc=' + str(e))
        if errs: raise ValueError (';'.join (errs))

          # Login, logout, and session identification...
        scur = jdb.dbOpenSvc (cfg, svc, session=True, nokw=True, noverchk=True)
        action = form.getfirst ('loginout') # Will be None, "login" or "logout"
        sid = get_sid_from_cookie() or ''
        sid_from_cookie = bool (sid)
        if usid: sid = usid     # Use sid from url if available.
        L('lib.jmcgi.parseform').debug("sid=%s, from_cookie=%s, action=%s" % (sid, sid_from_cookie, action))
        uname = form.getfirst('username') or ''
        pw = form.getfirst('password') or ''
        sid, sess = get_session (scur, action, sid, uname, pw)
        L('lib.jmcgi.parseform').debug("%s session, sid=%s" % ("got" if sess else "no", sid))
        if sid: set_sid_cookie (sid, delete=(action=="logout"))
        if sid_from_cookie: sid=''
        scur.connection.close()

          # Collect the form parameters.  Caller is expected to pass
          # them to the page template which will use them in the login
          # section as hidden parms so the page can be recreated after
          # a login.  We leave out any param name "result" since that
          # is used as a confirmation message by the userupd.py page
          # and best to see it only once.
        parms = [(k,v)
                 for k in list(form.keys())
                 if k not in ('loginout','username','password', 'result')
                     for v in form.getlist(k) ]

        return form, svc, dbg, cur, sid, sess, parms, cfg

def check_server_status (status_file_dir, ipaddr):
        location = None
        sfd = status_file_dir
        if check_blocked (status_file_dir, ipaddr):
            location = 'status_blocked.html'
        elif os.access (os.path.join (sfd, 'status_maint'), os.F_OK):
            location = 'status_maint.html'
        elif os.access (os.path.join (sfd, 'status_load'), os.F_OK):
            location = 'status_load.html'
        if location:
            print ("Location: %s\n" % ('../' + location))
            sys.exit (0)

def check_blocked (status_file_dir, ipaddr):
        if not ipaddr: return False
        try:
            with open (os.path.join (status_file_dir, 'status_blocked')) as f:
                lines = f.readlines()
        except OSError: return False
        for ln in lines:
              # Comment lines allowed but need no special check since
              # they won't match an IP address.
              # Look at only the first word, allowing ip address to be
              # followed by comment.
            words = ln.strip().split()
            if words and words[0] == ipaddr: return True
        return False

COOKIE_NAME = 'jmdictdb_sid'
SESSION_TIMEOUT = 4 * 60   # In minutes; used in dblogin(), db_validate_sid(),
                           #  db_del_old_sessions(), set_sid_cookie() below.

def get_session (cur, action=None, sid=None, uname=None, pw=None):
        # Do the authentication action specified by 'action':
        #  None -- Lookup 'sid' and return a session if there is one.
        #  "login" -- Create a new session authenticating with 'uname'
        #       and 'pw'.  Return the session and its sid.
        #  "logout" -- Lookup session 'sid' and delete it.
        #
        # cur (dbapi cursor object) -- Cursor to open jmsess database.
        # action (string) -- None, "login", or "logout".
        # sid (string) -- Session identifier if logged in or None is not.
        # uname (string)-- Username (only required if action is "login".)
        # pw (string)-- Password (only required if action is "login".)
        #
        # Returns: sid, sess

        sess = None
        if not action and not sid: # Not logged in
            return '', None
        if not action:             # Use sid to retrieve session.
            sess = dbsession (cur, sid)
            if not sess: sid = ''
        elif action == 'logout':
            if sid: dblogout (cur, sid)
              # Don't clear 'sid' because its value will be needed
              # by caller to delete cookie.
        elif action == 'login':
            if not re.match (r'^[a-zA-Z0-9_]+$', uname): return '', None
            sid, sess = dblogin (cur, uname, pw)
        else: pass    # Ignore invalid 'action' parameter.
        return sid, sess

def dbsession (cur, sid):
        # Return the session identified by 'sid' or None.
        # As a side effect, if we have a sucessful login we
        # delete all expired session records in the session
        # table.  This will hopefully avoid the need for a
        # cron job to prune expired entries.

        sess = db_validate_sid (cur, sid)
        if not sess: return None
        db_del_old_sessions (cur)
        db_update_sid_ts (cur, sid)
        return sess

def dblogin (cur, userid, password):
        # Login by authenticating the userid/password pair.
        # and getting a session record which is returned with
        # the session id.  If 'userid' has an active session
        # already, it (the most recent one if more than one)
        # is returned.  If not, a new session is created.
        # Reusing existing sessions help prevent the proliferation
        # of sessions that was occuring previously.

          # Check userid, password validity.
        sql = "SELECT userid FROM users "\
              "WHERE userid=%s AND pw=crypt(%s, pw) AND NOT disabled"
        rs = jdb.dbread (cur, sql, (userid, password))
        if not rs:
            L('lib.jmcgi.dblogin').debug("pw fail for %s" % userid)
            time.sleep (1);  return '', None

          # Look for an existing session (the most recent if more than one).
        sql = "SELECT s.id,s.userid,s.ts,u.fullname,u.email,u.priv" \
              " FROM sessions s JOIN users u ON u.userid=s.userid" \
              " WHERE u.userid=%%s AND NOT u.disabled" \
              "  AND (NOW()-ts)<'%s'::INTERVAL" \
              " ORDER BY ts DESC LIMIT 1" % SESSION_TIMEOUT
        rs = jdb.dbread (cur, sql, (userid,))
        L('lib.jmcgi.dblogin').debug("%s: %s sessions found" % (userid, len(rs)))
        if len (rs) == 1:
            sid = rs[0][0]
              # Update the session timestamp to 'now'.
            db_update_sid_ts (cur, sid)
            L('lib.jmcgi.dblogin').debug("%s: using session: %s" % (userid,sid))
            return sid, rs[0]

          # No existing session found, create a new session.
        sql = "INSERT INTO sessions(userid) VALUES(%s) RETURNING(id)"
        cur.execute (sql, (userid,))
        sid = cur.fetchone()[0]
        cur.connection.commit()
        L('lib.jmcgi.dblogin').debug("%s: new session %s" % (userid,sid))
        sess = db_validate_sid (cur, sid)
        return sid, sess

def dblogout (cur, sid):
        if not sid: return
          # Make logout delete all users sessions so that
          #  a logout will remedy a disclosed sid.  Of course
          #  this means a logout in one winow of one machine
          #  will affect every other login session.
        sql = "DELETE FROM sessions WHERE id IN"\
              "(SELECT s2.id FROM sessions s1"\
              " JOIN sessions s2 ON s1.userid=s2.userid"\
              " WHERE s1.id=%s)"
        L('lib.jmcgi.dblogout').debug("sql=%s; sid=s1.id=%s" % (sql,sid))
        cur.execute (sql, (sid,))
        cur.connection.commit()

def db_validate_sid (cur, sid):
        # Check that 'sid' is an existing session and if so
        # return a session record.  Otherwise return None.
        sql = "SELECT s.id,s.userid,s.ts,u.fullname,u.email,u.priv" \
              " FROM sessions s JOIN users u ON u.userid=s.userid" \
              " WHERE id=%%s AND NOT u.disabled" \
              "  AND (NOW()-ts)<'%s M'::INTERVAL" \
              % SESSION_TIMEOUT
        rs = jdb.dbread (cur, sql, (sid,))
        L('lib.jmcgi.db_validate_sid').debug("validating sid %s, result=%s" % (sid, len(rs)))
        if len (rs) == 0: return None
        return rs[0]

def db_update_sid_ts (cur, sid):
        # Update the last-used timestamp for 'sid'.
        sql = "UPDATE sessions SET ts=DEFAULT WHERE id=%s"
        L('lib.jmcgi.db_update_sid_ts').debug("sql=%s, id=sid=%s" % (sql,sid))
        cur.execute (sql, (sid,))
        cur.connection.commit()

def db_del_old_sessions (cur):
        # Delete all sessions that are expired, for all users.
        sql = "DELETE FROM sessions WHERE (NOW()-ts)>'%s M'::INTERVAL" \
               % SESSION_TIMEOUT
        L('lib.jmcgi.db_del_old_sessions').debug("sql=%s" % (sql,))
        cur.execute (sql)

def get_sid_from_cookie ():
        sid = ''
        if 'HTTP_COOKIE' in os.environ:
            c = http.cookies.SimpleCookie()
            c.load (os.environ['HTTP_COOKIE'])
            try: sid = c[COOKIE_NAME].value
            except KeyError: pass
        return sid

def set_sid_cookie (sid, delete=False):
        # Set a cookie on the client machine by writing an http
        # Set-Cookie line to stdout.  Caller is responsible for
        # calling this while http headers are being output.

        c = http.cookies.SimpleCookie()
        c[COOKIE_NAME] = sid
          # SESSION_TIMEOUT is in minutes but cookie needs time in seconds.
        c[COOKIE_NAME]['max-age'] = 0 if delete else 60*SESSION_TIMEOUT
          # Python earlier than 3.8 does not recognise the 'samesite' cookie
          # attribute and will throw a CookieError if we try to add it as
          # we added "max-age" above.  So instead, tack the appropriate text
          # onto the end of the cookie header line before outputting it.
        cookie_hdr = c.output() + "; SameSite=Strict"
        L('lib.jmcgi.set_sid_cookie').debug("cookie=%s" % cookie_hdr)
        print (cookie_hdr)

def is_editor (sess):
        """Return a true value if the 'sess' object (which may be None)
        is for a logged-in editor.  An editor is a user with either 'E'
        or 'A' privilege error."""

        if not sess: return None
        return getattr (sess, 'priv', '\uffff') in 'EA'

def get_user (uid, svc, cfg):
        cur = jdb.dbOpenSvc (cfg, svc, session=True, noverchk=True, nokw=True)
        sql = "SELECT * FROM users WHERE userid=%s"
        users = jdb.dbread (cur, sql, (uid,))
          # 'userid' is primary key of users table so we should never
          # receive more than one row.
        assert len(users)<=1, "Too many rows received"
        return users[0] if users else None

def adv_srch_allowed (cfg, sess):
        try: v = (cfg['search']['ENABLE_SQL_SEARCH']).lower()
        except (TypeError, ValueError, KeyError): return False
        if v == 'all': return True
        if v == 'editors' and is_editor (sess): return True
        return False

def form2qs (form):
        """
    Convert a cgi.FieldStorage object back into a query string.
        """
        d = []
        for k in list(form.keys()):
            for v in form.getlist (k):
                d.append ((k, v))
        qs = urllib.parse.urlencode (d)
        return qs

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

def str2seq (q):
        # Convert 'q', a string of the form of either 'seq' or
        # 'seq.corp', where 'seq' is a string of digits representing
        # a seq number, and 'corp' is either a string of digits
        # representing a corpus id number or the name of a corpus.
        # The existence of the  corpus, if given, is validated in
        # the KW.SRC dict.  The seq number is only validated as
        # being greater than 0.
        # If sucessful, a 2-tuple of (seq-number, corpus-id) is
        # returned, where 'corpus-id' will be None if the first
        # input string format was given.  Otherwise a ValueError
        # exception is raised.

        KW = jdb.KW
        seq_part, x, corp_part = q.partition ('.')
        try: seq = int (seq_part)
        except (ValueError, TypeError):
            raise ValueError("Invalid seq number '%s'." % (q,))
        if seq <= 0: raise ValueError("Invalid seq number '%s'." % (q,))
        corp = None
        if corp_part:
            corp = corp2id (corp_part)
            if not corp: raise ValueError("Invalid corpus in '%s'." % (q,))
        return seq, corp

def corp2id (c):
        # Convert 'c' which identifies a corpus and is either
        # the corpus id number in integer or string form or
        # the name of a corpus, to the id number of the corpus.
        # The existence id th corpus is validadedin the KW.SRC
        # dict.

        try: c = int (c)
        except (ValueError, TypeError): pass
        try: corpid = jdb.KW.SRC[c].id
        except KeyError: return None
        return corpid

def str2eid (e):
        n = int (e)
        if n <= 0: raise ValueError(e)
        return n

def safe (s):
        if not s: return ''
        if re.search (r'^[a-zA-Z_][a-zA-Z_0-9]*$', s): return s
        raise ValueError ()

def get_entrs (dbh, elist, qlist, errs, active=None, corpus=None):
        # Retrieve a set of Entr objects from the database, specified
        # by their entry id and/or seq numbers.
        #
        # dbh -- Open dbapi cursor to the current database.
        # elist -- List of id numbers of entries to get.  Each number
        #       may by either a integer or a string.
        # qlist -- List of seq numbers of entries to get.  Each seq
        #       number may be an integer or a string.  If the latter
        #       it may be followed by a period, and a corpus identifier
        #       which is either the corpus id number or the corpus name.
        # errs -- Must be a list (or other append()able object) to
        #       which any error messages will be appended.  The error
        #       messages may contain user data and should thus be
        #       escaped before being used in a web page.
        # active -- If 1, only active/approved or new/(unapproved)
        #       entries will be retrieved.
        #       If 2, at most one entry will be returned for each seq number
        #       in the results and that entry will be the most recently edited
        #       (chronologically based on history records) entry if one exists
        #       of the approved active entry.
        #       If active is any other value or not present, all entries
        #       meeting the entry-id, seq, or seq-corpus criteria will be
        #       retrieved.
        # corpus -- If not none, this is a corpus id number or name
        #       and will apply to any seq numbers without an explicit
        #       corpus given with the number.
        #
        # If the same entry is specified more than once in 'elist' and/or
        # 'qlist' ir will only occur once in the returned object list.
        # Objects in the returned list are in no particular order.

        eargs = []; qargs = []; xargs = []; whr = [];  corpid = None
        if corpus is not None:
            corpid = corp2id (corpus)
            if corpid is None:
                errs.append ("Bad corpus parameter: %s" % corpus)
                return []
        for x in (elist or []):
            try: eargs.append (str2eid (str(x)))
            except ValueError:
                errs.append ("Bad url parameter received: " + x)
        if eargs: whr.append ("id IN (" + ','.join(['%s']*len(eargs)) + ")")

        for x in (qlist or []):
            try: args = list (str2seq (str(x)))
            except ValueError:
                errs.append ("Bad parameter received: " + x)
            else:
                if corpus and not args[1]: args[1] = corpid
                if args[1]:
                    whr.append ("(seq=%s AND src=%s)"); qargs.extend (args)
                else:
                    whr.append ("seq=%s"); qargs.append (args[0])
        if not whr: errs.append ("No valid entry or seq numbers given.")
        if errs: return None
        whr2 = ''; distinct = ''; hjoin = ''; order = ''
        try: active = int (active)
        except (ValueError, TypeError): pass
        if active == 1:
              # Following will restrict returned rows to active/approved
              # (stat=A and not unap) or new (dfrm is NULL), that is, the
              # result set will not include any stat=D or stat=R results.
            whr2 = " AND stat=%s AND (NOT unap OR dfrm IS NULL)"
            xargs.append (jdb.KW.STAT['A'].id)
        elif active == 2:
              # Restrict returned rows to active (no stat=D or stat=R results)
              # and most recent edit as determined by the history records (if any).
              # In no event will more than one entry per seq number be returned.
              # Note that this will necessarily return the edit from only one
              # branch when multiple branches exist which may result in surprise
              # for a user when the returned entry shows no signs of a recent
              # edit known to have been made.
              # Example of generated sql:
              # SELECT DISTINCT ON (e.seq) e.id FROM entr e LEFT JOIN hist h ON h.entr=e.id
              #  WHERE e.seq=2626330 and e.stat=2 ORDER BY e.seq,h.dt DESC NULLS LAST;
            whr2 = " AND e.stat=%s"
            xargs.append (jdb.KW.STAT['A'].id)
            distinct = " DISTINCT ON (e.seq)"
            hjoin = " LEFT JOIN hist h ON h.entr=e.id"
              # "NULLS LAST" is needed below because some entries (e.g., entries
              # imported when JMdictDB is first initialized and never edited)
              # may not have history records which will result in 'dt' values of
              # NULL; we want those entries last.
            order = " ORDER BY e.seq,h.dt DESC NULLS LAST"
        sql = "SELECT" + distinct + " e.id FROM entr e " \
                 + hjoin + " WHERE (" + " OR ".join (whr) + ")" + whr2 + order
        entries, raw = jdb.entrList (dbh, sql, eargs+qargs+xargs, ret_tuple=True)
        if entries:
            jdb.augment_xrefs (dbh, raw['xref'])
            jdb.augment_xrefs (dbh, raw['xrer'], rev=1)
            jdb.add_xsens_lists (raw['xref'])
            jdb.mark_seq_xrefs (dbh, raw['xref'])
        return entries

def jinja_page (tmpl, output=sys.stdout, **kwds):
        httphdrs = kwds.get ('HTTP', None)
        if not httphdrs:
            if not kwds.get ('NoHTTP', None):
                httphdrs = "Content-type: text/html\n"
        if not httphdrs: html = ''
        else: html = httphdrs + "\n"
        env = jinja.init()
        html += jinja.render (tmpl, kwds, env)
        if output: print (html, file=output)
        return html

def err_page (errs=[], errid=None, prolog=None, epilog=None, cssclass=""):
          # CAUTION: 'prolog' and 'epilog' are rendered in the errors
          # page template without html escaping and should either not
          # include any text from untrusted sources or such text must
          # be escaped by the caller.
          # The texts in 'errs' will be escaped in the errors page template;
          # if you need to include html markup in them, wrap the marked up
          # text in jmcgi.Markup().
        if isinstance (errs, str): errs = [errs]
        jinja_page ('error.jinja', svc='', errs=errs, errid=errid,
                     prolog=prolog, epilog=epilog, cssclass=cssclass)
        sys.exit()

def redirect (url):
        print ("Status: 302 Moved")
        print ("Location: %s\n" % url)
        sys.exit()

def htmlprep (entries):
        """\
        Prepare a list of entries for display with an html template
        by adding some additional information that is inconvenient to
        generate from within a template."""

        add_p_flag (entries)
        add_restr_summary (entries)
        add_stag_summary (entries)
        add_audio_flag (entries)
        add_editable_flag (entries)
        add_unreslvd_flag (entries)
        add_pos_flag (entries)
        linkify_hists (entries)
        rev_hists (entries)

def linkify_hists (entries):
        """\
        For every Hist object in each Entr object in the list 'entries',
        replace the .notes (aka comments) and .refs text strings with
        values that have had all substrings that look like urls replaced
        with actual html links."""

        for e in entries:
            for h in e._hist:
                h.notes = linkify (h.notes)
                h.refs = linkify (h.refs)

def add_p_flag (entrs):
        # Add a supplemantary attribute to each entr object in
        # list 'entrs', that has a boolean value indicating if
        # any of its readings or kanji meet wwwjdic's criteria
        # for "P" status (have a freq tag of "ichi1", "gai1",
        # "spec1", or "news1").

        for e in entrs:
            if jdb.is_p (e): e.IS_P = True
            else: e.IS_P = False

def add_restr_summary (entries):

        # This adds an _RESTR attribute to each reading of each entry
        # that has a restr list.  The ._RESTR attribute value is a list
        # of text strings giving the kanji that *are* allowed with the
        # reading.  Recall that the database (and entry object created
        # therefrom) stores the *disallowed* reading/kanji combinations
        # but one generally wants to display the *allowed* combinations.
        #
        # Also add a HAS_RESTR boolean flag to the entry if there are
        # _restr items on any reading.

        for e in entries:
            if not hasattr (e, '_rdng') or not hasattr (e, '_kanj'): continue
            for r in e._rdng:
                if not hasattr (r, '_restr'): continue
                rt = fmt.restrtxts (r._restr, e._kanj, '_restr')
                if rt: r._RESTR = rt
                e.HAS_RESTR = 1

def add_stag_summary (entries):

        # This adds a STAG attribute to each sense that has any
        # stagr or stagk restrictions.  .STAG is set to a single
        # list that contains the kana or kanji texts strings that
        # are allowed for the sense under the restrictions.

        for e in entries:
            for s in getattr (e, '_sens', []):
                rt = []
                if getattr (s, '_stagr', None):
                    rt.extend (fmt.restrtxts (s._stagr, e._rdng, '_stagr'))
                if getattr (s, '_stagk', None):
                    rt.extend (fmt.restrtxts (s._stagk, e._kanj, '_stagk'))
                if rt:
                    s._STAG = rt

def add_audio_flag (entries):

        # The display template shows audio records at the entry level
        # rather than the reading level, so we set a HAS_AUDIO flag on
        # entries that have audio records so that the template need not
        # sear4ch all readings when deciding if it should show the audio
        # block.
        # [Since the display template processes readings prior to displaying
        # audio records, perhaps the template should set its own global
        # variable when interating the readings, and use that when showing
        # an audio block.  That would eliminate the need for this function.]

        for e in entries:
            if getattr (e, '_snd', None):
                e.HAS_AUDIO = 1;  continue
            for r in getattr (e, '_rdng', []):
                if getattr (r, '_snd', None):
                    e.HAS_AUDIO = 1
                    break

def add_editable_flag (entries):

        # This is a convenience function to avoid embedding this logic
        # in the page templates.  This sets a boolean EDITABLE flag on
        # each entry that says whether or not an "Edit" button should
        # be shown for the entry.  All unapproved entries, and approved
        # active or deleted entries are editable.  Rejected entries aren't.

        KW = jdb.KW
        for e in entries:
            e.EDITABLE = e.unap or (e.stat == KW.STAT['A'].id)\
                                or (e.stat == KW.STAT['D'].id)

def add_unreslvd_flag (entries):

        # This is a convenience function to avoid embedding this logic
        # in the page templates.  This sets a boolean UNRESLVD flag on
        # each entry that says whether or not it has any senses that
        # have unresolved xrefs in its '_xunr' list.

        KW = jdb.KW
        for e in entries:
            e.UNRESLVD = False
            for s in e._sens:
                if len (getattr (s, '_xunr', [])) > 0:
                    e.UNRESLVD = True

def add_pos_flag (entries):

        # This is a convenience function to avoid embedding this logic
        # in the page templates.  This sets a boolean POS flag on
        # each entry if any senses in the entry have a part-of-speech
        # (pos) tag that is conjugatable.  A POS tag is conjugatable
        # if its id number is an id number in jdb.KW.COPOS.  jdb.KW.COPOS
        # in turn is populated from database view 'vcopos' which are those
        # rows in kwpos which are also referenced in table 'copos' (that
        # identifies them as conjugatable.)  See also the comments for
        # view 'vcopos' in pg/conj.sql.
        # The .POS attribute set by this function is used to determine
        # if a "Conjugations" link should be shown for the entry.
        # We exclude nouns and na-adjectives even though the conjugator
        # will happily conjugate them as だ-predicates.

        KW = jdb.KW
        conjugatable_poslist = [x.id for x in jdb.KW.recs('COPOS')
                                if x.kw not in ('n', 'adj-na')]
        for e in entries:
            e.POS = False
            for s in e._sens:
                for p in s._pos:
                    if p.kw in conjugatable_poslist:
                        e.POS = True;  break

def rev_hists (entries):

        # Reverse the order of history items in each entry so that the
        # most recent will appear first and the oldest last.

        for e in entries:
            if e._hist: e._hist = list (reversed (e._hist))

def add_filtered_xrefs_old (entries, rem_unap=False):

        # Generate substitute _xref and _xrer lists and put them in
        # sense attribute .XREF and .XRER.  These lists are copies of
        # ._xref and ._xrer but references to deleted or rejected
        # entries are removed.  Additionally, if 'rem_unap' is true,
        # references to unapproved entries are also removed *if*
        # the current entry is approved.
        # The xrefs in ._xref and ._xrer must be augmented xrefs (i.e.
        # have had jdb.augment_xrefs() called on the them.)
        #
        # FIXME: have considered not displaying reverse xref if an
        #  identical forward xref (to same entr/sens) exists.  If
        #  we want to do that, this is the place.

        cond = lambda e,x: (e.unap or not x.TARG.unap or not rem_unap) \
                            and x.TARG.stat==jdb.KW.STAT['A'].id
        for e in entries:
            for s in e._sens:
                s.XREF = [x for x in s._xref if cond (e, x)]
                s.XRER = [x for x in s._xrer if cond (e, x)]

def add_filtered_xrefs (entries, rem_unap=False):

        # Works like add_filtered_xrefs_old() above except:
        # Put all xrefs, both forward (from list s._xref) and reverse
        # from list s._xrer), into s.XREF and creates an additional
        # attribute on the s.XREF objects, .direc, that indicates whether
        # the xref is a "from", "to" or "bidirectional" xref.  If the
        # same xref occurs in both the s._xref and s_xrer lists, it is
        # only added once and the .direc attribute set to "bidirectional".
        # This allows an entr display app (such as entr.py/entr.jinja) to
        # display an icon for the xref direction.  This was suggested
        # on the Edict maillist by Jean-Luc Leger, 2010-07-29, Subject:
        # "Re: Database testing - call for testers - more comments"

        cond = lambda e,x: (e.unap or not x.TARG.unap or not rem_unap) \
                            and x.TARG.stat==jdb.KW.STAT['A'].id
        def setdir (x, dir):
            x.direc = dir
            return x

        FWD = 1;  BIDIR = 0;  REV = -1  # Direction of an xref.
        for e in entries:
            for s in e._sens:
                  # Add all (non-excluded) forward xrefs to the xref list,
                  # s.XREF.  Some of these may be bi-directional (have
                  # xrefs on the target that refer back to us) but we will
                  # indentify those later to fixup the FWD flag to BIDIR.
                s.XREF = [setdir (copy.deepcopy(x), FWD) for x in s._xref if cond (e, x)]
                  # Make dict of all the fwd xrefs.
                fwdrefs = {(x.entr,x.sens,x.xentr,x.xsens):x for x in s.XREF}
                for x in s._xrer:
                    if not cond (e, x): continue
                    x = copy.deepcopy (x)
                      # Because we will display the reverse xref with the
                      # same code that displays forward xrefs (that is, it
                      # creates a link to the entry using x.xentr and x.xsens),
                      # swap the (entr,sens) and (xentr,xsens) values so that
                      # when (xentr,xsens) are used, they'll actually be
                      # the entr,sens values which identify the entry the
                      # the reverse xref is on, which is what we want.
                    x.entr,x.sens,x.xentr,x.xsens = x.xentr,x.xsens,x.entr,x.sens
                      # Is this reverse xref the same as a forward xref?
                    if (x.entr,x.sens,x.xentr,x.xsens) in fwdrefs:
                          # If so, change the forward xref's 'direc' attribute
                          # from FWD to BIDIR.
                        setdir (fwdrefs[(x.entr,x.sens,x.xentr,x.xsens)], BIDIR)
                      # Otherwise (our xref is not bi-directional), add us to
                      # the xref list as a reverse xref.
                    else: s.XREF.append (setdir (x, REV))

def add_encodings (entries, gahoh_url=None):

        # Add encoding info which is displayed when presenting kanjidic
        # (or similar single-character) entries.

        for e in entries:
            if not hasattr (e, 'chr') or not e.chr: continue
            c = e.chr; c.enc = {}
            c.enc['uni'] = hex (ord (c.chr)).upper()[2:]
            c.enc['unid'] = ord (c.chr)
            c.enc['uurl'] = 'http://www.unicode.org/cgi-bin/GetUnihanData.pl?codepoint=' + c.enc['uni']
            c.enc['utf8'] = ' '.join(["%0.2X"%x for x in c.chr.encode('utf-8')])
            try:
                iso2022jp = c.chr.encode ('iso2022-jp')
                c.enc['iso2022jp'] = ' '.join(["%0.2X"%x for x in iso2022jp])
                c.enc['jis'] = ''.join(["%0.2X"%x for x in iso2022jp[3:5]])
            except UnicodeEncodeError: c.enc['iso2022jp'] = c.enc['jis'] = '\u3000'
            try: c.enc['sjis'] = ''.join(["%0.2X"%x for x in c.chr.encode('sjis')])
            except UnicodeEncodeError: c.enc['sjis'] = '\u3000'
            try: c.enc['eucjp'] = ''.join(["%0.2X"%x for x in c.chr.encode('euc-jp')])
            except UnicodeEncodeError: c.enc['eucjp'] = '\u3000 '

class SearchItems (jdb.Obj):
    """Convenience class for creating objects for use as an argument
    to function so2conds() that prevents using invalid attribute
    names."""

    def __setattr__ (self, name, val):
        if name not in ('idtyp','idnum','src','txts','pos','misc',
                        'fld','dial','freq','kinf','rinf','grp','stat','unap',
                        'nfval','nfcmp','snote', 'ts','smtr',
                        'cmts', 'refs', 'mt',):
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
          dial -- List of Dialect keywords.
          kinf -- List of Kanj Info keywords.
          rinf -- List of Reading Info of Speech keywords.
          grp -- List of entry group keywords.
          stat -- List of Status keywords.
          unap -- List of Unapproved keywords.  #FIXME
          freq -- List of Frequency keywords.  #FIXME
                Note that an entry matches if there is either a
                matching kanj freq or a matching rdng freq.  There
                is no provision to specify just one or the other.
          snote -- 2-tuple of pattern to match with sens.notes, and
                bool indicating a regex (vs substring) match is desired.
          ts -- History min and max time limits as a 2-tuple.  Each
                time value is either None or number of seconds from
                the epoch as returned by time.localtime() et.al.
          smtr -- 2-tuple of name to match with hist.name, and bool
                indicating a wildcard (vs exact) match is desired.
          cmts -- 2-tuple of pattern to match with hist.notes (labeled
                "commments" in gui), and bool indicating a regex (vs
                substring) match is desired.
          refs -- 2-tuple of pattern to match with hist.refs, and bool
                indicating a regex (vs substring) match is desired.
          mt -- History record match type as an int:
                  0: match any hist record
                  1: match only first hist record
                 -1: match only last hist record

        Since it is easy to mistype attribute names, the classes
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
        conds.extend (_kwcond (o, 'dial', "dial",   "dial.kw"))
        conds.extend (_kwcond (o, 'kinf', "kinf",   "kinf.kw"))
        conds.extend (_kwcond (o, 'rinf', "rinf",   "rinf.kw"))
        conds.extend (_kwcond (o, 'grp',  "grp",    "grp.kw"))
        conds.extend (_kwcond (o, 'src',  "entr e", "e.src"))
        conds.extend (_kwcond (o, 'stat', "entr e", "e.stat"))
        conds.extend (_boolcond (o, 'unap',"entr e","e.unap", 'unappr'))
        conds.extend (_freqcond (getattr (o, 'freq', []),
                                 getattr (o, 'nfval', None),
                                 getattr (o, 'nfcmp', None)))
        conds.extend (_snotecond (getattr (o, 'snote', None)))
        conds.extend (_histcond (getattr (o, 'ts',    None),
                                 getattr (o, 'smtr',  None),
                                 getattr (o, 'cmts',  None),
                                 getattr (o, 'refs',  None),
                                 getattr (o, 'mt',    None)))
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

def _snotecond (snote):
        pat, ptype = snote
        if not pat: return []
        if ptype: cond = 'sens', "sens.notes ~* %s", [pat]
        else: cond = 'sens', "sens.notes ILIKE %s", [like_substr (pat)]
        return [cond]

def _histcond (ts, smtr, cmts, refs, mt):
        conds = []
        if ts and (ts[0] or ts[1]):
              # ts[0] and[1] are 9-tuples of ints that correspond
              # to time.struct_time objects.  We convert them to
              # datetime.datetime objects.
            if ts[0]: conds.append (('hist', "dt>=%s", [datetime.datetime.fromtimestamp(int(ts[0]))]))
            if ts[1]: conds.append (('hist', "dt<=%s", [datetime.datetime.fromtimestamp(int(ts[1]))]))
        if smtr and smtr[0]:
            name, wc = smtr
            if not wc: conds.append (('hist', "lower(name)=lower(%s)", [name]))
            else: conds.append (('hist', "name ILIKE %s", [wc2like (name)]))
        if cmts and cmts[0]:
            pat, wc = cmts
            if wc: conds.append (('hist', "hist.notes ~* %s", [pat]))
            else: conds.append (('hist', "hist.notes ILIKE %s", [like_substr (pat)]))
        if refs and refs[0]:
            pat, wc = refs
            if wc: conds.append (('hist', "refs ~* %s", [pat]))
            else: conds.append (('hist', "refs ILIKE %s", [like_substr (pat)]))
        if mt:
            if int(mt) ==  1: conds.append (('hist', "hist=1", []))
            if int(mt) == -1: conds.append (('hist', "hist=(SELECT COUNT(*) FROM hist WHERE hist.entr=e.id)", []))
        return conds

def _freqcond (freq, nfval, nfcmp):
        # Create a pair of 3-tuples (build_search_sql() "conditions")
        # that build_search_sql() will use to create a sql statement
        # that will incorporate the freq-of-use criteria defined by
        # our parameters:
        #
        # $freq -- List of indexes from a freq option checkbox, e.g. "ichi2".
        # $nfval -- String containing an "nf" number ("1" - "48").
        # $nfcmp -- String containing one of ">=", "=", "<=".
        #
        # Freq items consist of a scale (such as "ichi" or "nf")
        # and a value (such as "1" or "35").
        # Process the checkboxes by creating a hash indexed by
        # by scale and with each value a list of freq values.

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
              # Split into text (scale) and numeric (value) parts.
            match = re.search (r'^([A-Za-z_-]+)(\d*)$', f)
            scale, value = match.group(1,2)
            if scale == 'nf': have_nf = True
            else:
                  # Append this value to the scale list.
                x.setdefault (scale, []).append (int(value))

        # Now process each scale and it's list of values...

        whr = []
        for k,v in list(x.items()):
              # Convert the scale string to a kwfreq table id number.
            kwid = KW.FREQ[k].id

              # The following assumes that the range of values are
              # limited to 1 and 2.

              # As an optimization, if there are 2 values, they must be 1 and 2,
              # so no need to check value in query, just see if the scale exists.
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
        if nfcmp:
            kwid = KW.FREQ['nf'].id
              # Build list of "where" clause parts using the requested
              # comparison and value.  Validate 'nfcmp' and 'nfval' to
              # avoid SQL injection.
            try: nfcmp = {'=':'=', '≤':'<=', '≥':'>='}[nfcmp]
            except KeyError:
                raise ValueError ('Invalid value for "nfcmp": %r' % nfcmp)
            try: nfval = int (nfval or 0)
            except ValueError:
                raise ValueError ('Invalid value for "nfval": %r' % nfval)
            whr.append (
                "(freq.kw=%s AND freq.value%s%s)" % (kwid, nfcmp, nfval))

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

def utt (d):
        # Convert a simple string-to-string mapping into
        # the form required by <unicode>.translate().
        return dict ((ord(k), str(v)) for k,v in list(d.items()))

Wc_trans = utt({'*':'%', '?':'_', '%':'\\%', '_':'\\_'})
def wc2like (s):
        # Convert a string with wildcard characters '*' and '?' to SQL
        # "like" operator characters, "%" and "_", being careful of
        # escape "\" characters.
        s1 = str (s)
        s1 = s1.replace ('\\*', '\x01')
        s1 = s1.replace ('\\?', '\x02')
        s1 = s1.translate (Wc_trans)
        s1 = s1.replace ('\x01', '*')
        s1 = s1.replace ('\x02', '?')
        return s1

def like_substr (s):
        # Given string 's', return a new string 't' that can be used as
        # a pattern with the postgresql ILIKE operator for matching 's'
        # as a substring.  This is done by escaping any special characters
        # in 's' ("?", "_", "%") and pre- and post-fixing the string with
        # '%' characters.
        t = '%' + re.sub (r'([?_%])', r'\\\1', s) + '%'
        return t

def linkify (s, newpage=True):
        """Convert all text substrings in 's' that look like http,
        https or ftp url's into html <a href=...> links.  Since the
        return value will be further processed by the Jinja2 template
        engine which normally html-escapes text prior to output, we
        manually html-escape the non-url parts of 's' here and return
        the results as a markupsafe string that Jinja2 will not escape
        again.  For markupsafe doc see:
          https://markupsafe.palletsprojects.com/.
        If 'newpage' is True, the generated links will open the link
        in a new browser page/tab rather than the same page."""

        if not s: return s
          # The following regex used to identify urls and is based on:
          #    https://www.regextester.com/96504
          # modified to require a url scheme prefix (e.g. "http://") 
        urlpat = r'''(?:https?|ftp):\/\/(?:(?:[^\s()<>]+|\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))?\))+(?:\((?:[^\s()<>]+|(?:\(?:[^\s()<>]+\)))?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))?'''
          # Markup is the markupsafe.Markup() function, Escape is the
          # markupsafe.escape() function.  The former returns a str
          # subtype that will not be subject to the html-escaping that
          # jinja2 does on normal strings.  That latter returns a
          # different str subtype that is html-escaped and will not
          # be escaped again by jinja2.
        t = Markup('');  prev_end = 0;  end = len(s)
          # Iterate through the urls in 's'.  Each 'mo' is a "re"
          # module match object for one url.
        for mo in re.finditer (urlpat, s):
            start, end = mo.start(), mo.end()
              # The url text in 's' is at s[start:end].  'prev_end' is
              # the ending index of the url found before this one.
              # If there is any non-url text in front of the url,
              # escape it and append it to the results, 't'.
            if start > prev_end: t += Escape (s[prev_end:start])
              # Convert the url text into an html link.
            url = mo.group(0)
            targ = ' target="_blank"' if newpage else ''
              #FIXME? we url-decode the displayed link text since the encoded
              # form with many %xx values is often unreadable.  But this may be
              # confusing since it may lead one to look in the database for
              # for the decoded value when it is actually the encoded value
              # that is stored.
            link = '<a href="%s"%s>%s</a>' \
                   % (url, targ, urllib.parse.unquote(url))
              # Wrap the link with Markup() so that it won't be escaped
              # by jinja2 later.
            t += Markup (link)
              # Update 'prev_end' for next iteration.
            prev_end = end
          # Look for any non-url text after the last url, escape it,
          # and append to results, 't'.
        if prev_end < len(s):
            t +=  Escape (s[prev_end:len(s)])
        return t

def parse_cfg_logfilters (s):
        result = []
        for ln in s.splitlines():
            ln = ln.strip ()
            if not ln: continue
            result.append (ln)
        return result
