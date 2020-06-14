# This makefile simplifies some of the tasks needed when installing
# or updating the jmdictdb files.  It can be used on both Unix/Linux
# and Windows systems, although on the latter you will need to install
# GNU Make, either a native port or from Cygwin.  (The Cywin Make can
# be run directly from a CMD.EXE window -- it is not necessary to run
# it from a Cygwin bash shell.)  On Windows you will likely want to
# change the definition of WEBROOT below.
#
# "make all" will print a summary of targets.
#
# The following items should be adjusted based on your needs...
# Alternatively, they can be overridden when "make" is run as in
# the following example:
#
#    make JMDICTFILE=JMdict "LANGOPT=-g fre"
#
# Command used to run your Python interpreter.  Note that the
# JMdictDB code no longer runs under Python2.
PYTHON = python3

# The JMdict file to download.  Choice is usually between JMdict
# which contains multi-lingual glosses, and JMdict_e that contains
# only English glosses but is 25% smaller and parses faster.
JMDICTFILE = JMdict_e
#JMDICTFILE = JMdict

# Parse out only glosses of the specified language.  If not
# supplied, all glosses will be parsed, regardless of language.
# Language specified using ISO-639-2 3-letter abbreviation.
#LANGOPT = -g eng

# Name of database to load new data into.  The new data is loaded
# into this database first, without changing the in-service
# production database, for any testing needed.  When the database
# has been verified, in can be moved into the production database
# usng the makefile target "activate".
DB = jmnew

# Name of the production database...
DBACT = jmdict

# Name of previous production database (saved when newly
# created database is moved to production status...
DBOLD = jmold

# Postgresql user that will be used to create the jmdictdb
# tables and other objects.  Users defined in the
# python/lib/config.ini file should match.
USER = jmdictdb

# Postgresql user that has select-only (i.e. read-only access
# to the database.  Used only for creating this user in target
# 'jminit'.  Users defined in the python/lib/config.ini file
# should match.
RO_USER = jmdictdbv

# A Postgresql user that has superuser database privs.
PG_SUPER = postgres

# Name of the machine hosting the Postgresql database server.
# If blank, localhost will be used.
HOST =

# Install locations...
# If running as root, install will be system wide.  Otherwise it
# will be for the current user only.
# CMDSDIR specified where the command line scripts will be installed.
# WEBROOT specifies where the cgi scripts, static html and css
# files go.  The location and names can be changed, but (currently)
# their relative positions must remain the same: the cgi and lib
# dirs must be siblings and the css file goes in their common parent
# directory.
# On Windows "~" expansion doesn't seem to work, so you will likely
# want to change the definition of WEBROOT below.  Alternatively, you
# can configure your web server to serve the cgi files directly from
# the development working directory and not use the "web" target in
# this makefile (which installs the cgi files to WEBROOT).

ifeq (0, $(shell id -u))   # If running as root, do system install.
CMDS_DIR = /usr/local/bin
WEBROOT = /var/www/jmdictdb
else                         # Otherwise install for user only.
CMDS_DIR = $(wildcard ~/.local/bin)
WEBROOT = $(wildcard ~/public_html)
endif
CGI_DIR = $(WEBROOT)/cgi-bin
LIB_DIR = $(WEBROOT)/lib
CSS_DIR = $(WEBROOT)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# You should not need to change anything below here.

ifeq ($(HOST),)
PG_HOST =
JM_HOST =
else
PG_HOST = -h $(HOST)
JM_HOST = -r $(HOST)
endif

# CAUTION: Be careful in the file lists below to make sure that the
#  last item is NOT followed by a backslash.  If it is the rules that
#  use the list will not work but there will be no error messages.

CSS_FILES = jmdict.css \
	status_maint.html \
	status_load.html
WEB_CSS = $(addprefix $(CSS_DIR)/,$(CSS_FILES))

LIB_FILES = .htaccess \
	config-sample.ini \
WEB_LIB = $(addprefix $(LIB_DIR)/,$(LIB_FILES))

CGI_FILES = conj.py \
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
WEB_CGI = $(addprefix $(CGI_DIR)/,$(CGI_FILES))

CMD_FILES = bulkupd.py \
	dbcheck.py \
	dbreaper.py \
	entrs2xml.py \
	exparse.py \
	jelload.py \
	jmparse.py \
	kdparse.py \
	resetpw.py \
	shentr.py \
	xresolv.py
CMDS = $(addprefix $(CMDS_DIR)/,$(CMD_FILES))

#====== Rules ==========================================================

all:
	@echo 'You must supply an explicit target with this makefile.'
	@echo
	@echo 'Targets are in two groups, one for targets related to installing the'
	@echo 'JMdictDB software, the other for loading a JMdictDB database from'
	@echo 'various sources.'
	@echo
	@echo 'Software install targets.  These should be executed as root if'
	@echo 'if installing into system directories.'
	@echo '  install -- Install the jmdictdb package, the web cgi scripts,'
	@echo '    and the command line tools.'
	@echo '  package -- Install the JMdictdb packge (library modules).'
	@echo '  web -- Install cgi and other web files to the appropriate places.'
	@echo '  commands -- Install the command line tools.'
	@echo
	@echo 'Database loading targets:'
	@echo '  newdb -- Create an empty database named "jmnew".'
	@echo '  jmnew -- Create a database named "jmnew" with jmdictdb tables and '
	@echo '    jmdictdb objects created but no data loaded.'
	@echo
	@echo '  data/jmdict.xml -- Get latest jmdict xml file from Monash.'
	@echo '  data/jmdict.pgi -- Create intermediate file from jmdict.xml file.'
	@echo '  loadjm -- Load jmdict into existing database "jmnew".'
	@echo
	@echo '  data/jmnedict.xml -- Get latest jmnedict xml file from Monash.'
	@echo '  data/jmnedict.pgi -- Create intermediate file from jmdict.xml file.'
	@echo '  loadne -- Load jmnedict into existing database "jmnew".'
	@echo
	@echo '  data/examples.txt -- Get latest Examples file from Monash.'
	@echo '  data/examples.pgi -- Create intermediate file from examples.xml file.'
	@echo '  loadex -- Load examples into the existing database "jmnew".'
	@echo
	@echo '  data/kanjidic2.xml -- Get latest kanjidic2.xml file from Monash.'
	@echo '  data/kanjidic2.pgi -- Create intermediate file from examples.xml file.'
	@echo '  loadkd -- Load kanjidic into the existing database "jmnew".'
	@echo '   * WARNING: kanjidic2 support is usable but incomplete.'
	@echo
	@echo '  loadall -- Initialize database "jmnew" and load jmdict, jmnedict'
	@echo '    and examples.'
	@echo '  activate -- Rename the "jmnew" database to "jmdict".'
	@echo
	@echo '  * NOTE: "make loadall" will do all needed database initialization.'
	@echo '  To load a subset of loadall (eg only loadjm and loadne), you should'
	@echo '  do "make jmnew", then "make loadjm", "make loadne", etc as desired,'
	@echo '  then the last step should be "make postload".'

#------ Create jmsess and jmdictdb users ---------------------------------

    # Run this target only once when creating a jmdictdb server
    # installation.  Creates a jmsess database and two dedicated
    # users that the jmdictdb app will use to access the database.

init:
	# Assume any errors from 'createuser' are due to the user
	# already existing and ignore them.
	-createuser $(PG_HOST) -U $(PG_SUPER) -SDRP $(USER)
	-createuser $(PG_HOST) -U $(PG_SUPER) -SDRP $(RO_USER)
	# Don't automatically drop old session database due to risk
	# of unintentionally loosing user logins and passwords.  If
	# it exists, the subsequent CREATE  DATABASE command will
	# fail and require the user to manually drop the session
	# database or otherwise manually correct the situation.
	#psql $(PG_HOST) -U $(PG_SUPER) -d postgres -c 'drop database if exists $(DBSESS)'
	psql $(PG_HOST) -U $(PG_SUPER) -d postgres -c 'create database jmsess'
	psql $(PG_HOST) -U $(PG_SUPER) -d jmsess -c "CREATE EXTENSION IF NOT EXISTS pgcrypto"
	cd pg && psql $(PG_HOST) -U $(USER) -d jmsess -f mksess.sql
	@echo 'Remember to add jmdictdb editors to the jmsess "users" table.'

#------ Create a blank jmnew database ----------------------------------
#
# This may be useful when loading a dump of a jmdictdb database, e.g:
#   make newdb                       # Create blank jmnew database
#   pg_restore -O jmdictdb -d jmnew  # Restore the dump into jmnew.
#   make activate                    # Rename jmnew to jmdict.

newdb:
	psql $(PG_HOST) -U $(PG_SUPER) -d postgres -c 'drop database if exists $(DB)'
	psql $(PG_HOST) -U $(PG_SUPER) -d postgres -c "create database $(DB) owner $(USER) template template0 encoding 'utf8'"

#------ Create a new jmnew database with empty jmdictdb objects --------

jmnew: newdb
	cd pg && psql $(PG_HOST) -U $(USER) -d $(DB) -f schema.sql

#------ Move installation database to active ----------------------------

activate:
	psql $(PG_HOST) -U $(PG_SUPER) -d $(DB) -c 'SELECT 1' >/dev/null # Check existance.
	psql $(PG_HOST) -U $(PG_SUPER) -d postgres -c 'drop database if exists $(DBOLD)'
	-psql $(PG_HOST) -U $(PG_SUPER) -d postgres -c 'alter database $(DBACT) rename to $(DBOLD)'
	psql $(PG_HOST) -U $(PG_SUPER) -d postgres -c 'alter database $(DB) rename to $(DBACT)'

#------ Restore foreign key and index definitions -----------------------

postload:
	psql $(PG_HOST) -U $(PG_SUPER) -d $(DB) -f 'pg/syncseq.sql'
	  # Resolving xrefs below is lookup intensive so make sure we have good stats...
	psql $(PG_HOST) -U $(PG_SUPER) -d $(DB) -c 'vacuum analyze'
	  # Try to resolve unresolved xrefs.  Running these multiple times is innocuous.
	cd python && $(PYTHON) xresolv.py -d postgres://$(USER)@$(HOST)/$(DB) -i \
           -sjmdict   -tjmdict   -verror >../data/jmdict_xresolv.log 2>&1
	cd python && $(PYTHON) xresolv.py -d postgres://$(USER)@$(HOST)/$(DB) -i \
           -sjmnedict -tjmnedict -verror >../data/jmnedict_xresolv.log 2>&1
	cd python && $(PYTHON) xresolv.py -d postgres://$(USER)@$(HOST)/$(DB) -i \
           -sexamples -tjmdict   -verror >../data/examples_xresolv.log 2>&1
	psql $(PG_HOST) -U $(PG_SUPER) -d $(DB) -c 'vacuum analyze'
	@echo 'Remember to check the log files for warning messages.'

#------ Load JMdict -----------------------------------------------------

data/jmdict.xml:
	rm -f $(JMDICTFILE).gz
	wget ftp://ftp.monash.edu.au/pub/nihongo/$(JMDICTFILE).gz
	gzip -d $(JMDICTFILE).gz
	mv $(JMDICTFILE) data/jmdict.xml

data/jmdict.pgi: data/jmdict.xml
	cd python && $(PYTHON) jmparse.py $(LANGOPT) -l ../data/jmdict.log -o ../data/jmdict.pgi ../data/jmdict.xml

loadjm: data/jmdict.pgi
	rm -f data/jmdict_xresolv.log
	psql $(PG_HOST) -U $(USER) -d $(DB) -c 'DELETE FROM imp.kwsrc'
	PGOPTIONS=--search_path=imp,public psql $(PG_HOST) -U $(USER) -d $(DB) -f data/jmdict.pgi
	psql $(PG_HOST) -U $(USER) -d $(DB) -v 'src=1' -f pg/import.sql

#------ Load JMnedict ----------------------------------------------------

# Assumes the jmdict has been loaded into database already.

data/jmnedict.xml:
	rm -f JMnedict.xml.gz
	wget ftp://ftp.monash.edu.au/pub/nihongo/JMnedict.xml.gz
	gzip -d JMnedict.xml.gz
	mv JMnedict.xml data/jmnedict.xml

data/jmnedict.pgi: data/jmnedict.xml
	cd python && $(PYTHON) jmparse.py -q5000000,1 -l ../data/jmnedict.log -o ../data/jmnedict.pgi ../data/jmnedict.xml

loadne: data/jmnedict.pgi
	rm -f data/jmnedict_xresolv.log
	psql $(PG_HOST) -U $(USER) -d $(DB) -c 'DELETE FROM imp.kwsrc'
	PGOPTIONS=--search_path=imp,public psql $(PG_HOST) -U $(USER) -d $(DB) -f data/jmnedict.pgi
	psql $(PG_HOST) -U $(USER) -d $(DB) -v 'src=2' -f pg/import.sql

#------ Load examples ---------------------------------------------------

data/examples.txt:
	rm -f examples.utf.gz
	wget ftp://ftp.monash.edu.au/pub/nihongo/examples.utf.gz
	gzip -d examples.utf.gz
	mv examples.utf data/examples.txt

data/examples.pgi: data/examples.txt
	cd python && $(PYTHON) exparse.py -o ../data/examples.pgi -l ../data/examples.log ../data/examples.txt

loadex: data/examples.pgi
	rm -f data/examples_xresolv.log
	psql $(PG_HOST) -U $(USER) -d $(DB) -c 'DELETE FROM imp.kwsrc'
	PGOPTIONS=--search_path=imp,public psql $(PG_HOST) -U $(USER) -d $(DB) -f data/examples.pgi
	psql $(PG_HOST) -U $(USER) -d $(DB) -v 'src=3' -f pg/import.sql

#------ Load kanjidic2.xml ---------------------------------------------------

data/kanjidic2.xml:
	rm -f kanjidic2.xml.gz
	wget ftp://ftp.monash.edu.au/pub/nihongo/kanjidic2.xml.gz
	gzip -d kanjidic2.xml.gz
	mv kanjidic2.xml data/kanjidic2.xml

data/kanjidic2.pgi: data/kanjidic2.xml
	cd python && $(PYTHON) kdparse.py -g en -o ../data/kanjidic2.pgi -l ../data/kanjidic2.log ../data/kanjidic2.xml

loadkd: data/kanjidic2.pgi
	rm -f data/kanjidic2_xresolv.log
	psql $(PG_HOST) -U $(USER) -d $(DB) -c 'DELETE FROM imp.kwsrc'
	PGOPTIONS=--search_path=imp,public psql $(PG_HOST) -U $(USER) -d $(DB) -f data/kanjidic2.pgi
	psql $(PG_HOST) -U $(USER) -d $(DB) -v 'src=4' -f pg/import.sql

#------ Load jmdict, jmnedict, examples -------------------------------------

loadall: jmnew loadjm loadne loadex postload
	@echo 'Remember to check the log files for warning messages.'

reloadall: loadclean loadall
	@echo 'Remember to check the log files for warning messages.'

loadclean:
	-cd data && rm jmdict.pgi jmdict.log jmdict_xresolv.log \
          jmnedict.pgi jmnedict.log jmnedict_xresolv.log \
          examples.pgi examples.log examples_xresolv.log \
          kanjdic2.pgi kanjdic2.log

#------ Install everything ---------------------------------------------
install: install-pkg install-web install-cmds

#------ Install the jmdictdb Python library ----------------------------
#       If this target is run as root, the jmdictdb package will be
#       installed in the system-wide python libraries.  If run as a
#       normal user it will be installed only for that user, typically
#       in ~/.local/lib/.
install-pkg:
	$(PYTHON) -m pip install --upgrade --no-deps .

#------ Install command scripts to a bin/ location ---------------------
install-cmds: $(CMDS)
$(CMDS): $(CMDS_DIR)/%: bin/%
	@echo install -pm 755 $? $@

#------ Install cgi files to web server location -----------------------
install-web:	webcgi webcss weblib

webcss: $(WEB_CSS)
$(WEB_CSS): $(CSS_DIR)/%: web/%
	install -pm 644 $? $@

webcgi: $(WEB_CGI)
$(WEB_CGI): $(CGI_DIR)/%: web/cgi/%
	install -p -m 755 $? $@

weblib: $(WEB_LIB)
$(WEB_LIB): $(LIB_DIR)/%: web/lib/%
	install -p -m 644 $? $@

#------ Uninstall things -----------------------------------------------
uninstall: uninstall-pkg uninstall-web uninstall-cmds
uninstall-pkg:
	$(PYTHON) -m pip uninstall jmdictdb
uninstall-web:
uninstall-cmds:
	rm $(CMDS)

#------ Other ----------------------------------------------------------

.DELETE_ON_ERROR:

subdirs:
	cd pg/ && $(MAKE)
	cd python/lib/ && $(MAKE)

clean:
	rm -f jmdict.tgz
	find -name '*.log' -type f -print0 | xargs -0 /bin/rm -f
	find -name '*~' -type f -print0 | xargs -0 /bin/rm -f
	find -name '*.tmp' -type f -print0 | xargs -0 /bin/rm -f
	find -name '\#*' -type f -print0 | xargs -0 /bin/rm -f
	find -name '\.*' -type f -print0 | xargs -0 /bin/rm -f
