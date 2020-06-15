# Compare tags in pg/data/*.csv with tags in jmtest01 database.
#
# These tests compare the contents two Kwds instances, one loaded
# from the pg/dayta/*.csv files, the other loaded from the jmtest01
# database.
#
# Since the jmtest01 database should always be at the current database
# patch level and thus have the current tag set when we compare those
# tags with the tags as defined in the csv files we check that:
#   - the patch file has been applyed to the jmtest01 database
#   - the updates made by the patch file are consistent with the
#     changes made to the *.csv files.

import sys, pdb, unittest
from jmdb import DBmanager
from jmdictdb import jdb

Cursor = None
def setUpModule():
       global Cursor
       Cursor = DBmanager.use ("jmtest01", "data/jmtest01.sql")

KwdsAttrs = set (('DIAL','FLD','FREQ','GINF','KINF','LANG','MISC','POS',
                  'RINF','SRC','SRCT','STAT','XREF','CINF','GRP','COPOS'))

def add_domain_tests (cls):
        for domain in KwdsAttrs:
              # We use default argument values in the lambda expression
              # they are bound when the "setattr(...lambda...) line
              # is executed.  Otherwise, the lambda arguments will be
              # evaluated when the lambda is, and will contain the
              # values that the variable had when the loop was exited.
            setattr (cls, 'test_cmp_%s' % domain,
                     lambda self, domain=domain:
                         compare_kwds_items (self, domain, cls.db, cls.csv))

#====== Tests ================================================================

class Compare_db_csv (unittest.TestCase):
    '''Compare the Kwds table loaded from the .csv files with one
       loaded from a database.'''

    @classmethod
    def setUpClass(cls):
        cls.db = jdb.Kwds (Cursor)
        cls.csv = jdb.Kwds ('')

      #FIXME? Not sure the following two tests are useful.  In any
      # Kwds instance a standard set of domains are always created
      # (that are the same as KwdsAttrs above); the contents will
      # be empty if the corresponding *.csv file or table is missing
      # or empty (in which case the per domain tests added by 
      # add_domain_tests() below will find  content difference) but
      # I wonder if looking for attribute differences is testing a
      # tautology.
    def test_db_domains (_):
        compare_domains (_, "database", _.db)
    def test_csv_domains (_):
        compare_domains (_, "csv files", _.csv)

    # The add_domain_tests() function call below adds tests to the
    # Compare_db_csv class above.  The tests, one per domain and
    # named "test_cmp_XXX" where "XXX" is the domain, eg "DIAL",
    # "KINF", "POS", etc, compares each of the tags in the domain
    # between the database Kwds instance and the CSV Kwds instance
    # and reports any differences (id or kw key in one but not the
    # other or unequal id, key, or descr values).
add_domain_tests (Compare_db_csv)

#====== Support functions ====================================================

def compare_domains(_, source, kwds):
          # Verify that all the tag domains (ie, the attributes of a
          # jdb.Kwds instance like .DIAL, .KINF, .POS, etc) are as
          # expected as defined in KwdsAttrs; list any that are
          # missing (in KwdsAttrs but not in 'kwds') or extra (in
          # 'kwds' but not in KwdsAttrs).
        std_domains = KwdsAttrs
        domains = set (kwds.attrsall())
        missing = std_domains - domains
        extra = domains - std_domains
        for txt,attrs in (("missing", missing), ("extra", extra)):
            if not attrs: continue
            with _.subTest (source):
                _.fail ("%s: %s domain(s): %s"
                        % (source, txt, ", ".join(attrs)))

def compare_kwds_items (_, domain, db_kwds=None, csv_kwds=None):
        '''
        Given a Kwds "domain" (eg 'FREQ','GINF','KINF', etc) check that
        both 'db_kwds' and 'csv_kwds' Kwds instances have the same set of
        records (aka tags) for that domain.  Noe that this is not intended
        to check structural details (eg the same record is keyed by both
        kw tag and id number, etc) -- those details are the province of
        other tests -- we want to make sure each Kwds instance has the
        same contents, that a tag in one has the same id, kw, descr, etc
        as the same tag in the other.  '''

        db_recs  = getattr (db_kwds,  domain, None)
        csv_recs = getattr (csv_kwds, domain, None)
        if not db_recs or not csv_recs: return
          # We only compare the keys in the domains present in both db_kwds
          # and csv_kwds -- any differences in the domains present is the
          # responsibility of other tests to report.
        keys = set (db_recs.keys()) | set (csv_recs.keys())
        for key in keys:
              # Don't check the GRP and SRC domains.  Both contain
              # dynamic data that varies between databases and is not
              # loaded from static kw*.csv files.
            if domain=='GRP' or domain=='SRC': continue
            with _.subTest (domain=domain, key=key):
                db_rec = db_recs.get (key)
                csv_rec = csv_recs.get (key)
                assert db_rec or csv_rec    # They should never both be false.
                if not csv_rec:
                     _.fail ("Key %s[%s] in database, not in csv files"
                                        % (domain, key))
                if not db_rec:
                     _.fail ("Key %s[%s] in csv files, not in database"
                                        % (domain, key))
                _.assertEqual (db_rec, csv_rec, "Database and csv files differ")

if __name__ == '__main__': unittest.main()
