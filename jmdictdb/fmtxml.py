# Copyright (c) 2006-2014 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Functions for generating XML descriptions of entries.

"""
import re, os, difflib
from xml.sax.saxutils import escape as esc, quoteattr as esca
from jmdictdb import jdb
global KW

def entr (entr, compat='jmex', geninfo=True, genhists=True,
                genxrefs=True, wantlist=False):
        '''
        Generate an XML description of entry 'entr'.
        Parameters:
          entr -- An entry object (such as return by entrList()).
          compat --
                "jmex" or None: generate XML that completely
                  describes the entry using an enhanced version
                  of the jmdict DTD.
                "jmdict": generate XML that uses the most recent
                  version of the standard JMdictDTD (currently
                  rev 1.09).
                "jmnedict": generate XML that uses the standard
                  (post 2014-10) JMnedict DTD that include seq
                  numbers and xrefs.
          geninfo -- If true and if 'compat' is "jmex" (or None)
                then <info> elements may be generated containing
                <note> and <srcnote> elements.  They may also
                contain <audit> elements if 'genhists' is true.
                If false, <info> elements (and their descendant
                elements) will never be generated.
          genhists -- If true and if 'compat' is "jmex" (or None)
                and 'geninfo' is true, then <audit> elements may
                be generated as child elements in <info>.  They
                serialize an entry's history records.  If false
                <audit> elements will never be generated.
          genxrefs -- If true generate <xref> elements for the items
                in the entry's ._xref and .xrslv lists .  If false
                xrefs elements will be will not be generated.  Note
                that any ._xref items must be augmented xrefs; if an
                unaugmented xref is encountered an exception will be
                thrown.
          wantlist -- If false, return the xml as a single string.
                with embedded newline characters.  If true, return a
                list of strings, one line per string, with no embedded
                newlines.
        '''

        global KW; KW = jdb.KW
        if compat == 'jmex': compat = None
        fmt= entrhdr (entr, compat)

        kanjs = getattr (entr, '_kanj', [])
        for k in kanjs: fmt.extend (kanj (k, compat))

        rdngs = getattr (entr, '_rdng', [])
        for r in rdngs: fmt.extend (rdng (r, kanjs, compat))

        senss = getattr (entr, '_sens', [])
        if compat in ('jmnedict',):
            for x in senss: fmt.extend (trans (x, compat, entr.src, genxrefs))
        else:
            for x in senss:
                fmt.extend (sens (x, kanjs, rdngs, compat, entr.src, genxrefs))

        if not compat: fmt.extend (info (entr, compat, geninfo, genhists))
        if not compat: fmt.extend (audio (entr))
        if not compat: fmt.extend (grps (entr))
        fmt.append ('</entry>')
        if wantlist: return fmt
        return '\n'.join (fmt)

def kanj (k, compat):
        fmt = []
        fmt.append ('<k_ele>')
        fmt.append ('<keb>%s</keb>' % esc(k.txt))
        fmt.extend (ents (k, '_inf', 'KINF', 'ke_inf', sort=True, dtd=compat))
        fmt.extend (['<ke_pri>%s</ke_pri>' %s
                     for s in jdb.freq2txts (getattr (k,'_freq',[]))])
        fmt.append ('</k_ele>')
        return fmt

def rdng (r, k, compat):
        fmt = []
        fmt.append ('<r_ele>')
        fmt.append ('<reb>%s</reb>' % esc(r.txt))
        fmt.extend (restrs (r, k))
        fmt.extend (ents (r, '_inf', 'RINF', 're_inf', sort=True, dtd=compat))
        fmt.extend (['<re_pri>%s</re_pri>' %s
                     for s in jdb.freq2txts (getattr (r,'_freq',[]))])
        if not compat: fmt.extend (audio (r))
        fmt.append ('</r_ele>')
        return fmt

def restrs (rdng, kanjs, attr='_restr'):
        # Generate xml lines for reading-kanji (or sense-reading, or
        # sense-kanji) restrictions.  This function does the necessary
        # inversion between the "dis-allowed" form of restrictions used
        # in the database and API, and the "allowed" form used in the
        # XML.  It also properly generates "re_nokanji" elements when
        # appropriate for reading-kanji restrictions.  It does not
        # require or use Rdng.rdng, Kanj.kanj, or Sens.sens attributes.
        #
        # rdng -- A Rdng (or Sens) object.
        # kanjs -- A list of Kanj (or Rdng) objects.
        # attr -- Name of the attribute on the 'rdng' or 'kanj' object(s)
        #   that contains the restriction list.

        fmt = []; invrestr = []
        invdkanjs = jdb.restrs2ext (rdng, kanjs, attr)
        if invdkanjs is None:
            if attr != '_restr': raise RuntimeError ()
            fmt.append ('<re_nokanji/>')
        elif invdkanjs:
            tag = "re_"+attr[1:] if attr=='_restr' else attr[1:]
            fmt.extend (['<%s>%s</%s>' % (tag, x.txt, tag) for x in invdkanjs])
        return fmt

def sens (s, kanj, rdng, compat, src, genxrefs=True):
        """
        Format a sense.
        fmt -- A list to which formatted text lines will be appended.
        s -- The sense object to format.
        kanj -- The kanji object of the entry that 's' belongs to.
        rdng -- The reading object of the entry that 's' belongs to.
        compat -- See function entr().  We assume in sens() that if
            compat is not None it is =='jmdictxxx', that is, if it
            were 'jmnedict', trans() would have been called rather
            than sens().
        src -- If 'compat' is None, this should be the value of the
            entry's .src attribute.  It is passed to the xref() func
            which needs it when formatting enhanced xml xrefs.  If
            'compat' is not None, this parameter is ignored.
        genxrefs -- If false, do not attempt to format xrefs.  This
            will prevent an exception if the entry has only ordinary
            xrefs rather than augmented xrefs.
        """
        fmt = []
        fmt.append ('<sense>')

        fmt.extend (restrs (s, kanj, '_stagk'))
        fmt.extend (restrs (s, rdng, '_stagr'))

        fmt.extend (ents (s, '_pos', 'POS', 'pos', dtd=compat))

        xr = sens_xrefs (s, src, compat)
        fmt.extend (xr)

        fmt.extend (ents (s, '_fld', 'FLD', 'field', dtd=compat))
        fmt.extend (ents (s, '_misc', 'MISC', 'misc', dtd=compat))

        notes = getattr (s, 'notes', None)
        if notes: fmt.append ('<s_inf>%s</s_inf>' % esc(notes))

        lsource = getattr (s, '_lsrc', None)
        if lsource:
            for x in lsource: fmt.extend (lsrc (x))

        fmt.extend (ents (s, '_dial', 'DIAL', 'dial', dtd=compat))

        for x in s._gloss: fmt.extend (gloss (x, compat))

        fmt.append ('</sense>')
        return fmt

def trans (sens, compat, src, genxrefs):
        "Format a jmnedict trans element."

        fmt = (ents (sens, '_misc', 'MISC', 'name_type', dtd=compat))
        if genxrefs:
            xr = sens_xrefs (sens, src, compat)
            fmt.extend (xr)
        eng_id = KW.LANG['eng'].id
        for g in getattr (sens, '_gloss', []):
            lang = getattr (g, 'g_lang', eng_id)
            lang_attr = (' xml:lang="%s"' % KW.LANG[lang].kw)\
                        if lang != eng_id else ''
            fmt.append ('<trans_det%s>%s</trans_det>' % (lang_attr, esc(g.txt)))
        if fmt:
            fmt.insert (0, '<trans>')
            fmt.append ('</trans>')
        return fmt

def gloss (g, compat=None):
        fmt = []
        attrs = []
        if g.lang != KW.LANG['eng'].id:
            attrs.append ('xml:lang="%s"' % KW.LANG[g.lang].kw)
          # As of DTD rev 1.09 ginf attributes are added to glosses so
          # we no longer do this only for the 'compat is None' condition.
          #FIXME: this will produce "g_type" attributes in jmnedict
          # in violation of the jmnedict DTD if there are .ginf items
           # in the data.  We fragilely count on there not being any.
        if g.ginf != KW.GINF['equ'].id:
            attrs.append ('g_type="%s"' % KW.GINF[g.ginf].kw)
        attr = (' ' if attrs else '') + ' '.join (attrs)
        fmt.append ("<gloss%s>%s</gloss>" % (attr, esc(g.txt)))
        return fmt

def ents (parent, attr, domain, elem_name, sort=False, dtd="jmdict"):
        '''
    Given a list of tag items (in the form ('parent','attr')) we return
    a list of XML elements containing the entities representing those
    tags.
      parent -- A Entr component like Kanj, Sens, etc.
      attr -- (str) A tag list attribute on 'parent' like "_kinf",
          "_pos", etc.
      domain -- (str) Type of tag list for lookup in jdb.KW ("KINF",
          "POS", etc.)
      elem_name --(str) Name of XML element to use (eg "ke_inf",
          "pos", etc.)
      sort -- (bool) If true sort list of elements before return.
      dtd -- (str) Entity set.  Identifies a particular set of
          tag -> entity mappings in the Kwds data.  Typically will
          be "jmdict" or "jmnedict" but other alternatives may be
          available depending on the data in the kw* tables and
          xsv files.  None is equivalent to "jmdict".'''

        nlist = getattr (parent, attr, [])
        if not nlist: return nlist
          # For brevity make a temporary function that returns only
          # the entity name.
        ent_name = lambda id: entity(KW,domain,id,dtd)[0]
        kwlist = ['<%s>&%s;</%s>'
                    # Note that x.kw is the tag id number.
                  % (elem_name, ent_name(x.kw), elem_name)
                  for x in nlist]
        if sort: kwlist.sort()
        return kwlist

def entity (kwds, domain, id, dtd):
        '''
    Return the XML entity name and value for the 'domain' tag with
    id number 'id' in 'kwds' for use with the DTD 'dtd'.
      kwds -- A jdb.Kwds instance.
      domain -- (str) The type of tag (eg "DIAL", "POS", etc).
      id -- (int) Id number of tag.
      dtd -- (str) Entity set.  Identifies a particular set of
          tag -> entity mappings in the Kwds data.  Typically will
          be "jmdict" or "jmnedict" but other alternatives may be
          available depending on the data in the kw* tables and
          xsv files.  None is equivalent to "jmdict".'''

        msg = "Illegal tag for DTD \"%s\": '%s'"
          #FIXME: following dtd adjustment should be done higher
          # in call chain.
        if dtd in (None, 'jmex'): dtd = 'jmdict'
        rec = getattr (kwds, domain)[id]
          # Assume the entity name and value will be the same as the tag
          # name and descr.  We'll overwrite later if wrong.
        ent, value = rec.kw, rec.descr
        if not rec.ents or dtd not in rec.ents:
              # If there is no specific entity info for our DTD in the
              # rec.ents attribute then, if the DTD is 'jmdict', the entity
              # name and value are the tag's 'kw' and 'descr' values.  That
              # is, unless contrary info is provided in rec.ents we assume
              # that all tags are DTD entities.  Conversely, if the DTD is
              # "jmnedict" (anything other than "jmdict") we assume that
              # no tags are DTD entities by default and hence if there is
              # no rec.ents value, raise an error.
            if dtd != 'jmdict': raise KeyError(msg % (dtd, rec.kw))
        else:
            entinfo = rec.ents[dtd]
            if not isinstance (entinfo, dict):
                  # If the entity info is not a dict, then we presume it's
                  # a scalar whose bool value indicates when true that the
                  # tag's 'kw'/'descr' values are the same as the entity,
                  # or when false, the tag is disallowed.
                if not entinfo: raise KeyError(msg % (dtd, rec.kw))
            else:
                  # If the entity info is a dict, then it's "e" item, if
                  # present, is the entity name.  If not present the entity
                  # name is the same as the tag.  Same for the "v" and the
                  # entity value / tag descr.
                if ('e' not in entinfo and 'v' not in entinfo)\
                        or len(entinfo)>2:
                    raise ValueError ("Bad entity info for %s[%d]: %r"
                                      % (domain, id, entinfo))
                if 'e' in entinfo: ent = entinfo['e']
                if 'v' in entinfo: value = entinfo['v']
        return ent, value

def entities (kwds, dtd, grouped):
       'Return a list of entity definitions suitable for inclusion in a DTD.'

         # Note that there may be duplicate entity lines (where both the
         # name and value are the same; for example at the current time
         # "ik/word containing..." occurs in both the KINF and RINF groups.
         # In the grouped output we leave the duplicates. In the ungrouped
         # output (which is sorted) we eliminate duplicates.
         #FIXME: should raise an error when duplicate entity names are
         # present with different values.  It seems we can't rely on XML
         # validation to pick this up: a quick check with a couple online
         # XML validators reported no errors, even when the values were
         # different.

       dominfo = [  # These are the tag domains that use entities:
           ('DIAL', '<dial> (dialect)'),
           ('FLD',  '<field>'),
           ('KINF', '<ke_inf> (kanji info)'),
           ('MISC', '<misc> (miscellaneous)'),
           ('POS',  '<pos> (part-of-speech)'),
           ('RINF', '<re_inf> (reading info)'), ]
       lines = []
       for domain, descr in dominfo:
           group = []
           for rec in kwds.recs (domain):
               try: ename, eval = entity (kwds, domain, rec.id, dtd)
               except KeyError: pass
               else: group.append ('<!ENTITY %s "%s">' % (ename, eval))
           if grouped: group.sort (key=lambda x: x.lower())
           if grouped and group:
                 #FIXME: hardwiring "jmnedict" here is a hack.
               if dtd == 'jmnedict' and domain == 'MISC':
                   descr = '<name_type>';
               lines.append ("<!-- %s entities -->" % descr)
           lines.extend (group)
       if not grouped:
           lines = list (set (lines))  # Remove any duplicate lines.
           lines = sorted (lines, key=lambda x: x.lower())
       return '\n'.join (lines)

def lsrc (x):
        fmt = [];  attrs = []
        if x.lang != KW.LANG['eng'].id or not x.wasei:
            attrs.append ('xml:lang="%s"' % KW.LANG[x.lang].kw)
        if x.part: attrs.append ('ls_type="part"')
        if x.wasei: attrs.append ('ls_wasei="y"')
        attr = (' ' if attrs else '') + ' '.join (attrs)
        if not x.txt: fmt.append ('<lsource%s/>' % attr)
        else: fmt.append ('<lsource%s>%s</lsource>' % (attr, esc(x.txt)))
        return fmt

def sens_xrefs (sens, src, compat):
        # Format xrefs and unresolved xrefs for a specific sense.
        xr = []
        xrfs = getattr (sens, '_xref', None)
        if xrfs:
            xr.extend (xrefs (xrfs, (not compat) and src))
        xrfs = getattr (sens, '_xrslv', None)
        if xrfs:
            xr.extend (xrslvs (xrfs, (not compat) and src))
        if compat:
              # The legacy jmdict dtd requires <xref> elements
              # to preceed <ant> elements.  We sort on the second
              # character of the xml string which will be "x" for
              # "<xref>..." and "a" for "<ant>...".  Python sorts
              # are stable so preexisting order within the xref
              # and ant groups will be maintained..
            xr.sort (key=lambda x:x[1], reverse=True)
        return xr

def xrefs (xrefs, src):
        # Generate xml for xrefs.  If there is an xref to every
        # sense of a target entry, then we generate a single
        # xref element without a sense number.  Otherwise we
        # generate an xref element with sense number for each
        # target sense.
        #
        # xrefs -- A list of xref objects to be formatted.  The
        #   xrefs must have an augmented target attribute (as
        #   produced by calling augment_xrefs()) or an error
        #   will be raised (in function xref).
        #
        # src -- Corpus id number of the entry that contains
        #   the target 'xref' of the xrefs.
        #   If 'src' is true, enhanced XML will be generated.
        #   If not, legacy JMdict XML will be generated.

        fmt = []

          # Mark each xref that differs only by .xsens value with
          # a ._xsens attribute that will be a list of all .xsens
          # values on the first such xref, and an emply list on
          # subsequent such xrefs.
        jdb.add_xsens_lists (xrefs)

        for x in xrefs:
              # If ._xsens is empty, this xref can be ignored since
              # we already formatted a preceeding matching xref that
              # contained a list of all .xsens values.
            if not x._xsens: continue

              # Check that augment_xrefs() was called on this
              # xref.  The target object is needed because we
              # it has the actual kanji and reading texts that
              # will be used in the xml xref, as well and the
              # the number of senses, which we also need.
            try: targ = x.TARG
            except AttributeError: raise AttributeError (
                                   "xref missing TARG attribute.  "
                                   "Did you forget to call augment_xrefs()?")
              # If generating JMdict-compatible XML, don't generate
              # xrefs to entries that are unapproved or whose status
              # is not active (i.e. deleted or rejected.)
            if not src and (targ.unap or targ.stat != jdb.KW.STAT['A'].id):
                continue

              # Format the xref into xml text.
            fmtdxref = xref (x, src)

              # We can assume that, since the database RI constraints
              # won't allow two xrefs in the same source to point to
              # the same target and sense, if the number of xsens values
              # in the .xsens list equals the number of target senses,
              # there is one xref pointing to each sense.
            if len(targ._sens) == len(x._xsens) or x.nosens:
                  # There is an xref for each target sense or the "nosens"
                  # flag is set on this xref.  Both indicate that we want
                  # to present a generic xref that refers to the entire
                  # entry rather than a particular sense of it.  The former
                  # condition was used prior to the introduction of the
                  # "nosens" flag and is supported for compatibility with
                  # existing entries.
                  #FIXME? we assume here that the .nosens flag is on the
                  # first xref of the group marked by '.xsens'.  But there
                  # is nothing in the database that enforces that.  It is
                  # not well defined how we should treat a nosens flag on
                  # an xref to a sense other than 1; right now we ignore it.
                fmt.append (fmtdxref % '')
            else:
                  # Otherwise, we want to generate an separate xref for
                  # each target senses.
                for s in x._xsens:
                      # The string returned by xref() has a "%s"
                      # placeholder for the sense number.  Generate
                      # an xref element with sense for each xref in
                      # the group.  \u30FB is mid-height dot.
                    fmt.append (fmtdxref % '\u30FB%d' % s)
        return fmt

def xref (xref, src):
        """
        Generate a formatter xml string for a single xref.

        xref -- The xref object to be formatted.  The xref must
          have an augmented target attribute (as produced by calling
          augment_xrefs()) since that infomation is required to
          generate the kanji and reading texts, and an error will
          be raised if not.

        src -- Corpus id number of the entry that contains 'xref'.
          If 'src' is true, enhanced XML will be generated.
          If not, legacy JMdict XML will be generated.

        The returned xref string will have a "%s" where the target
        sense number would go, which the caller is expected to
        replace with the sense number or not, as desired.
        """
        targobj = xref.TARG
        k = r = ''
        if getattr (xref, 'kanj', None):
            k = targobj._kanj[xref.kanj-1].txt
        if getattr (xref, 'rdng', None):
            r = targobj._rdng[xref.rdng-1].txt
        if k and r: target = k + '\u30FB' + r  # \u30FB is mid-height dot.
        else: target = k or r

        tag = 'xref'; attrs = []
        if src:
            attrs.append ('type="%s"' % KW.XREF[xref.typ].kw)
            attrs.append ('seq="%s"' % targobj.seq)
            if targobj.src != src:
                attrs.append ('corp="%s"' % jdb.KW.SRC[targobj.src].kw)
            if getattr (xref, 'notes', None):
                attrs.append ('note="%s"' % esc(xref.notes))
        else:
            if xref.typ == KW.XREF['ant'].id: tag = 'ant'

        attr = (' ' if attrs else '') + ' '.join (attrs)
        return '<%s%s>%s%%s</%s>' % (tag, attr, target, tag)

def xrslvs (xrslvs, src):
        # Generate a list of <xref> elements based on the list
        # Xrslv objects, 'xrlvs'.  If 'compat' is false, extended
        # xml will be produced which will use <xref> elements with
        # "type" attributes for all xrefs.
        # If 'compat' is true, plain <xref> and <ant> elements
        # compatible to EDRDG JMdict XML will be produced.
        # Xref items with a type other than "see" or "ant" will
        # be ignored.
        #FIXME: what is meaning of above comment regarding 'compat'?
        # No such variable/parameter any more.
        #FIXME: xrefs that are neither "see" or "ant" should not be
        # ignored when (the missing) 'compat' parameter is None.
        #
        # xrslvs -- List of unresolved xrefs as Xrslv objects.
        # src -- Corpus id number of the entry that contains 'xref'.
        #   If 'src' is true, enhanced XML will be generated.
        #   If not, legacy JMdict XML will be generated.

        fmt = []
        for x in xrslvs:
            v = []; elname = "xref"
            if src:
                attrs = ' type="%s"' % KW.XREF[x.typ].kw
                  # FIXME: Can't generate seq and corp attributes because
                  #  that info is not available from Xrslv objects. See
                  #  IS-150.
            else:
                if x.typ == KW.XREF['see'].id: elname = 'xref'
                elif x.typ == KW.XREF['ant'].id: elname = 'ant'
                else: continue
                attrs = ''
            if getattr (x, 'ktxt',  None): v.append (x.ktxt)
            if getattr (x, 'rtxt',  None): v.append (x.rtxt)
            if getattr (x, 'tsens', None): v.append (str(x.tsens))
            xreftxt = '\u30FB'.join (v)        # U+30FB is middot.
            fmt.append ("<%s%s>%s</%s>" % (elname, attrs, xreftxt, elname))
        return fmt

def info (entr, compat, geninfo, genhists):
        if compat or not geninfo: return []
        fmt = []
        x = getattr (entr, 'srcnote', None)
        if x: fmt.append ('<srcnote>%s</srcnote>' % esc(entr.srcnote))
        x = getattr (entr, 'notes', None)
        if x: fmt.append ('<notes>%s</notes>' % esc(entr.notes))
        if genhists:
            for n, x in enumerate (getattr (entr, '_hist', [])):
                fmt.extend (audit (x, compat))
        if fmt:
            fmt.insert (0, '<info>')
            fmt.append ('</info>')
        return fmt

def audit (h, compat=None):
        if compat: return []  # Generate <audit> elements only for "jmex".
        fmt = []
        fmt.append ('<audit>')
        dt = h.dt.isoformat (' ', 'seconds')
        fmt.append ('<upd_date>%s</upd_date>' % dt)
        if h.notes: fmt.append ('<upd_detl>%s</upd_detl>'   % esc(h.notes))
        if h.stat:  fmt.append ('<upd_stat>%s</upd_stat>'   % KW.STAT[h.stat].kw)
        if h.unap:  fmt.append ('<upd_unap/>')
        if h.email: fmt.append ('<upd_email>%s</upd_email>' % esc(h.email))
        if h.name:  fmt.append ('<upd_name>%s</upd_name>'   % esc(h.name))
        if h.refs:  fmt.append ('<upd_refs>%s</upd_refs>'   % esc(h.refs))
        if h.diff:  fmt.append ('<upd_diff>%s</upd_diff>'   % esc(h.diff))
        fmt.append ('</audit>')
        return fmt

def grps (entr):
        fmt = []
        for x in getattr (entr, '_grp', []):
            ord = (' ord="%d"' % x.ord) if x.ord is not None else ''
            fmt.append ('<group%s>%s</group>' % (ord, KW.GRP[x.kw].kw))
        return fmt

def grpdef (kwgrp_obj):
        fmt = []
        fmt.append ('<grpdef id="%d">' % kwgrp_obj.id)
        fmt.append ('<gd_name>%s</gd_name>' % kwgrp_obj.kw)
        fmt.append ('<gd_descr>%s</gd_descr>' % kwgrp_obj.descr)
        fmt.append ('</grpdef>')
        return fmt

def audio (entr_or_rdng):
        a = getattr (entr_or_rdng, '_snd', [])
        if not a: return []
        return ['<audio clipid="c%d"/>' % x.snd for x in a]

def entrhdr (entr, compat=None):
        if not compat:
            id = getattr (entr, 'id', None)
            idattr = (' id="%d"' % id) if id else ""
            stat = getattr (entr, 'stat', None)
            statattr = (' stat="%s"' % KW.STAT[stat].kw) if stat else ""
            apprattr = ' appr="n"' if entr.unap else ""
            dfrm = getattr (entr, 'dfrm', None)
            dfrmattr = (' dfrm="%d"' % entr.dfrm) if dfrm else ""
            fmt = ["<entry%s%s%s%s>" % (idattr, statattr, apprattr, dfrmattr)]
        else: fmt = ['<entry>']
        if getattr (entr, 'src', None) and not compat:
            src = jdb.KW.SRC[entr.src].kw
            srctid = jdb.KW.SRC[entr.src].srct
            srct = jdb.KW.SRCT[srctid].kw
            fmt.append ('<ent_corp type="%s">%s</ent_corp>' % (srct,src))
        if getattr (entr, 'seq', None):
            fmt.append ('<ent_seq>%d</ent_seq>' % entr.seq)
        return fmt

def sndvols (vols):
        if not vols: return []
        fmt = []
        for v in vols:
            idstr = ' id="v%s"' % str (v.id)
            fmt.append ('<avol%s>' % idstr)
            if v.loc:   fmt.append ('<av_loc>%s</av_loc>'     % v.loc)
            if v.type:  fmt.append ('<av_type>%s</av_type>'   % v.type)
            if v.title: fmt.append ('<av_title>%s</av_title>' % v.title)
            if v.idstr: fmt.append ('<av_idstr>%s</av_idstr>' % v.idstr)
            if v.corp:  fmt.append ('<av_corpus>%s</av_corpus>' % v.corp)
            if v.notes: fmt.append ('<av_notes>%s</av_notes>' % v.notes)
            fmt.append ('</avol>')
        return fmt

def sndsels (sels):
        if not sels: return []
        fmt = []
        for s in sels:
            idstr = ' id="s%s"' % str (s.id)
            volstr = ' vol="v%s"' % str (s.vol)
            fmt.append ('<asel%s%s>' % (idstr, volstr))
            if s.loc:   fmt.append ('<as_loc>%s</as_loc>'     % s.loc)
            if s.type:  fmt.append ('<as_type>%s</as_type>'   % s.type)
            if s.title: fmt.append ('<as_title>%s</as_title>' % s.title)
            if s.notes: fmt.append ('<as_notes>%s</as_notes>' % s.notes)
            fmt.append ('</asel>')
        return fmt

def sndclips (clips):
        if not clips: return []
        fmt = []
        for c in clips:
            idstr = ' id="c%s"' % str (c.id)
            selstr = ' sel="s%s"' % str (c.file)
            fmt.append ('<aclip%s%s>' % (idstr,selstr))
            if c.strt:  fmt.append ('<ac_strt>%s</ac_strt>'   % c.strt)
            if c.leng:  fmt.append ('<ac_leng>%s</ac_leng>'   % c.leng)
            if c.trns:  fmt.append ('<ac_trns>%s</ac_trns>'   % c.trns)
            if c.notes: fmt.append ('<ac_notes>%s</ac_notes>' % c.notes)
            fmt.append ('</aclip>')
        return fmt

def corpus (corpora):
        KW = jdb.KW;  fmt = []
        for c in corpora:
            s = KW.SRC[c]
            fmt.append ('<corpus id="%d">' % s.id)
            fmt.append ('<co_name>%s</co_name>' % s.kw)
            if s.descr:
                fmt.append ('<co_descr>%s</co_descr>' % esc(KW.SRC[c].descr))
            if s.dt:
                fmt.append ('<co_date>%s</co_date>'   % KW.SRC[c].dt)
            if s.notes:
                fmt.append ('<co_notes>%s</co_notes>' % esc(KW.SRC[c].notes))
            if s.seq:
                fmt.append ('<co_sname>%s</co_sname>' % esc(KW.SRC[c].seq))
            if s.sinc:
                fmt.append ('<co_sinc>%d</co_sinc>'   % KW.SRC[c].sinc)
            if s.smin:
                fmt.append ('<co_smin>%d</co_smin>'   % KW.SRC[c].smin)
            if s.smax:
                fmt.append ('<co_smax>%d</co_smax>'   % KW.SRC[c].smax)
            fmt.append ('</corpus>')
        return fmt


def entr_diff (eold, enew, n=2):
        # Returns a text string of the unified diff between the xml for
        # the entries 'eold' and 'enew'.  'eold' and/or 'enew' can be
        # either Entr objects or XML strings of Entr objects.
        # 'n' is the number of context lines to be output in the diff
        # (equivalent to the 'n' value in the unix command, "diff -Un ...".

        if isinstance (eold, str): eoldxml = eold.splitlines(False)
        else: eoldxml = entr (eold, wantlist=1)
        if isinstance (enew, str): enewxml = enew.splitlines(False)
        else: enewxml = entr (enew, wantlist=1)
          # Generate diff and remove trailing whitespace, including newlines.
          # Also, skip the <entry> line since they will always differ.
        rawdiff = difflib.unified_diff (eoldxml, enewxml, n=n)
        diffs = [x.rstrip() for x in rawdiff
                 if not (x[1:].startswith ('<entry')
                         or x.startswith ('@@ -1 +1 @@')) ]
          # Remove the intial "---", "+++" lines.
        if len(diffs) >= 2: diffs = diffs[2:]
        diffstr = '\n'.join (diffs)
        return diffstr

def get_dtd (kwds, dtd, grouped=True):
        '''-------------------------------------------------------------------
        kwds -- An initialized jdb.Kwds instance.
        dtd -- DTD type: "jmdict' or "jmnedict".
        grouped -- (bool) If true, entity definitions in the returned DTD
          will be grouped by element; if false they will be in alphabetic
          order.
        -------------------------------------------------------------------'''
        ents = entities (kwds, dtd, grouped)
        fname = "dtd-%s.xml" % dtd
        path = os.path.join (jdb.std_csv_dir(), fname)
        with open (path) as f: txt = f.read()
        txt = txt.replace ('<!-- {{entities}} -->', ents)
        return txt

def _main():
        import sys
        if len (sys.argv) not in (2,3):
            sys.exit ("Usage:\n  python3 fmtxml.py id# [compat]")
        dbname = 'jmdict'
        if len (sys.argv) == 3: compat = sys.argv[2]
        id = int(sys.argv[1])
        cur = jdb.dbOpen (dbname)
        e, raw = jdb.entrList (cur, [id], ret_tuple=True)
        if not e: sys.exit ("Entry id %d not found" % id)
        jdb.augment_xrefs (cur, raw['xref'])
        txt = entr (e[0], compat=compat)
        print (txt)

  # Assuming you are cd'd to jmdictdb/ when running this, you will
  # need to run like:
  #   PYTHONPATH='..' python3 -mpdb fmtxml.py
  # to make sure the local modules are imported.
if __name__ == '__main__': _main()
