# Copyright (c) 2019 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, os, configparser, pdb
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
        'PRIVATE': '' },
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
        # Open and parse a config file.  If the config file has a
        # "config" section with a "PRIVATE" value, that file too will
        # be read.  A config.Config() object is returned.
        # If the main config file, or private file if given in the
        # main file, can't be read, the resulting OSError exception
        # is not caugfht here but allowed to propogate to the caller.
        # The full paths of the config files are recorded in the
        # returned ConfigParser object in a new section added here
        # with two values:
        #   [status]/cfg_dir
        #   [status]/cfg_files
        # The "cfg_files" value contains the main status file name
        # followed by a '\n' and the private file name if it was given
        # in the main file.  The filenames are given with full paths
        # from "/".

        cfg = configparser.ConfigParser (interpolation=None)
          # Disable ConfigParser's normal lowercasing of option names.
        cfg.optionxform = lambda option: option
          # Set default values.
        cfg.read_dict (DEFAULTS)
        files = []
        #print ("config: opening %s" % cfgname, file=sys.stderr)       ##DEBUG
        with open (cfgname) as fl:
            cfg.read_file (fl);  files.append (cfgname)
        cfgdir = os.path.dirname (abspath (cfgname))
        cfgpvt = cfg.get ('config', 'PRIVATE')
        if cfgpvt:
            cfgpvtfn = abspath (cfgpvt, cfgdir)
            #print ("config: opening %s" % cfgpvtfn, file=sys.stderr)  ##DEBUG
            with open (cfgpvtfn) as fl:
                cfg.read_file (fl);  files.append (cfgpvtfn)

        cfg.add_section ('status')
        cfg_files = '\n  '.join((os.path.abspath(x) for x in files))
        cfg.set ('status', 'cfg_files', cfg_files)
        cfg.set ('status', 'cfg_dir', cfgdir)
          # Replace any possibly relative filenames with their full
          # paths from "/" relative to the config file directory.
          # This is because filenames relative to the current working
          # directory are problematical when different web servers will
          # run this code with varying cwd's.  Converting them to absolute
          # full paths now will will save debugging time trying to figure
          # out where a file really is or should be.
        normcfg (cfg, 'web', 'STATUS_DIR')
        normcfg (cfg, 'logging', 'LOG_FILENAME')
        return cfg

def normcfg (cfg, section, key):
        '''-------------------------------------------------------------------
        Replace a config value, identified by 'section' and 'key' and
        assumed to be a file name, with a new value that is the full
        path from "/" of that filename relative to the config file
        directory.
        -------------------------------------------------------------------'''
        cfgdir = cfg.get ('status', 'cfg_dir')
        try: fn = cfg.get (section, key)
          # If the section or key doesn't exist, ignore it.
        except (configparser.NoSectionError, configparser.NoOptionError):
            return
        afn = abspath (fn, cfgdir)
        cfg.set (section, key, afn)

def abspath (path, relative_to=None):
          # Like os.path.abspath() but allows 'path' to be relative
          # to an arbitrary directory.
        if not path: return path    # Null paths are not equiv to cwd, use
                                    # "." when the latter is wanted.  See
                                    # for example LOG_FILENAME where ""
                                    # means stderr.
        P = os.path     # For brevity.
        if not relative_to: relative_to = os.getcwd()
        fn = P.normpath (P.join (P.abspath (relative_to), path))
        return fn
