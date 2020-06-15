# Test JEL parsing of Restr, Stagk and Stagr restrictions.

# These tests replace the tests formerly in tests_jelparse.Restr.  Those
# worked by parsing test JEL text entries, formatting the resulting Entr
# objects back into JEL and comparing that with the original JEL text.
# The tests herein forgo the conversion back into JEL and check the
# restriction lists on the Entr objects directly.  This excludes issues
# arising in the JEL formatter but consequently no longer provides testing
# for those issue and could also miss remotely possible side-effects on
# the Entr object outside the scope the restriction lists.

import sys, unittest, pdb
import jmdb     # For JelParser
from jmdictdb import jdb; from jmdictdb.objects import *
from jmdictdb.jelparse import ParseError

  # Functions for defining expected restriction results concisely.
  # If the second argument is not given, the corresponding Restr (or
  # (Stagk or Stagr) value will compared against None.  The restriction
  # objects produced by the JEL parser will usually have these values
  # set to None (as opposed to those read from a database which will
  # have integer values.)  See check() below for reason for using dict's
  # the reference data.
def RK(k, r=None): return {'kanj':k, 'rdng':r};
def SK(k, s=None): return {'kanj':k, 'sens':s};
def SR(r, s=None): return {'rdng':r, 'sens':s};
# 亜井卯絵小  # あいうえお

# When adding new tests check the fmtjel tests to see if a similar test
# is also appropriate there.

#=============================================================================
class KRrestrs (unittest.TestCase):
  # When adding tests here, consider adding them to SKrestrs and SRrestrs
  # as well.
#=============================================================================
    # No spontaneous generation of rk restrictions :-)
  def test0010110(_): rk(_, '亜;井;卯', 'あ;い',           [[], []])
    # Basic 3Kx2R combinations.
  def test0010210(_): rk(_, '亜;井;卯', 'あ[亜];い',       [[RK(2),RK(3)], []])
  def test0010220(_): rk(_, '亜;井;卯', 'あ[井];い',       [[RK(1),RK(3)], []])
  def test0010230(_): rk(_, '亜;井;卯', 'あ[卯];い',       [[RK(1),RK(2)], []])
  def test0010240(_): rk(_, '亜;井;卯', 'あ[亜、井];い',    [[RK(3)], []])
  def test0010250(_): rk(_, '亜;井;卯', 'あ[亜、卯];い',    [[RK(2)], []])
  def test0010252(_): rk(_, '亜;井;卯', 'あ[卯、亜];い',    [[RK(2)], []])
  def test0010260(_): rk(_, '亜;井;卯', 'あ[井、卯];い',    [[RK(1)], []])
  def test0010270(_): rk(_, '亜;井;卯', 'あ[亜、井、卯];い', [[], []])
  def test0010272(_): rk(_, '亜;井;卯', 'あ[卯、亜、井];い', [[], []])
  def test0010280(_): rk(_, '亜;井;卯', 'あ[nokanji];い',  [[RK(1),RK(2),RK(3)], []])

  def test0010310(_): rk(_, '亜;井;卯', 'あ;い[亜]',       [[], [RK(2),RK(3)]])
  def test0010320(_): rk(_, '亜;井;卯', 'あ;い[井]',       [[], [RK(1),RK(3)]])
  def test0010330(_): rk(_, '亜;井;卯', 'あ;い[卯]',       [[], [RK(1),RK(2)]])
  def test0010340(_): rk(_, '亜;井;卯', 'あ;い[亜、井]',    [[], [RK(3)]])
  def test0010350(_): rk(_, '亜;井;卯', 'あ;い[亜、卯]',    [[], [RK(2)]])
  def test0010360(_): rk(_, '亜;井;卯', 'あ;い[井、卯]',    [[], [RK(1)]])
  def test0010370(_): rk(_, '亜;井;卯', 'あ;い[亜、井、卯]', [[], []])
  def test0010380(_): rk(_, '亜;井;卯', 'あ;い[nokanji]',  [[], [RK(1),RK(2),RK(3)]])

  def test0010410(_): rk(_, '亜;井;卯', 'あ[卯];い[亜、卯]', [[RK(1),RK(2)], [RK(2)]])
  def test0010420(_): rk(_, '亜;井;卯', 'あ[卯、亜];い[亜]', [[RK(2)], [RK(2),RK(3)]])

    # Alternate syntactical forms.
  def test0010510(_): rk(_, '亜;井;卯', 'あ[亜,卯]',              [[RK(2)]])   # Ascii comma.
  def test0010520(_): rk(_, '亜;井;卯', 'あ[亜][卯]',             [[RK(2)]])   # Separate tags.
  def test0010530(_): rk(_, '亜;井;卯', 'あ[restr=亜;卯]',        [[RK(2)]])   # Ascii semicolon.
  def test0010540(_): rk(_, '亜;井;卯', 'あ[restr=亜；卯]',        [[RK(2)]])  # JP semicolon.
  def test0010550(_): rk(_, '亜;井;卯', 'あ[restr=亜,restr=卯]',  [[RK(2)]])
  def test0010560(_): rk(_, '亜;井;卯', 'あ[restr=亜][restr=卯]', [[RK(2)]])
  def test0010570(_): rk(_, '亜;井;卯', 'あ[restr=nokanji]',     [[RK(1),RK(2),RK(3)]])

  def test0010610(_): rk(_, '亜;井;卯', 'あ[亜,亜]',              [[RK(2),RK(3)]])   # Duplicates ignored.

  def test0010710(_): rk(_, '亜;井;卯・う', 'あ["卯・う"]',        [[RK(1),RK(2)]])    # Quoted middot.
  def test0010711(_): rk(_, '一人一人;１人１人', 'ひとりびとり["１人１人"]', [[RK(1)]])   # c.f. jmdict-q1612530

    # Failures
  def test0020110(_): rkf(_, '亜;井;卯', 'あ[絵]',    KeyError, "Restriction target.*not found")
  def test0020120(_): rkf(_, '亜;井;卯', 'あ[井、絵]', KeyError, "Restriction target.*not found")
  def test0020530(_): rkf(_, '亜;井;卯', 'あ[亜;卯]', ParseError, "Syntax Error") # Semicolon separator.
  def test0020710(_): rkf(_, '亜;井;卯・う', 'あ[卯・う]', ParseError, "Syntax Error")  # unquoted "・"; c.f. 0010710.

#=============================================================================
class SKrestrs (unittest.TestCase):
  # We duplicate most of the rk tests here because sk/sr-restrictions
  # use a different code path in the JEL parser than the rk-restrictions.
#=============================================================================
    # No spontaneous generation of sk restrictions :-)
  def test0010110(_): sk(_, '亜;井;卯', '[1]x [2]x',           [[], []])
    # Basic 3K[1]x2S combinations.
  def test0010210(_): sk(_, '亜;井;卯', '[1]x[亜] [2]x',       [[SK(2),SK(3)], []])
  def test0010220(_): sk(_, '亜;井;卯', '[1]x[井] [2]x',       [[SK(1),SK(3)], []])
  def test0010230(_): sk(_, '亜;井;卯', '[1]x[卯] [2]x',       [[SK(1),SK(2)], []])
  def test0010240(_): sk(_, '亜;井;卯', '[1]x[亜、井] [2]x',    [[SK(3)], []])
  def test0010250(_): sk(_, '亜;井;卯', '[1]x[亜、卯] [2]x',    [[SK(2)], []])
  def test0010252(_): sk(_, '亜;井;卯', '[1]x[卯、亜] [2]x',    [[SK(2)], []])
  def test0010260(_): sk(_, '亜;井;卯', '[1]x[井、卯] [2]x',    [[SK(1)], []])
  def test0010270(_): sk(_, '亜;井;卯', '[1]x[亜、井、卯] [2]x', [[], []])
  def test0010272(_): sk(_, '亜;井;卯', '[1]x[卯、亜、井] [2]x', [[], []])

  def test0010310(_): sk(_, '亜;井;卯', '[1]x [2]x[亜]',        [[], [SK(2),SK(3)]])
  def test0010320(_): sk(_, '亜;井;卯', '[1]x [2]x[井]',        [[], [SK(1),SK(3)]])
  def test0010330(_): sk(_, '亜;井;卯', '[1]x [2]x[卯]',        [[], [SK(1),SK(2)]])
  def test0010340(_): sk(_, '亜;井;卯', '[1]x [2]x[亜、井]',     [[], [SK(3)]])
  def test0010350(_): sk(_, '亜;井;卯', '[1]x [2]x[亜、卯]',     [[], [SK(2)]])
  def test0010360(_): sk(_, '亜;井;卯', '[1]x [2]x[井、卯]',     [[], [SK(1)]])
  def test0010370(_): sk(_, '亜;井;卯', '[1]x [2]x[亜、井、卯]',  [[], []])

  def test0010410(_): sk(_, '亜;井;卯', '[1]x[卯] [2]x[亜、卯]', [[SK(1),SK(2)], [SK(2)]])
  def test0010420(_): sk(_, '亜;井;卯', '[1]x[卯、亜] [2]x[亜]', [[SK(2)], [SK(2),SK(3)]])

    # Alternate syntactical forms.
  def test0010510(_): sk(_, '亜;井;卯', '[1]x[亜,卯]',              [[SK(2)]])   # Ascii comma.
  def test0010520(_): sk(_, '亜;井;卯', '[1]x[亜][卯]',             [[SK(2)]])   # Separate tags.
  def test0010530(_): sk(_, '亜;井;卯', '[1]x[restr=亜;卯]',        [[SK(2)]])   # Ascii semicolon.
  def test0010540(_): sk(_, '亜;井;卯', '[1]x[restr=亜；卯]',        [[SK(2)]])  # JP semicolon.
  def test0010550(_): sk(_, '亜;井;卯', '[1]x[restr=亜,restr=卯]',  [[SK(2)]])
  def test0010560(_): sk(_, '亜;井;卯', '[1]x[restr=亜][restr=卯]', [[SK(2)]])
      # Position of restr(s) relative to gloss doesnt matter.
  def test0010570(_): sk(_, '亜;井;卯', '[1][井]x',       [[SK(1),SK(3)]])  # c.f. 0010220
  def test0010571(_): sk(_, '亜;井;卯', '[1][restr=井]x', [[SK(1),SK(3)]])  # c.f. 0010220
  def test0010572(_): sk(_, '亜;井;卯', '[1][亜]x[卯]',   [[SK(2)]])       # c.f. 0010250
  def test0010573(_): sk(_, '亜;井;卯', '[1][亜,卯]x',    [[SK(2)]])       # c.f. 0010250
  def test0010574(_): sk(_, '亜;井;卯', '[1][卯]x;y[亜]', [[SK(2)]])       # c.f. 0010250

  def test0010610(_): sk(_, '亜;井;卯', '[1]x[亜,亜]',    [[SK(2),SK(3)]])   # Duplicates ignored.

  def test0010710(_): sk(_, '亜;井;卯・う', '[1]x["卯・う"]', [[SK(1),SK(2)]])    # Quoted middot.

    # Failures
  def test0020110(_): skf(_, '亜;井;卯', '[1]x[絵]',      KeyError, "Restriction target.*not found")
  def test0020120(_): skf(_, '亜;井;卯', '[1]x[井、絵]',   KeyError, "Restriction target.*not found")
  def test0020530(_): skf(_, '亜;井;卯', '[1]x[亜;卯]',    ParseError, "Syntax Error")
      # rk-restr tag "nokanji' not recognised in stagk, stagr restrs.
  def test0020540(_): skf(_, '亜;井;卯', '[1]x[nokanji]',  KeyError, 'Restriction target.*nokanji.*not found')
  def test0020710(_): skf(_, '亜;井;卯・う', '[1]x[卯・う]', ParseError, "Syntax Error")  # unquoted "・"; c.f. 0010710.

#=============================================================================
class SRrestrs (unittest.TestCase):
  # We duplicate most of the rk tests here because sk/sr-restrictions
  # use a different code path in the JEL parser than the rk-restrictions.
#=============================================================================
    # No spontaneous generation of sk restrictions :-)
  def test0010110(_): sr(_, 'あ;い;う', '[1]x [2]x',           [[], []])
    # Basic 3K[1]x2S combinations.
  def test0010210(_): sr(_, 'あ;い;う', '[1]x[あ] [2]x',       [[SR(2),SR(3)], []])
  def test0010220(_): sr(_, 'あ;い;う', '[1]x[い] [2]x',       [[SR(1),SR(3)], []])
  def test0010230(_): sr(_, 'あ;い;う', '[1]x[う] [2]x',       [[SR(1),SR(2)], []])
  def test0010240(_): sr(_, 'あ;い;う', '[1]x[あ、い] [2]x',    [[SR(3)], []])
  def test0010250(_): sr(_, 'あ;い;う', '[1]x[あ、う] [2]x',    [[SR(2)], []])
  def test0010252(_): sr(_, 'あ;い;う', '[1]x[う、あ] [2]x',    [[SR(2)], []])
  def test0010260(_): sr(_, 'あ;い;う', '[1]x[い、う] [2]x',    [[SR(1)], []])
  def test0010270(_): sr(_, 'あ;い;う', '[1]x[あ、い、う] [2]x', [[], []])
  def test0010272(_): sr(_, 'あ;い;う', '[1]x[う、あ、い] [2]x', [[], []])

  def test0010310(_): sr(_, 'あ;い;う', '[1]x [2]x[あ]',        [[], [SR(2),SR(3)]])
  def test0010320(_): sr(_, 'あ;い;う', '[1]x [2]x[い]',        [[], [SR(1),SR(3)]])
  def test0010330(_): sr(_, 'あ;い;う', '[1]x [2]x[う]',        [[], [SR(1),SR(2)]])
  def test0010340(_): sr(_, 'あ;い;う', '[1]x [2]x[あ、い]',     [[], [SR(3)]])
  def test0010350(_): sr(_, 'あ;い;う', '[1]x [2]x[あ、う]',     [[], [SR(2)]])
  def test0010360(_): sr(_, 'あ;い;う', '[1]x [2]x[い、う]',     [[], [SR(1)]])
  def test0010370(_): sr(_, 'あ;い;う', '[1]x [2]x[あ、い、う]',  [[], []])

  def test0010410(_): sr(_, 'あ;い;う', '[1]x[う] [2]x[あ、う]', [[SR(1),SR(2)], [SR(2)]])
  def test0010420(_): sr(_, 'あ;い;う', '[1]x[う、あ] [2]x[あ]', [[SR(2)], [SR(2),SR(3)]])

    # Alternate syntactical forms.
  def test0010510(_): sr(_, 'あ;い;う', '[1]x[あ,う]',              [[SR(2)]])   # Ascii comma.
  def test0010520(_): sr(_, 'あ;い;う', '[1]x[あ][う]',             [[SR(2)]])   # Separate tags.
  def test0010530(_): sr(_, 'あ;い;う', '[1]x[restr=あ;う]',        [[SR(2)]])   # Ascii semicolon.
  def test0010540(_): sr(_, 'あ;い;う', '[1]x[restr=あ；う]',        [[SR(2)]])  # JP semicolon.
  def test0010550(_): sr(_, 'あ;い;う', '[1]x[restr=あ,restr=う]',  [[SR(2)]])
  def test0010560(_): sr(_, 'あ;い;う', '[1]x[restr=あ][restr=う]', [[SR(2)]])
      # Position of restr(s) relative to gloss doesnt matter.
  def test0010570(_): sr(_, 'あ;い;う', '[1][い]x',       [[SR(1),SR(3)]])  # c.f. 0010220
  def test0010571(_): sr(_, 'あ;い;う', '[1][restr=い]x', [[SR(1),SR(3)]])  # c.f. 0010220
  def test0010572(_): sr(_, 'あ;い;う', '[1][あ]x[う]',   [[SR(2)]])       # c.f. 0010250
  def test0010573(_): sr(_, 'あ;い;う', '[1][あ,う]x',    [[SR(2)]])       # c.f. 0010250
  def test0010574(_): sr(_, 'あ;い;う', '[1][う]x;y[あ]', [[SR(2)]])       # c.f. 0010250

  def test0010610(_): sr(_, 'あ;い;う', '[1]x[あ,あ]',    [[SR(2),SR(3)]])   # Duplicates ignored.

  def test0010710(_): sr(_, 'あ;い;う・う', '[1]あ["う・う"]',  [[SR(1),SR(2)]])    # Quoted middot.

    # Failures
  def test0020110(_): srf(_, 'あ;い;う', '[1]x[ん]',      KeyError, "Restriction target.*not found")
  def test0020120(_): srf(_, 'あ;い;う', '[1]x[い、ん]',   KeyError, "Restriction target.*not found")
  def test0020530(_): srf(_, 'あ;い;う', '[1]x[あ;う]',    ParseError, "Syntax Error")
      # rk-restr tag "nokanji' not recognised in stagk, stagr restrs.
  def test0020540(_): srf(_, 'あ;い;う', '[1]x[nokanji]',  KeyError, 'Restriction target.*nokanji.*not found')
  def test0020710(_): srf(_, 'あ;い;う・う', '[1]x[卯・う]', ParseError, "Syntax Error")  # unquoted "・"; c.f. 0010710.

#=============================================================================

class Issues (unittest.TestCase):
  # These are tests ported from the former test_jelparse.Restr tests that
  # address specific previous issues.

    # See IS-26; c.f. entry jmdict.2529240
    # restr tag to a middot kanji.
  def test0300280(_): rk(_, '・；中ポツ', 'なかぽつ["・"]；なかポツ', [[RK(2)],[]])

    # See IS-222; c.f. entry jmdict.1436570
    # U+3006 (IDEOGRAPHIC CLOSING MARK) should be kanji.
  def test0300290(_): sk(_, '締める；〆る；緊める',
                            '[1][v1][restr=締める; 〆る] to total', [[SK(3)],])

    # See IS-248; the "nokanji" tag without kanji in entry should
    #  produce a parse error.
  def test9000010(_): rkf(_, '', 'アルバイト[nokanji]', ParseError,
                          "Reading 1 has 'nokanji' tag but entry has no kanji")

#=============================================================================

  # The following six functions are called from within the tests and
  # check the JEL parser for rk, sk and sr restrictions.  The versions
  # suffixed with "f" check for failures that raise exceptions.
  # Each accepts the two parts of a JEL entry that participate in the
  # restriction.  They are passed to tojel() which makes the full jel
  # text for an entry which then is parsed, the appropriate restriction
  # list extracted and compared to the expected values.  The parsing
  # and checking happen in check().
  # Note the 'expect' argument should be a list of 'n' items where 'n'
  # is the length of the second ('r' or 's') argument of the function.
  # Each item in the list is an empty list or a list of RK(), SK() or
  # SR() values of the number needed to match the expected restriction
  # objects in the Rdng._restr, Sens._stagk or Sens._stagr restriction
  # list.

def rk (_, k, r, expect): check (_, tojel(r=r,k=k), expect, 'rk')
def rkf (_, k, r, excp, regex):
         _.assertRaisesRegex (excp, regex, JELparser.parse, tojel(r=r,k=k), resolve=False)
def sk (_, k, s, expect): check (_, tojel(s=s,k=k), expect, 'sk')
def skf (_, k, s, excp, regex):
        _.assertRaisesRegex (excp, regex, JELparser.parse, tojel(s=s,k=k), resolve=False)
def sr (_, r, s, expect): check (_, tojel(s=s,r=r), expect, 'sr')
def srf (_, r, s, excp, regex):
        _.assertRaisesRegex (excp, regex, JELparser.parse, tojel(s=s,r=r), resolve=False)

  # Turn two restriction parts into a complete, parsable JEL entry.
def tojel (r='', k='', s='[1]x'): return "%s\f%s\f%s" % (k, r, s)

def check (_, jeltext, expect, typ):
    # Parse the JEL entry 'jeltext' and check that the appropriate
    # restriction lists determined by 'typ' match the expected values
    # given in 'expect'.  'typ' must be one of "rk", "sk" or "sr"
    # depending of whether restr, stagk or stagr restrictions are
    # being checked.  'expect' is a list of lists.  Each list in
    # 'expect' corresponds to each reading (if 'typ' is "rk") or
    # sense (if 'typ' is "sk" or 'sr") in the entry, and is a list
    # of values returned by RK(), SK() or SR() functions (see above)
    # that are matched against the Restr, Stagk or Stagr instances
    # in the selected restriction list.
        eattr, name, rattr \
           = {'rk':('_rdng','readings', '_restr'),
              'sk':('_sens',  'senses', '_stagk'),
              'sr':('_sens',  'senses', '_stagr'),
              }[typ]
        entr = JELparser.parse (jeltext, resolve=False)
          # There must be one expect item for each reading or sense
          # (depending on 'typ') in the entry.
        if len (expect) != len(getattr (entr, eattr)):
            raise ValueError ("test data error: %s %s but %s expect items"
                            % (len (getattr(entr,eattr)), name, len (expect),))
        rlists = [getattr(r,rattr) for r in getattr(entr,eattr)]
          # Check that we have the expected number of restriction lists.
        len_err = []
        if len (rlists) != len (expect):
            len_err.append ("expected %s restr lists but got %s"
                            % (len (expect), len (rlists)))
        for restrs, exp in zip (rlists, expect):
            cmp (_, restrs, exp)

def cmp (_, restrs, expect):
    # Compare a list of restriction (Restr, Stagk, Stagr) instances, 'restrs',
    # with reference data given in 'expect', a list of dicts of the same length
    # as 'restrs'.  The value of each key in those dicts will will be compared
    # with the value of the same-named attribute of the corresponding restriction
    # instance.  The use of dicts for the reference data allows ignoring
    # restriction instance attributes whose value we don't care about.

        if len (restrs) != len (expect):
            len_err.append ("expected %s restr lists but got %s"
                            % (len (expect), len (restrs)))
        results = {}
        for rs, exp in zip (restrs, expect):
            for k,ve in exp.items():
                    v = getattr (rs, k)
                    if v != ve: results[k] = (v, ve)
        _.assertFalse (results)

JELparser = None

def setUpModule():
        global JELparser
        JELparser = jmdb.JelParser()
          # We don't need access to a database but the JEL parser needs
          # access to a populated KW object, so we create and initialize
          # it directly from the data csv files.  The given path to them
          # is relative to python/tests/.
        jdb.KW = jdb.Kwds ("../../pg/data/")

def main(): unittest.main()

if __name__ == '__main__': unittest.main()
