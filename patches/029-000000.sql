\set ON_ERROR_STOP
BEGIN;

-- is-255: fix conjugation tables for v1, v1-s verbs.
-- We also correct two 'descr' values in table kwpos to match the
-- descriptions used in the JMdict XML DTD and remove an unused
-- item from table kwcinf.
-- This update is idempotent and can be applied to any database
-- version.  It does not update the database version number.

-- Do the update...
-- We include the erroneous value to be corrected in the WHERE
--  clause (which is not strictly necessary) for two reasons:
--  1) it makes clearer what is being changed.
--  2) without the erroneous values in the WHERE clauses the queries
--     will always report that records were changed.  With them the
--     queries will report 0 records changed if the records have
--     already been updated, a minor but possibly useful piece of
--     information for the person doing the updating.

UPDATE conjo SET okuri='ません'
  WHERE pos IN (28,29) AND conj=1 AND neg AND fml AND onum=1
    AND okuri='ました';

UPDATE kwpos SET descr='expressions (phrases, clauses, etc.)'
  WHERE kw='exp' AND descr LIKE 'Expressions (phrases, clauses, etc.)';
UPDATE kwpos SET descr='suru verb - included'
  WHERE kw='vs-i' AND descr='suru verb - irregular';

DELETE FROM kwcinf WHERE KW='gahoh';  -- Not used anymore

COMMIT;
