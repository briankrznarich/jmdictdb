#!/bin/sh
# This is a wrapper around the system 'install' command that skips
# running it if the target file exists already with the same permissions
# and content as the repacement file.

usage() {
    echo \
"$0 [-m mode][-n][-v][-h] -t target-dir replacement-file ...
  -m mode -- The chmod mode to set the installed file to.
  -n -- No action: print the command but don't actually execute it.
  -v -- Verbose: print names of files skipped in addition to installed.
  -h -- Print this usage message and exit."; }

while getopts "m:t:nvh" opt; do
    case "$opt" in
    h|\?) usage; exit 0 ;;
    t)  targdir=$OPTARG ;;
    m)  mode=$OPTARG ;;
    n)  noaction=1 ;;
    v)  verbose=1 ;; esac
    done
shift $((OPTIND-1))

for src in $*; do
    b=`basename $src`
    targ=$targdir/$b
    inst=""
    if   [ ! -e $targ ]; then inst=yes  # Target doesn't exist, install.
    else  # Target does exist...
          # If no -m given, use mode from src file.
        if [ -z "$mode" ]; then mode=`stat -c '%a' $src`; fi
          # If the target's mode differs from source, then reinstall.
        if [ "$mode" != `stat -c '%a' $targ` ]; then inst=yes
          # If mode ok, then reinstall if target and source contents differ.
        elif ! diff -q $targ $src >/dev/null; then inst=yes; fi; fi
    if [ "$inst" = yes ]; then
        echo  "install -pm $mode -t $targdir $src"
        if [ -z "$noaction" ]; then install -pm $mode -t $targdir $src; fi
    elif [ -n "$verbose" ]; then
        echo "skipping $src"
        fi
    done
