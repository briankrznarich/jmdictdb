-- This file is recreated during the database build process.
-- See pg/Makefile for details.

\set ON_ERROR_STOP 1
DROP INDEX IF EXISTS entr_seq;
DROP INDEX IF EXISTS entr_stat;
DROP INDEX IF EXISTS entr_dfrm;
DROP INDEX IF EXISTS entr_unap;
DROP INDEX IF EXISTS rdng_txt;
DROP INDEX IF EXISTS rdng_txt1;
DROP INDEX IF EXISTS rdng_txt2; --For fast LIKE 'xxx%'
DROP INDEX IF EXISTS kanj_txt;
DROP INDEX IF EXISTS kanj_txt1;
DROP INDEX IF EXISTS kanj_txt2; --For fast LIKE 'xxx%'
DROP INDEX IF EXISTS gloss_txt;
DROP INDEX IF EXISTS gloss_txt1;
DROP INDEX IF EXISTS gloss_txt2; --For case-insensitive LIKE 'xxx%'
DROP INDEX IF EXISTS gloss_txt3; 		    --For case-insensitive '='
DROP INDEX IF EXISTS xref_xentr;
DROP INDEX IF EXISTS hist_dt;
DROP INDEX IF EXISTS hist_email;
DROP INDEX IF EXISTS hist_userid;
DROP INDEX IF EXISTS freq_idx1;
DROP INDEX IF EXISTS grp_kw;
DROP INDEX IF EXISTS sndfile_vol;
DROP INDEX IF EXISTS entrsnd_snd;
DROP INDEX IF EXISTS rdngsnd_snd;
DROP INDEX IF EXISTS xresolv_rdng;
DROP INDEX IF EXISTS xresolv_kanj;
DROP INDEX IF EXISTS chr_chr;
DROP INDEX IF EXISTS cinf_kw;
DROP INDEX IF EXISTS cinf_val;
ALTER TABLE entr DROP CONSTRAINT IF EXISTS entr_src_fkey;
ALTER TABLE entr DROP CONSTRAINT IF EXISTS entr_stat_fkey;
ALTER TABLE entr DROP CONSTRAINT IF EXISTS entr_dfrm_fkey;
ALTER TABLE rdng DROP CONSTRAINT IF EXISTS rdng_entr_fkey;
ALTER TABLE kanj DROP CONSTRAINT IF EXISTS kanj_entr_fkey;
ALTER TABLE sens DROP CONSTRAINT IF EXISTS sens_entr_fkey;
ALTER TABLE gloss DROP CONSTRAINT IF EXISTS gloss_entr_fkey;
ALTER TABLE gloss DROP CONSTRAINT IF EXISTS gloss_lang_fkey;
ALTER TABLE xref DROP CONSTRAINT IF EXISTS xref_entr_fkey;
ALTER TABLE xref DROP CONSTRAINT IF EXISTS xref_xentr_fkey;
ALTER TABLE xref DROP CONSTRAINT IF EXISTS xref_typ_fkey;
ALTER TABLE xref DROP CONSTRAINT IF EXISTS xref_rdng_fkey;
ALTER TABLE xref DROP CONSTRAINT IF EXISTS xref_kanj_fkey;
ALTER TABLE hist DROP CONSTRAINT IF EXISTS hist_entr_fkey;
ALTER TABLE hist DROP CONSTRAINT IF EXISTS hist_stat_fkey;
ALTER TABLE dial DROP CONSTRAINT IF EXISTS dial_entr_fkey;
ALTER TABLE dial DROP CONSTRAINT IF EXISTS dial_kw_fkey;
ALTER TABLE fld DROP CONSTRAINT IF EXISTS fld_entr_fkey;
ALTER TABLE fld DROP CONSTRAINT IF EXISTS fld_kw_fkey;
ALTER TABLE freq DROP CONSTRAINT IF EXISTS freq_entr_fkey;
ALTER TABLE freq DROP CONSTRAINT IF EXISTS freq_entr_fkey1;
ALTER TABLE freq DROP CONSTRAINT IF EXISTS freq_kw_fkey;
ALTER TABLE kinf DROP CONSTRAINT IF EXISTS kinf_entr_fkey;
ALTER TABLE kinf DROP CONSTRAINT IF EXISTS kinf_kw_fkey;
ALTER TABLE lsrc DROP CONSTRAINT IF EXISTS lsrc_entr_fkey;
ALTER TABLE lsrc DROP CONSTRAINT IF EXISTS lsrc_lang_fkey;
ALTER TABLE misc DROP CONSTRAINT IF EXISTS misc_entr_fkey;
ALTER TABLE misc DROP CONSTRAINT IF EXISTS misc_kw_fkey;
ALTER TABLE pos DROP CONSTRAINT IF EXISTS pos_entr_fkey;
ALTER TABLE pos DROP CONSTRAINT IF EXISTS pos_kw_fkey;
ALTER TABLE rinf DROP CONSTRAINT IF EXISTS rinf_entr_fkey;
ALTER TABLE rinf DROP CONSTRAINT IF EXISTS rinf_kw_fkey;
ALTER TABLE restr DROP CONSTRAINT IF EXISTS restr_entr_fkey;
ALTER TABLE restr DROP CONSTRAINT IF EXISTS restr_entr_fkey1;
ALTER TABLE stagr DROP CONSTRAINT IF EXISTS stagr_entr_fkey;
ALTER TABLE stagr DROP CONSTRAINT IF EXISTS stagr_entr_fkey1;
ALTER TABLE stagk DROP CONSTRAINT IF EXISTS stagk_entr_fkey;
ALTER TABLE stagk DROP CONSTRAINT IF EXISTS stagk_entr_fkey1;
ALTER TABLE grp DROP CONSTRAINT IF EXISTS grp_entr_fkey;
ALTER TABLE grp DROP CONSTRAINT IF EXISTS grp_kw_fkey ;
ALTER TABLE sndvol DROP CONSTRAINT IF EXISTS sndvol_corp_fkey;
ALTER TABLE sndfile DROP CONSTRAINT IF EXISTS sndfile_vol_fkey;
ALTER TABLE snd DROP CONSTRAINT IF EXISTS snd_file_fkey;
ALTER TABLE entrsnd DROP CONSTRAINT IF EXISTS entrsnd_entr_fkey;
ALTER TABLE entrsnd DROP CONSTRAINT IF EXISTS entrsnd_entr_fkey1;
ALTER TABLE rdngsnd DROP CONSTRAINT IF EXISTS rdngsnd_entr_fkey;
ALTER TABLE rdngsnd DROP CONSTRAINT IF EXISTS rdngsnd_entr_fkey1;
ALTER TABLE xresolv DROP CONSTRAINT IF EXISTS xresolv_entr_fkey;
ALTER TABLE xresolv DROP CONSTRAINT IF EXISTS xresolv_typ_fkey;
ALTER TABLE chr DROP CONSTRAINT IF EXISTS chr_entr_fkey;
ALTER TABLE cinf DROP CONSTRAINT IF EXISTS chr_entr_fkey;
ALTER TABLE cinf DROP CONSTRAINT IF EXISTS chr_kw_fkey;
ALTER TABLE kresolv DROP CONSTRAINT IF EXISTS kresolv_entr_fkey;
