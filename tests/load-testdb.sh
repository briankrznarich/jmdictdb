#!/usr/bin/bash
set -e

usage() { echo "\
Usage: $script [-d dbname] filename.sql
  filename.sql -- Name of a file containing a Postgresql database dump in
      sql (non-compressed) format.  The .sql extension is mandatory.
  dbname -- Name of database to load.  If not given, the filename sans
      the .sql exension will be used for the database name.  Any existing
      database with this name will be dropped and its data lost." 1>&2; }
while getopts "hd:" opt; do
    case "$opt" in
        h|\?) usage; exit 0;;
        d)  dbname=$OPTARG;;
        esac
    done
shift $((OPTIND-1))
dbfile=$1

fullfn=`realpath "$dbfile"`
hash=`sha1sum "$dbfile" | cut -d' ' -f1`
dbname=${dbname:-`basename "$dbfile" .sql`}
export PGOPTIONS="-c client-min-messages=warning"
export PGOPTIONS="--client-min-messages=warning"
dropdb --if-exists $dbname
createdb -Ojmdictdb $dbname
echo "Loading database $dbname, it may take a few minutes..."
psql -v ON_ERROR_STOP=1 -d $dbname -f $dbfile >/dev/null
cat <<EOF  | psql -v 'ON_ERROR_STOP=1' -d $dbname >/dev/null
DROP TABLE IF EXISTS testsrc;
CREATE TABLE testsrc (filename TEXT, method TEXT, hash TEXT);
INSERT INTO testsrc VALUES('$fullfn','sha1','$hash');
EOF
echo "Database $dbname loaded from $dbfile"
