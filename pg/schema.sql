-- This script loads a newly created database with the
-- JMdictDB tables, views and other objects preparatory
-- to loading corpora content.

\set ON_ERROR_STOP 1

\ir mktables.sql
\ir loadkw.sql
\ir loadconj.sql
\ir mkviews.sql
\ir imptabs.sql
