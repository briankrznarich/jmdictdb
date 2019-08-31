#######################################################################
#  This file is part of JMdictDB.
#  Copyright (c) 2018 Stuart McGraw
#
#  JMdictDB is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published
#  by the Free Software Foundation; either version 2 of the License,
#  or (at your option) any later version.
#
#  JMdictDB is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with JMdictDB; if not, write to the Free Software Foundation,
#  51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
#######################################################################

import sys, cgi, copy, os, re, pdb
sys.path.extend (['../lib','../../python/lib','../python/lib'])
import logger; from logger import L
import jdb, jmcgi

def view (svc, cfg, sess, cur, params):
          # Note that 'sess' is named 'user' in most other views and
          # is the user profile object for the currently logged in user.
          # 'sess' is the pre-Flask, cgi name and was left unchanged
          # to minimize code changes when migrating to Flask.

        errs = []; so = None; stats = {}
        fv = params.get; fl = params.getlist
          # fvn() will retrieve empty param as None rather than ''.
        fvn = lambda x: params.get(x) or None

          # The form values "userid", "fullname", "email", "priv",
          #  "disabled", come from editable fields in the user.py
          #  page.
          # The values "new" (i.e. create) and "delete" are also user
          #  boolean input from user.py indicating what the user wants
          #  to do.  Neither of them set indicates an update action on
          #  an existing account.  Both of them set is an error.
          # The form value "subjid" identifies the user whose data was
          #  originally loaded into the user.py form and is the user any
          #  update or delete will be performed on.  It will be empty
          #  when creating a new user.  If may differ from "userid"
          #  If the submitter changed the contents the "userid" box in
          #  user page before sunmitting.
          #  If it differs from "sess.userid" it indcates the action is to
          #  be done on the account of someone other than the logged
          #  user themself and is prohibited unless the logged in user
          #  has "admin" privilege.  For a new (create) action, "subjid"
          #  is ignored and the new user is created with the id given
          #  in "userid".

          # Set 'action' to "n" (new), "u" (update), "d" (delete) or
          #  "x" (invalid) according to the values of fv('new') and
          #  fv('delete') that were received from as url parameters
          #  from the User form.
        action = {(0,0):'u', (0,1):'d', (1,0):'n', (1,1):'x'}\
                   [(bool(fv('new')),bool(fv('delete')))]
        f_subjid, f_userid  = fvn('subjid'), fvn('userid')
        L('cgi.userupd').debug("new=%r, delete=%r, action=%r, subjid=%r, userid=%r"
            % (fv('new'), fv('delete'), action, f_subjid, f_userid))

        prolog = None
        if not sess:
            prolog = "<p>You must login before you can change your "\
                     "user settings.</p>"
        elif f_subjid != sess.userid and sess.priv != 'A':
            prolog = "<p>You do not have sufficient privilege to alter "\
                     "settings for anyone other than yourself.</p>"
        elif action in ('nd') and sess.priv != 'A':
            prolog = "<p>You do not have sufficient privilege to create "\
                     "or delete users.</p>"
        elif action == 'x':
            prolog = "<p>\"New user\" and \"Delete\" are incompatible.</p>"
        if prolog: return {}, {'prolog': prolog, errs: []}

        errors = []
         # Get the id of the user we will be updating.  If creating a
         # new user, 'subjid' should not exist and thus 'subj' will be
         # None which has the beneficial effect of causing gen_sql_-
         # params() to generate change parameters for every form value
         # which is what we want when creating a user.
        subj = jmcgi.get_user (f_subjid, svc, cfg)
        if action in 'nu':   # "new" or "update" action...
            if action == 'u':
               L('cgi.userupd').debug("update user %r" % sanitize_o(subj))
            else:
                L('cgi.userupd').debug("create user %r" % f_userid)
            if action == 'n' and \
                    (subj or f_userid==sess.userid
                     or jmcgi.get_user(f_userid, svc, cfg)):
                  # This is the creation of a new user (f_userid).
                  # The userid must not already exist.  The tests for
                  # subj and sess.userid are simply to avoid an expensive
                  # get_user() call when we already know the user exists.
                errors.append ("Account name %s is already in use."
                               % f_userid)
            if action == 'u' and f_userid!=subj.userid \
                    and (f_userid==sess.userid \
                         or jmcgi.get_user(f_userid, svc, cfg)):
                  # This is an update of an existing user.
                  # If the new userid (f_userid) is the same as the
                  # subj.userid it's not being changed and is ok.  If
                  # different then it must not be the same as an exiting
                  # userid.  The test for sess.userid is simply to avoid
                  # an expensive get_user() call when we already know
                  # that user exists.
                errors.append ("Account name %s is already in use."
                               % f_userid)

              # Get the parameters we'll need for the sql statement used
              # to update the user/sessions database.
            collist, values, err \
                = gen_sql_params (sess.priv=='A', subj, fvn('pw1'), fvn('pw2'),
                                  f_userid, fvn('fullname'), fvn('email'),
                                  fv('priv'), fv('disabled'))
            errors.extend (err)
            L('cgi.userupd').debug("collist: %r" % collist)
            L('cgi.userupd').debug("values: %r" % sanitize_v (values, collist))

        else:  # "delete" action...
              # We ignore changes made to the form fields since we
              # are going to delete the user, they are irrelevant.
              # Except for one: the "userid" field.  If that was
              # changed we treat it as an error due to the risk that
              # the user thought the changed userid will be deleted
              # which is not what will happen (we delete the "subjid"
              # user.)
            values = []
            if f_userid != f_subjid:
                errors.append (
                    "Can't delete user when userid has been changed.")
            if not subj:
                errors.append ("User '%s' doesn't exist." % f_subjid)

        if errors:
            return {}, {'errs': errors,
                'prolog': "The following errors were found in the changes "
                "you requested.  Please use your browser's Back button "
                "to return to the user page, correct them, and resubmit "
                "your changes."}

        update_session = None;  result = None;  summary = 'not available'
        if action == 'n':                         # Create new user...
            cols = ','.join (c for c,p in collist)
            pmarks = ','.join (p for c,p in collist)
            sql = "INSERT INTO users(%s) VALUES (%s)" % (cols, pmarks)
            values_sani = sanitize_v (values, collist)
            summary = "added user \"%s\"" % f_userid
        elif action == 'd':                       # Delete existing user...
            sql = "DELETE FROM users WHERE userid=%s"
            values.append (f_subjid)
            values_sani = values
            summary = "deleted user \"%s\"" % f_subjid
        else:                                     # Update existing user...
            if not collist: result = 'nochange'
            else:
                if subj and subj.userid == sess.userid \
                        and f_userid and f_userid:
                    update_session = f_userid
                updclause = ','.join (("%s=%s" % (c,p)) for c,p in collist)
                sql = "UPDATE users SET %s WHERE userid=%%s" % updclause
                values.append (f_subjid)
                values_sani = sanitize_v (values, collist)
                summary = "updated user %s (%s)" \
                           % (f_subjid, ','.join([c for c,p in collist]))

        if result != 'nochange':
            sesscur = jdb.dbOpenSvc (cfg, svc, session=True, noverchk=True, nokw=True)
            L('cgi.userupd.db').debug("sql:  %r" % sql)
              # 'values_sani' should be the same as values but with any
              # password text masked out.
            L('cgi.userupd.db').debug("args: %r" % values_sani)
            sesscur.execute (sql, values)
            sesscur.connection.commit()
              #FIXME: trap db errors and try to figure out what went
              # wrong in terms that a user can remediate.
            if update_session:
                L('cgi.userupd').debug("update sess.userid: %r->%r" % (sess.userid, update_session))
                sess.userid = update_session
            L('cgi.userupd').info(summary)
            return {'result': ('success', summary)}, {}


def gen_sql_params (is_admin, subj, pw1, pw2, userid, fullname, email,
                    priv, disabled):
        """
        Compares the form values received from the User form
        with the values in 'subj' to determine which have been
        changed.  For user creation ("new" action) there is no
        'subj' so any non-null form values will be seen as changes.
        If the action is delete, this function need not even be
        called since the only info needed for deletion is the
        user id.

        Return values:
        collist -- A list of 2-tuples each consisting of
           column name -- Name of the changed field/
           parameter -- This is either a psycopg2 paramater marker
             ("%s") or a Postgresql expression containing the same.
        values -- A list of the same length as 'collist' containing
           the values the will be substituted for the parameter markers
           in collist be Postgresql.
        errors -- A list of errors discovered when generating 'collist'
           and 'values'.  If this list in non-empty, 'collist' and
           'values' should be ignored and the errors should be displayed
           to the user.
        """

        new = not subj
          # Convert from the "priv" strings we receive from the user.jinja
          # form to the single letter keys used in the user database.
        priv = {'admin':'A', 'editor':'E', 'user':None}.get(priv)
        collist = [];  values = [];  errors = [];

        if pw1 or pw2:
            if pw1 != pw2:
                errors.append ("Password mismatch.  Please reenter "
                               "your passwords.")
            else:
                collist.append (('pw', "crypt(%s, gen_salt('bf'))"))
                values.append (pw1)
        else:
            if not subj:   # 'not subj' is a proxy for action=='n'
                errors.append ("Password is required for new users.")

        if new or userid != subj.userid:
            L('cgi.userupd').debug("userid change: %r" % userid)
              # Max length of 16 is enforced in database DDL.
            if not re.match (r'[a-zA-Z][a-zA-Z0-9]{2,15}$', userid or ''):
                errors.append ('Invalid "userid" value')
            else:
                collist.append (('userid', "%s"))
                values.append (userid)

        if new or fullname != subj.fullname:
            L('cgi.userupd').debug("fullname change: %r" % fullname)
            if fullname and len (fullname) > 120:
                  # This limit is not enforced in database DDL but is
                  # applied here as a sanity/maleficence check.
                errors.append ("Full name is too long, max of 120 "
                               "characters please.")
            collist.append (('fullname', "%s"))
            values.append (fullname)

        if new or email != subj.email:
            L('cgi.userupd').debug("email change: %r" % email)
            if email and '@' not in (email):
                errors.append ('Email addresses must include an "@" '
                               'character.')
            elif email and len (email) > 120:
                  # This limit is not enforced in database DDL but is
                  # applied here as a sanity/maleficence check.
                errors.append ("Email address too long, max of 120 "
                               "characters please.")
            else:
                collist.append (('email', "%s"))
                values.append (email)

        if is_admin:
              # Only if the script executor is an admin user do we
              # allow changing the account's priv or disabled status.

            if new or priv != subj.priv:
                L('cgi.userupd').debug("priv change: %r" % priv)
                collist.append (('priv', "%s"))
                values.append (priv)

            if new or bool(disabled) != subj.disabled:
                L('cgi.userupd').debug("disabled change: %r" % bool(disabled))
                collist.append (('disabled', "%s"))
                values.append (bool(disabled))

        return collist, values, errors

def sanitize_o (obj):
        if not hasattr (obj, 'pw'): return obj
        o = obj.copy()
        if o.pw: o.pw = sanitize_s (o.pw)
        return o

def sanitize_v (values, collist):
        try: i = [c for c,p in collist].index ('pw')
        except ValueError: return values
        v = copy.copy (values)
        v[i] = sanitize_s (v[i])
        return v

def sanitize_s (s):
        if not s: return s
        return '***'
