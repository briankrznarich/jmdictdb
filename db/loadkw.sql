-- Load all the kw* tables from CSV data.
-- This script is normally executed by schema.sql.

\set ON_ERROR_STOP 1
\copy kwdial from '../jmdictdb/data/kwdial.csv' CSV delimiter E'\t'
\copy kwfreq from '../jmdictdb/data/kwfreq.csv' CSV delimiter E'\t'
\copy kwfld  from '../jmdictdb/data/kwfld.csv'  CSV delimiter E'\t'
\copy kwginf from '../jmdictdb/data/kwginf.csv' CSV delimiter E'\t'
\copy kwkinf from '../jmdictdb/data/kwkinf.csv' CSV delimiter E'\t'
\copy kwlang from '../jmdictdb/data/kwlang.csv' CSV delimiter E'\t'
\copy kwmisc from '../jmdictdb/data/kwmisc.csv' CSV delimiter E'\t'
\copy kwpos  from '../jmdictdb/data/kwpos.csv'  CSV delimiter E'\t'
\copy kwrinf from '../jmdictdb/data/kwrinf.csv' CSV delimiter E'\t'
\copy kwstat from '../jmdictdb/data/kwstat.csv' CSV delimiter E'\t'
\copy kwxref from '../jmdictdb/data/kwxref.csv' CSV delimiter E'\t'
\copy kwcinf from '../jmdictdb/data/kwcinf.csv' CSV delimiter E'\t'
\copy kwsrct from '../jmdictdb/data/kwsrct.csv' CSV delimiter E'\t'
\copy kwsrc  from '../jmdictdb/data/kwsrc.csv'  CSV delimiter E'\t'
\copy rad    from '../jmdictdb/data/rad.csv'    CSV HEADER delimiter E'\t'

