
# jelparse_tab.py
# This file is automatically generated. Do not edit.
# pylint: disable=W,C,R
_tabversion = '3.10'

_lr_method = 'LALR'

_lr_signature = 'BRKTL BRKTR COLON COMMA DOT EQL FF GTEXT HASH KTEXT NUMBER QTEXT RTEXT SEMI SLASH SNUM TEXTentr : preentrpreentr : kanjsect FF rdngsect FF sensespreentr : FF rdngsect FF sensespreentr : kanjsect FF FF senseskanjsect : kanjitemkanjsect : kanjsect SEMI kanjitemkanjitem : krtextkanjitem : krtext taglistsrdngsect : rdngitemrdngsect : rdngsect SEMI rdngitemrdngitem : krtextrdngitem : krtext taglistskrtext : KTEXTkrtext : RTEXTsenses : sensesenses : senses sensesense : SNUM glossesglosses : glossglosses : glosses SEMI glossgloss : GTEXTgloss : GTEXT taglistsgloss : taglists GTEXTgloss : taglists GTEXT tagliststaglists : taglisttaglists : taglists taglisttaglist : BRKTL tags BRKTRtags : tagitemtags : tags COMMA tagitemtagitem : KTEXTtagitem : RTEXTtagitem : TEXTtagitem : QTEXTtagitem : TEXT EQL TEXTtagitem : TEXT EQL TEXT COLONtagitem : TEXT EQL TEXT COLON atexttagitem : TEXT EQL TEXT SLASH TEXT COLONtagitem : TEXT EQL TEXT SLASH TEXT COLON atexttagitem : TEXT EQL jrefsatext : TEXTatext : QTEXTjrefs : jrefjrefs : jrefs SEMI jrefjref : xrefnumjref : xrefnum slistjref : xrefnum DOT jitemjref : jitemjitem : dotlistjitem : dotlist slistdotlist : jtextdotlist : dotlist DOT jtextjtext : KTEXTjtext : RTEXTjtext : QTEXTxrefnum : NUMBERxrefnum : NUMBER HASHxrefnum : NUMBER TEXTslist : BRKTL snums BRKTRsnums : NUMBERsnums : snums COMMA NUMBER'
    
_lr_action_items = {'FF':([0,3,5,6,7,8,9,11,12,13,14,15,18,19,22,23,35,36,],[4,9,-5,-7,-13,-14,17,20,-9,-11,-8,-24,33,-6,-12,-25,-10,-26,]),'KTEXT':([0,4,9,10,16,21,37,38,62,64,69,],[7,7,7,7,26,7,26,54,54,54,54,]),'RTEXT':([0,4,9,10,16,21,37,38,62,64,69,],[8,8,8,8,27,8,27,55,55,55,55,]),'$end':([1,2,15,23,30,31,34,36,39,40,41,42,44,58,59,70,71,],[0,-1,-24,-25,-4,-15,-3,-26,-16,-17,-18,-20,-2,-21,-22,-19,-23,]),'SEMI':([3,5,6,7,8,11,12,13,14,15,18,19,22,23,35,36,40,41,42,47,48,49,50,51,52,53,54,55,56,58,59,63,66,67,68,70,71,76,77,80,82,],[10,-5,-7,-13,-14,21,-9,-11,-8,-24,21,-6,-12,-25,-10,-26,57,-18,-20,62,-41,-43,-46,-54,-47,-49,-51,-52,-53,-21,-22,-44,-55,-56,-48,-19,-23,-42,-45,-50,-57,]),'BRKTL':([6,7,8,13,14,15,22,23,32,36,42,43,49,51,52,53,54,55,56,57,58,59,66,67,71,80,],[16,-13,-14,16,16,-24,16,-25,16,-26,16,16,65,-54,65,-49,-51,-52,-53,16,16,16,-55,-56,16,-50,]),'GTEXT':([15,23,32,36,43,57,],[-24,-25,42,-26,59,42,]),'SNUM':([15,17,20,23,30,31,33,34,36,39,40,41,42,44,58,59,70,71,],[-24,32,32,-25,32,-15,32,32,-26,-16,-17,-18,-20,32,-21,-22,-19,-23,]),'TEXT':([16,37,38,51,60,61,81,],[28,28,46,67,72,75,72,]),'QTEXT':([16,37,38,60,62,64,69,81,],[29,29,56,74,56,56,56,74,]),'BRKTR':([24,25,26,27,28,29,45,46,47,48,49,50,51,52,53,54,55,56,60,63,66,67,68,72,73,74,76,77,78,79,80,81,82,84,85,],[36,-27,-29,-30,-31,-32,-28,-33,-38,-41,-43,-46,-54,-47,-49,-51,-52,-53,-34,-44,-55,-56,-48,-39,-35,-40,-42,-45,82,-58,-50,-36,-57,-37,-59,]),'COMMA':([24,25,26,27,28,29,45,46,47,48,49,50,51,52,53,54,55,56,60,63,66,67,68,72,73,74,76,77,78,79,80,81,82,84,85,],[37,-27,-29,-30,-31,-32,-28,-33,-38,-41,-43,-46,-54,-47,-49,-51,-52,-53,-34,-44,-55,-56,-48,-39,-35,-40,-42,-45,83,-58,-50,-36,-57,-37,-59,]),'EQL':([28,],[38,]),'NUMBER':([38,62,65,83,],[51,51,79,85,]),'COLON':([46,75,],[60,81,]),'SLASH':([46,],[61,]),'DOT':([49,51,52,53,54,55,56,66,67,80,],[64,-54,69,-49,-51,-52,-53,-55,-56,-50,]),'HASH':([51,],[66,]),}

_lr_action = {}
for _k, _v in _lr_action_items.items():
   for _x,_y in zip(_v[0],_v[1]):
      if not _x in _lr_action:  _lr_action[_x] = {}
      _lr_action[_x][_k] = _y
del _lr_action_items

_lr_goto_items = {'entr':([0,],[1,]),'preentr':([0,],[2,]),'kanjsect':([0,],[3,]),'kanjitem':([0,10,],[5,19,]),'krtext':([0,4,9,10,21,],[6,13,13,6,13,]),'rdngsect':([4,9,],[11,18,]),'rdngitem':([4,9,21,],[12,12,35,]),'taglists':([6,13,32,42,57,59,],[14,22,43,58,43,71,]),'taglist':([6,13,14,22,32,42,43,57,58,59,71,],[15,15,23,23,15,15,23,15,23,15,23,]),'tags':([16,],[24,]),'tagitem':([16,37,],[25,45,]),'senses':([17,20,33,],[30,34,44,]),'sense':([17,20,30,33,34,44,],[31,31,39,31,39,39,]),'glosses':([32,],[40,]),'gloss':([32,57,],[41,70,]),'jrefs':([38,],[47,]),'jref':([38,62,],[48,76,]),'xrefnum':([38,62,],[49,49,]),'jitem':([38,62,64,],[50,50,77,]),'dotlist':([38,62,64,],[52,52,52,]),'jtext':([38,62,64,69,],[53,53,53,80,]),'slist':([49,52,],[63,68,]),'atext':([60,81,],[73,84,]),'snums':([65,],[78,]),}

_lr_goto = {}
for _k, _v in _lr_goto_items.items():
   for _x, _y in zip(_v[0], _v[1]):
       if not _x in _lr_goto: _lr_goto[_x] = {}
       _lr_goto[_x][_k] = _y
del _lr_goto_items
_lr_productions = [
  ("S' -> entr","S'",1,None,None,None),
  ('entr -> preentr','entr',1,'p_entr_1','jelparse.py',37),
  ('preentr -> kanjsect FF rdngsect FF senses','preentr',5,'p_preentr_1','jelparse.py',60),
  ('preentr -> FF rdngsect FF senses','preentr',4,'p_preentr_2','jelparse.py',64),
  ('preentr -> kanjsect FF FF senses','preentr',4,'p_preentr_3','jelparse.py',68),
  ('kanjsect -> kanjitem','kanjsect',1,'p_kanjsect_1','jelparse.py',72),
  ('kanjsect -> kanjsect SEMI kanjitem','kanjsect',3,'p_kanjsect_2','jelparse.py',76),
  ('kanjitem -> krtext','kanjitem',1,'p_kanjitem_1','jelparse.py',80),
  ('kanjitem -> krtext taglists','kanjitem',2,'p_kanjitem_2','jelparse.py',84),
  ('rdngsect -> rdngitem','rdngsect',1,'p_rdngsect_1','jelparse.py',91),
  ('rdngsect -> rdngsect SEMI rdngitem','rdngsect',3,'p_rdngsect_2','jelparse.py',95),
  ('rdngitem -> krtext','rdngitem',1,'p_rdngitem_1','jelparse.py',99),
  ('rdngitem -> krtext taglists','rdngitem',2,'p_rdngitem_2','jelparse.py',103),
  ('krtext -> KTEXT','krtext',1,'p_krtext_1','jelparse.py',110),
  ('krtext -> RTEXT','krtext',1,'p_krtext_2','jelparse.py',114),
  ('senses -> sense','senses',1,'p_senses_1','jelparse.py',118),
  ('senses -> senses sense','senses',2,'p_senses_2','jelparse.py',122),
  ('sense -> SNUM glosses','sense',2,'p_sense_1','jelparse.py',126),
  ('glosses -> gloss','glosses',1,'p_glosses_1','jelparse.py',133),
  ('glosses -> glosses SEMI gloss','glosses',3,'p_glosses_2','jelparse.py',137),
  ('gloss -> GTEXT','gloss',1,'p_gloss_1','jelparse.py',141),
  ('gloss -> GTEXT taglists','gloss',2,'p_gloss_2','jelparse.py',145),
  ('gloss -> taglists GTEXT','gloss',2,'p_gloss_3','jelparse.py',149),
  ('gloss -> taglists GTEXT taglists','gloss',3,'p_gloss_4','jelparse.py',153),
  ('taglists -> taglist','taglists',1,'p_taglists_1','jelparse.py',157),
  ('taglists -> taglists taglist','taglists',2,'p_taglists_2','jelparse.py',161),
  ('taglist -> BRKTL tags BRKTR','taglist',3,'p_taglist_1','jelparse.py',166),
  ('tags -> tagitem','tags',1,'p_tags_1','jelparse.py',170),
  ('tags -> tags COMMA tagitem','tags',3,'p_tags_2','jelparse.py',174),
  ('tagitem -> KTEXT','tagitem',1,'p_tagitem_1','jelparse.py',179),
  ('tagitem -> RTEXT','tagitem',1,'p_tagitem_2','jelparse.py',183),
  ('tagitem -> TEXT','tagitem',1,'p_tagitem_3','jelparse.py',187),
  ('tagitem -> QTEXT','tagitem',1,'p_tagitem_4','jelparse.py',196),
  ('tagitem -> TEXT EQL TEXT','tagitem',3,'p_tagitem_5','jelparse.py',205),
  ('tagitem -> TEXT EQL TEXT COLON','tagitem',4,'p_tagitem_6','jelparse.py',209),
  ('tagitem -> TEXT EQL TEXT COLON atext','tagitem',5,'p_tagitem_7','jelparse.py',217),
  ('tagitem -> TEXT EQL TEXT SLASH TEXT COLON','tagitem',6,'p_tagitem_8','jelparse.py',231),
  ('tagitem -> TEXT EQL TEXT SLASH TEXT COLON atext','tagitem',7,'p_tagitem_9','jelparse.py',242),
  ('tagitem -> TEXT EQL jrefs','tagitem',3,'p_tagitem_10','jelparse.py',253),
  ('atext -> TEXT','atext',1,'p_atext_1','jelparse.py',293),
  ('atext -> QTEXT','atext',1,'p_atext_2','jelparse.py',297),
  ('jrefs -> jref','jrefs',1,'p_jrefs_1','jelparse.py',301),
  ('jrefs -> jrefs SEMI jref','jrefs',3,'p_jrefs_2','jelparse.py',305),
  ('jref -> xrefnum','jref',1,'p_jref_1','jelparse.py',309),
  ('jref -> xrefnum slist','jref',2,'p_jref_2','jelparse.py',313),
  ('jref -> xrefnum DOT jitem','jref',3,'p_jref_3','jelparse.py',317),
  ('jref -> jitem','jref',1,'p_jref_4','jelparse.py',321),
  ('jitem -> dotlist','jitem',1,'p_jitem_1','jelparse.py',325),
  ('jitem -> dotlist slist','jitem',2,'p_jitem_2','jelparse.py',329),
  ('dotlist -> jtext','dotlist',1,'p_dotlist_1','jelparse.py',333),
  ('dotlist -> dotlist DOT jtext','dotlist',3,'p_dotlist_2','jelparse.py',337),
  ('jtext -> KTEXT','jtext',1,'p_jtext_1','jelparse.py',341),
  ('jtext -> RTEXT','jtext',1,'p_jtext_2','jelparse.py',345),
  ('jtext -> QTEXT','jtext',1,'p_jtext_3','jelparse.py',349),
  ('xrefnum -> NUMBER','xrefnum',1,'p_xrefnum_1','jelparse.py',353),
  ('xrefnum -> NUMBER HASH','xrefnum',2,'p_xrefnum_2','jelparse.py',357),
  ('xrefnum -> NUMBER TEXT','xrefnum',2,'p_xrefnum_3','jelparse.py',361),
  ('slist -> BRKTL snums BRKTR','slist',3,'p_slist_1','jelparse.py',365),
  ('snums -> NUMBER','snums',1,'p_snums_1','jelparse.py',369),
  ('snums -> snums COMMA NUMBER','snums',3,'p_snums_2','jelparse.py',376),
]
