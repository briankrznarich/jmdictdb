# This makefile simplifies some of the tasks needed when installing
# the JMdictDB software.
#
# "make all" will print a summary of targets.
#
# The following variables can be adjusted based on your needs...
# Alternatively, they can be overridden when "make" is run as in
# the following example:
#
#    make -fMakefile.inst WEBROOT=/srv/jmdictdb install
#

# Command use to run your Python interpreter.  Note that JMdictDB
# will not run under python2.
PYTHON = python3

# Command to install programs and other files.  The rule actions
# below do not use 'make's ability to install only when the source
# file is newer than the target file; instead the full list of source
# files is unconditionally given to INSTALLER.  The reason is that
# it is possible to checkout a different code version in VCS that
# has some files older than the installed ones; they still need to
# need to be installed despite that.  The standard /usr/bin/install
# would work fine by installing every file.  But our custom installer
# compares the target and source files' mode and content and installs
# only when they differ.  This provides some feedback to the user
# that the files installed were the ones expected in the way 'make'
# used to when installing based on date.
INSTALLER = tools/install.sh

# Install locations...
# If running as root, use system-wide locations.  If running as
# ordinary user, user per-user locations.  Note that the install-sys
# target will check that user is root, and install-user target will
# check that the user is not root.  These checks are only done for
# the install-sys and install-user targets; if you run the dependent
# targets (_install, install-web, etc) you are on your own.
# The root/non-root distinction stems from Python's pip installer
# that uses it to decide whether to install the Python package in
# a system or user location.  AFAICT, there is no way to tell it
# explicitly which to use which is pretty broken IMO.  ('pip install'
# has a --user option but no --system option and 'pip uninstall'
# has neither.)
#
# CMDSDIR specifies where the command line scripts will be installed.
# WEBROOT specifies where the cgi scripts, static html and css
# files go.  The location and names can be changed, but (currently)
# their relative positions must remain the same: the cgi and lib
# dirs must be siblings and the css file goes in their common parent
# directory.

ifeq (0, $(shell id -u))      # Running as root.
  CMDS_DIR = /usr/local/bin
  WEBROOT = /var/www/jmdictdb
else                          # Running as ordinary user.
  CMDS_DIR = ~/.local/bin
  WEBROOT = ~/public_html
  PKGPATH = $(shell $(PYTHON) -msite --user-site)
  PIPOPTS = --user
endif

# Locations of web server subdirectories.
CGI_DIR = $(WEBROOT)/cgi-bin
LIB_DIR = $(WEBROOT)/lib
CSS_DIR = $(WEBROOT)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# You should not need to change anything below here.

CSS_FILES = jmdict.css \
        status_maint.html \
        status_load.html \
        status_blocked.html
WEB_CSS = $(addprefix web/,$(CSS_FILES))

LIB_FILES = .htaccess \
        jmdictdb.ini-sample \
        jmdictdb-pvt.ini-sample
WEB_LIB = $(addprefix web/lib/,$(LIB_FILES))

CGI_FILES = cgiinfo.py \
        conj.py \
        entr.py \
        edconf.py \
        edform.py \
        edhelp.py \
        edhelpq.py \
        edsubmit.py \
        srchform.py \
        srchformq.py \
        srchres.py \
        srchsql.py \
        updates.py \
        user.py \
        users.py \
        userupd.py
WEB_CGI = $(addprefix web/cgi/,$(CGI_FILES))

CMD_FILES = bulkupd.py \
        entrs2xml.py \
        exparse.py \
        jelload.py \
        jmparse.py \
        kdparse.py \
        shentr.py \
        xresolv.py
CMDS = $(addprefix bin/,$(CMD_FILES))

#====== Rules ==========================================================

all:
	@echo 'You must supply an explicit target with this makefile:'
	@echo
	@echo '  install-sys -- Install the jmdictdb package, the web'
	@echo '    cgi scripts, and the command line tools into system-'
	@echo '    wide directories.  You must be running as root to'
	@echo '    execute this target.'
	@echo '  install-user -- Install the jmdictdb package, the web'
	@echo '    cgi scripts, and the command line tools into per-'
	@echo '    user directories.  You must be running as a non-root'
	@echo '    user to execute this target.'
	@echo
	@echo '  install-pkg -- Install the JMdictdb packge (library modules).'
	@echo '  install-web -- Install cgi and other web files to WEBROOT.'
	@echo '  install-cmds -- Install the command line tools to CMDS_DIR.'
	@echo
	@echo 'Each of the above has a corresponding "uninstall-* target.'
	@echo


#------ Install everything ---------------------------------------------
#       All the target directories must exist (except the Python package
#       directory; it will be created by pip).
install-sys: chkroot install_
install-user: chkuser install_
install_: install-pkg install-web install-cmds

#------ Install the jmdictdb Python library ----------------------------
#       If this target is run as root, the jmdictdb package will be
#       installed in the system-wide python libraries.  If run as a
#       normal user it will be installed only for that user, typically
#       in ~/.local/lib/.
install-pkg:
	@echo "Installing the jmdictdb python package..."
	$(PYTHON) tools/upd-version.py
	$(PYTHON) -m pip install $(PIPOPTS) --upgrade --no-deps .

#------ Install command scripts to a bin/ location ---------------------
install-cmds:
	@echo "Installing jmdictdb command line programs to $(CMDS_DIR)..."
	mkdir -p $(CMDS_DIR)
	@$(INSTALLER) -m 755 -t $(CMDS_DIR) $(CMDS)

#------ Install web files to web server location -----------------------
install-web:
	@echo "Installing jmdictdb web files to $(CSS_DIR)..."
	mkdir -p $(CSS_DIR) $(CGI_DIR) $(LIB_DIR)
	@$(INSTALLER) -m 644 -t $(CSS_DIR) $(WEB_CSS)
	@$(INSTALLER) -m 755 -t $(CGI_DIR) $(WEB_CGI)
ifdef PKGPATH
	echo "import sys; sys.path[1:1]=['$(PKGPATH)']">$(CGI_DIR)/pkgpath.py
endif
	@$(INSTALLER) -m 644 -t $(LIB_DIR) $(WEB_LIB)

chkuser:
ifeq (0, $(shell id -u))
	@echo 'You must run make as a regular user (not root) to do a per-user install.'
	@exit 1
endif

chkroot:
ifneq (0, $(shell id -u))
	@echo 'You must run make as root (not a regular user) to do a system-wide install.'
	@exit 1
endif

#------ Uninstall things -----------------------------------------------

uninstall-sys: chkroot uninstall_
uninstall-user: chkuser uninstall_
uninstall_: uninstall-pkg uninstall-web uninstall-cmds
uninstall-pkg:
          # 'pip uninstall', rather incredibly, has no --user option.
          # If doing a user uninstall but there is no jmdictdb per-user
          # package installed, pip will stupidly try to uninstall the
          # system-wide package if there is one.  This will fail due to
          # file permissions normally but with a page of horrible looking
          # stack dumps.
	@echo "Removing the jmdictdb python package (ignoring errors)..."
	-$(PYTHON) -m pip uninstall -y jmdictdb
uninstall-web:
	@echo "Removing jmdictdb web files from $(CSS_DIR)..."
	rm -fv $(addprefix $(CSS_DIR)/,$(CSS_FILES))
	rm -fv $(addprefix $(CGI_DIR)/,$(CGI_FILES))
	rm -fv $(addprefix $(LIB_DIR)/,$(LIB_FILES))
	rm -fv $(CGI_DIR)/pkgpath.py
uninstall-cmds:
	@echo "Removing jmdictdb command line programs from $(CMDS_DIR)..."
	rm -fv $(addprefix $(CMDS_DIR)/,$(CMD_FILES))
