# Test JEL parsing and resolution of xrefs.
# Resolution is done against a static test database.
# These tests are interim until the development "xrslv" branch is merged,
# after which these tests can be divided into two sets: jel parsing, and
# resolution.  Until then these combined tests should pass in both xrslv
# and non-xrslv branches.

import sys, os, re, unittest, signal, pdb
if '../lib' not in sys.path: sys.path.append ('../lib')
import jdb; from objects import *
import jmdb
from jmdb import DBmanager
__unittest = 1

from jelparse import ParseError

def generate_tests (cls, func, data):
    # Add test case methods to the class 'cls' dynamically, one for
    # each item in list 'data'.  Each added method is named "test<nnn>"
    # where <nnn> is the value of data[n][0] padded with 0 to 3 digits.
    # 'func' is a function that is curried with positional arguments
    # assigned from data[n][1:].
    # Using subtests is an alternate way of achieving something similar
    # but separate tests can be run individually, and they report indivdual
    # success or failure, which we find preferable.  (Subtests report only
    # success of the single encompassing test).
    # Tried using using functools.partialmethod() rather than lambda
    # here but that produced extraneous
    #   partial(...) - new function with partial application
    # messages I couldn't figure out how to get rid of (functools docs
    # are pretty opaque.)
        for row in data:
            testfunc = lambda x: func(x, *row[1:])
            setattr (cls, 'test%03d' % row[0], testfunc)

  # These two functions create and return dict objects that define the
  # reference data to which the test data is compared.  Only Xref/Xrslv
  # attributes corresponding to keys in these dicts are compared.
  # See cmp() for more details.
def X (typ,sens,xref, xentr, xsens, r=None, k=None):
        return dict (typ=typ, sens=sens, xref=xref, xentr=xentr, xsens=xsens, rdng=r, kanj=k)
def V (typ,sens,ord, r=None, k=None, tsens=None, vsrc=None, vseq=None, msg=None):
        x = dict (typ=typ, sens=sens, ord=ord, rtxt=r, ktxt=k, tsens=tsens)
        if msg: x['msg'] = msg
        return x

#===== Tests =================================================================

class Xrefs (unittest.TestCase):
    Tests = [
      # The following data is used by generate_tests() to dynamically
      # add test methods to this class.  Each row consists of four
      # items:
      #   test number: The added tests will be named "testnn" where
      #     "nn" is this number.
      #   jel xref: A string specifying an xref in JEL format.  It
      #     will be added to the JEL for a dummy entry and then
      #     parsed by the JEL parser and resolved.
      #   The remaining two items may be either:
      #     xrefs: A list of Xref objects that are expected to be
      #       found on the Entr object returned by the JEL parser.
      #       The function X provides a concise way to define these.
      #     vrefs: A list of Xrslv objects that are expected to be
      #        found on the Entr object returned by the JEL parser.
      #        These represent xrefs that could not be resolved.
      #        The function V provides a concise way to define these.
      #   or:
      #     xrefs: An Exception class object or subclass thereof
      #        that the JEL parser is expected to raise.
      #     vrefs: A regex string that is expected to match the
      #        raised exception rendered as a string.  May be
      #        None to skip this check.

          # Basic lookup by kanji:
        (11, "[see=会う]",          [X(3,None,None, 35,1,k=1), X(3,None,None, 35,2,k=1)], []),
        (12, "[see=会う[1]]",       [X(3,None,None, 35,1,k=1)], []),
        (13, "[see=会う[2]]",       [X(3,None,None, 35,2,k=1)], []),
        (14, "[see=会う[1,2]]",     [X(3,None,None, 35,1,k=1), X(3,None,None, 35,2,k=1)], []),
            #FIXME? xrefs for multiple senses are not necessarily
            # returned in same order given in jel.
        (15, "[see=大文字[2,3]]",   [X(3,None,None, 46,2,k=1), X(3,None,None, 46,3,k=1)], []),
        (16, "[see=大文字[3,2]]",   [X(3,None,None, 46,2,k=1), X(3,None,None, 46,3,k=1)], []),

          # Basic lookup by reading:
        (21, "[see=あう]",          [X(3,None,None, 35,1,r=1), X(3,None,None, 35,2,r=1)], []),
        (23, "[see=あう[2]]",       [X(3,None,None, 35,2,r=1)], []),
        (24, "[see=おおもじ[2,4]]",  [X(3,None,None, 46,2,r=1),X(3,None,None, 46,4,r=1)], []),
        (25, "[see=だいもんじ[1,4]]", [X(3,None,None, 46,1,r=2),X(3,None,None, 46,4,r=2)], []),

          # Basic lookup by kanji and reading:
        (31, "[see=会う・あう]",      [X(3,None,None, 35,1,k=1,r=1), X(3,None,None, 35,2,k=1,r=1)], []),
        (32, "[see=会う・あう[2]]",   [X(3,None,None, 35,2,k=1,r=1)],[]),
        (33, "[see=甘子・あまご]",    [X(3,None,None, 5,1,k=1,r=1)],[]),
        (34, "[see=雨子・あまご]",    [X(3,None,None, 5,1,k=3,r=1)],[]),
        (35, "[see=天魚・アマゴ]",    [X(3,None,None, 5,1,k=2,r=2)],[]),

          # Sense number related failures:
        (41, "[see=会う[3]]",       [], [V(3,None,None,k='会う', msg="Sense 3 not in target")]),
        (42, "[see=会う[0]]",       ParseError, "Invalid sense number"),
        (43, "[see=会う[1,3]]",     [], [V(3,None,None,k='会う', msg="Sense 3 not in target")]),
        (44, "[see=会う[3,1]]",     [], [V(3,None,None,k='会う', msg="Sense 3 not in target")]),
        (45, "[see=会う[3,4]]",     [], [V(3,None,None,k='会う', msg="Sense 3 not in target")]),
        (46, "[see=会う[4,3]]",     [], [V(3,None,None,k='会う', msg="Sense 4 not in target")]),

          # Target not found failures:
        (50, "[see=会会]",          [], [V(3,None,None,k='会会', msg="No entry found")]),
        (51, "[see=ゑゑ]",          [], [V(3,None,None,r='ゑゑ', msg="No entry found")]),

          # Multiple matches:
        (61, "[see=何の]",          [], [V(3,None,None,k='何の', msg="Multiple entries found")]),
          # Targets with same kanji disambiguated by reading or seq#:
        (64, "[see=何の・なんの]",   [X(3,None,None, 64,1,r=1,k=1)], []),
        (65, "[see=何の・どの]",     [X(3,None,None, 63,1,r=1,k=1)], []),

          # Seq numbers:
        (71, "[see=1920240・何の]",         [X(3,None,None, 63,1,k=1)], []),
        (72, "[see=1920240・どの]",         [X(3,None,None, 63,1,r=1)], []),
        (73, "[see=1920240・何の・どの]",    [X(3,None,None, 63,1,k=1,r=1)], []),
        (74, "[see=1920240・何の・どの[1]]", [X(3,None,None, 63,1,k=1,r=1)], []),
        (75, "[see=1920240・何の・なんの]",   [],[V(3,None,None,k='何の',r='なんの',msg="No entry found")]),

          # Xref types:
        (81, "[syn=漫才]",         [X(1,None,None, 59,1,k=1)], []),
        (82, "[ant=漫才]",         [X(2,None,None, 59,1,k=1)], []),
        (83, "[see=漫才]",         [X(3,None,None, 59,1,k=1)], []),
        (84, "[cf=漫才]",          [X(4,None,None, 59,1,k=1)], []),
        (85, "[ex=漫才]",          [X(5,None,None, 59,1,k=1)], []),
        (86, "[uses=漫才]",        [X(6,None,None, 59,1,k=1)], []),

          # Quotes and middots:
        (101, "[see=ドアマン]",       [X(3,None,None, 29,1,r=1)], []),
        (102, '[see="ドアマン"]',     [X(3,None,None, 29,1,r=1)], []),
            #FIXME? raise in jelparse because 'ドア' is not kanji?
        (103, '[see=ドア・マン]',      [], [V(3,None,None,r='マン',k='ドア', msg="No entry found")]),
        (104, '[see="ドア・マン"]',    [X(3,None,None, 29,1,r=2)], []),
        (105, '[see="ドア・マン"[1]]', [X(3,None,None, 29,1,r=2)], []),

          # Todo: xrefs to deleted/rejected fail (is-203),
          #  ambiguous lookups to non-first kanji/reading,
        ]
    # Test methods are dynamically added to this class by the
    # generate_tests() call below.

class Issues (unittest.TestCase):
      # IS-203/Can add xref to rejected entry.
      # IS-245/Edited entry has resolvable xref shown as unresolved
    def test0010(_):    
        jel = '\fＸ\f[1] test [see=2833900]'
          # Xrefs should be generated to the A and two A* entries in q2833900
          # but not to the D* (id=107) or R (id=109) entries.
        check (_, jel, [X(3,None,None,104,1,k=1,r=1),
                        X(3,None,None,105,1,k=1,r=1),
                        X(3,None,None,106,1,k=1,r=1)], [])
    def test0020(_):
        jel = '\fＸ\f[1] test [see=2833910]'
          #FIXME? q2833910 is a single deleted entry, correctly no xrefs
          # are generated but an unresolved xref is -- without any kanji
          # or reading, since none were given.  Is this behavior useful?
        check (_, jel, [], [V(3,None,None)])
    def test0030(_):
        jel = '\fＸ\f[1] test [see=2833920]'
          #FIXME? same as test0020 above but with rejected rather than
          # deleted entry.
        check (_, jel, [], [V(3,None,None)])

#===== Create dynamically added tests ========================================

  # Template for test methods to add to class Xrefs.
def test_tmpl (_, jelref, xrefs_ex, vrefs_ex):
        # Template function for creating test methods for class Xrefs.
          # Add the xref tag given in 'jelref' to a dummy JEL entry.
        jeltext = "\fＸ\f[1] test" + jelref
          # check() will call the JEL parser with 'jeltext', and check
          # that either the resulting Xrefs and Xrlvs in the returned
          # Entr object match those expected (given in 'xrefs_ex' and
          # 'vrefs_ex') or, if an exception is raised, it is a 'xrefs_ex'
          # exception and its string representation matched the regex
          # 'vrefs_ex'.
        #print ('%s: %s' % (jelref, len(xrefs_ex)), file=sys.stderr)
        check (_, jeltext, xrefs_ex, vrefs_ex)
  # Dynamically add test methods to class Xrefs.
generate_tests (Xrefs, test_tmpl, Xrefs.Tests)

#===== Support functions =====================================================

def check (_, jeltext, xrefs_ex, vrefs_ex):
           # Dispatch to either chkfail() or chkok() depending if
           # xrefs_ex is an Exception object or not.
        r = xrefs_ex
        if type(r)==type(object) and issubclass (r, Exception):
            chkfail (_, jeltext, xrefs_ex, vrefs_ex)
        else: chkok (_, jeltext, xrefs_ex, vrefs_ex)

def chkok (_, jeltext, xrefs_ex, vrefs_ex):
        #pdb.set_trace()
        entr = JELparser.parse (jeltext, src=1)
        xrefs = entr._sens[0]._xref
        vrefs = entr._sens[0]._xrslv
          # Check that we have the expected number of Xref and Xrslv objects.
        len_err = []
        if len (xrefs) != len (xrefs_ex):
            len_err.append ("expected %s Xref objects but got %s"
                            % (len (xrefs_ex), len (xrefs)))
        if len (vrefs) != len (vrefs_ex):
            len_err.append ("expected %s Vrslv objects but got %s"
                            % (len (vrefs_ex), len (vrefs)))
        if len_err: _.fail (("\n"+' '*16).join (len_err))
          # Compare the xrefs/vrefs to the reference ones.
        for x,e in zip (xrefs, xrefs_ex): cmp (_, x, e)
        for v,e in zip (vrefs, vrefs_ex): cmp (_, v, e)

def chkfail (_, jeltext, excp_class, regex):
        with _.assertRaisesRegex (excp_class, regex):
            entr = JELparser.parse (jeltext, src=1)

def cmp (_, test, expect):
    # Compare an Xref or Xrslv object, 'test', with reference data given
    # in the dict, 'expect'.  The reason for using a dict for the reference
    # data rather than a reference Xref or Xrslv object is comparision
    # is limited to the keys in 'test'.  This allows us to skip checking
    # attributes we don't care about like .entr or .sens.
    # We treat the .msg attribute specially using a regex match rather than
    # equality.  All of the xref/xeslv attributes given in 'expect' are
    # checked before raising an assert error is order to present the caller
    # with a complete comparision.  Differences are shown as a dict with
    # each key giving the attribute having a difference, and its value a
    # 2-tuple of (actual_value, expected_value).

        results = {}
        for k,ve in expect.items():
            if not hasattr (test, k):
                results[k] = "attribute missing"; continue
            if k == 'msg':
                if not re.search (ve, test.msg):
                    retults['msg'] = 'not matched'
            else:
                v = getattr (test, k)
                if v != ve: results[k] = (v, ve)
        _.assertFalse (results,
                       msg="\n  Each key is an attribute name whose value "
                           "was not what was expected.\n  Each value is a "
                           "tuple  of (actual-value, expected-value).")

  # Temporary adjustment for different behavior in git branches.
VERSION = "master"
#VERSION = "xrslv"
  # Following borrowed from the not-yet-merged xrslv branch and modified
  # to use the pre-xrslv-branch xref resolver, jelparse.resolv_xrefs()
  # rather than the xrslv-branch version, jdb.xresolv().
import jellex, jelparse
class JelParser:
        def __init__(self, dbcursor=None,
                           src=None, stat=None, unap=None,
                           debug=False):
              # 'dbcursor' is an open JMdictDB cursor such as returned
              # by jdb.dbOpen() and used when resolving any xrefs in the
              # parsed entry.  It is not required if .parse() wil be
              # called with 'resolve' set to false.
              # 'src', 'stat' and 'unap' are defaults value to use in
              # the Entr objects if values weren't supplid in the JEL
              # text.
              # NOTE: while 'dbcursor' is optional here, jdb.dbOpen()
              # *must* be called prior to executing .parse() since the
              # latter requires the jdb.KW structure to be initialized,
              # which jdb.dbOpen() does.

            self.lexer, tokens = jellex.create_lexer ()
            self.parser = jelparse.create_parser (self.lexer, tokens)
            self.dbcursor, self.src, self.stat, self.unap, self.debug \
              = dbcursor, src, stat, unap, debug
        def parse (self, jeltext, resolve=True, dbcursor=None,
                   src=None, stat=None, unap=None):
            jellex.lexreset (self.lexer, jeltext)
              #FIXME? why do we give the jeltext to both the lexer
              # and the parser?  One of the other should be sufficient.
            entr = self.parser.parse (debug=self.debug)
            if not entr.src: entr.src = src or self.src
            if not entr.stat: entr.stat = stat or self.stat
            if not entr.unap: entr.unap = unap or self.unap
            if resolve:
                if not dbcursor: dbcursor = self.dbcursor
                if not dbcursor: raise RuntimeError (
                    "Xref resolution requested but no database available")
                if VERSION == "xrslv":    jdb.xresolv (dbcursor, entr)
                elif VERSION == "master": jelparse.resolv_xrefs (dbcursor, entr)
            return entr

  # Database name and load file for tests.
DBNAME, DBFILE = "jmtest01", "data/jmtest01.sql"
  # Global variables.
DBcursor = JELparser = None

def setUpModule():
        global DBcursor, JELparser
        DBcursor = DBmanager.use (DBNAME, DBFILE)
        JELparser = JelParser (DBcursor)

def main(): unittest.main()

if __name__ == '__main__': unittest.main()
