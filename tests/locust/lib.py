import sys, os, copy, random, re, urllib, pdb
import logging;  L = logging.getLogger
import requests, lxml.html
# Additional import(s) below in function(s): view()

FAIL = 0
SUCCESS = 1

class JMconn:
    def __init__ (self, urlbase, session=None):
        urlbase += "/" if urlbase[-1]!= '/' else ""
        self.urlbase = urlbase
        self.session = session or requests

    def get_page (self, meth, relurl, **kwargs):
        L('cc.lib.get_page').debug("meth=%s, url=%s" % (meth, relurl))
        url = urllib.parse.urljoin (self.urlbase, relurl)
          # Check if we are running under Locust.  The following avoids
          # importing Locust which don't want to do because it appears
          # Locust does some monkey patching on import which we'd like to
          # avoid if nothing else has imported it.  Downside is that we
          # require an actual locust.HttpSession instance, an instance of
          # a subclass won't work.
        if self.session.__class__.__name__ == 'HttpSession':
              # Locust bins the result of each request together under its
              # URL.  To avoid a zillion bins, one for each page with a
              # different entry id, set the 'request' name parameter which
              # Locust will use instead of the URL, to the url value sans
              # the entry id.
            name = re.sub(r'((?<=\?)e=\d+&?)|(&e=\d+)', '',
                          url.replace (self.urlbase, ""))
            self.session.request_name = name
          # Execute the request.
        resp = self.session.request (meth, url, **kwargs)
        if resp.status_code != 200:
            msg = "HTTP status code: %s, url: %s"\
                  % (resp.status_code, resp.url)
            raise OperationError (msg)
        resp.encoding = 'utf-8'
        page = lxml.html.document_fromstring (resp.text)
          # FYI: to print 'page' as html text use:
          #   print (lxml.html.tostring(page).decode('utf-8'))
          # To view in browser (from documentation, doesn't work for me):
          #   lxml.html.open_in_browser (page)
        return page

    def submit_form (self, form, fields, extra, session=None):
        '''-------------------------------------------------------------------
        Submit a form with values from 'fields' and 'extra'.
          form -- A parsed "form" element.
          fields -- A dict whose keys correspond to field names in the form
            and whose values will be use to set those fields.
          extra -- Additional submission data.  This may be a dict or list
            of 2-tuples as described in the Request package documentation.
            This is generally needed  to supply the value of the
            <input type="submit"> element.
          session -- A Requests session instance or None.
        -------------------------------------------------------------------'''

        #form.fields = fields  # clears all field first, including defaults.
        for name,value in fields.items():
            form.fields[name] = value

          # We want the lxml submit_form() call to submit the url and
          # retrieve the resulting document using our own get_page() (rather
          # than lxml's default opener function that uses Python's urllib)
          # so that:
          #   1) we can use our established requests.Session to maintain
          #    cookie persistence.
          #   2) we can return the retrieved document in the same form and
          #    processed consistently with other retrieved urls.
          # Submit the form.  We supply any needed hidden input values
          # via the 'extra' argument.
        page = lxml.html.submit_form (form, extra_values=extra,
                                     open_http=self._lxml_submit)
        return page

    def _lxml_submit (self, method, url, values):
         # This function is called by lxml.submit_form() indirectly via the
         # _lxml_submit_shim() lambda expression in our submit_form().
           # The lxml.submit_form() doc indicates that GET and POST are
           # the only two methods supported so that's all we'll bother
           # with here.
         if method == 'GET':
             page = self.get_page (method, url, params=values)
         elif method == 'POST':
             page = self.get_page (method, url, data=values)
         else: raise ValueError (method)
         return page

    def login (self, username='', pw='', page=None):
        if page is None: page = self.get_page ('GET', 'srchformq.py')
        form_data = {'username':username, 'password':pw}
        page = self.submit_form (page.forms[0],form_data,{'loginout':'login'})
        if not logged_in (page): raise OperationError ("Failed to log in")

    def logout (self, page=None):
        if page is None: page = self.get_page ('GET', 'srchformq.py')
        page = self.submit_form (page.forms[0], {}, {'loginout':'logout'})
        if logged_in (page): raise OperationError ("Failed to log out")

def logged_in (page):
          # If logged in, form[0]'s submit button (which is named "loginout")
          # will have a value of "logout" rather than "login".
        xpath = ".//tbody[@class='hlogin']//form//input[@name='loginout']"
        value = page.body.find(xpath).get('value')
        if value == 'logout': return True
        if value == 'login': return False
        raise WrongDataError ("'loginout' button value: %r" % value)

def logged_in_as (page):
          # If logged in, return the user's name extracted from the link
          # to the user.py page.  If not logged in return None..
        xpath = ".//tbody[@class='hlogin']//form/a"
        link = page.body.find(xpath)
        if link is None: return None
        return link.text    # User's full name if logged in or None if not.

def get_srchres_eids (page, no_eids=False):
        '''-------------------------------------------------------------------
        Given an srchres.py page in parsed form (an lxml.etree), verify it
        has a correct title, then return a 2-tuple of the number of entries
        found and a list of the entry id numbers.  The number of entry id's
        returned may be less that the reported number found because the
        srchres page pagainates results.
        -------------------------------------------------------------------'''

        check_title (page, 'Search results')
        count = None
        counttext = page.body.find (".//span[@class='count']").text
        if "No entries found." in counttext: count = 0
        else:
            mo = re.search (r'([0-9]+) matching entries found.', counttext)
            if mo: count = int(mo.group(1))
            else: raise MissingDataError (counttext, page)
        xpath = './/tr[@class="resrow"]/td/input[@name="e"]'
        elist = page.body.findall (xpath)
        eids = [int(x.get('value')) for x in elist]
        return count, eids

def check_entr (page, eid, text=None):
        '''-------------------------------------------------------------------
        Given an entr.py page 'page' in parsed form (lxml.etree), verify that
        it has a correct title, an entry with the correct id number, and, if
        'text' was given, a reading or kanji with 'text' as a substring.  A
        failure of any of these conditions will result in an error being
        thrown; no return value is provided.
        -------------------------------------------------------------------'''

        check_title (page, 'Entries')
          # Extract the entry id number from the page...
        if eid:
            xpath = ".//div[@class='item']//span[@class='pkid']/a"
            try: id = int (page.body.find(xpath).text)
            except (TypeError, AttributeError):
                msg = "Cant find 'pkid' element or no 'id' in it"
                raise MissingDataError (msg, page) from None

              # ...and confirm it is what was expected.
            if id != eid:
                raise WrongDataError ("Expected eid=%s, got %s" % (eid, id))

          # If 'text' was provided make sure it is is found in at least
          # one of the entry's kanji or readings.  We don't look for an
          # exact match (i.e., "==") because 'text' may be a search term
          # and the entry was found by a "begins" or "contains" search and
          # thus the text my be a substring of one of the entry's kanji
          # or readings.
        if text is not None:
            word_elems = page.body.findall(".//span[@class='kanj']")\
                         + page.body.findall(".//span[@class='rdng']")
            for w in [x.text for x in word_elems]:
                if text in w: break
            else:
                msg = "\"%s\" not found in any 'kanj' or 'rdng' elements"\
                      % text
                raise MissingDataError (msg, page)

def entr_details (page, one_only=False):
          # Scrape the entry id, sequence number, corpus, and status from
          # the entries on a parsed entr.jinja page.  Since there may be
          # multiple entries on the page, a list of 4-tuples of the afore-
          # mentioned data items is returned, unless 'one_only' is true, in
          # in which case more than one entry will raise an error and only
          # a single 4-tuple will be returned.

        check_title (page, 'Entries')
        xpath = './/div[@class="jmd-content"]/div[@class="item"]'
        entrs = page.findall (xpath)
        details = [_entr_detail(e) for e in entrs]
        if not one_only: return details
        if len(details) != 1:
            raise OperationError ("Multiple entries returned", page)
        return details[0]

def _entr_detail (entr_item):
        e = entr_item        # For brevity.
        if "No entries found" in e.findtext ('span'): return (None,)*5
        src = e.text.strip()
        seq = getattr (e.find ('a'), 'text', None)
        eid = getattr (e.find ('span[@class="pkid"]/a'), 'text', None)
        pid = getattr (e.find ('span[@class="status"]/a'), 'text', None)
        stat = e.find ('span[@class="status"]').text \
          or  e.find ('span[@class="status"]/span[@class="pend"]').text
        seq = int (seq) if seq else None
        eid = int (eid) if eid else None
        pid = int (pid) if pid else None
        unappr = "*" if "pending" in stat else ""
        if "Active" in stat: stat = 'A'
        elif "Rejected" in stat: stat = 'R'
        elif "Deleted" in stat: stat = 'D'
        else: raise ValueError ("Bad 'stat' value: %r" % stat)
        return src, seq, eid, pid, stat+unappr

def check_thankyou (page):
        check_title (page, "Submission successful")
        xpath = ".//div[@class='jmd-content']/div[@class='item']/table/tr/td"
        cells = page.findall (xpath)
          #FIXME: currently the Thank You page uses <td> elements for the
          # header row so we have an extra row of three items at front of
          # list.
        if cells[0].text == "Corpus": cells = cells[3:]
          #FIXME? the Thank You page supports submission of multiple entries
          # in which case there will multiple rows of (src,seq,id) triples.
          # Since I don't know how to handle that case and am not sure it
          # will occur in practice, we'll just bail.
        if len (cells) != 3:
            raise WrongDataError ("Got %d rows, expected 3" % len(cells), page)
        src = cells[0].text
        href = cells[1].find('a').get('href')
        seq = id_from_url (href, typ="q")
        if not seq: raise WrongDataError ('No seq# found in "%s"' % href, page) 
        href = cells[2].find('a').get('href')
        eid = id_from_url (href, typ="e")
        if not eid: raise WrongDataError ('No id# found in "%s"' % href, page) 
        return eid, seq, src

def check_title (page, expect):
        title = page.head.find('title').text.replace("JMdictDB - ", "")
        if title == expect: return
        if title != "Error":
            msg = "Expected page '%s', got '%s'" % (expect, title)
            raise WrongPageError (msg)
        errtxt = extract_errs (page, nocheck_title=True)
        raise ErrorPageError (errtxt, page)

def extract_errs (page, nocheck_title=False):
        if not nocheck_title: check_title (page, "Error")
        xpath = './/div[@class="jmd-content"]'\
                  '//div[@class="item"]/ul/li/span'
        err_elems = page.findall (xpath)
        err_txts = [e.text for e in err_elems]
        errtxt = (".\n".join (err_txts)).strip()
        if not errtxt: raise MissingDataError ("No error text in Error page")
        return errtxt

def id_from_url (url, typ="e"):
          # Extract the int value of an entry id or sequence number from
          # the parameters of a URL text string.  'typ' should be "e" to
          # get the entry id, or "q" to get the sequence number.
          # If no id/seq number is found, None is returned.
        mo = re.search (r'[?&]%s=(\d+)' % typ, url)
        if mo: return int (mo.group(1))
        return ''

Edform_fieldtypes = {
        'src': 'select',
        'kanj': 'textarea',
        'rdng': 'textarea',
        'sens': 'textarea',
        'reference': 'textarea',
        'comment': 'textarea',
        'name': 'input',
        'email': 'input', }

def set_fields (form, items):
        for name, value in items.items():
            fieldtype = Edform_fieldtypes[name]
            xpath = ".//td/%s[@name='%s']" % (fieldtype, name)
            field = form.find (xpath)
            if fieldtype in ('input','textarea'):
                field.value = value
            elif fieldtype in ('select',):
                  #FIXME: need some error handling for eg 'value' not found.
                field.value = [x.get('value') for x in field.getchildren()
                               if x.text==value][0]
            else: raise ValueError (fieldtype)

def prt (page):
        print (lxml.html.tostring(page).decode('utf-8'))

def view (page):
        import subprocess
        fname = "/tmp/jmdict-test.html"
        html = lxml.html.tostring(page).decode('utf-8')
        html = "<!DOCTYPE html>\n" + html
        with open (fname, 'w') as f: print (html, file=f)
        subprocess.run (['firefox', "file://" + fname])

def fake_word():
        charset = HCHRS if random.random() > 0.2 else KCHRS
        chars = charset.split()
        ktxt, kleng = "", random.randint(3,7)
        rleng = kleng + random.randint(1,5)
        rtxt = ''.join (random.choices (chars, k=rleng))
        if charset==HCHRS and random.random() >= 0.17:
            ktxt = ''.join (randk() for i in range(kleng))
        return ktxt, rtxt

def randk ():    # Random kanji character.
    return chr (random.choice (range(int('4E00',16),int('9FEA',16))))

HCHRS = "あ い う え お か き く け こ さ し す せ そ た ち つ て と な に ぬ ね の"\
  "は ひ ふ へ ほ ま み む め も や ゆ よ ら り る れ ろ わ ゐ ゑ を ん っ "\
  "が ぎ ぐ げ ご ざ じ ず ぜ ぞ だ ぢ づ で ど ば び ぶ べ ぼ ぱ ぴ ぷ ぺ ぽ "\
  "きゃ きゅ きょ しゃ しゅ しょ ちゃ ちゅ ちょ にゃ にゅ にょ ひゃ ひゅ ひょ "\
  "みゃ みゅ みょ りゃ りゅ ちょ"
KCHRS = "ア エ ウ エ オ カ キ ク ケ コ サ シ ス セ ソ タ チ ツ セ ソ ナ ニ ヌ ネ ノ "\
  "ハ ヒ フ ヘ ホ ヤ ユ ヨ ラ リ ル レ ロ ワ ヰ ヱ ヲ ン ッ ー "\
  "ガ ギ グ ゲ ゴ ザ ジ ズ ゼ ゾ ダ ヂ ヅ デ ド バ ビ ベ ブ ボ パ ピ ウ ペ ポ "\
  "キャ キュ キョ シャ シュ ショ チャ チュ チョ ニャ ニュ ニョ ヒャ ヒュ ヒョ "\
  "ミャ ミュ ミョ リャ リュ リョ"

class JMError (RuntimeError):
    def __init__ (self, *args, **kwargs):
        self.args = args;  self.__dict__.update (kwargs)
    def __str__ (self):
        return str ("%s: %s" % (self.__class__.__name__, self.args[0]))
class MissingDataError (JMError): pass
class WrongDataError (JMError): pass
class WrongPageError (JMError): pass
class ErrorPageError (JMError): pass
class LoggedInError (JMError): pass
class NotLoggedInError (JMError): pass
class WrongUserError (JMError): pass
class OperationError (JMError): pass
