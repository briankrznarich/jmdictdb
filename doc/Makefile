
INSTALLER = ../tools/install.sh
WEBROOT = ~/public_html
DOC_DIR = /doc            # Requires leading slash if not empty.

  # List of doc files that will be installed to ~/WEBROOT/DOC_DIR/
DOC_FILES = README.txt \
        asciidoctor.css \
        dev.html \
        index.html \
        install.html \
        schema.html \
        schema.pdf \
        schema.png \
        tags.html \
        2020-06-changes.html \
        2020-06-update.html

all: basic schema updates

.DELETE_ON_ERROR:

%.html : src/%.asc
	asciidoctor -a linkcss -D . $?

basic: index.html dev.html install.html tags.html
index.html: src/index.asc
install.html: src/install.asc
dev.html: src/dev.asc
tags.html: src/tags.asc

schema: schema.png schema.pdf
schema.png: src/schema.dia
	dia --export $@ -s 1500x $?
schema.pdf: src/schema.odt
	/usr/bin/libreoffice --headless --convert-to pdf $?
  # Have been unable to generate reasonable quality html output from 
  # LO Writer so dropping support for that for now.
#schema.html: src/schema.odt
#	/usr/bin/libreoffice --headless --convert-to html $?

updates: 2020-06-changes.html 2020-06-update.html
2020-06-changes.html: src/2020-06-changes.asc
2020-06-update.html: src/2020-06-update.asc


install:
	$(INSTALLER) -m 644 -t $(WEBROOT)$(DOC_DIR) $(DOC_FILES)
