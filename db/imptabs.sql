-- Create the schema used for loading corpus data initially
-- prior to its migration to the main "public" schema.
-- This script is normally executed by schema.sql.

\set ON_ERROR_STOP

DROP SCHEMA IF EXISTS imp CASCADE;
CREATE SCHEMA imp;
SET search_path TO imp, public;

-- Create a copy of the tables that contain corpra entry data
-- in the "imp" schema.  Data from external sources will be loaded
-- here prior to being moved to the main tables in the "public"
-- schema.

BEGIN;
\ir entrobjs.sql
COMMIT;
