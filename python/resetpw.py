#!/usr/bin/env python3

# A simple command line program to reset a jmdictdb user's password
# should the cgi "user.py" page be unavailable for some reason.  You
# will need access to the jmsess database (a database username and
# password).
# Run with the --help option for more details.

import sys, os, inspect, pdb
_ = os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])
_ = os.path.join (os.path.dirname(_), 'python', 'lib')
if _ not in sys.path: sys.path.insert(0, _)

import db

def main():
        args = parse_cmdline (sys.argv)
        try: dbconn = db.connect (args.dburi)
        except db.Error as e: sys.exit(e)
        sql = "UPDATE users SET pw=crypt(%s, gen_salt('bf')) WHERE userid=%s"
        cur = db.ex (dbconn, sql, (args.pw, args.user))
        dbconn.commit()
        if cur.rowcount != 1: sys.exit ('User "%s" not found' % args.user)

def parse_cmdline (argv):
        import argparse
        p = argparse.ArgumentParser (argv,
            description="Reset a JMdictDB user's password.  CAUTION: "
                "This program accepts the password on the command line "
                "which means the password may be visble to other users "
                "in a 'ps' command listing, saved in your shell history "
                "file, etc.  This program should only be run on a "
                "single-user machine where all users are trusted.")
        p.add_argument ('user', help="User's username")
        p.add_argument ('pw', help="New password to be set")
        p.add_argument ('--dburi', default='postgres://localhost/jmsess', 
            help="A URI for the session database for JMdictDB users.  "
                "Default is \"postgres://localhost/jmsess\".")
        args = p.parse_args ()
        return args

if __name__ == '__main__': main()
