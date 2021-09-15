#!/usr/bin/env python3

# Set the JMdictDB package version number.
#
# This program will set the version number of the jmdictdb Python
# package by writing it into jmdictdb/__version__.py.  The version
# number is derived from the date and hash of the Git HEAD commit.
# It is a text string with four "."-separated parts having the
# format: "YY.MM.DD.vxxxxxxx" where YY, MM, DD are from the date
# of the commit, "v" is a literal "v" character and "xxxxxxx" is
# the 7-character hexadecimal commit hash.  It should be run to
# update the version number before the JMdictDB package is built
# or installed.
#
# This program may be used as Git post-commit and/or post-checkout
# hook by creating symlink(s) to it in .git/hooks/.  However, this 
# is likely to to be unreliable in many cases, eg when a branch or
# revision in which this program doesn't exist is checked out and
# so one should still check or update the version number before 
# relying on it to be accurate.
#
# The JMdictDB package should only be built or installed when there
# are no uncommited changes; any uncommitted changes will be included
# in the package but the version number will misleadingly imply that
# they are not.

import sys, os, subprocess

def main():
        #print ("%s: __file__=%s" % (sys.argv[0],__file__),file=sys.stderr)
        #print ("args: %r" % sys.argv[1:], file=sys.stderr)
        upd_version (locate_vfile(), git_version())

def git_version ():         # Determine the version number.
        cmd = 'git log --date=format:%y.%m.%d --pretty=format:"%cd.v%h"'\
              '|head -1'
        version = subprocess.check_output (cmd, shell=True).strip()
        return version.decode ('utf-8')

def locate_vfile():         # Locate the __version__.py file.
          # We have a relative path to our script in '__file__'
        p = os.path     # For brevity.
          # We may have been executed directly or through a symlink
          # (if it was run by a Git hook for example).  Get our actual
          # filename sans symlinks and from that, our directory.
        our_dir = p.dirname (p.realpath (__file__))
          # Since we know we are in tools/, the package directory is
          # <our-dir>/../jmdictdb/.
        pkgdir = p.normpath (p.join (our_dir,'..','jmdictdb'))
        versionfile = p.join (pkgdir, '__version__.py')
        return versionfile

def upd_version (vfile, version):  # Update the __version__.py file.
        with open (vfile, "w") as fh:
            print ('"%s"' % version, file = fh)

if __name__ == '__main__': main()
