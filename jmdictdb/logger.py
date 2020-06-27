# Copyright (c) 2018 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# Provide a standard logging configuration for JMdictDB cgi scripts,
# tools and library functions and supply functionality that should
# be provided by the Python's logging module.

import sys, logging, traceback, os, datetime, re, pdb

  # The function L() is a convenience function provided to importers
  # as a consise way to write logging calls.  It is used like:
  #   L('logger_name').info("log message...")
L = logging.getLogger;

  # Define an aditional logging level for summary messages: informational
  # messages that are for providing top-level summary of results and
  # which should be shown even when info-level messages aren't.
SUMMARY = 36

def log_config (level="warning", filename=None, ts=None, filters=None):
        """
        level -- One of: "critical", "error", "warning", "info", "debug".
        filename -- If not given or None, logging messages will be written
          to sys.stderr.  Otherwise the name of a file to which the logging
          messages will be appended.  If the file is not writable at the
          time this function is called, a logging message will be written
          to stderr to that effect and further logging disabled.
        ts -- Controls the presence or absence of a timestamp prefix on the
          logging messages.  If None the timestamp will be absent if the
          'filename' parameter is false (ie, output to stderr) and present
          otherwise (output to a file).  If 'ts' is not None then timestamp
          will be present if true, absent if false.
        filters -- A list of strings that specify logging messages to
          output.  Each consists of an initial (case-insensitive) letter
          from the set ('s', 'w', 'i', 'd'} (corresponding to the logging
          levels, SUMMARY, WARNING, INFO, DEBUG) optionally preceeded by
          a "!" character and the remainder of the string being a regular
          expression.
          - Messages with a level less than the logger's level will be
            compared with each filter in the order given looking for a
            match: the message's log level is greater or equal to the
            filter's log level and message's source (logger name) matches
            the filter's regex.
          - If the matched filter was not preceeded with a "!" the log
            message will be printed and no further filters will be compared.
          - If the matched filter was preceeded with a "!" the log message
            will not be printed  no further filters will be compared.
          - If the log message matched no filters it is output if its level
            is greater than the logger's level, otherwise supressed.

          Example:
            logger.log_config (level="error", filters=['!D^xx', 'Dyes$'])
            L('test_yes').debug('wow')       # Printed (matched filt#2)
            L('test_no').debug('no see me')  # Not printed (no match)
            L('test_no').error('see me!')    # Printed (no match but msg
                                             #  level >= logger level.
            L('xx_yes').info('but not me')   # Not printed (neg. match)
          Note that if the order of the two filters were reversed, the
          forth message would be output because the 'Dyes$' filter would
          match before the '!D^xx' filter could reject it.
        """

          # Replace the Python "logging" module's CRITICAL level with a more
          # meaningful (to us) value of FATAL.  The numerical level remains
          # the same (50) as does the function name logging.critical().  We
          # are interested only in changing the output messages.
        logging.addLevelName (50, 'FATAL')
          # The following might be more interoperable with other libraries'
          # use of logging but accesses a logging module "private" variable.
        #logging._levelToName[50] = 'FATAL'  # Replaces 'CRITICAL'.
          # Add a new SUMMARY level between WARNING and ERROR.  This
          # is for high level info messages tha summarize succesful
          # results such as a message that 'n' items were processed.
        logging.addLevelName (SUMMARY, 'SUMMARY')
          # Remove any existing handlers.  This allows us to reconfigure
          # logging even if caller previously called basicConfig().
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        msgdest, disable = {'stream': sys.stderr}, False
        if filename:
            if os.access (filename, os.W_OK):
                  # We should be able to set 'msgdest' below to simply:
                  #   {'filename': filename}
                  # However, it seems that when running as a cgi script under
                  # Apache-2.4, the file is opened with ascii encoding rather
                  # than utf-8.  When a logging message is written that contains
                  # non-ascii characters, a UnicodeEncodingError is raised.
                  # Curiously, the error and traceback is written to the web
                  # server log file and then control is returned to the python
                  # program that generated the message, which continues on
                  # normally, though the original non-ascii log message never
                  # appears in the logging log file.  The following forces the
                  # logging file to be opened with utf-8 encoding.
                msgdest = {'handlers':
                           [logging.FileHandler(filename,'a','utf-8')] }
            else: disable = True
        if ts is None: want_ts = bool (filename)
        else: want_ts = ts
        tsfmt = '%(asctime)s-%(process)d ' if want_ts else ''
          # Now do our configuration.
        logging.basicConfig (
            level=levelnum(level),
            format=tsfmt + '%(levelname)1.1s %(name)s: %(message)s',
            datefmt="%y%m%d-%H%M%S",
              # When both "stream" and "filename" are present and non-None,
              # "filename" takes precedence according to
            **msgdest)
        if disable:
            cwd = os.getcwd()
            L('lib.logger').error(('Unable to write to logging file: %s'
                                  '\n  (cwd: %s)') % (filename, cwd))
            logging.disable (logging.CRITICAL)
        elif filters:
            try: filter = parse_filter_list (filters, L().getEffectiveLevel())
            except ValueError as e:
                L('lib.logger').error("Bad filter: '%s'" % str (e))
            else:
                  # Filters attached to loggers apply only to messages
                  # produced by that logger, the root logger will not
                  # apply a filter to a message produced by a different
                  # logger, even if the the root logger is handling it.
                  # However, the handler will.
                L().handlers[0].addFilter (filter)
                  # To allow debug messages to be filtered the logger's
                  # level has to allow them too.
                L().setLevel(1)

def levelnum( level ):
        """
        Convert logging 'level' which may be an int already or a string
        representation of an int, or a logging level string ("info",
        "error", etc) in either upper or lower case, to an int.
        """
        try: lvl = int(level)
        except ValueError: lvl = logging.getLevelName (level.upper())
        if not isinstance (lvl, int):
            raise ValueError ("bad 'level' parameter: %s" % level)
        return lvl

Level_abbr2num = {'F':50,'E':40,'S':36,'W':30,'I':20,'D':10}
def parse_filter_list (flist, lvllimit=30):
        regexes = []
        for t in flist:
            t_orig, neg = t, 1
            try:
                if t[0] == '!': neg, t = -1, t[1:]
                if t[0].isdigit():
                    level, regex = int(t[0:1]), t[2:]
                else:
                    level, regex = Level_abbr2num[t[0].upper()], t[1:]
                regexes.append ((level * neg, regex))
            except (ValueError, KeyError, IndexError):
                raise ValueError (t_orig)
        filter = lambda x: _logmsg_filter (x, regexes, lvllimit)
        return filter

def _logmsg_filter (rec, regexes, lvllimit):
          # rec -- Log record created by a logger.
          # regexes -- List of (level,regex) tuples.
          # lvllimit -- Logging level at or above which logging messages
          #   will be output if no regexes were matched.
        for lvl,regex in regexes:
            if rec.levelno < abs(lvl) or not re.search(regex,rec.name):
                continue
              # We get here if a regex matched and message level is equal
              #  or greater than the filter level.  If 'lvl'>0 we return
              #  True to output the message.  If 'lvl' is negative, this
              #  is a negative match: return False to NOT output the message.
            return True if lvl >= 0 else False
        if rec.levelno >= lvllimit: return True
        return False

  # This function can be used as the sys.excepthook handler by CGI
  # scripts to present an error message in HTML format.
def handler( ex_cls, ex, tb ):
        import jmcgi
        errid = datetime.datetime.now().strftime("%y%m%d-%H%M%S")\
                + '-' + str(os.getpid())
        logging.critical( '{0}: {1}'.format(ex_cls, ex) )
        logging.critical( '\n' + ''.join( traceback.format_tb(tb)) )
        jmcgi.err_page( [str(ex)], errid )

def enable(): sys.excepthook = handler

__all__ = ['log_config', 'L']
