#-------------------------------------------------------------------
# The following functions deal with restriction lists.
#-------------------------------------------------------------------

# Restrictions are used to to indicate certain pairs of readings and
# kanji, senses and readings or senses and kanji are linguistically
# disallowed.  In a JMdictDB database they are implemented as rows in
# the tables "restr" (reading-kanji pairs), "stagr" (sense-reading
# pairs) and "stagk" (sense-kanji pair).  Each of those tables has a
# foreign key that identifies the first member of the pair (a particular
# "rdng" table row for example), and another foreign key that identifies
# the other member of the pair (a particular "kanj" table row).
#
# In code they are implemented in the Entr object structure as lists
# of Restr, Stagr and Stagk objects that are referenced by Rdng._restr,
# Sens._stagr, and Sens._stagk.  Each Restr, Stagr or Stagk object is
# an image of a row (actual or potential) from the corresponding database
# table ("restr", "stagr" or "stagk".  The foreign key values that identify
# the "primary" member of the restriction pair, that is, the item that the
# restriction object is attached to, are generally ignored in code since
# that relationship is indicated by the presence of the restriction object
# on the primary object.  For example we don't pay much attention to the
# Restr.entr or Restr.rdng values because a Restr object's presence in a
# particular Rdng._restr list is sufficient to say what those values
# effectively are (they are effectively Rdng.entr and Rdng.rdng regardless
# of the values actually in Restr.entr and Restr.rdng).
#
# The "other" member of the restriction pair (which we'll call the
# target) *is* identified solely by a numeric value in the restriction
# object (e.g. '.kanj' in a Restr object.)  In the database and in
# restriction objects read from the database, the target attribute
# value in the restriction object will match the attribute value of
# the same name in the target: a restriction object Restr(kanji=2)
# will usually find a Kanj(kanj=2) at Entr._kanj[1] (index [1] is
# position 2 counting when counting from 1).  However, the above while
# usual is not guaranteed; under some circumstances the N values used
# in Kanj(kanj=N) may not be sequenial.  What is guaranteed is that
# Restr(kanj=N) refers to some Kanj(kanj=N) somewhere in the Entr._kanj
# list.
#
# Additionally, when Entr objects are constructed in code it is
# often more convenient not to have to have to set the N values
# in Kanj(kanj=N) and rather just assume that the Kanj object at
# position N in the Entr._kanj list whose .kanj value remains
# None (the default) has an implied .kanj=N value.
#
# To satisfy both the above we find the the target of a restriction
# object with .kanj=N using this algorithm:
#   1. Look at Entr._kanj[N-1].  If it has a .kanj value of None
#      or N, choose it as the the restriction target.
#   2. Otherwise, interate through the Entr._kanj list lookin for
#      a Kanj object with .kanj=N which is choosen as the target.
#   3. If no such Kanj object is found, raise a KeyError.
# The above algorithm can easily give wrong results if some Kanj
# objects in Entr._kanj have explicit .kanj=N values and some are
# None.  Don't do that. :-)
# All the above applies equally with the appropriate substitutions
# for Stagr restrictions that reference Rdng objects in the Entr._rdng
# list.
#
# Finally note that restriction objects identify *disallowed*
# pairings; this is in contrast to the use of restrictions in the
# JMdict XML (the <re_restr>, <stagr> and <stagk> tags) and those
# shown in display output which give the *allowed* pairings.

from .objects import *

def get_restrs (restrs, targs):
        '''
        Given 'restrs', a list of restriction objects (Restr, Stagr or
        Stagk) that specify disallowed pairings of items (Rdng/Kanj,
        Sens/Rdng or Sens/Kanj for Restr, Stagr, or Stagk restrictions
        respectively), and 'targs', a list of the restriction targets
        (Rdng or Kanj objects depending on the type of the objects in
        'restrs'), return a list of the 'targs' that are not in the
        restriction list (that is, the target items that constitute
        allowed pairings.)  However, if 'restrs' is empty, return an
        empty list (an empty "allowed" list means all pairings are
        allowed).  If every item in the 'targs' list is disallowed
        return None.  For the case of Restr restrictions, this corresponds
        to the <re_nokanji> case in the JMdict XML.
        '''

        if not restrs: return []
          # Get the name of the restriction items' "other" attribute.
        _, attr, _ = restr_info (restrs[0])
        if len(restrs) > len(targs):
              # This should be impossible unless something got really messed up.
            raise ValueError ("jdb.restr: len('restrs') greater "
                              "than len('targs')")
        disallowed = set()
        for r in restrs:
              # 'restr_targ_pos()' finds the item in 'targs' that matches the
              # restriction object 'r' (see comments in restr_targ_pos() for
              # meaning of "match") and returns its base-1 index in 'targs'.
            disallowed.add (restr_targ_pos (getattr (r, attr), targs))
        if len(disallowed) == len(targs): return None
        allowed = [x for n,x in enumerate(targs,start=1)
                     if n not in disallowed]
        return allowed

def restr_targ_pos (tnum, targs):
        '''
        Locate a target Rdng or Kanj object identified by a number,
        'tnum', in a list of such objects and return its (base-1)
        index in the list.
        Parameters:
          tnum -- An integer giving either:
            - the base-1 position of 'targ' in 'targs', or
            - the key value of the looked for target.
          targs -- A list of Rdng or Kanj instances.
        Returns:
          The position (base-1 index) of the object in 'targs' that
          matches 'tnum'.  The matching object is identified by:
          1. If the 'tnum'th item's attr value is None or is equal
             to 'tnum' it matches; return 'tnum'.
          2. Otherwise iterate through the 'targs' list and return
             the (base-1) index of the first object whose attr value
             is equal to 'tnum'.
        '''
        attr = (type(targs[0]).__name__).lower()
        if tnum <= len(targs):
            p = getattr (targs[tnum-1], attr)
            if not p or p == tnum: return tnum
        for i,item in enumerate (targs, start=1):
            if tnum == getattr (item, attr): return i
        raise KeyError (
            "Restriction target number %s not found"
            % tnum)

def restr_info (obj1, obj2=None):
        '''
        Given either a pair of objects between which a restriction can
        be placed (eg Rdng/Kanj, Sens/Rdng, Sens/Kanj) or a single restriction
        object (Restr, Stagr or Stagk), return a 3-tuple of information
        that is useful processing those restrictions:
          0 -- Class of restriction object
          1 -- Name of attribute that identifies the "other" member of the
               restriction pair (ie the item to which the restriction object
               is not attached).
          3 -- Name of attribute holding the restriction list on the object
               that the restriction object is attached to.
        '''
        t1 = type(obj1).__name__
        if obj2:
            t2 = type(obj2).__name__
            t1 = {('Rdng','Kanj'): 'Restr',
                  ('Sens','Rdng'): 'Stagr',
                  ('Sens','Kanj'): 'Stagk'}[(t1,t2)]
        return {'Restr': (Restr, 'kanj', '_restr'),
                'Stagr': (Stagr, 'rdng', '_stagr'),
                'Stagk': (Stagk, 'kanj', '_stagk'),}[t1]


def restrs2txts (rdng, kanjs, attr='_restr'):
        # Given a Rdng object and a list of Kanj objects from the
        # same entry, return a list of text strings that give the
        # allowed kanji for the reading as determined by the Rdng's
        # ._restr list.
        # This is similar to restrs2ext but returns a list of text
        # strings rather than a list of Kanj objects.

        return [x.txt for x in get_restrs (getattr (rdng, attr, []), kanjs)]

  #FIXME: fix modules using either of the following two functions
  # function to standardize on one of them and remove the other.
def restrs2ext (rdng, kanjs, attr='_restr'):
        restrs = getattr (rdng, attr, [])
        return restrs2ext_ (restrs, kanjs, attr)

def restrs2ext_ (restrs, kanjs, attr='_restr'):
        # Given a list of Restr objects, 'restrs', create a list Kanj
        # objects taken from 'kanjs' such that each Kanj object's
        # ._restr list contains no Restr objects in 'restrs'.  However,
        # if 'restrs' is an empty list, return an empty list.  And if
        # every Kanj object in 'kanjs' has a ._restr list item that
        # in in 'restrs', return None.  Note that common membership
        # of a Restr object in the 'restrs', and kanj._restr lists
        # constitutes a restriction -- the values of the attributes
        # of the Restr objects ('.rdng', .kanj', etc) are ignored.
        #
        # This function can be used in generating restr text when
        # displaying an entry in JMdict XML, JEL, or similar textual
        # output from jdb entry objects.  A return value [] indicates
        # there are no restr's, a return of None indicates "nokanji",
        # and a list of kanji are the "restr" kanji for the reading
        # 'restrs' is from.
        #
        # Although parameter names assume reading-kanji restrictions
        # defined in 'rdng._restr", this function can be used for
        # stagr or stagk restrictions by supplying a Sens object
        # and list of Rdng or Kanj objects respectively for 'rdng'
        # and 'kanj', and setting 'attr' to "_stagr" or "stagk"
        # respectively.
        #
        # restr -- A list of Restr objects on a Rdng (or Sens) object.
        # kanjs -- A list of Kanj (or Rdng) objects.
        # attr -- Name of the attribute on the 'rdng' and 'kanj' object(s)
        #   that contains the restriction list, one of: "_restr", "_stagr",
        #   "_stagk".

        return get_restrs (restrs, kanjs)

def txt2restr (restrtxts, rdng, kanjs, attr=None, bad=None):
        # Converts a list of text strings, 'restrtxts', that give allowed
        # combinations (external form) into a list of Restr objects that
        # that give disallowed combinations (internal form) and sets the
        # value of the attribute named by 'attr' on 'rdng' to that list.
        #
        # restrtxts -- List of texts (that occur in kanjs) of allowed
        #   restrictions.  However, if 'restrtxts' is empty, there
        #   are no restrictions (all 'kanjs' items are ok.)  If
        #   'restrtxts' is None, every 'kanjs' item is disallowed.
        # kanjs -- List of Kanj (or Rdng) objects.
        # attr -- ignored.
        # bad -- ignored.
        # Returns: A list of ints giving the 1-based indexes of the
        #  kanji objects matching the restr list set on 'rdng'.

          # Check that all the restrtxts match a kanjs.
        ktxts = [x.txt for x in kanjs]
        if restrtxts is not None:
            for x in restrtxts:
                if x not in ktxts:
                    if bad is not None: bad.append (x)
                    else: raise KeyError (
                      'Restriction target text "%s" not found' % x)
        restrs = []; nkanjs = []
        if restrtxts != []:
            cls, attr, lst = restr_info (rdng, kanjs[0])
            for n,k in enumerate (kanjs, start=1):
                if restrtxts is None or k.txt not in restrtxts:
                    ro = new_restrobj (cls, attr, n, kanjs)
                    getattr(rdng, lst).append (ro)
                    nkanjs.append (n)
        return nkanjs

def new_restrobj (cls, attr, n, targs):
        tn = getattr (targs[n-1], attr)
        if tn is not None and tn != n:
            for t in targs:
                if getattr (t, attr) == n: break
            else: raise KeyError ("Restriction target %s not found" % n)
        restr = cls();  setattr (restr, attr, n)
        return restr

def restr_expand (entr):
        # Return an iterator over the valid (taking restrictions into
        # account) reading/kanji pairs.
        for nr, r in enumerate (entr._rdng, start=1):
            disallowed = set()
            for ro in r._restr:
                disallowed.add (restr_targ_pos (getattr (ro, 'kanj'),
                                                entr._kanj))
            for nk, k in enumerate (entr._kanj, start=1):
                if nk in disallowed: continue
                yield nr-1, nk-1     # Yield base-0 indices.
