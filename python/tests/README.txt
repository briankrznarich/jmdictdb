==============
Notes on tests
==============
Although these tests use the Python "unittest" testing framework,
they are for the most part functional or integration tests, not
unit tests.   There are a large number of units and many have
relatively complex behavior; there are not enough development
resources available to do the analysis and creation of mock objects
required for "pure" unit tests.

The testing infrastructure code is in this directory, the test
modules in tests/, data for the tests in data/.

Running tests
=============
Although the tests can be run directly by the Python unittest module
command line interface, e.g:
  python3 -m unittest tests/test_*.py
or
  cd python/tests; python3 -m unittest discover -s tests

a test runner program, runtests.py, was written that provides more
control of the tests run and the results format than the unittest
module does (or did, when runtests.py was written.)

The command (run in python/tests/):

  ./runtests.py 

will run all tests.  To run a specific test or set of tests, specify
them as 'module name' (always prefixed with "tests."), 'class' and
'test',  Examples:

  ./runtests.py tests.test_jelparse
  ./runtests.py tests.test_jelparse.Roundtrip
  ./runtests.py tests.test_jelparse.Roundtrip.test1000290

Multiple test arguments can be given.  To debug test failures:

  python3 -mpdb runtests.py -d [tests...]

This will start the test under the Python debugger (type 'c' to start
running) and will stop at the first error or failure allowing the use 
of pdb to diagnose the problem.

For more details on argument syntax: ./runtest.py --help

Test construction
=================
In the test methods in the test modules, "_" is often used instead
of the conventional "self" as the name of the first parameter for
brevity.

The test methods often call a helper function to do the grunt work.
These functions typically called with the test case object as the
first argument (since they often need access to the .assert* methods
of the test case object).  These have exactly the same form as they
would if they were test case methods but using them as functions
allows them to be called from multiple test case classes.  This seems
simpler than the alternative of a hierarchy of test case subclasses
possibly with multiple inheritance mixins.

Because most tests do not adhere to unit testing principles, isolation
between tests is not a high priority.  Consequently, caching is used
extensively to avoid time consuming operations such as database creation.
Database connections and things like JEL parser instances are created
once per test runner execution and rused for multiple tests.

An important data object is jdb.KW, a collection of static keyword
tables usualy initialized by jdb.dbOpen().  Because this is a module
global it retains state between execution of test modules.  It is
critical that any test module that will reference it call jdb.dbOpen()
or DBmanager.use() in at least in a setUpModule() function if not in
test case or test setUp() functions.  In particular making those calls
outside of any function will have the effect of executing them at test
module import time and should any other test (even in a different test
module) change the contents, all following tests (that don't call
jdb.dbOpen()/DBmanager at run time) will see the changes too.

If a test module code references other files (data files or modules to
import) references should be relative to the python/tests/ directory,
not the python/tests/tests/ directory the test module are in.

Test databases
==============
Prior to rev git-190508-02d9fdb the JMdictDB tests used the live "jmdict"
database (loaded from the EDRDG jmdict XML file) as a source for test data.
This was an unfortuate choice made when the tests were first implemented
based on the erroneous assumption that most existing entries were stable
and unlikely to change frequently.  In fact, entries are constantly being
edited resulting in the need to constantly revise tests to keep up.

The static test database was developed by identifying the entries used
in the live tests (plus some additional ones that provide xref targets)
and extracting them from a recent jmdict XML file, loading them into a
new, empty JMdictDB database, from which a loadable copy was produced
using Postgresql's pg_dump tool.  The process was:

    # Extact the entries listed in jmtest01.seq from a full jmdict XML file.
    #  and save them as jmtest01.xml in the tests/ directory.
  $ tools/jmextract.py data/jmdict-190430.xml \
     -s python/tests/data/jmtest01.seq >python/tests/data/jmtest01.xml
  $ cp python/tests/data/jmdict.xml data/jmdict.xml
    # Create a "jmnew" database from the test data xml file.
  $ make jmnew
  $ make loadjm     # Loads jmdict.xml into new database "jmnew"
  $ make postload
    # Dump the "jmnew" database containing the test data so it can
    #  be reloaded later on demand when running tests.
  $ pg_dump -d jmnew >python/tests/data/jmtest01.sql
    # Drop the old "jmtest01" so that the new one will be loaded
    # next time the tests are run.
  $ dropdb jmtest01
    # Run the tests.  The first time they are run, they should reload
    # the test database from the new jmtest01.sql file.
  $ cd python/tests && python3 runtests.py

python/tests/data/data/jmtest01.seq is the list of entry sequence numbers
that was determined to be needed be the test codes.

Updating test databases
=======================
When new tests are added it is sometimes necessary to add new new
test entries to the test database(s).  Additionally, if the JMdictDB
database schema is updated to a new version, the test database must
be updated to match.

Maintenance on the test database can be performed on the test database
using the usual Postgresql tools.

To update the schema of a test database file, load it into a database,
apply the updates, then save it:

  $ dropdb --if-exists jmtemp
  $ createdb -O jmdictdb jmtemp
  $ psql -d jmtemp -f python/tests/data/test01.sql
  $ psql -d jmtemp -f patches/nnn-xxxxxx.sql
  $ pg_dump -d jmtemp > python/tests/data/test01.sql

While it is loaded, changes can be made using the JMdictDB web pages
if a service has been set up in config.ini to allow access to the test
database.
