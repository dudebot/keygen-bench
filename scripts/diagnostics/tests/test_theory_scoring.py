"""Behavioral falsification gates; not human enjoyment validation."""
import math
import random
import unittest
from scripts.diagnostics.theory_scoring import score_events,entropy,core_content
BASE=[48,52,55,50,53,57,52,55]
def phrases(blocks):return [{'tick':k*96+i*12,'pitch':p,'channel':0} for k,b in enumerate(blocks) for i,p in enumerate(b)]
class TheoryScoringTests(unittest.TestCase):
 def test_entropy_fixed_alphabet(self):
  self.assertAlmostEqual(entropy([0,1]*8),1);self.assertAlmostEqual(entropy(list(range(12))*2),math.log2(12))
 def test_constant_tone_never_gains_development(self):
  for n in [16,64,512]:
   r=score_events([{'tick':i*6,'pitch':48,'channel':i%4} for i in range(n)],n*6)
   self.assertEqual(r['structural_score'],0);self.assertEqual(r['evolution_required_score'],0)
 def test_static_chord_has_no_motion(self):self.assertEqual(core_content({(t,p) for t in range(0,96,12) for p in [48,52,55]})['gate'],0)
 def test_exact_loop_bounded_and_no_development(self):
  r=score_events(phrases([BASE]*8),768);self.assertGreater(r['structural_score'],0);self.assertLessEqual(r['structural_score'],25);self.assertEqual(r['evolution_required_score'],0)
 def test_replicated_changed_shapes_supply_development(self):
  v=[48,52,55,50,53,57,54,59];c=[50,53,57,52,55,59,53,57]
  r=score_events(phrases([BASE,BASE,v,BASE,c,BASE,v,c]),768)
  self.assertGreater(r['evolution_required_score'],0);self.assertGreater(r['structural_score'],score_events(phrases([BASE]*8),768)['structural_score'])
 def test_random_fixture_is_not_organized(self):
  rng=random.Random(25);r=score_events(phrases([[rng.randrange(48,72) for i in range(8)] for _ in range(8)]),768);self.assertEqual(r['structural_score'],0)
 def test_layout_duplicates_order_invariance(self):
  a=phrases([BASE]*4);b=list(reversed([dict(e,channel=i%8) for i,e in enumerate(a)]))+[dict(e,channel=99) for e in a]
  self.assertEqual(score_events(a,384),score_events(b,384))
 def test_octave_invariance(self):
  a=phrases([BASE]*4);self.assertAlmostEqual(score_events(a,384)['structural_score'],score_events([dict(e,pitch=e['pitch']+12) for e in a],384)['structural_score'])
 def test_trailing_padding_invariance(self):
  e=phrases([BASE]*4);self.assertEqual(score_events(e,384),score_events(e,1000))
 def test_single_random_ornaments_do_not_unlock_variants(self):
  a=phrases([BASE]*8);base=score_events(a,768)['structural_score']
  for seed in [21,25,101]:
   rng=random.Random(seed);e=a+[{'tick':k*96+1,'pitch':rng.randrange(60,84),'channel':2} for k in range(8)];r=score_events(e,768)
   self.assertEqual(r['evolution_required_score'],0);self.assertLessEqual(r['structural_score'],base)
 def test_15_17_beat_phase_walk(self):
  for period in [360,408]:
   block=[{'tick':i*6,'pitch':48+[0,4,7,4][i%4],'channel':0} for i in range(period//6)];e=[dict(v,tick=v['tick']+k*period) for k in range(4) for v in block];r=score_events(e,4*period)
   self.assertEqual(r['periodicity']['fit'],1);self.assertEqual(r['evolution_required_score'],0);self.assertLessEqual(r['structural_score'],25)
 def test_bounds_rejected_before_huge_bitsets(self):
  for es,t in [([{'tick':1.1,'pitch':48}],10),([{'tick':-1,'pitch':48}],10),([{'tick':10,'pitch':48}],10),([{'tick':10**9,'pitch':48}],10**9+1),([{'tick':0,'pitch':96}],10)]:
   with self.assertRaises(ValueError):score_events(es,t)
 def test_iterators_have_same_evidence_as_lists(self):
  e=phrases([BASE]*4);self.assertEqual(score_events(e,384),score_events(iter(e),384))
 def test_empty(self):self.assertEqual(score_events([],0)['structural_score'],0)
if __name__=='__main__':unittest.main()
