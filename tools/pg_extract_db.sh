#!/bin/sh
# This script from:
#  http://madssj.com/blog/2010/04/09/extracting-a-single-database-from-a-pg_dumpall-postgresql-dump/
# It will extract a single database from a multi-database 
# backup created by pg_dumpall.

if [ $# -ne 2 ]
then
echo "Usage: $0 <postgresql sql dump> <db_name>" >&2
exit 1
fi
 
db_file=$1
db_name=$2
 
if [ ! -f $db_file -o ! -r $db_file ]
then
echo "error: $db_file not found or not readable" >&2
exit 2
fi

grep -b '^\\connect' $db_file | grep -m 1 -A 1 "$db_name$" | while read line
do
bytes=`echo $line | cut -d: -f1`
echo "bytes = $bytes" >&2

if [ -z "$start_point" ]
then
echo "setting start_point to $bytes" >&2
start_point=$bytes
echo "start_point = $start_point" >&2
else
echo "setting end_point to $bytes" >&2
end_point=$bytes
echo "end_point = $end_point" >&2
db_length=`expr $end_point - $start_point`
echo "db_length = $db_length" >&2
echo "tail -c +$start_point $db_file | head -c $db_length | tail -n +3 " >&2
tail -c +$start_point $db_file | head -c $db_length | tail -n +3
break
fi
done

echo "after loop start_point = $start_point" >&2
echo "after loop end_point = $end_point" >&2
 
if [ -z "$start_point" ]
then
echo "error: start not found" >&2
exit 3
fi
if [ -z "$end_point" ]
then
echo "error: end not found" >&2
exit 3
fi
 
