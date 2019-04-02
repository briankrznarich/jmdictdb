#######################################################################
#  This file is part of JMdictDB.
#  Copyright (c) 2019 Stuart McGraw
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

import sys, os, os.path, configparser
import jdb

  # The following supplies default values for any config.ini
  # values not present in the config.ini file read by cfgOpen().
  # The values given in config.ini.sample and here should be
  # kept in sync since the former also serves as documentation
  # for these defaults.

DEFAULTS = {
    'web': {
        'STATUS_DIR': '.',
        ##'CONTACT_EMAIL': 'admin@localsite.example',
        'DEFAULT_SVC': 'db_jmdict',
        'DEF_ENTRIES_PER_PAGE': 100,
        'MAX_ENTRIES_PER_PAGE': 1000,
        'MIN_ENTRIES_PER_PAGE': 1,
        'EDITDATA_DIR': '/home/me/public_html/editdata',
        'EDITDATA_URL': 'http://localhost/~me/editdata',
        'GAHOH_URL': '', },
    'logging': {
        'LOG_FILENAME': 'jmdictdb.log',
        'LOG_LEVEL': 'warning',
        'LOG_FILTERS': '', },
    'search': {
        'ENABLE_SQL_SEARCH': 'editors',
        'SEARCH_TIMEOUT': 3000, },

    'db_session': {
        #'host': 'localhost',
        'dbname': 'jmdict',
        'user': 'jmdictdb',
        #'pw': 'xxxxxx',
        'session_db': 'db_session', },
    'db_jmdict': {
        #'host': 'localhost',
        'dbname': 'jmdict',
        #'sel_user': 'jmdictdbv',
        #'sel_pw': 'xxxxxx',
        'user': 'jmdictdb',
        #'pw': 'xxxxxx',
        'session_db': 'db_session', },
    'db_jmtest': {
        #'host': 'localhost',
        'dbname': 'jmtest',
        #'sel_user': 'jmdictdbv',
        #'sel_pw': 'xxxxxx',
        #'user': 'jmdictdb',
        #'pw': 'xxxxxx',
        'session_db': 'db_session', },
    'db_jmnew': {
        #'host': 'localhost',
        'dbname': 'jmnew',
        #'sel_user': 'jmdictdbv',
        #'sel_pw': 'xxxxxx',
        #'user': 'jmdictdb',
        #'pw': 'xxxxxx',
        'session_db': 'db_session', },
        }

def cfgOpen (cfgname):
        # Open and parse a config file returning the resulting
        # config.Config() object.  If 'cfgname' contains a path
        # separator character (either a back- or forward-slash)
        # it is treated as a filename.  Otherwise it is a path-
        # less filename that is searched for in sys.path.
        # To explicitly open a file in the current directory
        # without searching sys.path, prefix the filename with
        # "./".

        if '\\' in cfgname or '/' in cfgname:
            fname = cfgname
        else:
            d = jdb.find_in_syspath (cfgname)
            if not d:
                raise IOError (2, 'File not found on sys.path', cfgname)
            fname = os.path.join (d, cfgname)
        cfg = configparser.ConfigParser (interpolation=None)
          # Disable ConfigParser's normal lowercasing of option names.
        cfg.optionxform = lambda option: option
          # Set default values.
        cfg.read_dict (DEFAULTS)
          # Override the defaults with values from the config file.
        with open (fname) as cfgfile:
            cfg.read_file (cfgfile)
        return cfg
