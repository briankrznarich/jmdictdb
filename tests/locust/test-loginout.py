# This test simulates multiple users viewing a selection of pages
# (view only, no submissions and all are top-level pages, no
# searching or following links inside pages) and periodically
# logging in and out.
# The goals are to:
# * Look for login/out interactions between users (eg a logged-in
#   state lost when changing pages, or assigned to wrong user.
#   #FIXME: to test the former more thoroughly we should be following
#   # links inside pages.
# * Connection or other resource leaks related to the database server
#   (eg connection obtained but not released.)  Check this by monitoring
#   Postgresql stats independently while test is running.
#
# When run, the Locust web interface asks for the total number of
# users to create and the url prefix to direct the test requests to.
# It will create the number of users request and start each running the
# same task: view a random page (with prob = 0.85) or change login state
# (with prob = 0.15).  Changing state means to login if currently logged
# out or visa versa.  The user name to log in as is obtained by calling
# get_user().  get_user() returns a user name of the form "test<n>" where
# <n> is a three-digit number between 0 and NUSERS-1 inclusive.
#
# The userids used by the test must have been previously added to the jmsess
# database.  This can be done by creating a file containing lines like the
# following and running it with psql.  
#   INSERT INTO users VALUES
#     ('test000','test000','a@b.com','$2a$06$2NmQyFw4elpKqF9fmzsUce4r0MPf8MENcbzh8kuZkhA6/JMDAGtD2','f','E',NULL),
#     ('test001',...),
#     ...
# up to the maximum needed (at least NUSERS-1).  The 2nd field must be the
# same as the the 1st (userid) field.  The pw field corresponds to a password
# of "abc".
#
# This test should NOT be run on a production JMdictDB database and the test
# users should not be added to the the production jmsess database; use
# separate, private versions of both for testing.
#
# When running under CGI with users' sessions obtained from the Postgresql
# "jmsess" user database, multiple Locust users can log in as the same
# JMdictDB user but if any of them log out, they all will be logged out.
# The get_user1() function will only hand out a given userid once and
# will need to get it back before handing it out again.  If more Locust
# users are created than there are userid's available and the userids are
# all in use when a Locust user tries to get one, it will wait a short time
# and try again until one is available.
# Under WSGI/Flask each web connection is independent and thus to users can
# both log in and out with the same userid without affecting the other.  The
# get_usern() function can be used in this case: it will gave out userid
# sequentially in round-robin fashion as requested.
# Choose one or the other userid dispensers by setting 'get_user' below to
# either 'get_user1' or 'get_usern'. 
#
# To run under locust:
#   locust -f test-loginout.py --only-summary 2>&1 | tee test.log
# Point web browser to http://localhost:8089.
#   Fill out form (total users, spawn rate, url prefix for a JMdictDB
#   server, e.g., http//localhost/jmdictdb/cgi-bin/ or http://localhost/jmsgi
# Or run in console only:
#   locust -f test-loginout.py -headless -u<N> -r<R> --only-summary \
#      -H <url-prefix>
# where <n> is total number of users, <R> is spawn rate, <url-prefix> is
# as described above.
#
# FIXME: see the FIXME comment near end regarding the entry ID numbers
#  used with the entry.py URL; these will likely need to be regenerated
#  when using a database other than the author's
# FIXME? we could scrape retrieved pages for urls and crawl a random
#  selection to improve realism a little?

import sys, os, itertools, random, re, time, pdb
import logging;  L = logging.getLogger
import locust, requests, lxml, lxml.html
from behaviors import *

PASSWD = 'abc'      # Passwd for the JMdictDB test* users.
NUSERS = 20
  # Create a pool of userid's for get_user1().
USERS = []
for n in range (0, NUSERS): USERS.append ('test' + str(n).zfill(3))

  # Give out userid's from pool to users exclusively.
def get_user1 (user=None):
       if user:  # Return 'user' to pool.
           USERS.append (user); return None
       else:     # Get 'user' from pool and give to caller.
           try: user = USERS.pop (0); return user
           except KeyError: return None
       assert False, "Programming error"

  # Give out userid's sequentially and non-exclusively.
Counter = itertools.count()
def get_usern (user=None):
       if not user: return 'test' + str(next (Counter) % NUSERS).zfill(3)
       return None

get_user = get_user1

URLS = [('entr.py',        'Entries'),
        ('srchform.py',    'Advanced Search'),
        ('srchformq.py',   'Basic Search'),
        ('edform.py',      'Edit Entry'),
        ('edhelp.py',      'Help'),
        ('updates.py?i=1', 'Recent Updates')]

  # Choose a random URL, with entry.py being the most most likely.
def get_url():
        url,title = random.choices (URLS, [8,1,1,1,1,1])[0]
        if url == 'entr.py':
            url += "?e=%s" % random.choice (IDs)
        return url,title

class MsFroop (locust.HttpUser):
    weight = 1
    def __init__ (self, *args, **kwargs):
        super().__init__ (*args, **kwargs)
        self.uid = "u"+hex(id(self))[2:]
        L('test.main').info("[%s] new ms.froop" % self.uid)
        self.jmconn = JMconn (self.host, self.client)
        self.loggedin = None
    @locust.task
    def view_page (self):
        url, title = get_url()
        try:
            L('test.main').info ("[%s] getting page %s" % (self.uid, url))
            page = view_page (self.jmconn, url, title, self.loggedin)
            if title == "Help": return   # No login form on Help page.
            if random.random() < .15:   # Change login state
                if self.loggedin:  # logout
                    L('test.main').info("[%s] logging out %s"
                                        % (self.uid, self.loggedin))
                    self.jmconn.logout (page)
                    get_user (self.loggedin)  # Release our userid.
                    self.loggedin = None
                else:              # login
                    user = get_user()
                    if user:
                        L('test.main').info("[%s] logging in as %s"
                                            % (self.uid, user))
                        self.jmconn.login (user, PASSWD, page)
                        self.loggedin = user
                    else:
                        L('test.main').warn("[%s] no userid, will try later"
                                            % (user))
                        time.sleep (.01 * random.random())
        except JMError as e:
            L('test.main').error("[%s] %s" % (self.uid, e))
           ## raise locust.exception.StopUser()

  # Set logging level for our log messages...
@locust.events.init.add_listener
def on_locust_init (environment, **kwargs):
        environment.catch_exceptions = False
        L('test').setLevel('DEBUG')
        pass

#from locust import LoadTestShape
#class MyCustomShape (LoadTestShape):
#    time_limit = 10
#    spawn_rate = 1
#    def tick (self):
#        env = self.runner.environment
#        print (self, self.runner.environment)
#        print (self.runner.user_classes_by_name)
#        run_time = self.get_run_time()
#        if run_time < self.time_limit:
#            users = env.runner.spawn_users({'Approver': 2})
#            spawn_rate = 1
#            return (0, spawn_rate)
#        return None

#from locust import events
##@events.init.add_listener
#def on_init (env, **kwargs):
#        print ("in on_init()")
#        env.host = HOST
#events.init.add_listener(on_init)

import gevent
from locust import HttpUser, task, between
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging

  # List of random entry ID numbers for use with the enty.py
  # and edform.py urls.
  #FIXME: these entry id numbers are from author's database and
  # and will likely be invalid for any other database.  Need
  # to generate this list dynamically or something.
IDs = [
    40005, 50818, 53735, 63992, 66112, 68149, 71822, 73672, 84865,
    89004, 95553, 112342, 116424, 125050, 126886, 129913, 135334,
    1036951, 1082705, 1083242, 1086275, 1132286, 1139066, 1139412,
    1166920, 1172623, 1173442, 1179252, 1182373, 1190471, 1200965,
    1206443, 1207148, 1214336, 1214416, 1214664, 1217652, 1218785,
    1220326, 1231397, 1233501, 1237774, 1245138, 1254489, 1260282,
    1264052, 1266259, 1271719, 1276501, 1285119, 1293716, 1312895,
    1320063, 1327169, 1332978, 1339482, 1342266, 1344881, 1350182,
    1355477, 1364650, 1367477, 1368541, 1372512, 1381000, 1394823,
    1403628, 1404099, 1410203, 1412589, 1413166, 1416044, 1416559,
    1424398, 1424809, 1427468, 1430065, 1435645, 1439999, 1440244,
    1443367, 1446721, 1450638, 1454042, 1457910, 1460903, 1461794,
    1466153, 1468120, 1468440, 1477468, 1480933, 1484738, 1498799,
    1503734, 1506987, 1513481, 1514629, 1532047, 1537310, 1544057,
    1547306, 1550127, 1560989, 1563372, 1575942, 1588982, 1594091,
    1595238, 1603354, 1610528, 1612249, 1636199, 1638374, 1642177,
    1643831, 1646659, 1653288, 1654966, 1657286, 1667502, 1675904,
    1685171, 1694756, 1697925, 1706915, 1709752, 1716233, 1733881,
    1743704, 1745451, 1768987, 1774813, 1785736, 1790169, 1800274,
    1820232, 1821761, 1827909, 1833598, 1843467, 1847834, 1854628,
    1858864, 1872856, 1872952, 1873000, 1873069, 1875122, 1877741,
    1886463, 1892965, 1901777, 1917485, 1928128, 1950441, 1970315,
    1978228, 1980468, 1983012, 1988077, 1992280, 1992528, 2002224,
    2004130, 2020079, 2027300, 2028305, 2042386, 2052597, 2074948,
    2078962, 2102402, 2107501, 2108538, 2110059, 2110581, 2114038,
    2121690, 2129753, 2132581, 2137776, 2139469, 2157002, 2164597,]

  # This allows running stand-alone without the Locust main program.
def main():
        setup_logging("DEBUG", None)
        env = Environment (host=HOST,
                user_classes=[Creator,Submitter,Approver])
        print (env)
        env.create_local_runner()
        env.runner.start (1, spawn_rate=10)
        gevent.spawn_later (10, lambda: env.runner.quit())
        env.runner.greenlet.join()

if __name__ == '__main__': main()
