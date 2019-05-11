Notes on tests

Although these tests use the Python "unittest" testing framework,
they are for the most part functional or integration tests, not
unit tests.   There are a large number of units and many have
relatively complex behavior; there are not enough development
resources available to do the analysis and creation of mock objects
required for "pure" unit tests.

The testing infrastructure code in in this directory, the test
modules in tests/, data for the tests in data/.

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

An import data object is jdb.KW, a collection of static keyword tables
initialized by jdb.dbOpen().  Because this is a module global it retains
state between execution of test modules.  It is therefore critical that
any test module that will reference it call jdb.dbOpen() or DBmanager.use()
in at least in a setUpModule() function if not in test case or test setUp()
functions.  In particular making those calls outside of any function will
have the effect of executing them at test module import time and should
any other test (even in a different test module) change the contents,
all following tests (that don't call jdb.dbOpen()/DBmanager at run time)
will see the changes too.
