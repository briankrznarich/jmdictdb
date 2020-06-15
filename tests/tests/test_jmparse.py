import sys, os, tempfile, atexit, subprocess, difflib, \
        shutil, pdb, unittest, unittest_extensions

Global_setup_done = False
def global_setup():
        # This is done once per invocation
        global Global_setup_done, Workdir
        Global_setup_done = True
        Workdir = mk_temp_dir ("tmp", keep=False)

class Test_ (unittest.TestCase):
    def test001(_): do_test (_, "test001", "dtd-jmdict.xml")

def do_test (_, name, dtdfile):
        if not Global_setup_done: global_setup()
          # Following are all relative to the working directory, Workdir.
        jmbuild = "../../tools/jmbuild.py"
        jmparse = "../../bin/jmparse.py"
        dtdpath = "../../jmdictdb/%s" % dtdfile
        testdata = "../../data/jmparse/%s.xml" % name

        subprocess.call (cwd=Workdir, shell=True,
                         args="python3 %s %s %s >%s.xml"
                           % (jmbuild, dtdpath, testdata, name))
        so,se = runcmd (Workdir, "python3 %s -o %s.out -l %s.log %s.xml" %
                                  (jmparse, name, name, name))
        with open ("data/jmparse/%s.out" % name,  encoding='utf-8') as f:
            expected = f.read()
        with open ("%s/%s.out" % (Workdir, name), encoding='utf-8') as f:
            produced = f.read()
        if expected == produced: diff = ''
        else: diff = diff_strings (expected, produced)
        _.assertFalse (diff, msg=diff)

        with open ("data/jmparse/%s.log" % name, encoding='utf-8') as f:
            expected = f.read()
        with open ("%s/%s.log" % (Workdir, name), encoding='utf-8') as f:
            produced = f.read()
        if expected == produced: diff = ''
        else: diff = diff_strings (expected, produced)
        _.assertFalse (diff, msg=diff)

def runcmd (wkdir, cmdln):
        proc = subprocess.Popen (cmdln, shell=True, cwd=wkdir,
                    env=os.environ,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rc = proc.wait()
        stdout, stderr = proc.communicate()
        if rc != 0: raise RuntimeError (stderr)
        return stdout, stderr

def mk_temp_dir (in_dir=".", keep=False):
        dirname = tempfile.mkdtemp ("tmp", dir=in_dir)
        if not keep: atexit.register (rm_temp_dir, dirname)
        return dirname

def rm_temp_dir (dirname):
        if sys.platform == 'win32': dirname = str(dirname)
        else: dirname = dirname.encode(sys.getfilesystemencoding())
        print ("Removing", dirname)
        shutil.rmtree (dirname)

def diff_strings (a, b):
        """Return ndiff between two strings containing lines.
        A trailing newline is added if missing to make the strings
        print properly."""

        if b and b[-1] != '\n': b += '\n'
        if a and a[-1] != '\n': a += '\n'
        #difflines = difflib.ndiff(a.splitlines(True), b.splitlines(True),
        #                          linejunk=lambda x: False, charjunk=lambda x: False)
        difflines = difflib.unified_diff(a.splitlines(True), b.splitlines(True), n=0)
        return ''.join(difflines)

if __name__ == '__main__':
        global_setup ()
        unittest.main()
