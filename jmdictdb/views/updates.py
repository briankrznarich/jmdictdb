# Copyright (c) 2010 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# Display entries that were added or updated on a given date (that
# is, have a history entry with that date) or alternately, an index
# page that shows date links to pages for the entries updated on that
# date.
#
# URL parameters:
#   i -- Display an index page listing dates for which there
#        are undates.  Each date is a link which when clicked
#        will display the actual updates made on that date.
#        Only one year of dates is shown; the year is specified
#        with the 'y' parameter.  If 'i' is not present, a page
#        showing the actual entries updated on the date given
#        by 'y', 'm', 'd' will be shown with the entr.tal template.
#   y, m, d -- The year, month (1-12) and day (1-31) giving a
#        date.  If 'i' was not given, the updates made on this
#        date will be shown.  If 'i' was given, 'm' and 'd' are
#        ignored and an index page for the year 'y' is shown.
#        If any of 'y', 'm' or 'd' are missing, its value will
#        be taken from the current date.
#   n -- A integer greater than 0 that is a number of days that
#        will be subtracted from the date given with the other
#        parameters.  This is primarily used with the value 1
#        to get "yesterday's" updates but will work consistently
#        with other values.
#   [other] -- The standard jmdictdb cgi parameters like 'svc',
#        'sid', etc.  See python/lib/jmcgi.py.

import sys, datetime, pdb
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, jmcgi

  # History entries ending with the following text will be excluded
  # as indicators of an updated entry.  This text should match the
  # corresponding value in python/bulkupd.py.
BULKUPD_KEY = '-*- via bulkupd.py -*-'

def view (svc, cfg, user, cur, parms):
        fv = parms.get; fl = parms.getlist
        t = datetime.date.today()  # Will supply default value of y, m, d.
          # y, m, and d below are used to construct sql string and *must*
          # be forced to int()'s to eliminate possibiliy of sql injection.
        try: y = int (fv ('y') or t.year)
        except Exception as e:
            return {}, ["Bad 'y' url parameter."]

        show_index = bool (fv ('i'))
        if show_index:
            data, errs = get_year_index (svc, cur, y)
        else:
            try:
                m = int (fv ('m') or t.month)
                d = int (fv ('d') or t.day)
                n = int (fv ('n') or 0)
            except Exception as e:
                return {}, ["Bad 'm', 'd' or 'n' url parameter."]
            data, errs = get_day_updates (svc, cur, y, m, d, n, parms)
        return data, errs

def get_day_updates (svc, cur, y, m, d, n, parms):
        # If we have a specific date, we will show the actual entries that
        # were modified on that date.  We do this by retrieving Entr's for
        # any entries that have a 'hist' row with a 'dt' date on that day.
        # The Entr's are displayed using the standard entr.tal template
        # that is also used for displaying other "list of entries" results
        # (such as from the Search Results page).

        sql = '''SELECT DISTINCT e.id
                 FROM entr e
                 JOIN hist h on h.entr=e.id
                 WHERE h.dt BETWEEN %%s::timestamp
                            AND %%s::timestamp + interval '1 day'
                       AND h.notes not like '%%%%%s' ''' % BULKUPD_KEY
          # Note on "%" characters above: the sql will be passed to the
          # psycopg2 database driver which (unwisely) chose to use "%s"
          # as its parameter marker string and requires literal "%" to
          # be doubled.  The two "%%s"s above, after python's string
          # interpolation, become "%s" which is what we want psycopg2
          # to receive.  The "%%%%%s" becomes "%%xxx" (where the last
          # "%s" is replaced by BULKUPD_KEY (abbreviated xxx) and the
          # "%%%%" becomes "%%" by python's string interpolation.  In
          # psyscopg2 the "%%" becomes "%" which is the "wildcard" match
          # character for the "like" operator -- what we want.

        day = datetime.date (y, m, d)
        if n:
              # 'n' is used to adjust the given date backwards by 'n' days.
              # Most frequently it is used with a value of 1 in conjuction
              # with "today's" date to get entries updated "yesterday" but
              # for consistency we make it work for any date and any value
              # of 'n'.
            day = day - datetime.timedelta (n)
            y, m, d = day.year, day.month, day.day

        entries = jdb.entrList (cur, sql, (day, day),
                                'x.src,x.seq,x.id')

          # Prepare the entries for display... Augment the xrefs (so that
          # the xref seq# and kanji/reading texts can be shown rather than
          # just an entry id number.  Do same for sounds.
        for e in entries:
            for s in e._sens:
                if hasattr (s, '_xref'): jdb.augment_xrefs (cur, s._xref)
                if hasattr (s, '_xrer'): jdb.augment_xrefs (cur, s._xrer, 1)
            if hasattr (e, '_snd'): jdb.augment_snds (cur, e._snd)
        cur.close()
        jmcgi.htmlprep (entries)
        jmcgi.add_filtered_xrefs (entries, rem_unap=True)

        return dict (page='entr',
            entries=zip(entries, [None]*len(entries)), disp=None), []

def get_year_index (svc, cur, y):
        # If 'i' was given in the URL params we will generate an index
        # page showing dates, with each date being a link back to this
        # script with the result that clicking it will show the updates
        # (viw render_day_update() above) for that date.  The range of
        # the dates are limited to one year.
        # Also on the page we generate links for each year for which
        # there are updates in the database.  Those links also points
        # back to this script but with 'i' and a year, so that when
        # clicked, they will generate a daily index for that year.

          # Get a list of dates (in the form: year, month, day, count)
          # for year = 'y' for with there are hist records.  'count' is
          # the number of number of hist records with the corresponding
          # date.
        start_of_year = '%d-01-01' % y
        end_of_year = '%d-01-01' % (y + 1)
        sql = '''SELECT EXTRACT(YEAR FROM dt)::INT AS y,
                     EXTRACT(MONTH FROM dt)::INT AS m,
                     EXTRACT(DAY FROM dt)::INT AS d,
                     COUNT(*)
                 FROM hist h
                 WHERE dt >= '%s'::DATE AND dt < '%s'::DATE
                 GROUP BY EXTRACT(YEAR FROM dt)::INT,EXTRACT(MONTH FROM dt)::INT,EXTRACT(DAY FROM dt)::INT
                 ORDER BY EXTRACT(YEAR FROM dt)::INT,EXTRACT(MONTH FROM dt)::INT,EXTRACT(DAY FROM dt)::INT
                 ''' % (start_of_year, end_of_year)
        cur.execute (sql, (y,y))
        days = cur.fetchall()

          # Get a list of years (in the form: year, count) for which there
          # are history records.  'count' is the total number in the year.

        sql = '''SELECT EXTRACT(YEAR FROM dt)::INT AS y, COUNT(*)
                 FROM hist h
                 GROUP BY EXTRACT(YEAR FROM dt)::INT
                 ORDER BY EXTRACT(YEAR FROM dt)::INT DESC;'''
        cur.execute (sql, ())
        years = cur.fetchall()
        return dict (page='updates',
            years=years, year=y, days=days, disp=None), []
