# Copyright (c) 2019 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, os, os.path, configparser
from . import jdb

  # The following supplies default values for any config.ini
  # values not present in the config.ini file read by cfgOpen().
  # The values given in config.ini.sample and here should be
  # kept in sync since the former also serves as documentation
  # for these defaults.
  # Note too that defaults are not provided here for database
  # login credentials (see config-pvt-sample.ini for details).

DEFAULTS = {
    'web': {
        'STATUS_DIR': '.',
        ##'CONTACT_EMAIL': 'admin@localsite.example',
        'DEFAULT_SVC': 'db_jmdict',
        'DEF_ENTRIES_PER_PAGE': 100,
        'MAX_ENTRIES_PER_PAGE': 1000,
        'MIN_ENTRIES_PER_PAGE': 1,
        'GAHOH_URL': '', },
    'logging': {
        'LOG_FILENAME': '../lib/jmdictdb.log',  # Relative to web/cgi/.
        'LOG_LEVEL': 'warning',
        'LOG_FILTERS': '', },
    'search': {
        'ENABLE_SQL_SEARCH': 'editors',
        'SEARCH_TIMEOUT': 3000, },
        }

  # If the 'cfgname' or 'pvtname' filename arguments to cfgRead()
  # below are relative paths, they will be looked for in the
  # LOCATION directory which in turn is relative to the directory
  # of the running script (which normally will be the cgi directory.)
LOCATION = '../lib'

def cfgRead (cfgname, pvtname):
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

          # find_config_file() will raise IOError if unable to find.
        cfg_files = [find_config_file (cfgname, LOCATION)]
        try: pvtfn = find_config_file (pvtname, LOCATION)
        except IOError: pass
        else: cfg_files.append (pvtfn)
        cfg = configparser.ConfigParser (interpolation=None)
          # Disable ConfigParser's normal lowercasing of option names.
        cfg.optionxform = lambda option: option
          # Set default values.
        cfg.read_dict (DEFAULTS)
        read_files = cfg.read (cfg_files)
          # Make sure we were able to read 'cfgname'.
        if cfg_files[0] not in read_files:
            raise IOError ("Unable to read config file: %s" % cfgfiles[0])
          #FIXME: would be nice to generate a log warning or info message
          # if the 'pvtname' file was not read but we can't do that here
          # because logging is not initialized yet (we need to read the
          # config files to get the logging settings before initializing
          # the logging facility.)
        return cfg

def find_config_file (name, location):
        ''' Look for and return the absolute path of a file named 'name'
            in a directory, 'location', which is a path relative to the
            the location of the calling script.

            Example: if the calling script is:
              ~user/public_html/cgi/script.py
            'location' is "../lib" and 'name' is "config.ini", this
            function will look for a file:
              ~user/public_html/lib/config.ini
            and either return the absolute filename if it exists and is
            readable or raise an IOError exception if not. '''

        script = os.path.abspath (sys.argv[0])
        d = os.path.dirname (script)
        fname = os.path.normpath (os.path.join (d, location, name))
        if not os.access (fname, os.R_OK):
            raise IOError (2, "File not found", fname)
        return fname
