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
import logger; from logger import L
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
        'DEFAULT_SVC': 'jmdict',
        'DEF_ENTRIES_PER_PAGE': 100,
        'MAX_ENTRIES_PER_PAGE': 1000,
        'MIN_ENTRIES_PER_PAGE': 1,
        'EDITDATA_DIR': '/home/me/public_html/editdata',
        'EDITDATA_URL': 'http://localhost/~me/editdata',
        'GAHOH_URL': '', },
    'logging': {
        'LOG_FILENAME': 'jmdictdb.log',
        'LOG_LEVEL': 'info',
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
        }

def cfgRead (cfgname, pvtname=None):
        # Open and parse a config file and optional pvt config
        # file returning the results as a config.Config() object.
        # If 'cfgname' contains a path separator character (either
        # a back- or forward-slash) it is treated as a filename.
        # Otherwise a file of that name will be searched for in
        # sys.path.  To explicitly open a file in the current
        # directory without searching sys.path, prefix the filename
        # with "./"
        # Execpt that the first file is mandatory and the second
        # optional, there is no content restriction on either: any
        # recognised section can go in either file.  It is only by
        # convention that we expect the 'pvtname' file to be used
        # for the "db_*" sections.

          # findfile() will raise IOError if unable to find file.
        cfg_files = [findfile (cfgname)]
        if pvtname:
            try: pvtfn = findfile (pvtname)
            except IOError as e:
                L('lib.config').warn("Can't find file %s: %s" % (pvtname,e))
            else: cfg_files.append (pvtfn)
        cfg = configparser.ConfigParser (interpolation=None)
          # Disable ConfigParser's normal lowercasing of option names.
        cfg.optionxform = lambda option: option
          # Set default values.
        cfg.read_dict (DEFAULTS)
          #FIXME: would like to report why unread files couldn't be read
          # but cfg.read() only reports if they were read or not, not why.
        read_files = cfg.read (cfg_files)
          # Make sure we were able to read 'cfgname'.
        if not read_files or cfg_files[0] not in read_files:
            raise IOError ("Unable to read config file: %s" % cfgfiles[0])
          # We would like to generate a log message saying what config
          # files were read but we haven't configured logging yet (the
          # logging configuration is defined in the config files we just
          # read but haven't processed yet.)  So instead, add the read
          # config file names to the configparser object in a new "status"
          # section so they can be reported later.
        cfg.add_section ('status')
        cfg_files = '\n  '.join((os.path.abspath(x) for x in read_files))
        cfg.set ('status', 'cfg_files', cfg_files)
        return cfg

def findfile (name):
        if '\\' in name or '/' in name:
            fname = name
        else:
            d = jdb.find_in_syspath (name)
            if not d:
                raise IOError (2, 'File not found on sys.path', name)
            fname = os.path.join (d, name)
        return fname
