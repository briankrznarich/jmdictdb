# Functions for user management via a sqlite3 database.

import sys, os, pdb
import bcrypt
#import sqlite3, bcrypt
from getpass import getpass
import logging; L=logging.getLogger
from jmdictdb import db

def dbopen (dbname, create=False):
        # Commented out code below is for sqlite3 database.
        #exists = os.access (dbname, os.R_OK)
        #if exists and create:
        #    raise OSError (0, "database file exists", dbname)
        #if not exists and not create:
        #    raise OSError (0, "file doesn't exist or not accessible", dbname)
        conn = db.connect (dbname)
        return conn

def auth (conn, userid, pw):
        sql = "SELECT userid,fullname,email,pw,priv"\
              " FROM users WHERE userid=%s AND NOT disabled"
        cur = conn.cursor()
        cur.execute (sql, (userid,))
        r = cur.fetchone()
        if not r: return None
        if bcrypt.checkpw (bytes(pw,'utf-8'), bytes(r[3],'utf-8')):
            return  r[:3]+r[4:]  # Return: userid,fullname,email,priv
        return None

def user (conn, userid):
        sql = "SELECT userid,fullname,email,priv,disabled"\
              " FROM users WHERE userid=%s"
        cur = conn.cursor()
        cur.execute (sql)
        r = cur.fetchone()
        return r

def users (conn):
        sql = "SELECT userid,fullname,email,priv,disabled"\
              " FROM users ORDER BY userid"
        cur = conn.cursor()
        cur.execute (sql)
        rs = cur.fetchall()
        return rs

def add (conn, userid, pw, name, mail, priv, enabled=True):
        cols, values = ['userid'], [userid]
        if name:
            cols.append ('fullname'); values.append (name)
        if mail:
            cols.append ('email');    values.append (mail)
        if priv:
            cols.append ('priv');     values.append (priv.upper())
        if enabled is not None:
            cols.append ('disabled'); values.append (not enabled)
        if pw:
            if pw == 'u': pw = None
            cols.append ('pw');       values.append (pw)
        colsclause = ','.join (cols)
        sql = "INSERT INTO users(%s) VALUES(%s)"\
              % (colsclause, ','.join(['%s']*len(cols)))
        cur = conn.cursor()
        cur.execute (sql, values)
        return cur.rowcount

def upd (conn, userid, pw, name, mail, priv, enabled=True):
        cols, values = [], []
        if name:
            cols.append ('fullname'); values.append (name)
        if mail:
            cols.append ('email');    values.append (mail)
        if priv:
            cols.append ('priv');     values.append (priv.upper())
        if enabled is not None:
            cols.append ('disabled'); values.append (not enabled)
        if pw:
            if pw == 'u': pw = None
            cols.append ('pw');       values.append (pw)
        setclause = ','.join ([("%s=%s"%c) for c in cols])
        values.append (userid)
        sql = "UPDATE users SET %s WHERE userid=%s" % setclause
        cur = conn.cursor()
        cur.execute (sql, values)
        return cur.rowcount

def dele (conn, userid):
        sql = "DELETE FROM users WHERE userid=%s"
        cur = conn.cursor()
        cur.execute (sql, (userid,))
        return cur.rowcount

def newdb (filename):
        conn = dbopen (filename, create=True)
        cur = conn.cursor()
        sql = "CREATE TABLE users ("\
              "  userid VARCHAR(16) PRIMARY KEY,"\
              "  fullname TEXT,"\
              "  email TEXT,"\
              "  pw TEXT,"\
              "  disabled BOOLEAN NOT NULL DEFAULT false,"\
              "  priv CHAR(1) CHECK (instr('EA', priv)>0));"
        cur.execute (sql)
        return True

def load_csv_stream (dbconn, file=sys.stdin, pg=True, clean=False):
        import csv
        sql = "INSERT INTO users VALUES(%s,%s,%s,%s,%s,%s)"
        cur = dbconn.cursor()
        dialect = {'delimiter':'\t', 'quoting':csv.QUOTE_NONE}
        rdr = csv.reader (file, **dialect)
        if clean: 
            cur.execute ("DELETE FROM users")
            L('jmd.lib.userdb.load_csv').debug("Deleted %d rows"
                                               % cur.rowcount)
        lnnum = count = 0
        for lnnum, data in enumerate (rdr, start=1):
            if pg:  # Adjustments for data from Postgresql "jmsess" db.
                userid,name,mail,pw,disable,priv,notes = data
                  # Drop 7th col "notes", not in sqlite db.
                if pw and pw.startswith ("$2a"): pw = "$2b" + pw[3:]
                disable = 0  if disable=='f' else 1
                data = userid,name,mail,pw,disable,priv
            L('jmd.lib.userdb.load_csv').debug("Loading: [%d] %r"
                                               % (lnnum,data))
            cur.execute (sql, data)
            count += cur.rowcount
        return lnnum, count

def get_pw_hash (pw, userid):
        if not pw: return None
        if pw is ...: pw = get_pw_interactive (userid)
        if pw: pw = hash_pw(pw)
        return pw.decode ('ascii')

def get_pw_interactive (userid):
        while True:
            pw = getpass ("New password for user %s: " % userid)
            pw2 =  getpass ("Please enter again: ")
            if pw == pw2: break
            print ("Passwords did not match, please enter them again")
        return pw

def hash_pw (pw):
        hash = bcrypt.hashpw (bytes(pw, 'utf-8'), bcrypt.gensalt(6))
          # This is the same value as returned by Postgresql with
          # "crypt('foo', gen_salt('bf'))" as used previously in the
          # jmsess database except PG returns a hash with a prefix of
          # "$2a" and bcrypt gives a prefix of "$2b".   Other than that
          # they are interchangable.
        hash = b"$2a" + hash[3:]
        return hash

# In progress...
#def format_table (rows, descr):
#        colnames = [x[0] for x in descr]
#        lengths = [None]*len(rows[0])
#        types   = [None]*len(rows[0])
#        for r in colname + rows:
#            for n, c in enumberate (r):
#                if lengths[n] = max (lengths[n], len (repr(c)))
#                if c in None: continue
#                try: float(c)
#                except ValueError, TypeError: types[n] = "string"
#                else: types[n] = types[n] or "number"
#        divs = "+" + "+".join (["-"*x for x in lengths]) + "+"
#        for r in rows:
#             for n, c in enumerate (r):
