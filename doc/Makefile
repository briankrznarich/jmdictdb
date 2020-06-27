
INSTALLER = ../tools/install.sh
WEBROOT = ~/public_html
DOC_DIR = /doc            # Requires leading slash if not empty.

  # List of doc files that will be installed to ~/WEBROOT/DOC_DIR/
DOC_FILES = README.txt \
        asciidoctor.css \
        index.html \
        install.html \
        schema.html \
        schema.pdf \
        schema.png \
        2020-06-changes.html \
        2020-06-update.html

all: basic schema updates

.DELETE_ON_ERROR:

basic: index.html install.html
index.html: src/index.asc
	asciidoctor -a linkcss -D . $?
install.html: src/install.asc
	asciidoctor -a linkcss -D . $?

schema: schema.png schema.pdf schema.html
schema.png: src/schema.dia
	dia --export $@ -s 1500x $?
schema.pdf: src/schema.odt
	/usr/bin/libreoffice --headless --convert-to pdf $?
schema.html: src/schema.odt
	/usr/bin/libreoffice --headless --convert-to html $?

updates: 2020-06-changes.html 2020-06-update.html
2020-06-changes.html: src/2020-06-changes.asc
	asciidoctor -a linkcss -D . $?
2020-06-update.html: src/2020-06-update.asc
	asciidoctor -a linkcss -D . $?

install:
	$(INSTALLER) -m 644 -t $(WEBROOT)$(DOC_DIR) $(DOC_FILES)
