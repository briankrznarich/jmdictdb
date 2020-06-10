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
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: GPL2",
            "Operating System :: OS Independent", ],
        python_requires='>=3.6',

        install_requires = ['jinja', 'lxml', 'ply', 'psycopg2'], )
