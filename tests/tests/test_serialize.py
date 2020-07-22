import sys, re, unittest, datetime, pdb
from jmdictdb import jdb
from jmdictdb import serialize

  #FIXME: the output in failure cases is currently pretty worthless
  # since it is simply the repr's of the input and output objects
  # which don't show any detail below the attributes of the Entr
  # object itself.  To investigate failure cause usually involves
  # inserting a pdb.set_trace() breakpoint and examining the two
  # object interactively. 

def main(): unittest.main()

class Objects (unittest.TestCase):
    def setUp(_):
         if not hasattr(jdb,'KW') or not jdb.KW: 
             jdb.KW = jdb.Kwds ('../../pg/data')

    def test000010(_):
        rt(_, jdb.Entr())
    def test000020(_):
        rt(_, jdb.Entr(id=111,src=3,stat=2,seq=444,dfrm=555,unap=True,notes="xxx"))

    def test010010(_):  # Kanj
        rt(_, jdb.Entr(_kanj=[jdb.Kanj(txt='歌手')]))

    def test020010(_):  # Kinf
        rt(_, jdb.Entr(_kanj=[jdb.Kanj(txt='歌手', _inf=[jdb.Kinf(ord=2,kw=3)])]))

    def test030010(_):  # Kanj freq
        rt(_, jdb.Entr(_kanj=[jdb.Kanj(txt='歌手', _freq=[jdb.Freq(kw=6,value=14)])]))

    def test040010(_):  # Rdng
        rt(_, jdb.Entr(_rdng=[jdb.Rdng(txt='かしゅ')]))

    def test050010(_):  # Rinf
        rt(_, jdb.Entr(_rdng=[jdb.Rdng(txt='かしゅ', _inf=[jdb.Rinf(ord=2,kw=3)])]))

    def test060010(_):  # Rdng freq
        rt(_, jdb.Entr(_rdng=[jdb.Rdng(txt='かしゅ', _freq=[jdb.Freq(kw=6,value=14)])]))

    def test070010(_):  # Restr
        e = jdb.Entr(_kanj=[jdb.Kanj(kanj=1, txt='果物'), jdb.Kanj(kanj=2, txt='菓物')],
                     _rdng=[jdb.Rdng(rdng=1, txt='くだもの'),
                            jdb.Rdng(rdng=2, txt='かぶつ', _restr=[jdb.Restr(kanj=2)])])
        rt (_, e)

    def test080010(_):  # Sens
        e = jdb.Entr(_sens=[jdb.Sens(notes='test text')])

    def test090010(_):  # Gloss -- Basic roundtrip test.
        rt(_, jdb.Entr(_sens=[jdb.Sens(_gloss=[jdb.Gloss(txt='test text',lang=1,ginf=1)])]))
    def test090020(_):  # Gloss -- Non-default language.
        rt(_, jdb.Entr(_sens=[jdb.Sens(_gloss=[jdb.Gloss(txt='test',lang=137,ginf=1)])]))
    def test090030(_):  # Gloss -- Non-default type.
        rt(_, jdb.Entr(_sens=[jdb.Sens(_gloss=[jdb.Gloss(txt='test',lang=1,ginf=2)])]))
    @unittest.skip ("Anticipated future behavior")
    def test090040(_):  # Gloss -- Check no replacement of missing ginf values with defaults.
        rt(_, jdb.Entr(_sens=[jdb.Sens(_gloss=[jdb.Gloss(txt='test')])]),
              jdb.Entr(_sens=[jdb.Sens(_gloss=[jdb.Gloss(txt='test',lang=1,ginf=1)])]))

    def test100010(_):  # Dial
        rt(_, jdb.Entr(_sens=[jdb.Sens(_dial=[jdb.Dial(ord=2,kw=3)])]))

    def test110010(_):  # Fld
        rt(_, jdb.Entr(_sens=[jdb.Sens(_fld=[jdb.Fld(ord=2,kw=3)])]))

    def test120010(_):  # Lsrc
        rt(_, jdb.Entr(_sens=[jdb.Sens(_lsrc=[jdb.Lsrc()])]))
    def test120020(_):  # Lsrc
        rt(_, jdb.Entr(_sens=[jdb.Sens(_lsrc=[jdb.Lsrc(lang=137,txt='xxx',wasei=True,part=True)])]))

    def test130010(_):  # Misc
        rt(_, jdb.Entr(_sens=[jdb.Sens(_misc=[jdb.Misc(ord=2,kw=3)])]))

    def test140010(_):  # Pos
        rt(_, jdb.Entr(_sens=[jdb.Sens(_pos=[jdb.Pos(ord=2,kw=3)])]))

    def test150010(_):  # Stagr
        e = jdb.Entr(_rdng=[jdb.Rdng(rdng=1,txt='くだもの'), jdb.Rdng(rdng=2,txt='かぶつ')],
                     _sens=[jdb.Sens(sens=1, _stagr=[jdb.Stagr(rdng=2)]),
                            jdb.Sens(sens=2)])
        rt(_, e)

    def test160010(_):  # Stagk
        e = jdb.Entr(_kanj=[jdb.Kanj(kanj=1,txt='果物'), jdb.Kanj(kanj=2,txt='菓物')],
                     _sens=[jdb.Sens(sens=1, _stagk=[jdb.Stagk(kanj=1)]),
                            jdb.Sens(sens=2)])
        rt(_, e)

    def test170010(_):  # Xref
        rt(_, jdb.Entr(_sens=[jdb.Sens(_xref=[jdb.Xref()])]))
    def test170020(_):  # Xref
        rt(_, jdb.Entr(id=7,_sens=[jdb.Sens(7,8,_xref=[
           jdb.Xref(7,8,9,3,70,1,'あい','愛','xxx',True,True)])]))
    def test170030(_):  # Xref
        rt(_, jdb.Entr(id=7,_sens=[jdb.Sens(7,8,_xref=[
           jdb.Xref(7,8,9,3,70,1,None,'愛','xxx',True,True)])]))
    def test170040(_):  # Xref
        rt(_, jdb.Entr(id=7,_sens=[jdb.Sens(7,8,_xref=[
           jdb.Xref(7,8,9,3,70,1,'あい',None,'xxx',True,True)])]))

    def test180010(_):  # Xrslv
        rt(_, jdb.Entr(_sens=[jdb.Sens(_xrslv=[jdb.Xrslv(typ=3)])]))
    def test180020(_):  # Xrslv
        rt(_, jdb.Entr(id=7,_sens=[jdb.Sens(7,8,_xrslv=[
           jdb.Xrslv(7,8,9,3,'あい','愛',1,'xxx',True)])]))

    def test190010(_):  # Hist
        rt(_, jdb.Entr(_hist=[jdb.Hist(dt=s2dt('2020-10-31 12:21:00'))]))
    def test190020(_):  # Hist
        rt(_, jdb.Entr(7,_hist=[jdb.Hist(7,dt=s2dt('2020-10-31 12:21:00'))]))

class Roundtrip (unittest.TestCase):
    def test001010(_):
        rt(_, jdb.Entr(_rdng=[jdb.Rdng(None, 2,'あい')]))
    def test001020(_):
        rt(_, jdb.Entr(id=7,_rdng=[jdb.Rdng(7,2,'あい')]))
    @unittest.skip ("Anticipated future behavior")
    def test001030(_): 
        rt(_, jdb.Entr(_rdng=[jdb.Rdng(   7,1,'あい')]),
              jdb.Entr(_rdng=[jdb.Rdng(None,1,'あい')]))
    @unittest.skip ("Anticipated future behavior")
    def test001035(_): 
          # entr.id (7) is propagated to child object regardless of what
          # .entr value the child object has (6 in this case).
        rt(_, jdb.Entr(7, _rdng=[jdb.Rdng(6,1,'あい')]),
              jdb.Entr(7, _rdng=[jdb.Rdng(7,1,'あい')]))
    def test001040(_):
          # Order of child objects the remains same regardless of ord number.
        rt(_, jdb.Entr(id=7,_rdng=[jdb.Rdng(7,2,'あい'), jdb.Rdng(7,1,'かき')]))

class Other (unittest.TestCase):
    def test030310(_):  # Restr, same as Test_objects.test030310 but
                        # with permuted index numbers.
        e = jdb.Entr(_kanj=[jdb.Kanj(kanj=5, txt='果物'), jdb.Kanj(kanj=3, txt='菓物')],
                     _rdng=[jdb.Rdng(rdng=7, txt='かぶつ'), jdb.Rdng(rdng=2, txt='くだもの')])
        r = jdb.Restr(kanj=3, rdng=7)
        e._rdng[0]._restr= [r];  e._kanj[1]._restr = [r]
        rt (_, e)

#=============================================================================
# Support functions

def rt (_, inp, exp=None):  # Roundtrip test
        if exp is None: exp = inp      # If no "expected" arg, expect 'inp'.
        #pdb.set_trace()
        s = serialize.serialize (inp)
        out = serialize.unserialize (s)
        _.assertEqual (out, exp)       # Compare received obj to expected.

def s2dt (s): return datetime.datetime.strptime (s, "%Y-%m-%d %H:%M:%S")
def dt2s (d): return d.isoformat(sep=" ")

if __name__ == '__main__': main()





