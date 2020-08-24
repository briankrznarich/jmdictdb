The modules in this directory supply the view functions called
by the views the the main Flask application.  The purpose of
collecting the view code here is to get it out the main Flask
application where it would increase its size and make maintenance
difficult.

In general, each module contains a function named "view" with the
same signature:

  def view (svc, cfg, user, cur, params)

'svc', 'cfg', 'user', 'cur' are provided by the calling view in
the main application from 'G.svc', 'G.cfg', 'G.user' and 'G.dbcur'
respectively.  'params' (in some cases where the view is accessed
via a POST request it is called 'form' instead) is a Flask
'request.args' or 'flask.form' object (which in turn is actually
a werkzeug.MultiDict object) that contains the request's url or
form parameters.

The view() functions in these module also share a common return
value convention: a 2-tuple whose first item is a dict containing
the data returned and the second item, an array of error messages.
For a successful call, the second item will be an empty list.
If there were errors, the first item will be an empty dict.

The data dict (in the first item) should have the keys and values
expected by the view's template and thus can be passed directly
to the Flask render_template() call for the view.

A typical call in the main application will look like:

    @App.route ('/entr.py')
    def entr():
        from lib.views.entr import view
        data, errs = view (G.svc, G.cfg, G.user, G.dbcur, Request.args)
        if errs:
             return Render ('error.jinja', errs=errs, cssclass='errormsg')
        return Render ('entr.jinja', this_page=Request.full_path, **data)
