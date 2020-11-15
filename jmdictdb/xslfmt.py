# Copyright (c) 2009 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Apply an xslt transform to an entry formatted as xml.  Typically
this is used with the "to_edit2.xsl" stylesheet to get a Edict2
formmated version of an entry.

"""
import sys, re, html, lxml
from io import StringIO
from lxml import etree
from jmdictdb import jdb, fmtxml

def entr (entr, xslfile=None, xslt=[], want_utf8=False):
        # A slow but simple way to get an Edict2 formatted text for an entry.
        # entr -- A jmdictdb Entr object, or a string containing the xml
        #   of an Entr object, or None.
        # xslfile -- Name of an xslt file.  If the name contains any path
        #   separator characters, it will be used as is.  Otherwise is it
        #   will be taken as a plain filename and searched for on the Python
        #   search path (sys.path).  Either way, the resulting file is
        #   will be converted to a lxml .etree.XSLT transform object and
        #   applied the the xml from 'entr' (if 'entr' was not None.)
        # xslt -- May be None, an empty list, or a list of one item which
        #   is a lxml.etree.XSLT transform object that will be applied to
        #   in 'entr' xml.  If an empty list, the xslt file given 'xslfile'
        #   will be converted to a transform and saved in it (for use in
        #   subsequent calls).  If None, 'xslfile' will be converted to a
        #   transform and not saved.
        # want_utf8 -- If false, a unicode text string is returned.  If
        #   true, a utf-8 encoded text string is returned.

        if not xslt:
            if not xslfile: xslfile = 'edict2.xsl'
              # Read the xsl file.
            if '/' not in xslfile and '\\' not in xslfile:
                dir = jdb.std_csv_dir()
                xslfile = dir + '/' + xslfile
            xsldoc = lxml.etree.parse (xslfile)
              # Generate a transform, and use the default value
              # of the 'xslt' parameter to cache it.
            xslt[:] = [lxml.etree.XSLT (xsldoc)]
        edicttxt = None
        if entr:
            if not isinstance (entr, str):
                xml = fmtxml.entr (entr, compat='jmdict')
            else: xml = entr
              # De-entityize any entities in 'xml' by removing the leading "&"
              # and trailing ";".  The function _ent_repl() is used to do the
              # replacement because it skips entities like "&quot;" which we
              # dont want to change.
            pat = '&[a-zA-Z0-9-]+;'
            xml = re.sub (pat, _ent_repl, xml)
            xml = "<JMdict>%s</JMdict>" % xml
              # Apply the xsl to the xml, result is utf-8 encoded.
            edicttxt = str (xslt[0](etree.parse (StringIO (xml)))).rstrip('\n\r')
            edicttxt = html.unescape (edicttxt)
            if want_utf8:  # Convert to utf-8.
                edicttxt = edicttxt.encode('utf-8')
        return edicttxt

def _ent_repl (mo):
          # This func is used by the re.sub() call in entry() above to
          # replace all but the standard xml entities with ordinary text
          # strings.
	  #FIXME: this same function is also used in jmxml.py; that one
          # and this should be combined somewhere (jdb?)
        orig = mo.group(0)
        if orig in ('&lt;','&gt;','&amp;','&quot;'): return orig
        return orig[1:-1]
