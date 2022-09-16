import sys, unittest, contextlib, datetime, io, re, pdb
from jmdictdb import jdb, db
from jmdictdb.objects import *
from jmdictdb import fmtxml

global TestData  # Defined in SetUpModule() (near bottom).

# NOTE: some test class names below are prefixed with "t" to avoid shadowing
#  the name of a JMdictDB object class in object.py,

class tRestr (unittest.TestCase):
    def test_001(_):
        k1, k2, k3 = Kanj(txt='k1'), Kanj(txt='k2'), Kanj(txt='k3')
        kanjs = [k1, k2, k3]
        rdng = Rdng()
        xml = fmtxml.restrs (rdng, kanjs)
        _.assertEqual ([], xml)

    def test_002(_):
        k1, k2, k3 = Kanj(txt='k1'), Kanj(txt='k2'), Kanj(txt='k3')
        kanjs = [k1, k2, k3]
        rdng = Rdng(_restr=[Restr(kanj=1), Restr(kanj=3)])
        xml = fmtxml.restrs (rdng, kanjs)
        _.assertEqual (['<re_restr>k2</re_restr>'], xml)

    def test_003(_):
        k1, k2, k3 = Kanj(txt='k1'), Kanj(txt='k2'), Kanj(txt='k3')
        kanjs = [k1, k2, k3]
        rdng = Rdng(_restr=[Restr(kanj=2)])
        xml = fmtxml.restrs (rdng, kanjs)
        _.assertEqual (['<re_restr>k1</re_restr>','<re_restr>k3</re_restr>'], xml)

    def test_004(_):
        k1, k2, k3 = Kanj(txt='k1'), Kanj(txt='k2'), Kanj(txt='k3')
        kanjs = [k1, k2, k3]
        rdng = Rdng (_restr=[Restr(kanj=1), Restr(kanj=2), Restr(kanj=3)])
        xml = fmtxml.restrs (rdng, kanjs)
        _.assertEqual (['<re_nokanji/>'], xml)

class tEntr (unittest.TestCase):
    def setUp(_):
        jdb.KW = jdb.Kwds ('')
        for id,kw,descr in ((1,'grp1','group grp1'),
                            (2,'xx','group xx'),
                            (10,'zz','group zz'),
                            (11,'mxtpp55-2','group mxtpp55-2 with hyphen'),
                            (200,'aabb','group aabb'),):
            jdb.KW.add ('GRP', (id,kw,descr))
    def test0200010 (_): dotest (_, TestData['0200010'])
    def test0201020 (_): dotest (_, TestData['0201020'])
    def test0201030 (_): dotest (_, TestData['0201030'])
    def test0201040 (_): dotest (_, TestData['0201040'], compat='jmdict')
    def test0201050 (_): dotest (_, TestData['0201050'])

class tXrslv (unittest.TestCase):
    def setUp (_):
        jdb.KW = jdb.Kwds ('')
    def test0202010(_): dotest (_, TestData['0202010'], compat='jmdict')
    def test0202020(_): dotest (_, TestData['0202020'], compat='jmdict')
    def test0202030(_): dotest (_, TestData['0202030'], compat='jmdict')
    def test0202040(_): dotest (_, TestData['0202040'], compat='jmdict')
    def test0202050(_): dotest (_, TestData['0202050'], compat='jmdict')

class JMnedict (unittest.TestCase):
    def setUp(_):
        jdb.KW = jdb.Kwds ('')
    def test0300010(_): dotest (_, TestData['0300010'], compat='jmnedict')
    def test0300020(_): dotest (_, TestData['0300020'], compat='jmnedict')
    def test0300030(_): dotest (_, TestData['0300030'], compat='jmnedict')
    def test0300040(_): dotest (_, TestData['0300040'], compat='jmnedict')
    def test0300050(_): dotest (_, TestData['0300050'], compat='jmnedict')

    def test0305001(_):  # IS-221
        dotest (_, TestData['0305001'], compat='jmnedict')

class Jmex (unittest.TestCase):
    def setUp(_):
        jdb.KW = jdb.Kwds ('')
    def test_001(_):
          # Rinf(kw=103) below is a RINF['name'] tag used in kanjidic but
          # disallowed in jmdict.  Since the jmex format allows all tags
          # it should not cause an error.
        data = Entr (src=99, seq=601010,
                    _rdng=[Rdng (txt='たかはし',_inf=[Rinf(kw=103)])],)
        expect = '''\
            <entry corpus="test" type="jmdict">
            <ent_corp type="jmdict">test</ent_corp>
            <ent_seq>601010</ent_seq>
            <r_ele>
            <reb>たかはし</reb>
            <re_inf>&name;</re_inf>
            </r_ele>
            </entry>'''.replace(' '*12,'')
        got = fmtxml.entr (data)   # compat='jmex' is default.
        _.assertEqual (expect, got)

def dotest (_, testdata, **kwds):
        entr, xml = testdata
          # Remove the leading spaces due to formatting.
        expected = re.sub (r'^[ ]+', '', xml, flags=re.M)
        got = fmtxml.entr (entr, **kwds)
        _.assertEqual (expected, got)

  # Tests for fmtxml.entr_diff(), see IS-227.
  # Like class Test_entr above, we use data from data/fmtxml_data.py imported
  # (as 'f' for brevity) earlier.  See Test_entr above for more details.
class Entr_diff (unittest.TestCase):
    def setUp(_):
        jdb.KW = jdb.Kwds ('')
          # We need an additional kwsrc row to allow the tests to change
          # between src's but we don't need every field in it, so for
          # brevity add just the needed field: srct.
        jdb.KW.add ('SRC', db.DbRow((1,'jmdict','',1),
                                    ('id','kw','descr','srct')))
    def test_0400010(_): _.do_test (TestData['0400010'])   # No change.
    def test_0400020(_): _.do_test (TestData['0400020'])   # rdng.txt change.
    def test_0400030(_): _.do_test (TestData['0400030'])   # entr.src change.
    def test_0400040(_): _.do_test (TestData['0400040'])   # entr.seq change.
    def do_test (_, testdata):
        e1, e2, xml = testdata
          # Remove the leading spaces due to formatting.
        expected = re.sub (r'^[ ]+', '', xml, flags=re.M)
        got = fmtxml.entr_diff (e1, e2, n=0)
        _.assertEqual (expected, got)

class Xrefs (unittest.TestCase):
    def setUp(_):
        jdb.KW = jdb.Kwds ('')

    def test_00010(_):   # Xrefs must be augmented (have a .TARG attr)
        with _.assertRaisesRegex (AttributeError, 'missing TARG attribute'):
           fmtxml.xrefs([Xref()],None)

    def test_01010(_):   # Tests that fmtxml.xrefs() doesn't blow up.
        x = Xref(); setattr(x,'TARG',Entr())
        o = fmtxml.xrefs([x],None)
        _.assertEqual(o, [])

    def test_01020(_):   # Most minimal test that produces an xml xref.
        x = Xref(typ=3,rdng=1)
        setattr(x,'TARG',Entr(stat=2,
                              _rdng=[Rdng(txt='ゴミ')],
                              _sens=[Sens(sens=1)]))
        o = fmtxml.xrefs([x],None)
        _.assertEqual(o, ['<xref>ゴミ</xref>'])

    def test_01030(_):   # Xref to kanji.
        x = Xref(typ=3,xsens=1,rdng=1)
        setattr(x,'TARG',Entr(stat=2,
                              _kanj=[Kanj(txt='忠実')],
                              _rdng=[Rdng(txt='ちゅうじつ')],
                              _sens=[Sens(sens=1)]))
        o = fmtxml.xrefs([x],None)
        _.assertEqual(o, ['<xref>ちゅうじつ</xref>'])

    def test_01040(_):   # Xref to reading.
        x = Xref(typ=3,xsens=1,kanj=1)
        setattr(x,'TARG',Entr(stat=2,
                              _kanj=[Kanj(txt='忠実')],
                              _rdng=[Rdng(txt='ちゅうじつ')],
                              _sens=[Sens(sens=1)]))
        o = fmtxml.xrefs([x],None)
        _.assertEqual(o, ['<xref>忠実</xref>'])

    def test_01050(_):   # Xref to kanji and reading.
        x = Xref(typ=3,xsens=1,kanj=1,rdng=1)
        setattr(x,'TARG',Entr(stat=2,
                              _kanj=[Kanj(txt='忠実')],
                              _rdng=[Rdng(txt='ちゅうじつ')],
                              _sens=[Sens(sens=1)]))
        o = fmtxml.xrefs([x],None)
        _.assertEqual(o, ['<xref>忠実・ちゅうじつ</xref>'])

    def test_01060(_):   # Xref to kanji and reading.
        x = Xref(typ=3,xsens=1,kanj=3,rdng=2)
        setattr(x,'TARG',Entr(stat=2,
                              _kanj=[Kanj(txt='海辺'),Kanj(txt='海べ'),Kanj(txt='海邊')],
                              _rdng=[Rdng(txt='うみべ'),Rdng(txt='かいへん')],
                              _sens=[Sens(sens=1)]))
        o = fmtxml.xrefs([x],None)
        _.assertEqual(o, ['<xref>海邊・かいへん</xref>'])

    def test_01070(_):   # Xref to one of multiple senses produces xref
                        #  with sense number.
        x = Xref(typ=3,xsens=1,rdng=1)
        setattr(x,'TARG',Entr(stat=2,
                              _rdng=[Rdng(txt='ゴミ')],
                              _sens=[Sens(sens=1),Sens(sens=2)]))
        o = fmtxml.xrefs([x],None)
        _.assertEqual(o, ['<xref>ゴミ・1</xref>'])

    def test_01080(_):   # Xref to one of multiple senses produces xref
                        #  with sense number.
        x = Xref(typ=3,xsens=2,rdng=1)
        setattr(x,'TARG',Entr(stat=2,
                              _rdng=[Rdng(txt='ゴミ')],
                              _sens=[Sens(sens=1),Sens(sens=2)]))
        o = fmtxml.xrefs([x],None)
        _.assertEqual(o, ['<xref>ゴミ・2</xref>'])

    def test_02010(_):   # Xrefs to all senses of target are coalesced.
        targ = Entr(stat=2,
                    _rdng=[Rdng(txt='ゴミ')],
                    _sens=[Sens(sens=1),Sens(sens=2)])
        xm = [Xref(typ=3,xsens=1,rdng=1), Xref(typ=3,xsens=2,rdng=1)]
        for x in xm: setattr(x,'TARG',targ)
        o = fmtxml.xrefs(xm,None)
        _.assertEqual(o, ['<xref>ゴミ</xref>'])

    def test_02020(_):   # Xrefs to subset of senses of produces xref
                        #  to each sense.
        targ = Entr(stat=2,
                    _rdng=[Rdng(txt='ゴミ')],
                    _sens=[Sens(sens=1),Sens(sens=2),Sens(sens=3)])
        xm = [Xref(typ=3,xsens=1,rdng=1), Xref(typ=3,xsens=2,rdng=1)]
        for x in xm: setattr(x,'TARG',targ)
        o = fmtxml.xrefs(xm,None)
        _.assertEqual(o, ['<xref>ゴミ・1</xref>', '<xref>ゴミ・2</xref>'])

    def test_02030(_):   # "nosens" xref.
        targ = Entr(stat=2,
                    _rdng=[Rdng(txt='ゴミ')],
                    _sens=[Sens(sens=1),Sens(sens=2),Sens(sens=3)])
        x = Xref(typ=3,xsens=1,rdng=1,nosens=True);  setattr(x,'TARG',targ)
        o = fmtxml.xrefs([x],None)
        _.assertEqual(o, ['<xref>ゴミ</xref>'])

    def test_02040(_):   # "nosens" xref.
        targ = Entr(stat=2,
                    _rdng=[Rdng(txt='ゴミ')],
                    _sens=[Sens(sens=1),Sens(sens=2),Sens(sens=3)])
        x = Xref(typ=3,xsens=1,rdng=1,nosens=True);  setattr(x,'TARG',targ)
        o = fmtxml.xrefs([x],None)
        _.assertEqual(o, ['<xref>ゴミ</xref>'])

    def test_02050(_):   # Multiple xrefs.
        targ1 = Entr(stat=2,
                    _rdng=[Rdng(txt='ゴミ')],
                    _sens=[Sens(sens=1),Sens(sens=2)])
        targ2 = Entr(stat=2,
                    _kanj=[Kanj(txt='ゴミ箱')],
                    _sens=[Sens(sens=1),Sens(sens=2)])
        x1 = Xref(typ=3,xentr=200,xsens=1,rdng=1);  setattr(x1,'TARG',targ1)
        x2 = Xref(typ=3,xentr=201,xsens=1,kanj=1);  setattr(x2,'TARG',targ2)
        o = fmtxml.xrefs([x1,x2],None)
        _.assertEqual(o, ['<xref>ゴミ・1</xref>','<xref>ゴミ箱・1</xref>'])

    def test_02060(_):   # Multiple xrefs with one "nosens".
        targ1 = Entr(stat=2,
                    _rdng=[Rdng(txt='ゴミ')],
                    _sens=[Sens(sens=1),Sens(sens=2)])
        targ2 = Entr(stat=2,
                    _kanj=[Kanj(txt='ゴミ箱')],
                    _sens=[Sens(sens=1),Sens(sens=2)])
        x1 = Xref(typ=3,xentr=200,xsens=1,rdng=1,nosens=True);  setattr(x1,'TARG',targ1)
        x2 = Xref(typ=3,xentr=201,xsens=1,kanj=1);  setattr(x2,'TARG',targ2)
        o = fmtxml.xrefs([x1,x2],None)
        _.assertEqual(o, ['<xref>ゴミ</xref>','<xref>ゴミ箱・1</xref>'])

    def test_02070(_):   # Multiple xrefs with one "nosens".
        targ1 = Entr(stat=2,
                    _rdng=[Rdng(txt='ゴミ')],
                    _sens=[Sens(sens=1),Sens(sens=2)])
        targ2 = Entr(stat=2,
                    _kanj=[Kanj(txt='ゴミ箱')],
                    _sens=[Sens(sens=1),Sens(sens=2)])
        x1 = Xref(typ=3,xentr=200,xsens=1,rdng=1,nosens=True);  setattr(x1,'TARG',targ1)
        x2 = Xref(typ=3,xentr=201,xsens=1,kanj=1);  setattr(x2,'TARG',targ2)
        o = fmtxml.xrefs([x1,x2],None)
        _.assertEqual(o, ['<xref>ゴミ</xref>','<xref>ゴミ箱・1</xref>'])

    def test_02080(_):   # "nosens" xref works, even if sense!=1, as long
                         #  as it's on the first xref of the target group.
        targ = Entr(stat=2,
                    _rdng=[Rdng(txt='ゴミ')],
                    _sens=[Sens(sens=1),Sens(sens=2),Sens(sens=3)])
        x1 = Xref(typ=3,xsens=2,rdng=1,nosens=True);  setattr(x1,'TARG',targ)
        x2 = Xref(typ=3,xsens=3,rdng=1);  setattr(x2,'TARG',targ)
        o = fmtxml.xrefs([x1,x2],None)
        _.assertEqual(o, ['<xref>ゴミ</xref>'])

    def test_02090(_):   # "nosens" xref doesn't work if it's not on the
                         #  first xref of the target group.
        targ = Entr(stat=2,
                    _rdng=[Rdng(txt='ゴミ')],
                    _sens=[Sens(sens=1),Sens(sens=2),Sens(sens=3)])
        x1 = Xref(typ=3,xsens=2,rdng=1);  setattr(x1,'TARG',targ)
        x2 = Xref(typ=3,xsens=3,rdng=1,nosens=True);  setattr(x2,'TARG',targ)
        o = fmtxml.xrefs([x1,x2],None)
        _.assertEqual(o, ['<xref>ゴミ・2</xref>','<xref>ゴミ・3</xref>'])

class Compat (unittest.TestCase):
    def setUp(_):
        jdb.KW = jdb.Kwds ('')
        _.entr = Entr(id=33, src=99, seq=1000222, stat=2, unap=False, dfrm=None,
                      notes="entr-note",
                      srcnote="src-note",
                      _rdng=[Rdng(txt='ゴミ')],
                      _sens=[Sens(sens=1,
                                  notes="sense-note",
                                  _gloss=[Gloss(txt='trash',lang=1,ginf=1)])],
                      _hist=[Hist(hist=1,stat=2,unap=False,
                                  dt=datetime.datetime(2020,7,29,9,10,59),
                                  userid='xy',name="Xavier Yu",
                                  email='nowhere',diff="diff",refs="refs",
                                  notes="comments"),
                             Hist(hist=2,stat=2,unap=True,
                                  dt=datetime.datetime(2020,7,30,15,30,5),
                                  name="")]  )

    def test_01(_):
        got = fmtxml.entr(_.entr, compat='jmdict')
        expect = '''\
            <entry>
            <ent_seq>1000222</ent_seq>
            <r_ele>
            <reb>ゴミ</reb>
            </r_ele>
            <sense>
            <s_inf>sense-note</s_inf>
            <gloss>trash</gloss>
            </sense>
            </entry>'''.replace (' '*12,'')
        _.assertEqual (expect, got)

    def test_02(_):
        got = fmtxml.entr(_.entr, compat='jmnedict')
        expect = '''\
            <entry>
            <ent_seq>1000222</ent_seq>
            <r_ele>
            <reb>ゴミ</reb>
            </r_ele>
            <trans>
            <trans_det>trash</trans_det>
            </trans>
            </entry>'''.replace (' '*12,'')
        _.assertEqual (expect, got)

    def test_03(_):
        got = fmtxml.entr(_.entr, compat='jmex')
        expect = '''\
            <entry id="33" stat="A" corpus="test" type="jmdict">
            <ent_corp type="jmdict">test</ent_corp>
            <ent_seq>1000222</ent_seq>
            <r_ele>
            <reb>ゴミ</reb>
            </r_ele>
            <sense>
            <s_inf>sense-note</s_inf>
            <gloss>trash</gloss>
            </sense>
            <info>
            <srcnote>src-note</srcnote>
            <notes>entr-note</notes>
            <audit time="2020-07-29 09:10:59" stat="A">
            <upd_uid>xy</upd_uid>
            <upd_name>Xavier Yu</upd_name>
            <upd_email>nowhere</upd_email>
            <upd_detl>comments</upd_detl>
            <upd_refs>refs</upd_refs>
            <upd_diff>diff</upd_diff>
            </audit>
            <audit time="2020-07-30 15:30:05" stat="A" unap="true">
            </audit>
            </info>
            </entry>'''.replace (' '*12,'')
        _.assertEqual (expect, got)

    def test_04(_):
        got = fmtxml.entr(_.entr, compat='jmex', genhists=False)
        expect = '''\
            <entry id="33" stat="A" corpus="test" type="jmdict">
            <ent_corp type="jmdict">test</ent_corp>
            <ent_seq>1000222</ent_seq>
            <r_ele>
            <reb>ゴミ</reb>
            </r_ele>
            <sense>
            <s_inf>sense-note</s_inf>
            <gloss>trash</gloss>
            </sense>
            <info>
            <srcnote>src-note</srcnote>
            <notes>entr-note</notes>
            </info>
            </entry>'''.replace (' '*12,'')
        _.assertEqual (expect, got)

    def test_05(_):
        got = fmtxml.entr(_.entr, compat='jmex', geninfo=False)
        expect = '''\
            <entry id="33" stat="A" corpus="test" type="jmdict">
            <ent_corp type="jmdict">test</ent_corp>
            <ent_seq>1000222</ent_seq>
            <r_ele>
            <reb>ゴミ</reb>
            </r_ele>
            <sense>
            <s_inf>sense-note</s_inf>
            <gloss>trash</gloss>
            </sense>
            </entry>'''.replace (' '*12,'')
        _.assertEqual (expect, got)

class Tags (unittest.TestCase):
    def test001000(_):
          # Check that if there is a JMdict-exclusive tag (such as
          # 'abbr' (Misc(kw=2)) or 'ateji (Kinf(kw=5)) in a JMnedict
          # entry that fmtxmt.entr():
          #   1) will not be output in the XML,
          #   2) will not produce a warning message to stderr (prior
          #      to 2022-09-15 it did),
          #   3) will record the invalid tag(s) in xtags and
          #   4) won't interfere with or suppress a valid JMnedict
          #      tag (e.g. "place").
          # Create a minimal entry with two MISC tags: "abbr" (kw=2) and
          # "place" (kw=182) and a KINF tag "ateji".  Only the "place"
          # tag is valid for a jmnedict entry.
        e = Entr(id=33, seq=1023450, src=99, stat=2, unap=False,
                 _kanj=[Kanj(txt="中味",_inf=[Kinf(kw=5)])],
                 _sens=[Sens(sens=1,_misc=[Misc(kw=2),Misc(kw=182)])])
        xtags = [];  test_stderr = io.StringIO()
        with contextlib.redirect_stderr (test_stderr):
            got = fmtxml.entr(e, compat='jmnedict', xtags=xtags)
        expect = '''\
            <entry>
            <ent_seq>1023450</ent_seq>
            <k_ele>
            <keb>中味</keb>
            </k_ele>
            <trans>
            <name_type>&place;</name_type>
            </trans>
            </entry>'''.replace (' '*12,'')
        _.assertEqual (expect, got)
        _.assertEqual (test_stderr.getvalue(), '')
        _.assertEqual (xtags, [('KINF','ateji'),('MISC','abbr')])

def setUpModule():
    jdb.KW = jdb.Kwds('')   # Load JMdictDB tags from csv files.

    global TestData
    TestData = {
      # for class Entr
      '0200010': (
           Entr(),
           '''<entry>
           </entry>'''),
      '0201020': (
          Entr(_grp=[Grp(kw=2,ord=1)]),
          '''<entry>
          <group ord="1">xx</group>
          </entry>'''),
      '0201030': (
          Entr(_grp=[Grp(kw=11,ord=5),Grp(kw=10,ord=2)]),
          '''<entry>
          <group ord="5">mxtpp55-2</group>
          <group ord="2">zz</group>
          </entry>'''),
      '0201040': (
          Entr(_grp=[Grp(kw=5,ord=1)]),
          '''<entry>
          </entry>'''),
      '0201050': (
          Entr(_grp=[Grp(kw=1)]),
          '''<entry>
          <group>grp1</group>
          </entry>'''),

      # for class Xrslv
      '0202010': (
          Entr (src=99, _sens=[Sens (_xrslv=[Xrslv(typ=3, ktxt='\u540c\u3058')])]),
          '''<entry>
          <sense>
          <xref>同じ</xref>
          </sense>
          </entry>'''),
      '0202020': (
          Entr (src=99, _sens=[Sens (_xrslv=[Xrslv(typ=2, ktxt='\u540c\u3058')])]),
          '''<entry>
          <sense>
          <ant>同じ</ant>
          </sense>
          </entry>'''),
      '0202030': (
          Entr (src=99, _sens=[Sens (_xrslv=[Xrslv(typ=3, rtxt='\u304a\u306a\u3058')])]),
          '''<entry>
          <sense>
          <xref>おなじ</xref>
          </sense>
          </entry>'''),
      '0202040': (
          Entr (src=99, _sens=[Sens (_xrslv=[Xrslv(typ=3, ktxt='\u540c\u3058',\
                                                          rtxt='\u304a\u306a\u3058')])]),
          '''<entry>
          <sense>
          <xref>同じ・おなじ</xref>
          </sense>
          </entry>'''),
      '0202050': (
          Entr (src=99, _sens=[Sens (_xrslv=[Xrslv(typ=3, ktxt='\u540c\u3058',\
                                                          rtxt='\u304a\u306a\u3058', tsens=3)])]),
          '''<entry>
          <sense>
          <xref>同じ・おなじ・3</xref>
          </sense>
          </entry>'''),

      # for class JMnedict
      '0300010': (
          Entr (src=99, seq=300010),
          '''<entry>
          <ent_seq>300010</ent_seq>
          </entry>'''),
      '0300020': (
          Entr (src=99, _rdng=[Rdng (txt='たかはし')]),
          '''<entry>
          <r_ele>
          <reb>たかはし</reb>
          </r_ele>
          </entry>'''),

      '0300030': (
          Entr (src=99, _rdng=[Rdng (txt='キャッツ')]),
          '''<entry>
          <r_ele>
          <reb>キャッツ</reb>
          </r_ele>
          </entry>'''),
      '0300040': (
          Entr (src=99, _kanj=[Kanj (txt='高橋')]),
          '''<entry>
          <k_ele>
          <keb>高橋</keb>
          </k_ele>
          </entry>'''),
      '0300050': (
          Entr (src=99, _sens=[Sens (_gloss=[Gloss(txt='Takahashi')])]),
          '''<entry>
          <trans>
          <trans_det>Takahashi</trans_det>
          </trans>
          </entry>'''),
      '0305001': (
          Entr (src=99, _rdng=[Rdng (txt='キャッツ＆ドッグス')],\
                       _sens=[Sens (_gloss=[Gloss (txt='Cats & Dogs (film)')],\
                                    _misc=[Misc (kw=jdb.KW.MISC['unclass'].id)])]),
          '''<entry>
          <r_ele>
          <reb>キャッツ＆ドッグス</reb>
          </r_ele>
          <trans>
          <name_type>&unclass;</name_type>
          <trans_det>Cats &amp; Dogs (film)</trans_det>
          </trans>
          </entry>'''),

      # for class Entr_diff
      '0400010': (
          Entr (id=1, src=99, _rdng=[Rdng (txt='たかはし')]),
          Entr (id=2, src=99, _rdng=[Rdng (txt='たかはし')]),
          ''),
      '0400020': (
          Entr (id=1, src=99, _rdng=[Rdng (txt='たかはし')]),
          Entr (id=2, src=99, _rdng=[Rdng (txt='たかばし')]),
          '''@@ -4 +4 @@
          -<reb>たかはし</reb>
          +<reb>たかばし</reb>'''),
      '0400030': (
          Entr (id=1, src=1, _rdng=[Rdng (txt='たかはし')]),
          Entr (id=2, src=99, _rdng=[Rdng (txt='たかはし')]),
          '''@@ -1,2 +1,2 @@
          -<ent_corp type="jmdict">jmdict</ent_corp>
          +<ent_corp type="jmdict">test</ent_corp>'''),
      '0400040': (
          Entr (id=1, src=99, seq=1000123),
          Entr (id=2, src=99, seq=1000124),
          '''@@ -3 +3 @@
          -<ent_seq>1000123</ent_seq>
          +<ent_seq>1000124</ent_seq>'''),
      }

if __name__ == '__main__': unittest.main()
