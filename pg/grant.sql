-- Based on code given in:
-- http://kennii.wordpress.com/2007/09/21/postgres-grant-privileges-to-all-tables-in-a-database/
CREATE FUNCTION pg_grant (
       action TEXT,	 -- Either 'GRANT' or 'REVOKE'.
       rolenm TEXT, 	 -- Name of role to grant to or revoke from.
       privnm TEXT, 	 -- Privilege to grant or revoke.
       objpat TEXT,	 -- A "like" pattern that ohects must match.
       schemanm TEXT)	 -- Name of schema in which to look for objects.
       RETURNS integer AS '
    DECLARE obj RECORD; num INTEGER:=0; actionp TEXT:=' TO  ';
    BEGIN
        if action = 'REVOKE' THEN actionp := ' FROM ';
        FOR obj IN
                SELECT relname
                FROM pg_class c
                JOIN pg_namespace ns ON c.relnamespace = ns.oid
                WHERE relkind in (''r'',''v'',''S'') AND nspname = schemanm AND relname LIKE objpat LOOP
            EXECUTE action || ' ' || permnm || '' ON '' || obj.relname || actionp || rolenm;
            num := num + 1;
            END LOOP;
        RETURN num;
        END;'
    LANGUAGE plpgsql;

