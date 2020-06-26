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

