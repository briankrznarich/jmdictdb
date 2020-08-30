import sys, os, tempfile, atexit, subprocess, difflib, \
        re, shutil, pdb, unittest, unittest_extensions
from jmdictdb import jdb

Global_setup_done = False
def global_setup():
          # This is done once per module import.
        global Global_setup_done, Workdir
        Global_setup_done = True
        Workdir = mk_temp_dir()

class Test_ (unittest.TestCase):
        def test001(_): do_test (_, 'test001', 'jmdict')

def do_test (_, name, xmltype):
        if not Global_setup_done: global_setup()
          # Paths below are all relative to the tests/ directory.
          # Test source data...
        testdata = 'data/jmparse/%s.xml' % name
        expectpgi = 'data/jmparse/%s.out' % name
        expectlog = 'data/jmparse/%s.log' % name
          # Test intermediate data (actual XML to parse)...
        testxml = '%s/%s.xml' % (Workdir, name)
          # Test output (results) data...
        testpgi = '%s/%s.pgi' % (Workdir, name)
        testlog = '%s/%s.log' % (Workdir, name)
        run = lambda cmd: subprocess.run (cmd, shell=True, check=True)

        opts = "-o %s %s %s" % (testxml,xmltype,testdata)
        run ("../tools/jmbuild.py " + opts)
        opts = "-p -o %s -l %s %s" % (testpgi,testlog,testxml)
        run ("../bin/jmparse.py " + opts)

        with open (expectpgi) as f: expected = f.read()
        with open (testpgi) as f: got = f.read()
        _.assertEqual (expected, got)

        with open (expectlog) as f: expected = f.read()
        with open (testlog) as f: got = f.read()
        got = re.sub (r'^[0-9]{6}-[0-9]{6}-[0-9]+',
                      '000000-000000-0000', got)
        _.assertEqual (expected, got)

def runcmd (cmdln):
        proc = subprocess.Popen (cmdln, shell=True, env=os.environ,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rc = proc.wait()
        stdout, stderr = proc.communicate()
        if rc != 0: raise RuntimeError (stderr)
        return stdout, stderr

def mk_temp_dir (keep=False):
        dirname = tempfile.mkdtemp (prefix='', dir='tmp')
        if not keep: atexit.register (rm_temp_dir, dirname)
        return dirname

def rm_temp_dir (dirname):
        print ("Removing temp directory:", dirname)
        shutil.rmtree (dirname)

if __name__ == '__main__':
        global_setup ()
        unittest.main()
