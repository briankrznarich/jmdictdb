#!/usr/bin/env python3

# A tool and supporting functions for mapping between hg and git
# revision numbers after a hg->git conversion by "fast-export".
# (ref: https://github.com/frej/fast-export)

import sys, os.path, time, bisect, json

def main (cmdln_args):
        args = parse_cmdline (cmdln_args)
        if '/' in args.json: jsonfn = args.json
        else: jsonfn = os.path.join (args.dir, args.json)
        map = None
        if not args.write_json:
            try: map = json.load (open (jsonfn))
            except OSError: pass
            if args.verbose and map:
                print ("JSON map read from %s" % jsonfn)
        if not map:
            map = revs_map (dir=args.dir)
            if args.verbose and map:
                print ("Read fast-export maps from %s" % args.dir)
        if not map:
            sys.exit("Error, no mapping files found")
        if args.write_json:
            jmap = revs_json (map=map)
            open (jsonfn, "w").write(jmap)
            if args.verbose:
                print ("Wrote JSON map to %s" % jsonfn)
        for rev in args.revs:
            try: revx = lookup (map, rev)
            except KeyAmbigError:
                print ("ambiguous: %s" % (rev,), file=sys.stderr)
            except KeyError:
                print ("not found: %s" % (rev,), file=sys.stderr)
            else:
                if args.long: print ("%s: %s (%s)" % revx)
                else: print ("%s-%s" % (revx[2], revx[1][:7]))

def revs_map (dir='.git', use_prefixes=False,
              marks_fn='hg2git-marks', mapping_fn='hg2git-mapping'):
        """
        Given the two mapping files produced by the hg-fast-export
        mercurial to git repostitory converter, this function will
        return a python dict instance than maps both hg revision
        numbers to git revision numbers and visa versa.
        The pairs can be looked up by prefix using function lookup()
        below.  If 'use_prefixes' is true, hg revision numbers will
        be prefixed with "hg:" and git ones with "git:".
        """

        marks_path = os.path.join (dir, marks_fn)
        mapping_path = os.path.join (dir, mapping_fn)
          # Marks file maps marks (range 1 to N) to git rev number.
        marks = read_marks (marks_path)
          # Mapping file maps hg rev number to mark# (range 0 to N-1).
        mapping = read_mapping (mapping_path)
        if len (mapping) != len (marks):
            raise ValueError ("mapping-marks length mismmatch")
        hggit = {}
        hgpre, gitpre = ('hg:', 'git:') if use_prefixes else ('', '')
        for mark,hgrev in mapping.items():
            gitrev = marks[mark]
            hggit[hgpre+hgrev] = (gitpre+gitrev, 'git')
            hggit[gitpre+gitrev] = (hgpre+hgrev, 'hg')
        return hggit

def revs_json (map=None, dir='.git',
               marks_fn='hg2git-marks', mapping_fn='hg2git-mapping'):
        """
        If hg-to-git map, 'map', is not None, return it as a
        json-encoded string.  Otherwise generate a map (using
        revs_map()) from the 'dir', marks_fn' and 'mapping_fn'
        arguments and return it as a json-encoded string.
        """

        import json
        if map is None:
            map = revs_map (marks_fn, mapping_fn, dir)
        return json.dumps (map, sort_keys=True, indent=2)

class KeyAmbigError (KeyError): pass

def lookup (hggit, rev):
        """
        Lookup a revision number (either hg or git) 'rev' in the dict
        'hggit' which was created by revs_map().  'rev' may be abbreviated
        to a prefix.  If ambiguous (multiple entries exist in 'hggit'
        with that prefix, a KeyAmbigError is raised.  If no key exists
        with that prefix or value a python KeyError is raised.  If a
        single matching rev number is found, a 3-tuple of the key, value
        and vcs type of value ('hg' or 'git') from 'hggit' is returned.
        """

        if len (hggit) == 0: raise KeyError(rev)
        revs = sorted (hggit.keys())
        ip = bisect.bisect_left (revs, rev)
        if ip >= len (revs): raise KeyError (rev)
        candidate = revs[ip]
        if rev == candidate: return (candidate,)+tuple(hggit[candidate])
        if not candidate.startswith (rev):
            raise KeyError(rev)
        if ip < len(revs) and revs[ip+1].startswith (rev):
            raise KeyAmbigError(rev)
        return (candidate,)+tuple(hggit[candidate])

def read_marks (marks_fn):
        result = {}
        for ln in open (marks_fn):
            mark, gitrev = ln.split()
              # mark numbers range from 1 to N inclusive.  Subtract
              # one below to shift range to 0 to N-1 to match mapping
              # file.
            result[int(mark.strip(':'))-1] = gitrev
        return result

def read_mapping (mapping_fn):
        result = {}
        for ln in open (mapping_fn):
            hgrev, mark = ln.split()
              # mark numbers range from 0 to N-1 inclusive.
            result[int(mark)] = hgrev.strip(':')
        return result

def parse_cmdline (cmdln_args):
        import argparse
        p = argparse.ArgumentParser (prog=cmdln_args[0],
            description="Lookup hg or git equivalent revision numbers.")
        p.add_argument ("revs", nargs='*',
            help="Zero or more revision numbers to lookup.")
        p.add_argument ("-l", "--long", default=False,
            action="store_true",
            help="Print full hashes for both the requested hash and "
                "found hash.  If not given a short hash is printed "
                "for only the found hash.")
        p.add_argument ("-j", "--json", default="hg2git.json",
            help="Filename of JSON mappping file to read (or write "
                "if --write is given).  Default is \"hg2git.json\".  "
                "If the filename does not contain a \"/\" character, "
                "the file will be looked for in (or written to) the "
                "directory named by --dir.")
        p.add_argument ("-w", "--write-json", default=False,
            action="store_true",
            help="Generate a revision map from the hg2git mapping file "
                "produced by fast-export and write the map as JSON to "
                "the filename given by --json.")
        p.add_argument ("-v", "--verbose", default=False,
            action="store_true",
            help="Print info about reading/writing mapping files.")
        p.add_argument ("-d", "--dir", default="../doc/hg2git",
            help="Directory to look for mapping files in.  Default "
                "is ../doc/hg2git")
        args = p.parse_args (cmdln_args[1:])
        return args

if __name__ == '__main__': main (sys.argv)
