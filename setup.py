#!/usr/bin/env python3
import setuptools

def get_version():
        with open ("jmdictdb/__version__.py") as fh:
            return fh.read().strip().strip('"\'')

def get_descr():
        with open ("README.md", "r") as fh:
            return fh.read()

setuptools.setup (
        name = "jmdictdb",
        version = get_version(),
        author = "Stuart McGraw",
        author_email = "jmdictdb@mtneva.com",
        description = \
            "A Postgresql database, Python API and web CGI front-end"\
            " for storing and maintaining Japanese dictionary data.",
        long_description = get_descr(),
        long_description_content_type = "text/markdown",
        url = "https://gitlab.com/yamagoya/jmdictdb",
        packages = ['jmdictdb', 'jmdictdb.pylib', 'jmdictdb.views'],
        package_data = {
           'jmdictdb': ['tmpl/*.jinja',   # templates for CGI.
                        'tmpla/*.jinja',  # templates for WSGI.
                        'data/*.csv',     # tag table files.
                        'data/dtd-*.xml', # DTD templates.
                        'data/*.xsl', ]}, # XSL for edict.
        zip_safe = False,
        classifiers = [
            "Programming Language :: Python :: 3",
            "Programming Language :: SQL",
            "License :: OSI Approved :: GPL-2.0-or-later",
            "Operating System :: POSIX", ],
        python_requires = '>=3.6',
        install_requires = ['flask', 'jinja2', 'lxml', 'ply', 'psycopg2'], )
