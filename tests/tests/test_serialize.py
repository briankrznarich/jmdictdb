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
             jdb.KW = jdb.Kwds ('')

    def test000010(_):
        rt(_, jdb.Entr())
    def test000020(_):
        rt(_, jdb.Entr(id=111,src=3,stat=2,seq=444,dfrm=555,unap=True,notes="xxx"))

    def test010010(_):  # Kanj
        rt(_, jdb.Entr(_kanj=[jdb.Kanj(txt='歌手')]))

    def test020010(_):  # Kinf
        rt(_, jdb.Entr(_kanj=[jdb.Kanj(txt='歌手', _inf=[jdb.Kinf(ord=2,kw=3)])]),
                # Note that the 'ord=2' is expectedly lost in the reconstruction.
              jdb.Entr(_kanj=[jdb.Kanj(txt='歌手', _inf=[jdb.Kinf(kw=3)])]))

    def test030010(_):  # Kanj freq
        rt(_, jdb.Entr(_kanj=[jdb.Kanj(txt='歌手', _freq=[jdb.Freq(kw=6,value=14)])]))

    def test040010(_):  # Rdng
        rt(_, jdb.Entr(_rdng=[jdb.Rdng(txt='かしゅ')]))

    def test060010(_):  # Rdng freq
        rt(_, jdb.Entr(_rdng=[jdb.Rdng(txt='かしゅ', _freq=[jdb.Freq(kw=6,value=14)])]))

    def test070010(_):  # Restr
        e = jdb.Entr(_kanj=[jdb.Kanj(txt='果物'), jdb.Kanj(txt='菓物')],
                     _rdng=[jdb.Rdng(txt='くだもの'),
                            jdb.Rdng(txt='かぶつ', _restr=[jdb.Restr(kanj=2)])])
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
        rt(_, jdb.Entr(_sens=[jdb.Sens(_dial=[jdb.Dial(kw=3)])]))

    def test110010(_):  # Fld
        rt(_, jdb.Entr(_sens=[jdb.Sens(_fld=[jdb.Fld(kw=3)])]))

    def test120010(_):  # Lsrc
        rt(_, jdb.Entr(_sens=[jdb.Sens(_lsrc=[jdb.Lsrc()])]))
    def test120020(_):  # Lsrc
        rt(_, jdb.Entr(_sens=[jdb.Sens(_lsrc=[jdb.Lsrc(lang=137,txt='xxx',wasei=True,part=True)])]))

    def test130010(_):  # Misc
        rt(_, jdb.Entr(_sens=[jdb.Sens(_misc=[jdb.Misc(kw=3)])]))

    def test140010(_):  # Pos
        rt(_, jdb.Entr(_sens=[jdb.Sens(_pos=[jdb.Pos(kw=3)])]))

    def test150010(_):  # Stagr
        e = jdb.Entr(_rdng=[jdb.Rdng(txt='くだもの'), jdb.Rdng(txt='かぶつ')],
                     _sens=[jdb.Sens(_stagr=[jdb.Stagr(rdng=2)]),
                            jdb.Sens()])
        rt(_, e)

    def test160010(_):  # Stagk
        e = jdb.Entr(_kanj=[jdb.Kanj(txt='果物'), jdb.Kanj(txt='菓物')],
                     _sens=[jdb.Sens(_stagk=[jdb.Stagk()]),
                            jdb.Sens()])
        rt(_, e)

    def test170010(_):  # Xref
        rt(_, jdb.Entr(_sens=[jdb.Sens(_xref=[jdb.Xref()])]))
    def test170020(_):  # Xref
        rt(_, jdb.Entr(_sens=[jdb.Sens(_xref=[
           jdb.Xref(None,None,None,3,70,1,'あい','愛','xxx',True,True)])]))
    def test170030(_):  # Xref
        rt(_, jdb.Entr(_sens=[jdb.Sens(_xref=[
           jdb.Xref(None,None,None,3,70,1,None,'愛','xxx',True,True)])]))
    def test170040(_):  # Xref
        rt(_, jdb.Entr(id=7,_sens=[jdb.Sens(_xref=[
           jdb.Xref(None,None,None,3,70,1,'あい',None,'xxx',True,True)])]))

    def test180010(_):  # Xrslv
        rt(_, jdb.Entr(_sens=[jdb.Sens(_xrslv=[jdb.Xrslv(typ=3)])]))
    def test180020(_):  # Xrslv
        rt(_, jdb.Entr(_sens=[jdb.Sens(_xrslv=[
           jdb.Xrslv(None,None,None,3,'あい','愛',1,'xxx',True)])]))

    def test190010(_):  # Hist
        rt(_, jdb.Entr(_hist=[jdb.Hist(dt=s2dt('2020-10-31 12:21:00'))]))
    def test190020(_):  # Hist
        rt(_, jdb.Entr(_hist=[jdb.Hist(None,None,2,True,
                                       s2dt('2020-10-31 12:21:00'),
                                       'user','Bill','b@foo','diff','refs',
                                       'notes')]))

class Roundtrip (unittest.TestCase):
    def test001010(_):
        rt(_, jdb.Entr(id=7, _rdng=[jdb.Rdng(7,1,txt='あい')]),
              jdb.Entr(id=7, _rdng=[jdb.Rdng(None,None,txt='あい')]))
    def test001020(_):
        rt(_, jdb.Entr(id=7,_rdng=[jdb.Rdng(7,1,'あい')]), setkeys=True)
    def test001040(_):
          # Order of child objects the remains same regardless of ord number.
        rt(_, jdb.Entr(id=7,_rdng=[jdb.Rdng(7,2,'あい'),
                                   jdb.Rdng(7,1,'かき')]),
              jdb.Entr(id=7,_rdng=[jdb.Rdng(None,None,'あい'),
                                   jdb.Rdng(None,None,'かき')]))


#=============================================================================
# Support functions

def rt (_, inp, exp=None, setkeys=False):  # Roundtrip test
        if exp is None: exp = inp      # If no "expected" arg, expect 'inp'.
        #pdb.set_trace()
        s = serialize.serialize (inp)
        out = serialize.unserialize (s)
        if setkeys: jdb.setkeys (out)
        _.assertEqual (exp, out)       # Compare expected obj to received.

def s2dt (s): return datetime.datetime.strptime (s, "%Y-%m-%d %H:%M:%S")
def dt2s (d): return d.isoformat(sep=" ")

if __name__ == '__main__': main()





