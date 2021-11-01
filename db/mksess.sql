-- Copyright (c) 2008 Stuart McGraw
-- SPDX-License-Identifier: GPL-2.0-or-later

-- Schema for JMdictDB users/sessions database.

-- Note: the gen_random_bytes() function used below is in the pgcrypto
-- extention which must be installed (one time only) before this script
-- is executed.  It can be installed by a database superuser (e.g. user
-- "postgres") with the sql command:
--   CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- We don't install it here because this script may be run by a user
-- with insuffcient privilege.

\set ON_ERROR_STOP
\set updateid '''04f177'''

-- Database update table (see comments in mktables.sql).
CREATE TABLE db (
    id INT PRIMARY KEY,
    active BOOLEAN DEFAULT TRUE,
    ts TIMESTAMP DEFAULT NOW());
INSERT INTO db(id) VALUES(x:updateid::INT);
CREATE OR REPLACE VIEW dbx AS (
    SELECT LPAD(TO_HEX(id),6,'0') AS id, active, ts
    FROM db
    ORDER BY ts DESC);

-- Users and sessions tables.

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
        ts TIMESTAMP DEFAULT NOW(),
        svc VARCHAR(64) DEFAULT NULL,
        state JSONB DEFAULT NULL);
CREATE INDEX sessions_userid ON sessions(userid);
CREATE INDEX sessions_ts ON sessions(ts);

-- Add an initial user.
INSERT INTO users VALUES ('admin', 'Admin User', 'admin@localhost',
                           crypt('admin', gen_salt('bf')), FALSE, 'A', NULL);
