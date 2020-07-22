-- Load all the kw* tables from CSV data.
-- This script is normally executed by schema.sql.

\set ON_ERROR_STOP 1
-- We don't want any quote character but AFAICT Postgresql insists on
-- something so we use a character that should never occur in the data,
-- a backspace ('\b').
\copy kwdial from '../jmdictdb/data/kwdial.csv' CSV delimiter E'\t' quote E'\b'
\copy kwfreq from '../jmdictdb/data/kwfreq.csv' CSV delimiter E'\t' quote E'\b'
\copy kwfld  from '../jmdictdb/data/kwfld.csv'  CSV delimiter E'\t' quote E'\b'
\copy kwginf from '../jmdictdb/data/kwginf.csv' CSV delimiter E'\t' quote E'\b'
\copy kwkinf from '../jmdictdb/data/kwkinf.csv' CSV delimiter E'\t' quote E'\b'
\copy kwlang from '../jmdictdb/data/kwlang.csv' CSV delimiter E'\t' quote E'\b'
\copy kwmisc from '../jmdictdb/data/kwmisc.csv' CSV delimiter E'\t' quote E'\b'
\copy kwpos  from '../jmdictdb/data/kwpos.csv'  CSV delimiter E'\t' quote E'\b'
\copy kwrinf from '../jmdictdb/data/kwrinf.csv' CSV delimiter E'\t' quote E'\b'
\copy kwstat from '../jmdictdb/data/kwstat.csv' CSV delimiter E'\t' quote E'\b'
\copy kwxref from '../jmdictdb/data/kwxref.csv' CSV delimiter E'\t' quote E'\b'
\copy kwcinf from '../jmdictdb/data/kwcinf.csv' CSV delimiter E'\t' quote E'\b'
\copy kwsrct from '../jmdictdb/data/kwsrct.csv' CSV delimiter E'\t' quote E'\b'
\copy kwsrc  from '../jmdictdb/data/kwsrc.csv'  CSV delimiter E'\t' quote E'\b'
\copy rad from '../jmdictdb/data/rad.csv' CSV HEADER delimiter E'\t' quote E'\b'

