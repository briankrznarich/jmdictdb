#######################################################################
#  This file is part of JMdictDB.
#  Copyright (c) 2006-2012 Stuart McGraw
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
import jdb, srch

def view (svc, cfg, user, cur, params):
        d = sorted (jdb.KW.recs('SRC'), key=lambda x:x.kw.lower())
        corpora = srch.reshape (d, 10)
        return dict(src=corpora,
                    svc=svc, cfg=cfg, user=user, params=params), []
