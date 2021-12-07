#!/usr/bin/env python3

# This module uses the lxml package (an XML/HTML parser) to interact with
# a JMdictDB server the same way a web browser would, retrieving pages,
# clicking links in them, filling out forms and submitting them.
#
# It is intended to be run two different ways:
# * Directly under Python. This will run the main() fuction which will
#   do one iteration of a create_new_entry(), edit_random_entry(), and
#   dispose_random_entry() cycle using the Requests library to perform
#   the http actions.  It is useful when debugging the functions.
# * Under Locust.  Locust will import this file as a Python module and
#   run a separate script that calls the create_new_entry(), edit_random-
#   _entry(), and dispose_random_entry() in mutiple threads simultaneously
#   to load test a JMdictDB server, or check for proper operation of the
#   server scripts under high-concurrency conditions.
#
# To remove the entries added by these functions, use psql and run:
#   DELETE FROM entr WHERE id IN
#     (SELECT entr FROM hist WHERE name='<SUBMITTER>');
# Replace <SUBMITTER> with actual value from the defintion below.  This
# will delete all entries that have any history records added by <SUBMITTER>.

import sys, os, random, re, time, pdb
import logging;  L = logging.getLogger
import requests, lxml.html
from lib import *

SUBMITTER = "mr. testman"

def create_or_edit (jmconn, distrib, uid=None):
        choices = 'create', 'edita', 'editu'
        action = random.choices (choices, distrib)[0]
        L('test.bhav.cr-ed').debug("[%s] action = %s" % (uid, action))
        if action == 'create':
            create_new_entry (jmconn, uid)
        elif action == 'edita':
            edit_random_entry (jmconn, edappr=True, uid=uid)
        elif action == 'editu':
            edit_random_entry (jmconn, edappr=False, uid=uid)
        else: raise ValueError ("Bad 'action' value: %r" % action)
        return action

def create_new_entry (jmconn, uid=None):
        """===================================================================
        Create a new approved entry.
          1. Get the "New Entry" page.
          2. Fill out the New Entry form with a randomly generated nonsense
             word.  Use SUBMITTER for "Name".
          3. Submit (approve) the entry.
        ==================================================================="""
        u = uid if uid else "j"+hex(id(jmconn))[2:]   # For log messages.

          # 1. Get the "New Entry" page.
          # Also verify that we are already logged in as an editor.
        page = jmconn.get_page ('GET', 'edform.py', params={'svc':'jmdict'})
        #if not logged_in (page): raise NotLoggedInError()

          # 2. Fill out the New Entry form.
          # Enter some randomish data for the new entry and click the
          # "Next" button; we should get the "Confirmation" page back.
        kanj, rdng = fake_word()
        entry = {'src': 'jmdict',
                 'kanj':kanj, 'rdng':rdng, 'sens':"[1][exp] test entry",
                 'comment':"[%s] create" % u, 'name':SUBMITTER}
        set_fields (page.forms[1], entry)
        page = jmconn.submit_form (page.forms[1], {}, {})
        check_title (page, "Confirm Submission")

          # 3. Submit (approve) the entry.
          # This is the confirmation page.  Since we are logged in, the
          # default submit action is "Approve" and all we need do is click
          # the Submit button (by simply submitting the form.  We expect
          # to get the "Thank You" page back.
        page = jmconn.submit_form (page.forms[1], {}, {})
        eid, q, src = check_thankyou (page)
        msg = "[%s] Created %s %s/%s (%s %s)" % (u,src,q,eid,kanj,rdng)
        L('test.bhav.create').info(msg)
        return 1

def edit_random_entry (jmconn, edappr=None, delete=None, uid=None):
        """===================================================================
        Pick a random entry, edit and submit it.  Candidates are limited
        to those that are active (not deleted or rejected), approved or
        unapproved, and having a comment by created by SUBMITTER.  The
        latter condition limits edit to those entries that we created.
        Since we are  not logged in the entry will be submitted in the
        unapproved state.  The steps are:
          1. Get srchform.
          2. Search for an entry to edit.
          3. Scan the results, pick one at random for editing.
          4. Get the Entry page for it.
          5. Click the Entry page's Edit button to get the Edit page.
          6. Fill out the Edit form and click the Next button.  The
             only changes we make are to add a comment and, with a
             small probability, click the Delete checkbox.  The
             submitter "Name" field is set to SUBMITTER.
          7. On the Confirmation form click the Submit button.
        ==================================================================="""
        u = uid if uid else "j"+hex(id(jmconn))[2:]   # For log messages.

          # 1. Get srchform.
        page = jmconn.get_page ('GET', 'srchform.py')
        if logged_in (page): raise LoggedInError()
        check_title (page, "Advanced Search")

          # 2. Search for entries to edit.
          #
        form_data = {'smtr':SUBMITTER, 'appr':[]}  # Both approved and unappr.
        if edappr is True: form_data['appr'] = ['appr']    # Approved only.
        if edappr is False: form_data['appr'] = ['unappr'] # Unapproved only.
        page = jmconn.submit_form (page.forms[1], form_data,
                                   extra={'search':'Search', 'srchres':'1'})
        check_title (page, "Search results")

          # 3. Find all the results, pick one at random for editing.
          # We look for the results inside the <form action="entr.py">
          # element.  If there is only one page of results this will be
          # the only form (not counting the login/out form) but if there
          # is more than one page, there will be a "next page" form that
          # we don't want to get by mistake since it contains no results.
        xpath = './/div[@class="jmd-content"]/div[@class="item"]'\
                  '/form[@action="entr.py"]'\
                  '//tr[@class="resrow"]/td[@class="seq"]/a'
        links = page.body.findall(xpath)
        msg = "[%s] Found %s search results" % (u,len(links))
        L('test.bhav.edit').debug(msg)
        if len (links) == 0:
            msg = "[%s] No search results, try again later" % u
            L('test.bhav.edit').info(msg)
            return 0
        link = random.choice (links)
        url = link.attrib['href']
        L('test.bhav.edit').debug("[%s] Picked entry to edit: %s" % (u, url))

          # 4. Get the Entry page for it.
        page = jmconn.get_page ('GET', url)
        check_title (page, "Entries")
        src, q, eid, pid, stat = entr_details (page, one_only=True)
        if eid is None:
              # This can happen if someone else edits the entry before we do.
            msg = "[%s] Entry not found: %s" % (u, id_from_url (url))
            L('test.bhav.edit').warn(msg)
            return 0
        msg = "[%s] Editing %s %s/%s[%s]/%s" % (u,src,q,eid,pid,stat)
        L('test.bhav.edit').debug(msg)

          # 5. Click the Edit button to get the Edit page.
        page = jmconn.submit_form (page.forms[1], {}, extra={})
        check_title (page, "Edit Entry")

          # 6. Fill out the Edit form and click the Next button.
        edform = page.forms[1]
          # We don't actually change anything except to add a comment and
          # possibly check the "Delete" box.
        if delete is None: delete = random.random() < 0.15
        if delete:
            fld_delete = edform.find (".//td/input[@name='delete']")
            fld_delete.value = 1
        fld_name = edform.find (".//td/input[@name='name']")
        fld_comment = edform.find (".//td/textarea[@name='comment']")
        fld_name.value = SUBMITTER
        fld_comment.value = "[%s] edit" % u
        page = jmconn.submit_form (edform, {}, {})
        check_title (page, "Confirm Submission")

          # 7. We are now on the Confirmation form.  Submit the entry.
          # Since we are not logged in, the entry will be submitted as
          # unapproved.
        pid = eid   # Save parent id.
        page = jmconn.submit_form (page.forms[1], {}, {})
        eid, q, src = check_thankyou (page)
        msg = "[%s] Submitted %s %s/%s(%s) %s"\
              % (u, src, q, eid, pid, ("delete" if delete else ""))
        L('test.bhav.edit').info(msg)
        return 1

def dispose_random_entry (jmconn, disp=None, uid=None):
          # This is an alias for dispose_entry() that is more descriptive
          # for the case when the caller want to dispose a random entry
          # by not providing a 'url' argument.
        dispose_entry (jmconn, disp=disp, uid=uid)

def dispose_entry (jmconn, url=None, disp=None, uid=None):
        """===================================================================
        Dispose (approve or reject) an unapproved entry.  Steps are:
          1. Find an entry to process.  If 'url' was given, that is the
             entry.  Otherwise:
          1.1. Get the Search form.
          1.2. Fill it out and click the Search button.  Search is for
             unapproved entries having any history record added by SUBMITTER.
          1.3. Pick one of the results at random.
          2. Get the Entry page for 'url' (if given) or the randomly picked
             one (if 'url' not given).
          3. Click the Entry page's Edit button to get the Edit page.
          4. Fill out the Edit form (add a comment, set name to SUBMITTER,
             if no 'disp' parameter values was given, randomly choose
             between "approve" (frequently) and "reject" (infrequently).
             Click the Next button to get the Confirmation form.
          5. On the Confirmation form click the Submit button.
          6. If the result is a Thank You page, the submission was successful
             and we're done.
          7. Otherwise there was an error.  Check the error page and if
             the error was due to conflicting edits, extract the urls of
             the conflicting errors.
          8. Call dispose_entry() recusively to reject each of the conflicting
             edits.
          9. Call dispose_entry() again to dispose of our entry which this
             time should be successful.
        ==================================================================="""
        u = uid if uid else "j"+hex(id(jmconn))[2:]   # For log messages.
          # If we weren't given a specific entry to work on (via 'url') then
          # search for all unapproved entries and choose one randomly.  A
          # disposition can be given explicitly in the 'disp' parameter:
          # "": submit; "a": approve; "r": reject.  If not given, a random
          # choice between "a" and "r" will be made.
        L('test.bhav.disp').debug("[%s] Entered: disp=%r, url=%r"
                                  % (u, disp, url))
        if disp is None:
            disp = 'a' if  random.random() > .1 else 'r'
        if not url:
              # Get srchform.
            page = jmconn.get_page ('GET', 'srchform.py')
            check_title (page, "Advanced Search")
            if not logged_in (page): raise NotLoggedInError()

              # Search for entry to edit.
              # Look for unapproved entries by SUBMITTER.
            srchform = page.forms[1]
            form_data = {'smtr':SUBMITTER, 'appr':['unappr']}
            page = jmconn.submit_form (srchform, form_data,
                                       extra={'search':'Search','srchres':'1'})
            check_title (page, "Search results")

              # Find all the results, pick one at random and edit it.
            xpath = './/div[@class="jmd-content"]/div[@class="item"]'\
                      '/form[@action="entr.py"]'\
                      '//tr[@class="resrow"]/td[@class="seq"]/a'
            links = page.body.findall(xpath)
            L('test.bhav.disp').debug("[%s] Found %s search results"
                                         % (u, len(links)))
            if len (links) == 0:
                msg = "[%s] No search results, try again later" % u
                L('test.bhav.disp').info(msg)
                return
            link = random.choice (links)
            url = link.attrib['href']

          # Get the Entry page.
        page = jmconn.get_page ('GET', url)
        check_title (page, "Entries")
        src, q, eid, pid, stat = entr_details (page, one_only=True)
        if eid is None:
              # This can happen if someone else edits the entry before we do.
            msg = "[%s] Entry not found: %s" % (u, id_from_url (url))
            L('test.bhav.disp').warn(msg)
            return
        msg = "[%s] Disposing %s %s/%s[%s]/%s" % (u,src,q,eid,pid,stat)
        L('test.bhav.disp').debug(msg)

          # Click the Edit button, get the Edit page.
        page = jmconn.submit_form (page.forms[1], {}, {})
        check_title (page, "Edit Entry")

          # Edit the entry by adding a comment.
        edform = page.forms[1]
        fld_name = edform.find (".//td/input[@name='name']")
        fld_comment = edform.find (".//td/textarea[@name='comment']")
        fld_name.value = SUBMITTER
        fld_comment.value = "[%s] dispose" % u
           # Click Next button on Edit form, get Confirmation form.
        page = jmconn.submit_form (edform, {'disp':disp}, {})
        check_title (page, "Confirm Submission")

          # Click Submit button on Confirmation form, get Thank You form.
        page = jmconn.submit_form (page.forms[1], {}, {})
          # Check for the right returned page is done below in check_thankyou()

          # Check the returned page to see if the submission was successful.
          # If not, we'll have gotten an Error page rather than a Thank
          # You page and the check_thankyou() will raise a ErrorPageError
          # exception.
        links = []
        try: eid, q, src = check_thankyou (page)
        except ErrorPageError as e:
              # We got an error page back from the submit instead of the
              # "thank you" page indicating a succesful submission.  The
              # exception instane contains the parsed page which we save
              # here for furthe examination below.
            error_page = e.args[1]

          # This is the normal exit point for this function.
        else:   # No exception, we're done.
            d = {'':"submit",'r':"reject",'a':"approve"}[disp]
            msg ="[%s] Submitted %s %s/%s %s"%(u,src,q,eid,d)
            L('test.bhav.disp').info(msg)
            return eid, q, src

          # Following is executed only if error was raised above.
          # If the submission failed, a common cause is that there exist
          # other conflicting edited entries.  These entries have to be
          # rejected before we can commit our entry.  The Error page was
          # saved in 'error_page' above.  We call get_conflict_entries()
          # to examine it and, if the problem was conflicting edits,
          # extract the urls for the conflicting entries.  We will then
          # dispose of them recursively.
        links = get_conflict_entries (error_page)
        if not links:    # Problem was other than conflicting edits.
            msg = "[%s] None returned, error page errors follow... " % u
            L('test.bhav.conflict').warn (msg)
            errtxt = extract_errs (page, nocheck_title=True)
            raise ErrorPageError (errtxt)
        ids = ','.join ([str(id_from_url(x)) for x in links])
        msg = "[%s] Conflicting edits exist: %s" % (u,ids)
        L('test.bhav.conflict').warn (msg)
        for link in links:
            dispose_entry (jmconn, link, 'r', uid=uid)
          # With all the conficting entries now rejected, try to submit our
          # entry again.
        dispose_entry (jmconn,  url, disp, uid=uid)

def get_conflict_entries (page):
          # Given an error page reporting other predecessor entries with
          # outstanding edits, extract and return the URLs for those entries.
        key1 = "There are other edits pending"
        key2 = "Edits have been made to this entry"
        xpath = ".//div[@class='jmd-content']/div[@class='item']/ul/li/span"
        elem = page.find (xpath)
        if elem is not None and \
                key1 in elem.text or key2 in elem.text:
            links = [e.get('href') for e in elem.findall ("./a")]
            return links
        return None

def get_entry_count (jmconn, uid=None):
        u = uid if uid else "j"+hex(id(jmconn))[2:]   # For log messages.
          # 1. Get srchform.
        page = jmconn.get_page ('GET', 'srchform.py')
        if logged_in (page): raise LoggedInError()

          # 2. Search for active entries by us (ie have history record with
          #    a Name value of SUBMITTER.)
        form_data = {'smtr':SUBMITTER, }
        page = jmconn.submit_form (page.forms[1], form_data,
                                   extra={'search':'Search', 'srchres':'1'})
        check_title (page, "Search results")
        count = None
        xpath = './/div[@class="jmd-content"]/div[@class="item"]'\
                  '/form[@action="entr.py"]'
        elem = page.find (xpath + '/span[@class="count"]')
        if elem is not None:
            mo = re.match (r'(\d+) matching entries found', elem.text)
            if mo: count = int (mo.group(1))
        else:
              #FIXME: the html for "no entries found" should not have a form
              # element containing the message, but it does by error, which
              # is why we can reuse the 'xpath' prefix defined above.
            elem = page.find (xpath + '/span[@class="caution"]')
            key = "No entries found"
            if elem is not None and elem.text.strip().startswith (key):
                count = 0
        if count is None:
            raise MissingDataError ("No count line found in srchres page")
        return count

def view_page (jmconn, url, title, expected_user):
        # Get the page at 'url', verify the title matches 'title' and 
        # that we are logged in as 'username'.

        page = jmconn.get_page ('GET', url)
        check_title (page, title)
          # The Help page does not have a login section so we can't check
          #  that page for the logged in oser name.
        if title != "Help":
            actual_user = logged_in_as (page)
            if actual_user != expected_user:
                msg = "Logged in as user '%r', expected '%r'"\
                      % (actual_user, expected_user)
                raise WrongUserError (msg)
        return page

def log_config (level):
        fmt = '%(levelname)1.1s %(name)s: %(message)s'
        dfmt = "%y%m%d-%H%M%S"
        logging.basicConfig (level=level, format=fmt, datefmt=dfmt)

def treset():
          # Intended for interactive debugging.  When Locust is used to
          # execute the functions defined herein, it changes the terminal
          # settings to no-echo making the use of pdb difficult.
          # This function will restore the settings to something sane
          # and can be run by hand when the pdb debugger is started or
          # in the brk() function (below).
        import termios
        tset = [17664, 5, 191, 35387, 15, 15, [
                b'\x03', b'\x1c', b'\x7f', b'\x15', b'\x04', b'\x00',
                b'\x01', b'\x00', b'\x11', b'\x13', b'\x1a', b'\x00',
                b'\x12', b'\x0f', b'\x17', b'\x16', b'\x00', b'\x00',
                b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00',
                b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00',
                b'\x00', b'\x00']]
        termios.tcsetattr (sys.stdin.fileno(), termios.TCSANOW, tset)

def brk():
          # Use this as a breakpoint function when writing pdb breakpoints
          # into the code when intending to run under Locust.
        treset();  pdb.set_trace()

def main():
        HOST = "http://fuji.home/jmdictdb/cgi/"
        log_config (level="DEBUG")
        s0 = JMconn (HOST)
        s1 = JMconn (HOST, requests.Session())
        s1.login ('smg', 'foo')
        cnt = get_entry_count (s0)
        print ("Entry count = %s" % cnt)
        #create_new_entry (s1)
        #edit_random_entry (s0)
        create_or_edit (s0, (2,4,4))
        dispose_random_entry (s1)  # Will also reject any conflicting entries.
        cnt = get_entry_count (s0)
        print ("Entry count = %s" % cnt)
        print ('Done!')

if __name__ == '__main__': main()
