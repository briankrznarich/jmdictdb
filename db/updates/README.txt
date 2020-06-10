This directory contains update files that are used for migrating an
existing JMdictDB database to a state matching that which would be
created by a new install.  It is only necessary to apply those updates
that are more recent than the JMdictDB software used to create the
database initially.  That is, when a new database is created it
already incorporates all updates to that point in time.

Generally the updates are applied using Postgresql's 'psql' tool.
It should be run as the database user (using the -U option) that
owns the objects in the database (typically "jmdictdb") and specify
the database to update (typically "jmdict"):

  $ psql -d jmdict -U jmdictdb -f patches/024-20c2fe.sql

However, there may be exceptions which will be documented in the
comments in the file so you should look at the contents of the
update file before applying it.

Updates will generally be applied in numerical order although
some may be optional.

Updates with a "s" after the leading three digits are updates
to the session database (which is independent of the main jmdict
database.)

A new, random six-character hash can be generated with:
  python -c 'import random;print("%06.6x"%random.randint(0,16777215))'

Old format:
-----------
Up through 2017 (old/001.sql through old/023.sql) updates were applied
using the program tools/patchdb.py.  This tool is no longer used but
may still be recovered from the git source code repository revision:
  b2ec2a79 (2018-04-08): "edconf.jinja: another typo, cosmetic only"
The patch files have been moved to the old/ subdirectory.
