#!/bin/bash

# This script will compare the DTDs of the specified XML file
# with a saved copy and save a new copy when a difference is
# detected, along with a .diff file recording the differences.
# It may be run conveniently in a nightly cron script to monitor
# an xml file and keep an ongoing history of DTD changes.
#
# NOTE: Before this script is run for the first time on a particular
#   'xml-file', an initial copy of that file should be manually
#   copied into the 'arch-dir' directory.
#
# WARNING: Because archive file copies are distinguished only by
#   date (not time) in the filename, running this twice in the same
#   day with a change to the monitored file in between will result
#   in the archive copy and diff file of the first change being
#   overwritten and lost.
#
# Usage:  xmlarch.sh arch-dir xml-file
#   arch-dir -- Directory in which the saved .xml and .diff
#     files will be kept.  A trailing slash is optional.  Use "."
#     the specify the current directory.]
#   xml-file -- The xml file to be compared to the most recently
#     saved xml file in arch-dir.
#
# Examples:
#   xmlarch.sh ~/xmlarch /home/ftp/pub/Nihongo/JMdict_e
#   xmlarch.sh . /home/ftp/pub/Nihongo/JMnedict.xml

set -e

archloc=${1%'/'}  # Saved files directory, remove any trailing slash.
distfile=$2       # The file being monitored.
BASENAME=`basename $distfile`
BASENAME="${BASENAME%.*}"

  # Generate a warning if there are more than 5 saved files dated within
  # the last 8 days.  This is in case an error in this script results in
  # excessively frequent archiving.
filecnt=`find -mtime -8 -path "${archloc}/${BASENAME}-*.xml" \
           -o -mtime -8 -path "${archloc}/${BASENAME}-*.xml.gz" \
         | wc -l`
if [ $filecnt -gt 5 ]; then
  echo "xmlarch.sh: Warning Will Robinson! too many ($filecnt) files present">&2; fi

  # Extract the DTD from the latest distribution file.
dtdlen=`grep -n ']>' $distfile | sed -s 's/:.*//'`
head -n $dtdlen $distfile > ${archloc}/_new.dtd

  # Extract the DTD from the most recently archived file.
lastfile=`ls -1 ${archloc}/${BASENAME}-*.xml | tail -1`
dtdlen=`grep -n ']>' $lastfile | sed -s 's/:.*//'`
head -n $dtdlen $lastfile > ${archloc}/_last.dtd

  # Compare the two DTDs and if different, make a copy of the
  # changed xml file.
if ! /usr/bin/diff -q ${archloc}/_last.dtd ${archloc}/_new.dtd; then
    dt=`date +%y%m%d`
  echo "DTD change: copying $distfile to ${archloc}/${BASENAME}-${dt}.xml"
  diff -U3 ${archloc}/_last.dtd ${archloc}/_new.dtd \
     >${archloc}/${BASENAME}-${dt}.diff || true
  cp $distfile ${archloc}/${BASENAME}-${dt}.xml
  fi
rm -f ${archloc}/_new.dtd ${archloc}/_last.dtd
exit 0
