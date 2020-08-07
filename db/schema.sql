-- This script loads a newly created database with the
-- JMdictDB tables, views and other objects preparatory
-- to loading corpora content.

\set ON_ERROR_STOP 1

\qecho "Creating core JMdicDB database objects (db/mktables.sql)..."
\ir mktables.sql

\qecho "Loading the keyword tables (db/loadkw.sql)..."
\ir loadkw.sql

\qecho "Loading the conjugation tables (db/loadconj.sql)..."
\ir loadconj.sql

\qecho "Creating views (db/mkviews.sql)..."
\ir mkviews.sql

\qecho "Creating and loading the import schema (db/imptabs.sql)..."
\ir imptabs.sql
