\set dbversion  '''04f177'''

-- IMPORTANT:
-- This is an update to the "jmsess" database (not "jmdict")!

-- IMPORTANT:
-- When this script is executed on a server using a non-UTC timezone
-- it may prematurely expire sessions of logged in users or extend them
-- for up (worst case) 12 hours or so.

-- Updates to jmsess database:
-- + Change the default value for sessions.ts to NOW() from previous
--   value of "timezone('UTC'::text, CURRENT_TIMESTAMP)" which was
--   the value of NOW() (which is in the local timezone) converted to
--   UTC.  The JMdictDB code in module jmcgi generates SQL that compares
--   the 'ts' column to NOW() and produces erroneous results in non-UTC
--   timezones since it is comparing localtime to UTC.  By using localtime
--   NOW() as the default value for 'ts', the code will now correctly
--   compare localtime to localtime.  (This change is a no-op for servers
--   operating with localtime=UTC.)

\set ON_ERROR_STOP
BEGIN;

ALTER TABLE sessions
  ALTER COLUMN ts SET DEFAULT NOW();

COMMIT;
