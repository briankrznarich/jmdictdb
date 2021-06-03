#!/bin/bash

# This script will make an archive copy of a monitored XML file
# when the monitored file's DTD changes from the most recently 
# archived copy.
#
# Usage: xmlarch.sh /home/ftp/pub/Nihongo/JMdict_e
#        xmlarch.sh /home/ftp/pub/Nihongo/JMnedict.xml

set -e

ARCHLOC=/home/smg/xmlarch/
distfile=$1
BASENAME=`basename $distfile`
BASENAME="${BASENAME%.*}"

  # Check the number of files present in the archive directory 
  # and warn if more than a fixed limit.  This is in case an
  # error in this script results in excessively frequent archiving.
filecnt=`ls -1 $ARCHLOC | wc -l`
if [ $filecnt -gt 5 ]; then 
  echo "xmlarch.sh: Warning Will Robinson! $filecnt files present">&2; fi

  # Extract the DTD from the latest distribution file.
dtdlen=`grep -n ']>' $distfile | sed -s 's/:.*//'`
head -n $dtdlen $distfile > ${ARCHLOC}_new.dtd

  # Extract the DTD from the most recently archived file.
lastfile=`ls -1 ${ARCHLOC}${BASENAME}-*.xml | tail -1`
dtdlen=`grep -n ']>' $lastfile | sed -s 's/:.*//'`
head -n $dtdlen $lastfile > ${ARCHLOC}_last.dtd

  # Compare the two DTDs and if different, make a copy of the
  # changed xml file.
if ! /usr/bin/diff -q ${ARCHLOC}_last.dtd ${ARCHLOC}_new.dtd; then
    dt=`date +%y%m%d`
  echo "DTD change: copying $distfile to ${ARCHLOC}${BASENAME}-${dt}.xml"
  diff -U3 ${ARCHLOC}_last.dtd ${ARCHLOC}_new.dtd \
     >${ARCHLOC}${BASENAME}-${dt}.diff || true
  cp $distfile ${ARCHLOC}${BASENAME}-${dt}.xml
  fi
rm -f ${ARCHLOC}_new.dtd ${ARCHLOC}_last.dtd
exit 0
