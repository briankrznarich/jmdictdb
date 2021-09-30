#!/usr/bin/env python3

# A simple command line program to reset a jmdictdb user's password
# should the cgi "user.py" page be unavailable for some reason.  You
# will need access to the jmsess database (a database username and
# password).
# Run with the --help option for more details.

import sys, pdb
_=sys.path; _[0]=_[0]+('/' if _[0] else '')+'..'
from getpass import getpass
from jmdictdb import db

def main():
        args = parse_cmdline (sys.argv)
        try: dbconn = db.connect (args.dburi)
        except db.Error as e: sys.exit(e)
        sql = "SELECT priv,disabled FROM users WHERE userid=%s"
        rs = db.query1 (dbconn, sql, (args.user,))
        if not rs:
            sys.exit ("No such user: %s" % args.user)
        priv, disabled = rs
        print ("User '%s' currently has '%s' privilege and is '%sabled'" %
               (args.user, {None:'User','E':'Editor','A':'Admin'}[priv],
                 'dis' if disabled else 'en'))
        if args.password: pw = args.password
        else:
            while True:
                pw = getpass ("New password for user %s: " % args.user)
                pw2 =  getpass ("Please enter again: ")
                if pw == pw2: break
                print ("Passwords did not match, please enter them again")
        cols, values = [], []
        cols.append ("pw=crypt(%s, gen_salt('bf'))");  values.append (pw)
        if args.enable:
            cols.append ("disabled=%s");  values.append (False)
        if args.admin:
            cols.append ("priv=%s");  values.append ('A')
        cols = ','.join (cols);  values.append (args.user)
        sql = "UPDATE users SET %s WHERE userid=%%s" % cols
        cur = db.ex (dbconn, sql, tuple(values))
        dbconn.commit()

import argparse
def parse_cmdline (argv):
        p = argparse.ArgumentParser (argv,
            description="Reset a JMdictDB user's password.  The purpose of "
                "this program is primarily to regain access to the system "
                "should an administrator accidently get locked out of their "
                "account and is thus unable to access the Users web page "
                "to correct the situation.  It allows resetting the password "
                "of a user and optionally un-disabling and changing access "
                "to Administrator level for the user.  To run this program "
                "successfully you must have access (a user name and password) "
                "to the jmsess database.")
        p.add_argument ('user', help="User's username")
        p.add_argument ('-p', '--password', nargs='?', default=None,
            help="New password to be set.  If not given the program will "
                "prompt for the new pasword.  That is generally a better "
                "choice since command line options are visible to other "
                "users on the system, recorded in shell history, etc.")
        p.add_argument ('--enable', action='store_true', default=False,
            help="If this option is given, the user account will be enabled.")
        p.add_argument ('--admin', action='store_true', default=False,
            help="If this option is given, the user will be assigned "
                "Administrator privilege.")
        p.add_argument ('--dburi', default='postgres://localhost/jmsess',
            help="A URI for the session database for JMdictDB users.  "
                "Default is \"postgres://localhost/jmsess\".")
        args = p.parse_args ()
        return args

if __name__ == '__main__': main()
