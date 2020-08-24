#!/usr/bin/env python3
# Copyright (c) 2008 Stuart McGraw
# SPDX-License-Identifier: GPL-2.0-or-later

# Run all or a subset of the JMdictDB tests.
# Run with "--help" option for information on command line
# arguments and options.

import sys, unittest, glob, pdb
import unittest_extensions
  # Adjust sys.path so that the parent directory of this script's
  # directory (which contains the the jmdictdb package we want to
  # test) appears before any system or user library directories
  # which may also contain jmdictdb packages but which we don't
  # want to import.)
_ = sys.path
if '..' not in _[0]: _[:0] = [_[0] + ('/' if _[0] else '') + '..']

def main (args, opts):
          # Following raises an exception if wrong jmdictdb pkg was imported.
        chk_import ('jmdictdb', '..')
        suites = []
        testsdir = "tests"
        if not args:
            test_file_pattern = testsdir+('/' if testsdir else '')+"test_*.py"
            test_files = glob.glob (test_file_pattern)
            for filename in test_files:
                args.append ((filename[:-3]).replace('/', '.'))

        for testset in args:
            if '/' in testset:
                testset = testset.replace('./', '')
                testset = testset.replace('/', '.')
                if testset.endswith ('.py'): testset = testset[:-3]
            elif not testset.startswith ('tests.'):
                testset = 'tests.'+testset
            s = unittest.defaultTestLoader.loadTestsFromName (testset)
            s.name = testset
            suites.append (s)

        if opts.list: listtests (suites, opts.list.lower()[0])
        else:
            problems = runtests (suites, opts)
            if problems and opts.output:
                print ('Some tests failed, details in file "%s".' % opts.output)

def runtests (suites, opts):
        problems = 0
        if opts.output: outf = open (opts.output, "w")
        else: outf = None
        if opts.verbosity == 1: summary = False
        else: summary = True
        for suite in suites:
            if opts.debug:
                suite.debug(); continue
            runner = unittest_extensions.TextTestRunner (
                stream=sys.stdout, dstream=outf,
                verbosity=opts.verbosity, summary=summary)
            results = runner.run (suite)
            if not results.wasSuccessful(): problems += 1
        return problems

def listtests (obj, sumtyp):
        from collections import defaultdict
        if sumtyp == 't': collect=None
        else: collect = defaultdict (lambda: defaultdict (int))
        scantests (obj, collect)
        if collect is not None:
            for m,v in list(collect.items()):
                if sumtyp == 'm':
                    print ("%s (%d classes, %d tests)" \
                           % (m, len(v), sum (v.values())))
                else:
                    for c,n in list(v.items()):
                        print ("%s.%s (%d tests)" % (m, c, n))

def scantests (obj, collect):
        if isinstance (obj, unittest.TestCase):
            if collect is None: print (obj.id())
            else:
                modnm, clsnm, testnm = obj.id().rsplit ('.', maxsplit=2)
                collect[modnm][clsnm] += 1
        elif isinstance (obj, unittest.TestSuite):
            for s in obj._tests: scantests (s, collect)
        elif hasattr (obj, '__iter__'):
            for s in obj: scantests (s, collect)
        else:
            print ("Unexpected object found: %s" % repr (obj), file=sys.stderr)
            sys.exit (1)

def chk_import (package, relpos):
        ''' Verify that the imported 'jmdictdb' package is from a
            sibling directory of that in which our calling script
            (runtests.py) is located.  This assures we are testing
            code from the development directory and not from any
            system- or user-installed jmdictdb packages. '''
        import os.path as p
          # I've no idea what it means or what to do if there are
          # zero or mutiple items the package's .__path__ which
          # apparently there can be.
        libpath = p.normpath (p.abspath ((__import__ (package)).__path__[0]))
        ourpath =  p.dirname (p.abspath (globals()['__file__']))
        libexpected = p.normpath (p.join (ourpath, relpos, 'jmdictdb'))
        if libpath != libexpected:
             msg = "Wrong library was imported\n" \
                   "  expected '%s'\n"\
                   "  got '%s'"
             raise RuntimeError (msg % (libexpected, libpath))

from optparse import OptionParser

def parse_cmdline ():
        u = \
"""\n\t%prog [testcase [testcase [...]]]

  %prog will run all (by default) or selected tests.

Arguments:
  tests         Specific test(s) to run.  TESTS has the form
                module[.class[.method]].  If "method" is not given,
                all the tests in the class will be run.  If "class"
                is not not given, all the tests in all the classes
                in the module will be run.  Tests are assumed to be
                located in subdirectory "tests/", e.g.,
                   test_jelparser.Xrefs.test011
                will run Xref.test011 from tests/test_jelparser.py.
                To run tests located somewhere other than tests/
                include a path containing a "/" character:
                   ./xtest_jmparse
                The filename may optionally include a ".py" suffix
                but in that case an individual class and test cannot
                be given.

                If no arguments are given, all tests in modules with
                names matching the pattern, "tests.test_*" (i.e. python
                files in subdirectory "tests/" matching "test_*.py")
                will be run."""

        p = OptionParser (usage=u)
        p.add_option ("-o", "--output", metavar="FILENAME",
            help="""Write details of test failures and errors to
                FILENAME.  If not given details will be written
                to stderr along with the test progress and summary
                information.""")
        p.add_option ("-v", "--verbosity", default=1,
            type="int", metavar="INT",
            help="""0: no test progress display, 1: single line
                test progress display, 2: multiline test progress
                display.""")
        p.add_option ("-l", "--list", default=None, metavar="WHAT",
            help="""List tests that would be run, but don't actually
                run them.  WHAT is one of "tests", "classes", or
                "modules".  "tests" lists all test cases.  "classes"
                lists all test classes and the number of test cases
                in each.  "modules" lists all test modules and the
                numbers of classes and test cases in each.
                WHAT can be abbreviated to the first character. """)
        p.add_option ("-d", "--debug", default=False, action="store_true",
            help="""Run tests in debug mode.  In this mode exceptions
                will not be caught by unittest.  If runtests.py is
                also started with the pdb debugger (e.g., with the
                "-mpdb" python option), pdb will be started on the
                exception.  This will occur with *any* exception
                including SkipTest so generally you will want to
                specify a single test in the runtests.py arguments.""")
        opts, args = p.parse_args ()
        if opts.verbosity not in (0,1,2):
            p.error ('Bad "verbosity" option value %s, must be 0, 1, or 2.')
        return args, opts

if __name__ == '__main__':
        args, opts = parse_cmdline ()
        main (args, opts)
