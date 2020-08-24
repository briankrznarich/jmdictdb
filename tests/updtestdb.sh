#!/bin/sh
# Trivial script for apply a db update (or several)
# to the jmtest01 database.  Intentded to be run when
# cd'd to the tests/ subdirectory.
#
# Usage:
#   cd tests/
# ./updtest.sh ../db/updates/<nnn-xxxxxx>.sql ...
#
# FYI: to get current version of of jmtest01.sql:
#   $ git checkout -- test/data/jmtest01.sql
# To get earlier version (eg to redo multiple updates):
#   $ git show <rev>:./data/jmtest01.sql >data/jmtest.sql 

set -e
DB=jmtest01
DBFILE=data/${DB}.sql
echo Loading fresh copy of test database from $DBFILE
./load-testdb.sh $DBFILE
for upd in $@; do
  echo; echo "Applying update $upd to $DB..."
  psql -d ${DB} -Ujmdictdb -f $upd
  done
echo Saving updated test database to $DBFILE
  # Use -f option rather than ">" redirection because the latter will
  # overwrite the output file with an empty file for even trivial failures.
pg_dump ${DB} -f $DBFILE
