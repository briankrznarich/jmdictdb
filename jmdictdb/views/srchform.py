# Copyright (c) 2006-2012 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, pdb
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb
from jmdictdb.srvlib import reshape

def view (svc, cfg, user, cur, params):
          # reshapes()'s last argument is the maximum number of checkboxes
          # to put on a line, and is ajusted empirically to make the total
          # widths for all the sections approximately equal.
        pos =  reshape (sorted (jdb.KW.recs('POS'),  key=lambda x:x.kw.lower()), 10)
        misc = reshape (sorted (jdb.KW.recs('MISC'), key=lambda x:x.kw.lower()), 8)
        stat = reshape (sorted (jdb.KW.recs('STAT'), key=lambda x:x.kw.lower()), 10)
        fld =  reshape (sorted (jdb.KW.recs('FLD'),  key=lambda x:x.kw.lower()), 10)
        dial = reshape (sorted (jdb.KW.recs('DIAL'), key=lambda x:x.kw.lower()), 12)
        kinf = reshape (sorted (jdb.KW.recs('KINF'), key=lambda x:x.kw.lower()), 5)
          # FIXME: restricting 'rinf' kwds to values less that 100 causes
          #  the searchj form not to show the the kanjidic-related ones.
          #  This is really too hackish.  See IS-190 for fix.
        rinf = reshape (sorted ([x for x in jdb.KW.recs('RINF') if x.id < 100],
                                                     key=lambda x:x.kw.lower()), 5)
          # FIXME: Filter out the kanjidic corpus for now.  Will figure
          #  out how to integrate it later.  This too is pre- IS-190 hack.
        src = reshape (sorted ([x for x in jdb.KW.recs('SRC') if x.kw!='xxkanjidic'],
                                key=lambda x:x.kw.lower()), 10)
        class Kwfreq (object):
            def __init__ (self, kw, descr):
                self.kw, self.descr = kw, descr
        freq = []
        for x in sorted (jdb.KW.recs('FREQ'), key=lambda x:x.kw.lower()):
             # Build list of Kwfreq keywords for populating the webpage Freq
             # checkboxes.  Since the 'kwfreq' table does not include the
             # values (the "1", "2", in "ichi1" etc), we create the expanded
             # values here.  We also supply the "descr" value which will provide
             # tool tips on web page.
           if x.kw!='nf' and x.kw!='gA': freq.extend ([Kwfreq(x.kw+'1', x.descr),
                                                       Kwfreq(x.kw+'2', x.descr)])
        return dict(pos=pos, misc=misc, stat=stat, fld=fld, dial=dial,
                    kinf=kinf, rinf=rinf, src=src, freq=freq, KW=jdb.KW), []
