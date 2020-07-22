# Tests the jdb.Kwds class.

import sys, pdb, unittest
from jmdb import DBmanager
from jmdictdb import jdb

Cursor = None
def setUpModule():
       global Cursor
       Cursor = DBmanager.use ("jmtest01", "data/jmtest01.sql")

KwdsAttrs = set (('DIAL','FLD','FREQ','GINF','KINF','LANG','MISC','POS',
                  'RINF','SRC','SRCT','STAT','XREF','CINF','GRP', 'COPOS'))

class Empty (unittest.TestCase):
    def setUp (_):
        _.o = jdb.Kwds()

    def test001 (_):
          # Check that .Tables has the expected set of attribute
          # names since we will use them in later tests, and doesn't
          # have any unexpected ones.
        _.assertTrue (hasattr (_.o, 'Tables'))
        _.assertEqual (set (_.o.Tables.keys()), KwdsAttrs)

    def test002 (_):
          # .attrs() method should return empty list for empty instance.
        _.assertEqual (_.o.attrs(), [])

    def test003 (_):
          # .recs() method should return an empty list for every attribute.
        for a in KwdsAttrs:
            _.assertEqual (_.o.recs(a), [])

    def test004 (_):
          # .recs() method should fail with an unknown attribute.
        _.assertRaises (AttributeError, _.o.recs, 'XXX')

    def test005 (_):
        values = (22,'abc','a description')
        rec = jdb.DbRow (values,('id','kw','descr'))
        _.o.add ('DIAL', rec)
        validate_rec (_, _.o, 'DIAL', *values)

    def test006 (_):
        values = (22,'abc','a description')
        _.o.add ('DIAL', values)
        validate_rec (_, _.o, 'DIAL', *values)

class Loadcsv (unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = jdb.Kwds ('data/kwds')

    def test001 (_):
        _.assertTrue (hasattr (_.o, 'KINF'))
        _.assertTrue (hasattr (_.o, 'GINF'))
        _.assertTrue (hasattr (_.o, 'CINF'))
        validate_rec (_, _.o, 'KINF', 13, 'xxx', 'line 1')
        validate_rec (_, _.o, 'KINF', 27, 'yy')
        validate_rec (_, _.o, 'KINF', 8, 'qq-r')
        validate_rec (_, _.o, 'GINF', 1, 'equ',  'equivalent')
        validate_rec (_, _.o, 'GINF', 2, 'lit',  'literaly')
        validate_rec (_, _.o, 'GINF', 3, 'fig',  'figuratively')
        validate_rec (_, _.o, 'GINF', 4, 'expl', 'explanatory')
          # Check handling of double-quotes in descr fields.
          # The quotes in text fields of a .csv file are not treated
          # differently than any other character after a commit circa
          # 2020-07-21.  Previously they would be stripped. 
        validate_rec (_, _.o, 'CINF', 1, 'kw1',  'unquoted descr')
        validate_rec (_, _.o, 'CINF', 2, 'kw2',  '"quoted descr"')
        validate_rec (_, _.o, 'CINF', 3, 'kw3',  '"""embedded quotes"" unquoted part"')

    def test002 (_):
        _.assertEqual (_.o.attrs(), ['CINF', 'GINF', 'KINF'])

    def test002a (_):
        _.assertEqual (_.o.attrsall(), KwdsAttrs)

    def test003 (_):
          # Check KINF records.
        expect = set (((13, 'xxx', 'line 1'),(27, 'yy', None),(8, 'qq-r', None)))
        recs = _.o.recs('KINF')
        _.assertEqual (len(recs), 3)
        comparable_recs = set ((tuple(x) for x in recs))
        _.assertEqual (comparable_recs, expect)

    def test004 (_):
          # Check GINF records.
        expect = set (((1,'equ','equivalent'),(2,'lit','literaly'),
                       (3,'fig','figuratively'),(4,'expl','explanatory')))
        recs = _.o.recs('GINF')
        _.assertEqual (len(recs), 4)
        comparable_recs = set ((tuple(x) for x in recs))
        _.assertEqual (comparable_recs, expect)

    def test005 (_):
          # Check short-form kw->id attribute names.
        expected = set (
                'GINF_equ GINF_lit GINF_fig GINF_expl '
                'KINF_xxx KINF_yy KINF_qq_r '
                'CINF_kw1 CINF_kw2 CINF_kw3'.split())
        actual = set ([x for x in list(_.o.__dict__.keys()) if "_" in x])
        _.assertEqual (expected, actual)

    def test006 (_):
          # Check values of short-form kw->id attributes.
        attrs = 'GINF_equ GINF_lit GINF_fig GINF_expl ' \
                'KINF_xxx KINF_yy KINF_qq_r ' \
                'CINF_kw1 CINF_kw2 CINF_kw3'.split()
        expected = [1, 2, 3, 4, 13, 27, 8, 1, 2, 3]
        actual = [getattr (_.o, x) for x in attrs if "_" in x]
        _.assertEqual (expected, actual)

class Missing_csv (unittest.TestCase):
    def test001 (_):
        _.assertRaises (IOError, jdb.Kwds, 'data/kwds/empty')
    def test002 (_):
        o = jdb.Kwds()
        expected = set(o.Tables.values()) - set(['kwginf','kwkinf','kwcinf'])
        missing = o.loadcsv ('data/kwds')
        _.assertEqual (expected, set (missing))
    def test003 (_):
        o = jdb.Kwds()
        missing = o.loadcsv ('data/kwds/full')
          # There is no 'vcopos.csv' file since that data is only present as
          # a SQL view (see pg/conj.sql) and is only loaded when the kw* data
          # is loaded from a database rather then directly from *.csv files.
          # See IS-226.
        _.assertEqual (['vcopos'], missing)

#FIXME: need Test_missing_db.

class Loaddb (unittest.TestCase):

    def setUp (_):
        _.o = jdb.Kwds (Cursor)

    def test001 (_):
        expect = set (((1,'equ','equivalent'),(2,'lit','literaly'),
                       (3,'fig','figuratively'),(4,'expl','explanatory')))
        recs = _.o.recs('GINF')
        _.assertEqual (len(recs), 4)
        comparable_recs = set ((tuple(x) for x in recs))
        _.assertEqual (comparable_recs, expect)

class Missing: pass
def validate_rec (_, o, domain, idx, kw, descr=Missing):
          # Lookup a Kwds record and confirm that it matches
          # expectations: that the same record is found by
          # id number or kw string lookup, and the that id
          # number, kw string, and (optionally) descr in the
          # found record match what is expected (as given in
          # the arguments).

        r1 = getattr (o, domain)[idx]
        r2 = getattr (o, domain)[kw]
        _.assertEqual (id(r1), id(r2))
        _.assertEqual (r1.id, idx)
        _.assertEqual (r1.kw, kw)
        if descr is not Missing:
            _.assertEqual (r1.descr, descr)

if __name__ == '__main__': unittest.main()
