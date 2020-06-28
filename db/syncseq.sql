-- Copyright (c) 2007 Stuart McGraw
-- SPDX-License-Identifier: GPL-2.0-or-later

SELECT setval('entr_id_seq',  (SELECT max(id) FROM entr));
SELECT setval('snd_id_seq',  (SELECT max(id) FROM snd));
SELECT setval('sndfile_id_seq',  (SELECT max(id) FROM sndfile));
SELECT setval('sndvol_id_seq',  (SELECT max(id) FROM sndvol));

-- The following function (defined in mktables.sql) resets the
-- state of the sequences that generate entry "seq" column values.
-- The values must be reset following a bulk load of data or any
-- other load tha gets seq numbers from somewhere other than the
-- sequence tables.

SELECT syncseq();
