-- Load the tables that contain conjugation data.
-- This script is normally executed by schema.sql.

\set ON_ERROR_STOP 1

\copy conj FROM ../jmdictdb/data/conj.csv DELIMITER E'\t' CSV HEADER
\copy conjo FROM ../jmdictdb/data/conjo.csv DELIMITER E'\t' CSV HEADER
\copy conotes FROM ../jmdictdb/data/conotes.csv DELIMITER E'\t' CSV HEADER
\copy conjo_notes FROM ../jmdictdb/data/conjo_notes.csv DELIMITER E'\t' CSV HEADER

