# Copyright (c) 2006-2012 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, pdb
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, srch

def view (svc, cfg, user, cur, params):
        '''-------------------------------------------------------------------
        Run a database search for entries using the search parameters
        in 'params'.

        Parameters (standard set for view function calls):
        svc -- Database service name (not used).
        cfg -- Configuration settings.
        user -- Currently logged in user or None for anonymouse user.
        params -- A dict or similar (eg Flask Request object) containing
          search parameters.

        Parameters in 'params':
        so -- A srch.SearchItems object as return by extract_srch_params().
        sqlp -- A sql statement returning a set of entry id numbers.
        pt -- Total number of search results or -1 if not yet known.
        p0 -- Offset in search results of first entry to show on page.
        ps -- Page size: number of entries per page.  If not present
          this will be obtained from the configuration settings.
        Additional ones per code in extract_srch_params().
        -------------------------------------------------------------------'''

        errs = []
        p0 = params.get('p0', 0, int)   # Starting entry # on page.
        pt = params.get('pt', -1, int)  # Total # of found entries.
        ps = params.get('ps', 0, int)   # Page size (max # of entries/page).
        sqlp = params.get ('sql', '')
        so = extract_srch_params (params)
        if not sqlp: # Search parameters have been parsed and supplied
                # in 'so'.  This is a normal search from a search page.

            try: condlist = srch.so2conds (so)
            except ValueError as e:
                return None, [str(e)]
            if not condlist: return None, ["No search criteria given"]
              # FIXME: [IS-115] Following will prevent kanjidic entries from
              #  appearing in results.  Obviously hardwiring id=4 is a hack.
            #condlist.append (('entr e', 'e.src!=4', []))
            sql, sql_args = jdb.build_search_sql (condlist)
        else: # A search using raw sql is requested.
              # 'sqlp' is a SQL statement string that allows an arbitrary
              # search.  Because arbitrary sql can also do other things
              # such as delete the database, it is permitted only by
              # logged-in editors and executed in the database by a
              # read-only user.
            if not jmcgi.adv_srch_allowed (cfg, user):
                return [],['"sql" search allowed only by logged in editors']
            sql = sqlp.strip()
            if sql.endswith (';'): sql = sql[:-1]
            sql_args = []

        srch_timeout = cfg.get ('search', 'SEARCH_TIMEOUT')
        try: rs, pt, stats \
                = srch.run_search (cur, sql, sql_args, srch_timeout,
                                   pt, p0, entrs_per_page (cfg, ps))
        except srch.TimeoutError as e: return {}, [str(e)]
        return dict(results=rs, p0=p0, pt=pt, stats=stats, params=params), []

def extract_srch_params (params):
        '''-------------------------------------------------------------------
        Extract search related url parameters from the request parameters

        returns: A srch.SearchItems item initiailized from 'params'
            that can be used to generate sql for performing the search.
        --------------------------------------------------------------------'''

        def fv(k): return params.get(k)
        def fl(k): return params.getlist(k)
        def fvi(k): return params.get(k,type=int)

        errs = []
        so = srch.SearchItems()
        so.idnum=fv('idval');  so.idtyp=fv('idtyp')
        tl = []
        for i in (1,2,3):
            txt = (fv('t'+str(i)) or '')
            if txt: tl.append (srch.SearchItemsTexts (
                                 srchtxt = txt,
                                 srchin  = fv('s'+str(i)),
                                 srchtyp = fv('y'+str(i)) ))
        if tl: so.txts = tl
        so.pos   = fl('pos');   so.misc  = fl('misc');
        so.fld   = fl('fld');   so.dial  = fl('dial');
        so.rinf  = fl('rinf');  so.kinf  = fl('kinf');  so.freq = fl('freq')
        so.grp   = srch.grpsparse (fv('grp'))
        so.src   = fl('src');   so.stat  = fl('stat');  so.unap = fl('appr')
        so.nfval = fv('nfval'); so.nfcmp = fv('nfcmp')
          # Search using gA freq criterion no longer supported.  See
          # the comments in srch._freqcond() but code left here for
          # reference.
        so.gaval = fv('gaval'); so.gacmp = fv('gacmp')
          # Sense notes criteria.
        so.snote = (fv('snote') or ''), fvi('snotem')
          # Next 5 items are History criteria...
          #FIXME? use selection boxes for dates?  Or a JS calendar control?
        so.ts = srch.dateparse (fv('ts0'), 0, errs),\
                srch.dateparse (fv('ts1'), 1, errs)
        so.smtr = (fv('smtr') or ''), fvi('smtrm')
        so.cmts = (fv('cmts') or ''), fvi('cmtsm')
        so.refs = (fv('refs') or ''), fvi('refsm')
        so.mt = fv('mt')
        return so

def entrs_per_page (cfg, ps=0):
        if not ps: ps = 0   # In case we receive ps=None.
        epp = min (max (int (ps or cfg.get('web','DEF_ENTRIES_PER_PAGE')),
                        int(cfg.get('web','MIN_ENTRIES_PER_PAGE'))),
                   int(cfg.get('web','MAX_ENTRIES_PER_PAGE')))
        return epp
