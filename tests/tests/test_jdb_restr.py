import sys, unittest, pdb
if '../lib' not in sys.path: sys.path.append ('../lib')
from objects import *
import jdb
import fmtxml

class Test_restr2ext (unittest.TestCase):
    def test_001(_):
          # An empty restr list should produce an empty result.
        k1, k2, k3 = Kanj(txt='k1'), Kanj(txt='k2'), Kanj(txt='k3')
        restrs = []
        result = jdb.restrs2ext_ (restrs, [k1,k2,k3], '_restr')
        _.assertEqual ([], result)

    def test_002(_):
          # Restr on k2 results in list of remainder (k1, k3).
        k1, k2, k3 = Kanj(kanj=1,txt='k1'), Kanj(kanj=2,txt='k2'), Kanj(kanj=3,txt='k3')
        restrs = [Restr(kanj=2)]
        result = jdb.restrs2ext_ (restrs, [k1,k2,k3], '_restr')
        _.assertEqual ([k1,k3], result)

    def test_002a(_):
          # Restr on k2 results in list of remainder (k1, k3).
          # Target Kanj are not numered.
        k1, k2, k3 = Kanj(txt='k1'), Kanj(txt='k2'), Kanj(txt='k3')
        restrs = [Restr(kanj=2)]
        result = jdb.restrs2ext_ (restrs, [k1,k2,k3], '_restr')
        _.assertEqual ([k1,k3], result)

    def test_003(_):
          # Restr on k1,k3 results in list of remainder (k2).
        k1, k2, k3 = Kanj(kanj=1,txt='k1'), Kanj(kanj=2,txt='k2'), Kanj(kanj=3,txt='k3')
        restrs = [Restr(kanj=1), Restr(kanj=3)]
        result = jdb.restrs2ext_ (restrs, [k1,k2,k3], '_restr')
        _.assertEqual ([k2], result)

    def test_003a(_):
          # Restr on k1,k3 results in list of remainder (k2).
          # Target Kanj are not numbered.
        k1, k2, k3 = Kanj(txt='k1'), Kanj(txt='k2'), Kanj(txt='k3')
        restrs = [Restr(kanj=1), Restr(kanj=3)]
        result = jdb.restrs2ext_ (restrs, [k1,k2,k3], '_restr')
        _.assertEqual ([k2], result)

    def test_004(_):
          # All kanji restricted results in None ("nokanji" sentinal).
        k1, k2, k3 = Kanj(kanj=1,txt='k1'), Kanj(kanj=2,txt='k2'), Kanj(kanj=3,txt='k3')
        restrs = [Restr(kanj=1), Restr(kanj=2), Restr(kanj=3)]
        result = jdb.restrs2ext_ (restrs, [k1,k2,k3], '_restr')
        _.assertEqual (None, result)

    def test_004a(_):
          # All kanji restricted results in None ("nokanji" sentinal).
          # Target Kanj are not numbered.
        k1, k2, k3 = Kanj(txt='k1'), Kanj(txt='k2'), Kanj(txt='k3')
        restrs = [Restr(kanj=1), Restr(kanj=2), Restr(kanj=3)]
        result = jdb.restrs2ext_ (restrs, [k1,k2,k3], '_restr')
        _.assertEqual (None, result)

    def test_012(_):
          # stagk restr on k2 results in list of remainder (k1, k3).
        k1, k2, k3 = Kanj(kanj=1,txt='k1'), Kanj(kanj=2,txt='k2'), Kanj(kanj=3,txt='k3')
        restrs = [Stagk(kanj=2), Stagk(kanj=3)]
        result = jdb.restrs2ext_ (restrs, [k1,k2,k3], '_stagk')
        _.assertEqual ([k1], result)

    def test_022(_):
          # stagr restr on r2 results in list of remainder (r1, r3).
        r1, r2, r3 = Rdng(rdng=1,txt='r1'), Rdng(rdng=2,txt='r2'), Rdng(rdng=3,txt='r3')
        restrs = [Stagr(rdng=1)]
        result = jdb.restrs2ext_ (restrs, [r1,r2,r3], '_stagr')
        _.assertEqual ([r2,r3], result)


class Text_txt2restr (unittest.TestCase):
    def setUp (_):
        _.e = Entr (
                _rdng=[Rdng(txt='あ'),Rdng(txt='い')],
                _kanj=[Kanj(txt='亜'),Kanj(txt='居'),Kanj(txt='迂')],
                _sens=[Sens(_gloss=[Gloss(txt='A')]),Sens(_gloss=[Gloss(txt="B")])])

    def test110 (_):   # Empty text list applied to rdng[0]
        rtxts = []
        retval = jdb.txt2restr (rtxts, _.e._rdng[0], _.e._kanj, '_restr')
        _.assertEqual ([], _.e._rdng[0]._restr)
        _.assertEqual ([], _.e._rdng[1]._restr)
        _.assertEqual ([], retval)
    def test111 (_):   # KR-restr, kanj[0] allowed, kanj[1],[2] disallowed.
        rtxts = ['亜']
        retval = jdb.txt2restr (rtxts, _.e._rdng[0], _.e._kanj, '_restr')
        _.assertEqual (_.e._rdng[0]._restr, [Restr(kanj=2), Restr(kanj=3)])
        _.assertEqual (_.e._rdng[1]._restr, [])
        _.assertEqual ([2,3], retval)
    def test112 (_):   # KR-restr, kanj[1],[2] allowed, kanj[0] disallowed.
        rtxts = ['居', '迂']
        retval = jdb.txt2restr (rtxts, _.e._rdng[0], _.e._kanj, '_restr')
        _.assertEqual (_.e._rdng[0]._restr, [Restr(kanj=1)])
        _.assertEqual (_.e._rdng[1]._restr, [])
        _.assertEqual ([1], retval)
    def test113 (_):
        rtxts = None    # "nokanji".
        retval = jdb.txt2restr (rtxts, _.e._rdng[0], _.e._kanj, '_restr')
        _.assertEqual (_.e._rdng[0]._restr,
                       [Restr(kanj=1), Restr(kanj=2), Restr(kanj=3)])
        _.assertEqual (_.e._rdng[1]._restr, [])
        _.assertEqual ([1,2,3], retval)

    # Stagk tests...

    def test210 (_):
        rtxts = ['亜','迂']
        retval = jdb.txt2restr (rtxts, _.e._sens[1], _.e._kanj, '_stagk')
        _.assertEqual (_.e._sens[0]._stagk, [])
        _.assertEqual (_.e._sens[1]._stagk, [Stagk(kanj=2)])
        _.assertEqual ([2], retval)

    # Skagr tests...

    def test310 (_):
        rtxts = ['あ']
        retval = jdb.txt2restr (rtxts, _.e._sens[1], _.e._rdng, '_stagr')
        _.assertEqual (_.e._sens[0]._stagr, [])
        _.assertEqual (_.e._sens[1]._stagr, [Stagr(rdng=2)])
        _.assertEqual ([2], retval)

    def test320 (_):
        rtxts = ['い']
        retval = jdb.txt2restr (rtxts, _.e._sens[0], _.e._rdng, '_stagr')
        _.assertEqual (_.e._sens[0]._stagr, [Stagr(rdng=1)])
        _.assertEqual (_.e._sens[1]._stagr, [])
        _.assertEqual ([1], retval)

class Restr_expand (unittest.TestCase):
    def test_00011(_):
        e = Entr(_rdng=[],
                 _kanj=[])
        _.assertEqual ([], list(jdb.restr_expand (e)))
    def test_00012(_):
        e = Entr(_rdng=[],
                 _kanj=[Kanj(txt='')])
        _.assertEqual ([], list(jdb.restr_expand (e)))
    def test_00013(_):
        e = Entr(_rdng=[Rdng(txt='')],
                 _kanj=[])
        _.assertEqual ([], list(jdb.restr_expand (e)))
    def test_00021(_):
        e = Entr(_rdng=[Rdng(txt='')],
                 _kanj=[Kanj(txt='')])
        _.assertEqual ([(0,0)], list(jdb.restr_expand (e)))
    def test_00022(_):
        e = Entr(_rdng=[Rdng(txt=''),Rdng(txt='')],
                 _kanj=[Kanj(txt='')])
        _.assertEqual ([(0,0),(1,0)], list(jdb.restr_expand (e)))
    def test_00023(_):
        e = Entr(_rdng=[Rdng(txt='')],
                 _kanj=[Kanj(txt=''),Kanj(txt='')])
        _.assertEqual ([(0,0),(0,1)], list(jdb.restr_expand (e)))
    def test_00031(_):
        e = Entr(_rdng=[Rdng(txt=''),Rdng(txt='')],
                 _kanj=[Kanj(txt=''),Kanj(txt=''),Kanj(txt='')])
        _.assertEqual ([(0,0),(0,1),(0,2),(1,0),(1,1),(1,2)],
                       list(jdb.restr_expand (e)))
    def test_00032(_):
        e = Entr(_rdng=[Rdng(txt='',_restr=[Restr(kanj=1)]), Rdng(txt='')],
                 _kanj=[Kanj(txt=''),Kanj(txt=''),Kanj(txt='')])
        _.assertEqual ([(0,1),(0,2),(1,0),(1,1),(1,2)],
                       list(jdb.restr_expand (e)))
    def test_00033(_):
        e = Entr(_rdng=[Rdng(txt=''), Rdng(txt='',_restr=[Restr(kanj=3)])],
                 _kanj=[Kanj(txt=''),Kanj(txt=''),Kanj(txt='')])
        _.assertEqual ([(0,0),(0,1),(0,2),(1,0),(1,1)],
                       list(jdb.restr_expand (e)))
    def test_00034(_):
        e = Entr(_rdng=[Rdng(txt='',_restr=[Restr(kanj=1)]),
                        Rdng(txt='',_restr=[Restr(kanj=3)])],
                 _kanj=[Kanj(txt=''),Kanj(txt=''),Kanj(txt='')])
        _.assertEqual ([(0,1),(0,2),(1,0),(1,1)],
                       list(jdb.restr_expand (e)))
    def test_00035(_):
        e = Entr(_rdng=[Rdng(txt=''),
                        Rdng(txt='', _restr=[Restr(kanj=1),Restr(kanj=2),Restr(kanj=3)])],
                 _kanj=[Kanj(txt=''),Kanj(txt=''),Kanj(txt='')])
        _.assertEqual ([(0,0),(0,1),(0,2)],
                       list(jdb.restr_expand (e)))

if __name__ == '__main__': unittest.main()
