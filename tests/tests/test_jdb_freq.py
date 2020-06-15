import sys, unittest, pdb
from copy import deepcopy
from jmdictdb.objects import *
from jmdictdb import jdb

class Test_jdb_copy_freqs (unittest.TestCase):
    def setUp(_):
          # Create some freq objects for use in tests.
        _.ichi1  = Freq (kw=1, value=1)
        _.ichi2  = Freq (kw=1, value=2)
        _.gai1   = Freq (kw=2, value=1)
        _.nf17   = Freq (kw=5, value=17)
        _.nf16   = Freq (kw=5, value=16)
        _.ichi2a = Freq (kw=1, value=2)

    def test_0010(_):
          # No rdng or kanj.
        p, e = Entr(), Entr()
        jdb.copy_freqs (p, e)
        _.assertEqual ([], e._rdng)
        _.assertEqual ([], e._kanj)
    def test_0020(_):
          # No kanj.
        p = Entr(_rdng=[Rdng('よい')])
        e = deepcopy (p)
        jdb.copy_freqs (p, e)
        _.assertEqual ([], e._rdng[0]._freq)
    def test_0030(_):
          # No rdng.
        p = Entr (_kanj=[Kanj('良い')])
        e = deepcopy (p)
        jdb.copy_freqs (p, e)
        _.assertEqual ([], e._kanj[0]._freq)
    def test_0040(_):
          # Test existing freq removal
        p = Entr(_rdng=[Rdng(txt='よ')], _kanj=[Kanj(txt='良')])
        e = deepcopy (p)
        e._rdng[0]._freq = [_.ichi2]
        e._kanj[0]._freq = [_.gai1]
        jdb.copy_freqs (p, e)
        _.assertEqual ([], e._rdng[0]._freq)
        _.assertEqual ([], e._kanj[0]._freq)

    def test_0110(_):
          # Verify copied freq values are copied by value, not by reference.
        p = Entr(_rdng=[Rdng(txt='よ')], _kanj=[Kanj(txt='良')])
        e = deepcopy (p)
          # Note that we must use the same (as in 'is', not as in '==')
          # Freq object in the two freq lists, the lists themselves must
          # be distinct objects to accurately represent how things work
          # in the jmdictdb software.
        p._rdng[0]._freq = [_.ichi2]
        p._kanj[0]._freq = [_.ichi2]
        jdb.copy_freqs (p, e)
        _.assertEqual (1, len(e._rdng[0]._freq))
        _.assertEqual (1, len(e._kanj[0]._freq))
        _.assertFalse (check_neql (e._rdng[0]._freq[0], _.ichi2))
        _.assertFalse (check_neql (e._kanj[0]._freq[0], _.ichi2))
        _.assertNotEqual (id(e._rdng[0]._freq[0]), id(e._kanj[0]._freq[0]))
        _.assertNotEqual (id(e._rdng[0]._freq[0]), id(_.ichi2))
        _.assertNotEqual (id(e._rdng[0]._freq[0]), id(_.ichi2))

    def test_0120(_):
          # Rdng only freq
        p = Entr(_rdng=[Rdng(txt='よ')], _kanj=[Kanj(txt='良')])
        e = deepcopy (p)
        p._rdng[0]._freq = [_.ichi2]
        jdb.copy_freqs (p, e)
        _.assertEqual (1, len(e._rdng[0]._freq))
        _.assertEqual (0, len(e._kanj[0]._freq))
        _.assertFalse (check_neql (e._rdng[0]._freq[0], _.ichi2), '')

    def test_0130(_):
          # Kanj only freq
        p = Entr(_rdng=[Rdng(txt='よ')], _kanj=[Kanj(txt='良')])
        e = deepcopy (p)
        p._kanj[0]._freq = [_.ichi2]
        jdb.copy_freqs (p, e)
        _.assertEqual (0, len(e._rdng[0]._freq))
        _.assertEqual (1, len(e._kanj[0]._freq))
        _.assertFalse (check_neql (e._kanj[0]._freq[0], _.ichi2), '')

    def test_0140(_):
          # A more complex set.
        p = Entr(_rdng=[Rdng(txt='の'), Rdng(txt='や'), Rdng(txt='ぬ')],
                 _kanj=[Kanj(txt='野'), Kanj(txt='埜'), Kanj(txt='金')])
        e = deepcopy (p)
        p._rdng[1]._freq.append (_.ichi1); p._kanj[0]._freq.append (_.ichi1)
        p._rdng[1]._freq.append (_.gai1);  p._kanj[2]._freq.append (_.gai1)
        p._rdng[2]._freq.append (_.nf16);  p._kanj[0]._freq.append (_.nf16)
        p._rdng[2]._freq.append (_.nf17);  p._kanj[2]._freq.append (_.nf17)
        p._rdng[2]._freq.append (_.ichi2)
        p._kanj[2]._freq.append (_.ichi2a)
        jdb.copy_freqs (p, e)
          #FIXME: the 3rd arg below is supposed to suppress the default
          # message (which we don't want since check_neqls() provides our
          # message) but checking unitttest source code shows we need to
          # set TestCase.longMessage to False to make it effective; don't
          # know how to do that at the moment.
          # Right now a fail prints out message plus the confusing
          # observation that our message "is not False".
        _.assertFalse (check_neqls (e._rdng[0]._freq, p._rdng[0]._freq), '')
        _.assertFalse (check_neqls (e._rdng[1]._freq, p._rdng[1]._freq), '')
        _.assertFalse (check_neqls (e._rdng[2]._freq, p._rdng[2]._freq), '')
        _.assertFalse (check_neqls (e._kanj[0]._freq, p._kanj[0]._freq), '')
        _.assertFalse (check_neqls (e._kanj[1]._freq, p._kanj[1]._freq), '')
        _.assertFalse (check_neqls (e._kanj[2]._freq, p._kanj[2]._freq), '')

    def test_0250(_):
          # Check freq copy when position of rdng has changed.
        p = Entr(_rdng=[Rdng(txt='の', _freq=[_.ichi1]), Rdng(txt='が')],)
        e = Entr(_rdng=[Rdng(txt='が'), Rdng(txt='の')],)
        jdb.copy_freqs (p, e)
        _.assertEqual (e._rdng[0]._freq, [])
        _.assertFalse (check_neqls (e._rdng[1]._freq, p._rdng[0]._freq), '')

    def test_0260(_):
          # Check freq copy when position of kanj has changed.
          # Same as test_0250 except for kanji rather than rdng.
        p = Entr(_kanj=[Kanj(txt='野', _freq=[_.ichi1]), Kanj(txt='乃')],)
        e = Entr(_kanj=[Kanj(txt='乃'), Kanj(txt='野')])
        jdb.copy_freqs (p, e)
        _.assertEqual (e._kanj[0]._freq, [])
        _.assertFalse (check_neqls (e._kanj[1]._freq, p._kanj[0]._freq), '')

    def test_0270(_):
          # Check freq copy when matching rdng is gone.
        p = Entr(_rdng=[Rdng(txt='の', _freq=[_.ichi1]), Rdng(txt='が')],)
        e = Entr(_rdng=[Rdng(txt='が'), Rdng(txt='に')],)
        jdb.copy_freqs (p, e)
        _.assertEqual (e._rdng[0]._freq, [])
        _.assertEqual (e._rdng[0]._freq, [])

    def test_0280(_):
          # Check freq copy when matching kanj is gone.
          # Same as test_0270 except for kanji rather than rdng.
        p = Entr(_kanj=[Kanj(txt='野', _freq=[_.ichi1]), Kanj(txt='乃')],)
        e = Entr(_kanj=[Kanj(txt='乃'), Kanj(txt='箆')])
        jdb.copy_freqs (p, e)
        _.assertEqual (e._kanj[0]._freq, [])
        _.assertEqual (e._kanj[1]._freq, [])

def check_neql (f1, f2):
        # Check two freq items for differences.  Ignores .entr, .rdng, 
        # and .kanj attributes.
        if f1.kw!=f2.kw or f1.value!=f2.value:
            return "freq values differ: (%s,%s) vs (%s,%s)"\
                   % (f1.kw,f1.value,f2.kw,f2.value)
        return ""

def check_neqls (fl1, fl2):
        # Check corresponding items in two freq lists for differences.
        if len (fl1) != len(fl2): return \
            "length of first arg (%s) differs from length of second (%s)"\
            % (len(fl1), len(fl2))
        for n, (f1, f2) in enumerate (zip (fl1, fl2)):
            if check_neql (f1, f2):
                return "item %s: %s" % (n, check_eql (f1, f2))
        return ""
if __name__ == '__main__': unittest.main()





