#!/bin/sh
# Trivial script for applying multiple JMdictDB database updates.
# First argument is db name, following args are .sql update files.
set -e
db=$1; shift
for upd in $@; do
  echo; echo "Applying update $upd ..."
  psql -d $db -Ujmdictdb -f $upd
  done
