#!/usr/bin/bash
# This procedure will parse a JMdict or JMnedict XML file (using
# jmparse.py), load it into a temporary database, then dump that
# database out (using entrs2xml.py) to a temporary XML file.  The
# input and output XML files are compared; there should be no
# difference.
# 
# Usage:
#   $ cd python/tests/
#   $ tests/xml-rt.sh [-d dbname][-c][-h] <filename.xml>
#
# <filename.xml> is the path to a jmdict or jmnedict xml file.
# The -d option can be used to specify a database other than
# the default of "jmnew" to use for loading the parsed xml file.
# This is useful when running multiple invocations of this script
# simultaneously.
# The -c (clean) option will remove old temporary files but should
# not be use when running multiple invocations.
# -h will print a brief help message.
#
# This script should be run from the JMdictDB python/tests/ directory.
# It is not run automatically by runtests.py since it takes a fairly
# long time (several minutes) to complete.
#
# Warning: This procedure will overwrite any existing database given
#  by the -d option (default is "jmnew").
# Note: this script requires you to have permission to drop and create
# new Postgresql databases.

set -e
DBNAME=jmnew
TMPDIR=./tmp
OUTFILE=$TMPDIR/rtsh-$$.xml
TMPPGI=$TMPDIR/rtsh-$$.pgi
TMPLOG=$TMPDIR/rtsh-$$a.log
TMPLOG2=$TMPDIR/rtsh-$$b.log
  # We need a kwsrc.id number to use for the parsed data loaded
  # into the temporary database.  It can be arbitrary.
SRCID=1
clean=0

usage() { echo "\
Usage: $script [-d dbname][-c] filename.xml
  dbname -- Name of scratch database to use.  Will be dropped
    and overwritten.
  -c -- cleanup: remove temp files from previous runs.  Dont
    use if this script is running simultaneously in other 
    processes." 1>&2; }
while getopts "cd:" opt; do
    case "$opt" in
        h|\?) usage; exit 0;;
        d)  DBNAME=$OPTARG;;
        c)  clean=yes;;
        esac
    done
shift $((OPTIND-1))
INPFILE=$1

  # Remove any old temp files...
if [ $clean = "yes" ]; then echo rm -fv $TMPDIR/rtsh-*; fi
  # Following is based on the "loadjm" and "postload" targets
  #  of ../../Makefile.  Input file is data/jmdict.xml, intermediate
  #  files are written to python/tests/tmp/ as is the output xml
  #  file, jmdict-out.xml.
set -ex
../jmparse.py  -l $TMPLOG -o $TMPPGI $INPFILE
psql  -U postgres -d postgres -c "drop database if exists $DBNAME"
psql  -U postgres -d postgres -c "create database $DBNAME owner \
    jmdictdb template template0 encoding 'utf8'"
(cd ../../pg && psql  -U jmdictdb -d $DBNAME -f schema.sql
  psql -U jmdictdb -d $DBNAME -c "DELETE FROM imp.kwsrc"
  PGOPTIONS=--search_path=imp,public psql -U jmdictdb -d $DBNAME \
     -f ../python/tests/$TMPPGI
  psql -U jmdictdb -d $DBNAME -v "src=$SRCID" -f import.sql
  psql -U postgres -d $DBNAME -f 'syncseq.sql'
  psql -U postgres -d $DBNAME -c 'vacuum analyze' )

  # Don't resolve xrefs.  If left unresolved they will produce the same
  # <xref> elements when written back to xml.  If resolve attempted, some
  # will succeed, some fail and order of produced <xref> tags after writing
  # back to xml will be altered causing spurious differences.
##../xresolv.py -d postgres://jmdictdb@/$DBNAME -i \
##    -sjmdict -tjmdict -vwarning >$TMPLOG2 2>&1

  # dump the database back out as xml.  Use blocksize of 20K as the
  # default of 1K is pretty slow.
../entrs2xml.py -d $DBNAME -B20000 -s$SRCID -o $OUTFILE

  # ...and compare to original input xml.  We filter the diff output to
  # eliminate the expected difference in the timestamps and use grep's
  # -c option to get a count of the differing lines.
set +ex  # Unset option -e so diff status 1 won't exit, x for cosmetics
  # Warning: the following is intended to ignore an expected difference
  # the creation date comment in the XML files.  However it also ignores
  # the root name which is also in the comment and which could differ
  # wrongly, a difference that should be reported.
ndiffs=`/usr/bin/diff -U0 $INPFILE $OUTFILE \
  | egrep -v '^((@@)|(---)|(\+\+\+))' \
  | egrep -c -v '<!-- [a-zA-Z]+ created: [0-9]{4}-[0-9]{2}-[0-9]{2} -->'`
if [ $ndiffs != "0" ]; then
  echo "**** Differences found! ****"
  echo -e "To view, run:\n  diff $INPFILE $OUTFILE"
else
  echo "No differences found"; fi

##############################################################################
# The following two shell scripts may be useful in comparing xml
# output above...
#-----------------------------------------------------------------------------
## cmp.sh
## Compare the input and output files of tests/xml-rt.sh and report
## the seq numbers of xml entries that differ.  It works by converting
## the newlines preceeding entries to formfeeds, delete all newlines,
## then convert formfeeds back to newlines.  This puts each entry
## entirely on one line.  Then the two files can be diffed and the
## sequence numbers extracted.
#cat ../../data/jmdict.xml | sed -e 's/<!-- JMdict created.*//' | sed -e 's/<entry>/\f<entry>/'|tr -d '\n' |tr '\f' '\n' >tmp/f1.xml
#cat tmp/jmdict-out.xml    | sed -e 's/<!-- JMdict created.*//' | sed -e 's/<entry>/\f<entry>/'|tr -d '\n' |tr '\f' '\n' >tmp/f2.xml
#/usr/bin/diff -U0 tmp/f1.xml tmp/f2.xml | sed -Ee 's=.*<ent_seq>([0-9]+)</ent_seq>.*=\1='|grep -v '@@'|sort -u
#-----------------------------------------------------------------------------
## cmp2.sh
## Compare the input and output files of tests/xml-rt.sh and report
## the full xml of entries that differ.  It works by converting
## the newlines preceeding entries to formfeeds, convert all newlines
## to a placeholder character, then convert formfeeds back to newlines.
## This puts each entry entirely on one line.  Then the two files can
## be diffed with the differences being entire entries that are made
## readable again my converting the placeholder characters back to
## newlines.  The "JMdict created" replacement is to eliminate the
## creation date line which will usually differ and cause the entire
## DTD, on which it is on a single line with, to differ.
#cat ../../data/jmdict.xml | sed -e 's/<!-- JMdict created.*//' | sed -e 's/<entry>/\f<entry>/'|tr '\n' '\001' |tr '\f' '\n' >tmp/f1.xml
#cat tmp/jmdict-out.xml    | sed -e 's/<!-- JMdict created.*//' | sed -e 's/<entry>/\f<entry>/'|tr '\n' '\001' |tr '\f' '\n' >tmp/f2.xml
#/usr/bin/diff -U0 tmp/f1.xml tmp/f2.xml | tr '\001' '\n'
