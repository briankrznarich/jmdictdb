#!/usr/bin/env python3
#######################################################################
#  This file is part of JMdictDB.
#  Copyright (c) 2008 Stuart McGraw
#
#  JMdictDB is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published
#  by the Free Software Foundation; either version 2 of the License,
#  or (at your option) any later version.
#
#  JMdictDB is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with JMdictDB; if not, write to the Free Software Foundation,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#######################################################################

# Run all or a subset of the JMdictDB tests.
# Run with "--help" option for information on command line
# arguments and options.

import sys, unittest, glob
import unittest_extensions

__unittest = 1

def main (args, opts):
        suites = []
        testsdir = "tests"
        if not args:
            test_file_pattern = testsdir+('/' if testsdir else '')+"test_*.py"
            test_files = glob.glob (test_file_pattern)
            for filename in test_files:
                args.append ((filename[:-3]).replace('/', '.'))

        for testset in args:
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
                modnm, clsnm, testnm = obj.id().split ('.')
                collect[modnm][clsnm] += 1
        elif isinstance (obj, unittest.TestSuite):
            for s in obj._tests: scantests (s, collect)
        elif hasattr (obj, '__iter__'):
            for s in obj: scantests (s, collect)
        else:
            print ("Unexpected object found: %s" % repr (obj), file=sys.stderr)
            sys.exit (1)

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
                in the module will be run.  If the tests are in a
                subdirectory, e.g., "tests", include it:
                   tests.my_test_module.testcase1.test001

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
