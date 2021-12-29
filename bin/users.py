#!/usr/bin/env python3

# A simple command line program to manage a JMdictDB sqlite3 users
# database.  This provides a rudimentary command line version of
# the Users web page.
# Run with the --help option for more details.
#
# To create new database and import from PG jmsess database:
#   $ bin/users.py newdb -d web/lib/jmsess.sqlite
#   $ psql jmsess -c "\copy users TO stdout DELIMITER E'\t' CSV" \
#      | bin/users.py -d web/lib/jmsess.sqlite import
#
#FIXME: add option(s) to distinguish between importing from PG jmsess
# database and exported sqlite database.  Currently assumes PG.
#FIXME: need better error handling, catch exceptions from userdb.*.
#FIXME: import: csv values retrieved with doubly quoted text are
# saved to sqlite with excess quotes intact.
#FIXME: import: need option to call with clean=True.

import sys, os, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from jmdictdb import userdb, logger

def main():
        args = parse_cmdline (sys.argv)
        logger.config (level='debug')
        if args.action == 'newdb':
            userdb.newdb (args.database)
            print ("created %s" % args.database)
            return
        dbconn = userdb.dbopen (args.database)
        if args.action == 'list':
            rs = userdb.users (dbconn)
            for r in rs: print (r)
        elif args.action == 'del':
            n = userdb.dele (dbconn, args.user)
            print ("deleted %s user(s)" % n)
        elif args.action == 'add':
            pw = userdb.get_pw_hash (args.pw, args.user)
            n = userdb.add (dbconn, args.user, pw, args.name,
                                    args.mail, args.priv, args.enable)
            print ("added %s user(s)" % n)
        elif args.action == 'upd':
            pw = userdb.get_pw_hash (args.pw, args.user)
            n = userdb.upd (dbconn, args.user, pw, args.name,
                                    args.mail, args.priv, args.enable)
            print ("updated %s user(s)" % n)
        elif args.action == 'import':
            nread, nloaded = userdb.load_csv_stream (dbconn)
            print ("%s rows read, %s rows loaded" % (nread, nloaded))
        else: assert False, "Programming error"
        dbconn.commit()

import argparse
def parse_cmdline (argv):
        p = argparse.ArgumentParser (argv,
            description="Manage JMdictDB users (aka editors).  "
                "This program allows one to add, delete and modify user "
                "details in the users database.")
        p.add_argument ('action', choices=['list','add','upd','del',
                                           'newdb','import'],
            help='Action to perform.  '
                '"list": List all users; '
                '"add": Add a new user; '
                '"upd": Update the settings for an existing user; '
                '"del": Delete an existing user; '
                '"newdb": Create a new database with the filename given'
                ' by --db; '
                '"import": import a csv file on stdin.  ')
        p.add_argument ('-d', '--database', default=None, required=True,
            metavar='USER-DB',
            help='Name of the user database, typically "jmsess"')
        p.add_argument ('user', nargs='?', help="User's id.")
        p.add_argument ('--pw', nargs='?', default=None, const=...,
            help="Password to be set.  If no value given the program will "
                "prompt for the new pasword.  That is generally a better "
                "choice since command line options are visible to other "
                "users on the system, recorded in shell history, etc.")
        p.add_argument ('-n', '--name', help="Full name.")
        p.add_argument ('-m', '--mail', help="Email address.")
        p.add_argument ('--enable', action='store_true', default=None,
            help="If this option is given, the user account will be enabled.")
        p.add_argument ('--disable', action='store_false', dest='enable',
            help="If this option is given, the user account will be disabled.")
        p.add_argument ('-p', '--priv', choices=['a','e','u'], default=None,
            help='Privilege level for user: '
                '"u": user, no privileges (default for "add"); '
                '"e": editor; '
                '"a": administrator.')
        args = p.parse_args ()
        if args.action not in ('list','import','newdb') and not args.user:
            p.error ("%s action requires 'user' argument" % args.action)
        return args

main()
