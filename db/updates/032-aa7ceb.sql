\set ON_ERROR_STOP
BEGIN;

-- Remove obsolete tags, update tag descriptions to match DTD.

\set dbversion  '''aa7ceb'''  -- Update version applied by this update.
-- This update is supplementary and does not change any other updates
-- that are present.
INSERT INTO db(id) VALUES(x:dbversion::INT);

-- Do the update...

-- Delete RINF.oik and MISC.eK tags.
-- Removing tags is a little complicated because there may be entries
-- that use them.  Active entries should be edited by the usual means
-- and the tags removed or replaced prior to applying this update.
-- But there may be deleted or rejected entries for which this is
-- difficult.  In these cases we add a history note describing the
-- deletion since there won't be any "diff" field showing it (since
-- the deletion is made in-place rather than submitting an edit,
-- previous history records will show its addition but it will no
-- longer be present, an inconsistency the new note will explain.)
--
-- Also note that we identify and delete tags based on both id number
-- and kw string.  This is to protect against erroneous deletion should
-- this script get run again after a new tag is added that ruses the
-- same id number.
--
-- FIXME: the "SELECT COALESCE..." subselects below used to get the next
--  hist.hist number are definately not concurency safe and likely won't
--  even work for creating multiple history notes in the same entry.
--  Probably need a window function counting rows from a base value
--  given by that SELECT.

WITH del AS (
      -- Delete the MISC.eK tag on any entries.
    DELETE FROM misc i USING kwmisc k
        WHERE i.kw=k.id AND k.id=7 AND k.kw='eK' RETURNING entr,sens,k.kw)
    INSERT INTO hist (entr,hist,stat,unap,name,notes)
        (SELECT e.id,
            1+(SELECT COALESCE (MAX(hist),0) FROM hist WHERE entr=e.id),
            e.stat, e.unap,'dbmaint',
            'In-situ deletion of MISC '''
              || d2.kw || ''' tag from sens #'
              || d2.senss
         FROM entr e
         JOIN
            (SELECT entr, string_agg(sens::TEXT,', ') AS senss, kw
             FROM del GROUP BY entr,kw) AS d2 on d2.entr=e.id);
DELETE FROM kwmisc WHERE id=7 AND kw='eK';      -- Delete the tag itself.

WITH del AS (
      -- Delete the RINF.oik tag on any entries.
    DELETE FROM rinf i USING kwrinf k
        WHERE i.kw=k.id AND k.id=21 AND k.kw='oik' RETURNING entr,rdng,k.kw)
      -- Using the deleted rows returned above, insert notes into the
      -- "hist" lists on each of the entries.
    INSERT INTO hist (entr,hist,stat,unap,name,notes)
        (SELECT e.id,
            1+(SELECT COALESCE (MAX(hist),0) FROM hist WHERE entr=e.id),
            e.stat, e.unap,'dbmaint',
            'In-situ deletion of RINF '''
              || d2.kw || ''' tag from reading #'
              || d2.rdngs
         FROM entr e
         JOIN
            (SELECT entr, string_agg(rdng::TEXT,', ') AS rdngs, kw
             FROM del GROUP BY entr,kw) AS d2 on d2.entr=e.id);
DELETE FROM kwrinf WHERE id=21 AND kw='oik';    -- Delete the tag itself.

-- Bring tag descriptions into conformance with current JMdict XML DTD.

UPDATE kwdial SET descr='Hokkaido-ben'
    WHERE kw='hob' AND descr='Hokkaidou-ben';

UPDATE kwfld SET descr=replace(descr,'terminology','term')
     WHERE descr LIKE '%terminology%';
UPDATE kwfld SET descr='computer term'
    WHERE kw='comp' AND descr='computing term';
UPDATE kwfld SET descr='mathematics'
    WHERE kw='math' AND descr='mathematics term';
UPDATE kwfld SET descr='military'
    WHERE kw='mil' AND descr='military term';

UPDATE kwpos SET descr='adjective (keiyoushi) - yoi/ii class'
    WHERE kw='adj-ix' AND descr='yoi/ii i-adjective';

UPDATE kwpos SET descr=replace(descr, 'shiku ', '`shiku'' ')  WHERE kw IN ('adj-shiku');
UPDATE kwpos SET descr=replace(descr, 'kari ',  '`kari'' ')   WHERE kw IN ('adj-kari');
UPDATE kwpos SET descr=replace(descr, 'ku ',    '`ku'' ')     WHERE kw IN ('adj-ku','v4k','v2k-k','v2k-s');
UPDATE kwpos SET descr=replace(descr, ' gu ',   ' `gu'' ')    WHERE kw IN ('v4g','v2g-k','v2g-s');
UPDATE kwpos SET descr=replace(descr, ' su ',   ' `su'' ')    WHERE kw IN ('v4s','v2s-s');
UPDATE kwpos SET descr=replace(descr, ' tsu ',  ' `tsu'' ')   WHERE kw IN ('v4t','v2t-k','v2t-s');
UPDATE kwpos SET descr=replace(descr, ' nu ',   ' `nu'' ')    WHERE kw IN ('v4n','v2n-s');
UPDATE kwpos SET descr=replace(descr, ' bu ',   ' `bu'' ')    WHERE kw IN ('v4b','v2b-k','v2b-s');
UPDATE kwpos SET descr=replace(descr, ' mu ',   ' `mu'' ')    WHERE kw IN ('v4m','v2m-k','v2m-s');
UPDATE kwpos SET descr=replace(descr, ' dzu ',  ' `dzu'' ')   WHERE kw IN ('v2d-k','v2d-s');
UPDATE kwpos SET descr=replace(descr, ' hu/fu ',' `hu/fu'' ') WHERE kw IN ('v4h','v2h-k','v2h-s');
UPDATE kwpos SET descr=replace(descr, ' yu ',   ' `yu'' ')    WHERE kw IN ('v2y-k','v2y-s');
UPDATE kwpos SET descr=replace(descr, ' ru ',   ' `ru'' ')    WHERE kw IN ('v4r','v2r-k','v2r-s');
UPDATE kwpos SET descr=replace(descr, ' zu ',   ' `zu'' ')    WHERE kw IN ('v2z-s');
UPDATE kwpos SET descr=replace(descr, ' u ',    ' `u'' ')     WHERE kw IN ('v2w-s');
UPDATE kwpos SET descr=replace(descr, ' we ',   ' `we'' ')    WHERE kw IN ('v2w-s');

UPDATE kwrinf SET descr='gikun (meaning as reading) or jukujikun (special kanji reading)'
    WHERE kw='gikun' AND descr='gikun (meaning) reading';

-- At this point the "descr" fields all match the old DTD.  Last change
-- is to replace the back-quotes with regular single quotes which is the
-- convention that will be used in the DTD going forward.  Note that
-- there are additional rows with back-quotes in addition to the ones
-- updated above.

UPDATE kwpos SET descr=replace(descr,'`','''') WHERE descr LIKE '%`%';

COMMIT;
