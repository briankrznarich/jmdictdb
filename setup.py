#!/usr/bin/python3
import setuptools

with open ("README.md", "r") as fh:
        long_description = fh.read()

setuptools.setup (
        name="jmdictdb",
        version="2020.06.01",
        author="Stuart McGraw",
        author_email="jmdictdb@mtneva.com",
        description="A Postgresql database, Python API and web CGI front-end"\
                    " for storing and maintaining Japanese dictionary data.",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://gitlab.com/yamagoya/jmdictdb",
        packages=setuptools.find_packages(),
        package_data={'jmdictdb': ['tmpl/*.jinja', 'data/*.csv',
                                   'data/dtd-*.xml', 'data/*.xsl']},
        zip_safe = False,
        classifiers=[
            "Programming Language :: Python :: 3",
            "Programming Language :: SQL",
            "License :: OSI Approved :: GPL-2.0-or-later",
            "Operating System :: POSIX", ],
        python_requires='>=3.6',
        install_requires = ['jinja2', 'lxml', 'ply', 'psycopg2'], )
