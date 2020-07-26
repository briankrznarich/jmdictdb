import sys, unittest, pdb
from jmdictdb import jdb; from jmdictdb.objects import *
  # Module to test...
from jmdictdb import jmxml

KW = None

class Test_parse_jmdict (unittest.TestCase):
    def setUp (_):
        global KW
        if not KW:
            jdb.KW = KW = jdb.Kwds ('')
          # Use mode='b' in getxml call because we need undecoded
          # utf-8 for Jmparser.parse_entry() (which gives it to
          # ElementTree which needs utf-8.)
        _.getxml = lambda testid: getxml ('data/jmxml/parse_entry.xml',
                                          testid, 'b')
        _.jmparser = jmxml.Jmparser (KW)

    def dotest (_, testid):
        global _test_expect
        xml, exp = _.getxml (testid)
        entrs = _.jmparser.parse_entry (xml)
        exec ("_test_expect=" + exp, globals())
        _.assertEqual (entrs, _test_expect)
        return entrs, _test_expect

    def test_000010(_): _.dotest ('000010')
    def test_000020(_): _.dotest ('000020')
    def test_000030(_): _.dotest ('000030')
    def test_000040(_): _.dotest ('000040')
    def test_000050(_): _.dotest ('000050')
    def test_000060(_): _.dotest ('000060')  # rinf
    def test_000070(_): _.dotest ('000070')  # kinf
    def test_000080(_): _.dotest ('000080')  # restr
    def test_000210(_): _.dotest ('000210')  # pos propagation
    def test_3001010(_): _.dotest ('3001010')  # entities: dial
    def test_3001020(_): _.dotest ('3001020')  # entities: fld
    def test_3001030(_): _.dotest ('3001030')  # entities: kinf
    def test_3001040(_): _.dotest ('3001040')  # entities: misc
    def test_3001050(_): _.dotest ('3001050')  # entities: pos
    def test_3001060(_): _.dotest ('3001060')  # entities: rinf
    def test_1499230(_):_.dotest ('1499230') # restr/nokanji

    # To do: restr combos, freq, pos, misc, fld, dial, lsrc, stagr,
    #   stagk, xrslv, gloss (lang, ginf), hist, grp
    #   jmnedict: name_type and others
    #   kanjdic: cinf, chr, krslv
    #   jmdict-ex stuff.

class Test_jmnedict (unittest.TestCase):
    def setUp (_):
        global KW
        if not KW:
            jdb.KW = KW = jdb.Kwds ('')
          # Re mode='b', see comment in Test_parse_jmdict() above.
        _.getxml = lambda testid: getxml ('data/jmxml/jmnedict.xml',
                                          testid, 'b')
        _.jmparser = jmxml.Jmparser (KW)

    def dotest (_, testid):
        global _test_expect
        xml, exp = _.getxml (testid)
        entrs = _.jmparser.parse_entry (xml)
        exec ("_test_expect=" + exp, globals())
        _.assertEqual (entrs, _test_expect)
        return entrs, _test_expect

    def test_01_5001081(_): _.dotest ('5001081')
    def test_02_5485055(_): _.dotest ('5485055')
    def test_03_5478094(_): _.dotest ('5478094')
    def test_04_5389819(_): _.dotest ('5389819')
    def test_05_5259233(_): _.dotest ('5259233')

def getxml (fname, testid, mode=''):
        # Read and return test data from a file.  The file may contain
        # multiple sets of test data and contents should be utf-8.
        # encoded.  Each set of test data starts with a line like,
        # "## xxxxx" where "xxxxx" is an arbitrary testid string.
        # Following that are lines containing XML for an entry.
        # The XML is followed by a line starting with "##--", and that
        # is followed by Python code to created an Entr object equal to
        # what is expected from parsing the XML.  The python code must
        # start with "expect =" since it will be exec'd and the test code
        # will look for a variable named "expect".  The Python code may
        # be followed by another test data section of the end of the file.
        # Throughout the test data file, blank lines and lines
        # starting with a hash and a space, "# ", (comment line) are
        # ignored.
        # This function returns a two-tuple of test data (xml and python
        # code) for the test data identified by 'testid'.  The first item
        # is either a bytes object with the undecoded XML text if mode was
        # 'b', or decoded XML text string is mode was not 'b'.  The second
        # item is always a decoded text string containing the Python code
        # part of the test data set.
        # If the requested test data set is not found, an Error is raised.

        with open (fname, 'r'+mode) as f:
            state = '';  xml = [];  exp = []
            for lnnum, raw in enumerate (f):
                  # In Py2 'raw' is undecoded utf-8.  We need to decode
                  # it (in principle) to detect the testid lines.  If
                  # mode is 'b', we'll collect and return utf-8 lines.
                  # Otherwise, collect and return decoded unicode lines.
                if mode == 'b': ln = raw.decode ('utf-8').strip()
                else: ln = raw
                if not ln: continue                  # Skip blank lines.
                if (len(ln)==1 and ln.startswith ("#")) or ln.startswith ("# "):
                    continue                         # Skip comment lines.
                #print ("%d %s: %s" % (lnnum, state, ln))
                if ln == "## %s" % testid:           # Start of our test section.
                    state = "copying1"; continue
                if ln.startswith ("## "):            # Start of next section.
                    if state.startswith('copying'): break
                if ln.startswith ("##--"):           # Start of exec section.
                    if state == "copying1":
                        state = "copying2"; continue
                if state == "copying1":
                    xml.append (raw)
                if state == "copying2":
                    exp.append (ln)
            if not xml: raise RuntimeError ('Test section "%s" not found in %s'
                                            % (testid, fname))
            expstr = '\n'.join (exp) + '\n'
            if mode == 'b':
                return b''.join (xml), expstr
            return ('\n'.join (xml) + '\n'), expstr

if __name__ == '__main__': unittest.main()





