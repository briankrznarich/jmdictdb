# JMdictDB project

JMdictDB is a project to put the contents of [Jim Breen's]()
JMdict Japanese-English dictionary data into a Postgresql
database and provide a web-based maintenance system for it.
JMdictDB is written primarily in Python and requires a Postgresql
database server and an Apache web server for operation.  It is
currently capable of loading and serving data from the
[JMdict](http://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project) (Japanese words),
[JMnedict](http://www.edrdg.org/enamdict/enamdict_doc.html) (Japanese names)
and [Kanjidic2](http://www.edrdg.org/wiki/index.php/KANJIDIC_Project) (kanji)
dictionaries and the Tatoeba example sentences [*1].

Discussion takes place on the edict-jmdict@yahoo.com mailing
list (http://groups.yahoo.com/group/edict-jmdict/)

The software in this package is copyrighted by
Stuart McGraw, <jmdictdb@mtneva.com>
(except where otherwise noted)
and licensed under the GNU General Public License version 2+.
See the file LICENSE.txt for details.

JMdictDB comes with ABSOLUTELY NO WARRANTY.

The most recent version of this code may be downloaded at:
  http://gitlab.com/yamagoya/jmdictdb/

## STATUS

JMdictDB is under continual development and the code should
be considered alpha quality.  Everything here is subject to
future change.

JMdictDB runs under Linux (or likely any Unix-like operating
system).  At one time it also ran under
Windows but the principle developer's loss of access to a
Windows machine made continued support for that OS impossible.

JMdictDB requires a Postgresql database server and an Apache
web server.  Web pages are implemented in Python with CGI.

Python code is written for Python 3; Python 2 is no longer
supported (although an older Python 2 version is available
from the code repository.

For full details on requirements and installation instructions
see doc/INSTALLATION.txt.

The JMdictDB system is currently running on Jim Breen's
wwwjdic web sites:
 (http://www.edrdg.org/cgi-bin/wwwjdic/wwwjdic and mirrors)
where it is used to accept additions and corrections to the
wwwjdic/JMdict and JMnedict data from wwwjdic users.

The public development repository is maintained at GitLab:
  https://gitlab.com/yamagoya/jmdictdb/
GitLab Issues may be used to submit bug reports, feature
requests, etc.

## DOCUMENTATION

This file, README.txt, provides an overview and general information
about JMdictDB.  More detailed information including installation
and operation instructions can be found in the ./doc/ directory.

Additional information is available at:
- http://www.edrdg.org/~smg/  Project page of principal developer
- ...

## CONTENTS

The JMdictDB software directory is organized as follows:

    ./                   JMdictDB software root.
    ./doc/               Documentation.
    ./db/                Database installation scripts.
    ./db/updates/        Updates for in situ databases.
    ./bin/               Command line programs.
    ./jmdictdb/          Python library package.
    ./jmdictdb/data      Static data and xml templates.
    ./jmdictdb/tmpl/     Web page templates.
    ./tests/             Tests.
    ./tools/             Scripts useful in development.
    ./web/               Web related files.
    ./web/cgi/           CGI scripts.

## Notes:
[*1] https://tatoeba.org; JMdictDB requires the format as distributed in http://ftp.monash.edu/pub/nihongo/examples.utf.gz (description at http://ftp.monash.edu/pub/nihongo/)
