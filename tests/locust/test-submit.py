# This test simulates multiple users simultaneously editing and submitting
# entries to a JMdictDB database.
#
# When run, it will create the requested (via the Locust interface) number 
# of users distributed among two classes:
#   Submitter: these users will edit and existing approved entry, an
#     existing previously edited entry, or create a new entry.  They 
#     are not logged in so entries created are always unapproved.
#     When new entries are created they use nonsense readings and kanji.
#     When edits are made, no changes to the entries are made; only a 
#     comment it added.  A small percentage of edits are deletes.
#   Approver: these users log in as editors, look for unapproved entries 
#     and either approve, or less likely, reject them.
#   (The code contains a third class, currently deactivated, that creates
#   new entries.)
#
# All the Approvers log into JMdictDB with the same userid and password
# which is provided in the enviroment variables 'JMDICTDB_USER' and
# 'JMDICTDB_PW'.
#
# All entries created have a submitter name of SUBMITTER as defined below
# so they can be easily found and deleted. 
# Nevertheless this program should not be run against a production JMdictDB
# database since it will run up the entry id and seq numbers unnecessarily.
#
# WARNING: the usual messages will be written to the JMdictDB and webserver
# log files by the operations performed by this test and may be voluminous
# depending on how long the test is run for.  You may wish to temporarily
# redirect them elsewhere.
#
# Run under Locust:
#   locust -f test-submit.py --only-summary 2>&1 | tee test.log
# Point a web browser to http://localhost:8089)
#
# Run in console:
#   locust -f test-submit.py -headless -u<N> -r<R> --only-summary -H <url>
# where <N> is the max number of users, <R> is the spawn rate (users per
# second) and <url> is the base url for the JMdictDB server under test, e.g.,
# http://localhost/jmdictdb/cgi-bin.


import sys, os, random, re, time, pdb
import logging;  L = logging.getLogger
import locust, requests, lxml, lxml.html
from behaviors import *

HOST = 'http://localhost/jmdictdbv/cgi/'
EDITOR_USERID = os.environ.get ('JMDICTDB_USER', None)
if not EDITOR_USERID: sys.exit ("JMDICTDB_USER not set")
EDITOR_PW = os.environ.get ('JMDICTDB_PW', None)
if not EDITOR_PW: sys.exit ("JMDICTDB_PW'not set")
  # Probabilities that a Submitter user will: create new entry; edit
  #  an approved entry; edit an unapproved entry:
DISTRIB = 0.4, 0.3, 0.3
random.seed (33)

class Submitter (locust.HttpUser):
    weight = 1
    def __init__ (self, *args, **kwargs):
        super().__init__ (*args, **kwargs)
        self.uid = "u"+hex(id(self))[2:]
        L('test.main.subm').info("[%s] new Submitter" % self.uid)
        self.jmconn = JMconn (self.host, self.client)
    @locust.task
    def edit_entry (self):
        ##time.sleep (random.uniform (0.1, 0.3))
        try: action = create_or_edit (self.jmconn, DISTRIB, uid=self.uid)
        except JMError as e:
            L('test.main.subm').error("[%s] %s" % (self.uid, e))
           ## raise locust.exception.StopUser()

class Approver (locust.HttpUser):
    weight = 2
    def __init__ (self, *args, **kwargs):
        super().__init__ (*args, **kwargs)
        self.uid = "u"+hex(id(self))[2:]
        L('test.main.appr').info("[%s] new Approver" % self.uid)
        self.jmconn = JMconn (self.host, self.client)
        self.jmconn.login ('smg', 'foo')
    @locust.task
    def dispose_entry (self):
        ##time.sleep (random.uniform (0.2, 0.7))
        try: dispose_random_entry (self.jmconn, uid=self.uid)
        except JMError as e:
            L('test.main.appr').error("[%s] %s" % (self.uid, e))
            ## raise locust.exception.StopUser()

class Creator (locust.HttpUser):
    weight = 0
    def __init__ (self, *args, **kwargs):
        super().__init__ (*args, **kwargs)
        self.uid = "u"+hex(id(self))[2:]
        L('test.main.creat').info("[%s] new Creator" % self.uid)
        self.jmconn = JMconn (self.host, self.client)
        self.jmconn.login (EDITOR_USERID, EDITOR_PW)
        self.entry_cnt = 0
    @locust.task
    def create_entry (self):
        try: create_new_entry (self.jmconn, uid=self.uid)
        except JMError as e:
            L('test.main.creat').error("[%s] %s" % (self.uid, e))
            ## raise locust.exception.StopUser()
        else:
            self.entry_cnt += 1
            if self.entry_cnt > 5:
                msg = "[%s] Stopping Creator user" % self.uid
                L('test.main.creat').info (msg)
                self.stop()

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
