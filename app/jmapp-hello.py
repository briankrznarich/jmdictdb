# This is a simple "hello world" app that can be substituted
# for jmapp.py to check that Apache and mod-wsgi have been
# configured correctly.  The web server should respond to
# the urls http://localhost/jmapp/.

from flask import Flask, escape, request
App = Flask(__name__)
@App.route('/')
def hello():
    name = request.args.get("name", "World")
    return f'Hello, {escape(name)}!'
