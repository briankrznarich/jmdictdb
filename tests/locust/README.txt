This directory contains test programs and modules useful with Locust,
a web load-testing framework (https://pypi.org/project/locust/).
The test code in here is less interested in load testing (athough
the load test metrics presented by Locust are interesting) as using
Locust to test for correct behavior of the JMdictDB web backend under
conditions of high concurrency.  All actions of the test programs are
performed by sending http requests to a JMdictDB web server and screen-
scraping the returned pages to determine if the expected response was
received.

Test programs:
  test-submit.py -- Creates a number of users submitting edits and
    editors approving or rejecting them.  Detects and handles (by
     recusively rejecting) conficting edit branches.
  test-loginout.py -- Creates users that view pages while logging
    in and out of various editor id's.  Tests for correct behavior
    with multiple simultaneous logins and logouts.

Support modules:
  behaviors.py -- Functions that implement user behavior for the test
    programs.
  lib.py -- Support functions used by behaviors.py and the test programs.

There are several functions useful for debugging:
  lib.view (page) --Given a parsed web page such as returned by
    lib.JMconn.get_doc(), this will display the page in a web browser.
  lib.prt (page) -- Given a parsed web page such as returned by
    lib.JMconn.get_doc(), this will convert the page back to HTML
    and print it.
  behaviors.treset() -- Resets the terminal settings when a program
    running under Locust hits a pdb breakpoint.  Locust changes the
    terminal settings, disabling echo among other things making pdb
    hard to use.  This function can be called manually (albiet by
    typing blindly) to restore normal terminal functioning.
  behaviors.brk() -- Can use this as an alternative to pdb.set_trace()
    to add a breakpoint call that will call treset().
