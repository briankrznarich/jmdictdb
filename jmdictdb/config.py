# Copyright (c) 2019 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, os, os.path, configparser
from jmdictdb import jdb

  # The following supplies default values for any config.ini
  # values not present in the config.ini file read by cfgOpen().
  # The values given in config.ini.sample and here should be
  # kept in sync since the former also serves as documentation
  # for these defaults.
  # Note too that defaults are not provided here for database
  # login credentials (see config-pvt-sample.ini for details).

DEFAULTS = {
    'config': {
        'PVT': '' },
    'web': {
        'STATUS_DIR': '.',
        ##'CONTACT_EMAIL': 'admin@localsite.example',
        'DEFAULT_SVC': 'jmdict',
        'DEF_ENTRIES_PER_PAGE': 100,
        'MAX_ENTRIES_PER_PAGE': 1000,
        'MIN_ENTRIES_PER_PAGE': 1,
        'GAHOH_URL': '', },
    'logging': {
        'LOG_FILENAME': '',    # Write to stderr.
        'LOG_LEVEL': 'warning',
        'LOG_FILTERS': '', },
    'search': {
        'ENABLE_SQL_SEARCH': 'editors',
        'SEARCH_TIMEOUT': 3000, },
        }

def cfgRead (cfgname):
        # Open and parse a config file.  The config file has a 
        # "config" section with a "PVT" value, that file too will
        # be read.  A config.Config() object is returned.

        cfg = configparser.ConfigParser (interpolation=None)
          # Disable ConfigParser's normal lowercasing of option names.
        cfg.optionxform = lambda option: option
          # Set default values.
        cfg.read_dict (DEFAULTS)
        files = []
        with open (cfgname) as fl:
            cfg.read_file (fl);  files.append (cfgname)
        cfgpvt = cfg.get ('config', 'PVT')
        op = os.path
        if cfgpvt and not op.isabs (cfgpvt):
            cfgpvtfn = op.normpath (op.join (op.dirname (cfgname), cfgpvt))
        if cfgpvt:
            with open (cfgpvtfn) as fl:
                cfg.read_file (fl);  files.append (cfgpvtfn)
        cfg.add_section ('status')
        cfg_files = '\n  '.join((os.path.abspath(x) for x in files))
        cfg.set ('status', 'cfg_files', cfg_files)
        return cfg
