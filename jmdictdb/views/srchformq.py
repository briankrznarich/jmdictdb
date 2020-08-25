# Copyright (c) 2006-2012 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, pdb
from jmdictdb import logger; from jmdictdb.logger import L
from jmdictdb import jdb, srch

def view (svc, cfg, user, cur, params):
        d = sorted (jdb.KW.recs('SRC'), key=lambda x:x.kw.lower())
        corpora = srch.reshape (d, 10)
        return dict(src=corpora), []
