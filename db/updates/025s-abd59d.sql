\set dbversion  '''abd59d'''

-- IMPORTANT:
-- This is an update to the "jmsess" database (not "jmdict")!
-- Before executing this script, load the "pgcrypto" extension.  Note
-- that you need to have access (eg know the password for) the database
-- superuser account, "postgres" (or an equivalent database superuser
-- account):
--   $ psql -d jmsess -U postgres -c 'CREATE EXTENSION IF NOT EXISTS pgcrypto'
-- Then, run this script as the "jmsess" database owner (eg, "jmdictdb"):
--   $ psql -d jmsess -U jmdictdb -f patches/025s-7375f3.sql
-- (where "nnn-xxxxxx.sql" is the names of this script.)

-- IMPORTANT:
-- The jmsess database version implemented by this script is not compatible
-- with JMdictDB software versions earlier than the version that introduced
-- this script.  This script and the corresponding JMdictDB software upgrade
-- must be applied at the same time.
-- When this script is executed it will invalidate all currently active
-- jmdictdb sessions: users that were logged into a jmdictdb web page
-- will be logged out.

-- NOTE: This script uses functions from the pgcrypto extention which must
-- be installed (one time only) before this script is executed.  It can be
-- installed by a database superuser (e.g. user "postgres") with the sql
-- command:
--   CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- We don't install it here because this script may be run by a user
-- with insuffcient privilege.

-- Updates to jmsess database
-- + Add datbase version identification table and related items.
-- + Add addional field users.editor to allow for future non-editor
--     users.
-- + Change sessions.id from 64-bit int to 96-bit modified base64 text
--     string.  The "+" and "/" characters used in standard base64 are
--     replaced with "-" and "_" because the latter, unlike the former,
--     are usable in URLs without encoding.
-- + A random session.id is automatically generated by default.
-- + Add additional fields sessions.svc and sessions.state for future
--     use.

\set ON_ERROR_STOP
BEGIN;

CREATE TABLE db (
    id INT PRIMARY KEY,
    active BOOLEAN DEFAULT TRUE,
    ts TIMESTAMP DEFAULT NOW());
INSERT INTO db(id) VALUES(x:dbversion::INT);
CREATE OR REPLACE VIEW dbx AS (
    SELECT LPAD(TO_HEX(id),6,'0') AS id, active, ts
    FROM db
    ORDER BY ts DESC);
CREATE OR REPLACE FUNCTION err(msg TEXT) RETURNS boolean AS $body$
    BEGIN RAISE '%', msg; END;
    $body$ LANGUAGE plpgsql;

ALTER TABLE users RENAME TO xusers;
DROP TABLE sessions;
CREATE TABLE users (
        userid VARCHAR(16) PRIMARY KEY,
        fullname TEXT,
        email TEXT,
        pw TEXT,
        disabled BOOLEAN NOT NULL DEFAULT false,
        -- priv: null:user, 'E':editor, 'A':admin+editor.
        priv CHAR(1) CHECK (strpos('EA', priv)>0),
        notes TEXT);
CREATE TABLE sessions (
        id TEXT PRIMARY KEY DEFAULT
          translate (encode (gen_random_bytes (12), 'base64'), '+/', '-_'),
        userid VARCHAR(64)
          REFERENCES users(userid) ON DELETE CASCADE ON UPDATE CASCADE,
        ts TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
        svc VARCHAR(64),
        state JSONB DEFAULT NULL);
CREATE INDEX sessions_userid ON sessions(userid);
CREATE INDEX sessions_ts ON sessions(ts);

INSERT INTO users (
        SELECT userid, fullname, email,
               crypt(pw, gen_salt('bf')),
               disabled, 'E', notes
        FROM xusers);
DROP TABLE xusers;

COMMIT;