#######################################################################
#  This file is part of JMdictDB.
#  Copyright (c) 2014 Stuart McGraw
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
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#######################################################################

import datetime, re
from jmdictdb import jdb
from jmdictdb.db import QueryCanceledError

class TimeoutError (RuntimeError): pass

class SearchItems (jdb.Obj):
    """Convenience class for creating objects for use as an argument
    to function so2conds() that prevents using invalid attribute
    names."""

    def __setattr__ (self, name, val):
        if name not in ('idtyp','idnum','src','txts','pos','misc',
                        'fld','dial','freq','kinf','rinf','grp','stat','unap',
                        'nfval','nfcmp','gaval','gacmp','snote', 'ts','smtr',
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
                                 getattr (o, 'nfcmp', None),
                                 getattr (o, 'gaval', None),
                                 getattr (o, 'gacmp', None)))
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

def _freqcond (freq, nfval, nfcmp, gaval, gacmp):
        # Create a pair of 3-tuples (build_search_sql() "conditions")
        # that build_search_sql() will use to create a sql statement
        # that will incorporate the freq-of-use criteria defined by
        # our parameters:
        #
        # $freq -- List of indexes from a freq option checkboxe, e.g. "ichi2".
        # $nfval -- String containing an "nf" number ("1" - "48").
        # $nfcmp -- String containing one of ">=", "=", "<=".
        #   NOTE: The gA freq number was a from a database of Google
        #     "hits" for various words.  The data was unreliable at the
        #     time it was collected in the early 2000's and is of little
        #     use anymore.  The search forms no longer support gA as a
        #     search criterion but the code is left in here for reference.
        # gaval -- String containing a gA number.
        # gacmp -- Same as nfcmp.

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
            elif scale == 'gA': have_gA = True
            else:
                  # Append this value to the scale list.
                x.setdefault (scale, []).append (value)

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

        if nfval:
            kwid = KW.FREQ['nf'].id
            # Build list of "where" clause parts using the requested comparison and value.
            if nfcmp == '≤': nfcmp = '<='
            elif nfcmp == '≥': nfcmp = '>='
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

def run_search (cur, sql, sql_args, timeout,
                pgtotal, pgoffset=0, entrs_per_page=100):
        import time
        stats = {}
        orderby = "ORDER BY __wrap__.kanj,__wrap__.rdng,__wrap__.seq,__wrap__.id"
        page = "OFFSET %s LIMIT %s" % (pgoffset, entrs_per_page)
        sql2 = "SELECT __wrap__.* FROM esum __wrap__ " \
                 "JOIN (%s) AS __user__ ON __user__.id=__wrap__.id %s %s" \
                  % (sql, orderby, page)
        stats['sql']=sql; stats['args']=sql_args; stats['orderby']=orderby
        t0 = time.time()
        try: rs = jdb.dbread (cur, sql2, sql_args, timeout=timeout)
        except QueryCanceledError as e:
            msg = "The database query took too long to execute.  Please "\
                "make your search more specific."
            raise TimeoutError (msg)
          # Let any other database error bubble up.
        #except Exception as e:          #FIXME, what exception value(s)?
        #    raise ValueError ("Database error (%s): %s" % (e.__class__.__name__, e))
        stats['dbtime'] = time.time() - t0
        reccnt = len(rs)
        if pgtotal < 0:
          # 'pgtotal'<0 says that we do not yet know the total number of
          # results available (probably because this is the first call
          # with the current
          # search parameters.)
            if reccnt >= entrs_per_page:
              # If reccnt==entrs_per_page (it shouldn't really ever be
              # greater because it was used in a LIMIT condition in query
              # above), there may be more entries available.  We will
              # run the query below to find the total number of matching
              # results and return it.  The caller can then, on subsequent
              # calls, give it back to us and we won't determine it again.
              # This is a performance optimization since it can be an
              # expensive query to run when there are a large number of
              # matches.  If is possible the number will change between
              # calls but that will that should not cause any major problem
              # since database changes are infrequent.
                sql3 = "SELECT COUNT(*) AS cnt FROM (%s) AS i " % sql
                cntrec = jdb.dbread (cur, sql3, sql_args, timeout=timeout)
                pgtotal = cntrec[0][0]  # Total number of entries.
            else:
              # The number of results are less than the number we asked for
              # so we know we know we have all of them.
                pgtotal = reccnt
        return rs, pgtotal, stats

def reshape (array, ncols, default=None):
        result = []
        for i in range(0, len(array), ncols):
            result.append (array[i:i+ncols])
        if len(result[-1]) < ncols:
            result[-1].extend ([default]*(ncols - len(result[-1])))
        return result

def grpsparse (grpsstr):
        if not grpsstr: return []
        return grpsstr.split()

def dateparse (dstr, upper, errs):
        if not dstr: return None
        dstr = dstr.strip();  dt = None
        if not dstr: return None
          # Add a time if it wasn't given.
        if len(dstr) < 11: dstr += " 23:59" if upper else " 00:00"
          # Note: we use time.strptime() to parse because it returns
          # struct easily converted into a 9-tuple, which in turn is
          # easily JSONized, unlike a datetime.datetime object.
        try: dt = time.strptime (dstr, "%Y/%m/%d %H:%M")
        except ValueError:
            try: dt = time.strptime (dstr, "%Y-%m-%d %H:%M")
            except ValueError:
                errs.append ("Unable to parse date/time string '%s'." % dstr)
        if dt: return time.mktime (dt)
        return None
