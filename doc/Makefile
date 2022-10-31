
INSTALLER = ../tools/install.sh
WEBROOT = ~/public_html
DOC_DIR = /doc            # Requires leading slash if not empty.

  # List of doc files that will be installed to ~/WEBROOT/DOC_DIR/
DOC_FILES = README.txt \
        asciidoctor.css \
        index.html \
        install.html \
        oper.html \
        schema.pdf \
        schema.png \
        tags.html \
        2021-11-update.html \
        2020-06-changes.html \
        2020-06-update.html

all: basic schema updates

.DELETE_ON_ERROR:

%.html : src/%.adoc
	asciidoctor -a linkcss -D . $?

basic: index.html install.html oper.html tags.html
index.html: src/index.adoc
install.html: src/install.adoc
oper.html: src/oper.adoc
tags.html: src/tags.adoc

schema: schema.png schema.pdf
schema.png: src/schema.dia
	dia --export $@ -s 1500x $?
schema.pdf: src/schema.odt
	/usr/bin/libreoffice --headless --convert-to pdf $?
  # Have been unable to generate reasonable quality html output from 
  # LO Writer so dropping support for that for now.
#schema.html: src/schema.odt
#	/usr/bin/libreoffice --headless --convert-to html $?

updates: 2021-11-update.html 2020-06-changes.html 2020-06-update.html
2021-11-update.html: src/2021-11-update.adoc
2020-06-changes.html: src/2020-06-changes.adoc
2020-06-update.html: src/2020-06-update.adoc


install:
	$(INSTALLER) -m 644 -t $(WEBROOT)$(DOC_DIR) $(DOC_FILES)
