import random
import unittest
from scripts.diagnostics.motif_events import (align_points, describe_recurrence,
    lane_relations, points, shuffle_pitches, delayed_copy_sensitivity)


def melody():
    ps=[48,50,52,55,53,52,50,48]
    return [{'tick':k*96+i*12,'pitch':p+(5 if k%2 else 0),'channel':0}
            for k in range(4) for i,p in enumerate(ps)]


class MotifEventsTests(unittest.TestCase):
    def test_bitset_search_matches_independent_sets(self):
        rng=random.Random(84)
        for _ in range(30):
            a={(rng.randrange(96),rng.randrange(96)) for _ in range(12)}
            b={(rng.randrange(96),rng.randrange(96)) for _ in range(15)}
            expected=max(len(a & {(t+dt,p+dp) for t,p in b})
                         for dt in range(-18,19,6) for dp in range(-12,13))
            self.assertEqual(align_points(a,b)['matched'],expected)

    def test_start_ornament_preserves_core_and_reduces_purity(self):
        a={(0,48),(12,52),(24,55),(36,60)}
        b={(t+6,p+7) for t,p in a}|{(0,80),(18,82)}
        result=align_points(a,b)
        self.assertEqual(result['matched'],4)
        self.assertEqual(result['left_coverage'],1)
        self.assertAlmostEqual(result['right_coverage'],2/3)
        self.assertAlmostEqual(result['f1'],.8)
        self.assertEqual((result['time_shift_right_to_left'],result['pitch_shift_right_to_left']),(-6,-7))

    def test_entire_pipeline_ignores_per_note_channel_splits(self):
        a=melody();b=[dict(e,channel=i%16) for i,e in enumerate(a)]
        self.assertEqual(describe_recurrence(a,384,2),describe_recurrence(b,384,2))

    def test_entire_pipeline_ignores_event_order_and_unison_doubles(self):
        a=melody();b=list(reversed(a))+[dict(e,channel=2) for e in a]
        self.assertEqual(describe_recurrence(a,384,2),describe_recurrence(b,384,2))

    def test_whole_song_transpose_preserves_recurrence(self):
        a=melody();b=[dict(e,pitch=e['pitch']+12) for e in a]
        self.assertEqual(describe_recurrence(a,384,2),describe_recurrence(b,384,2))

    def test_trailing_padding_does_not_create_passage(self):
        a=melody()
        self.assertEqual(describe_recurrence(a,384,2),describe_recurrence(a,385,2))

    def test_null_preserves_onset_cardinality_and_pitch_marginal(self):
        from collections import Counter
        a=melody()+[dict(e,pitch=e['pitch']+7,channel=1) for e in melody()]
        b=shuffle_pitches(a,1)
        self.assertEqual(Counter(t for t,p in points(a)),Counter(t for t,p in points(b)))
        self.assertEqual(Counter(p for t,p in points(a)),Counter(p for t,p in points(b)))

    def test_dense_chromatic_sets_are_not_specific_motifs(self):
        a=[{'tick':t,'pitch':p,'channel':p%12} for t in range(0,384,12) for p in range(48,60)]
        result=describe_recurrence(a,384,2)
        for scale in result['scales']:
            self.assertEqual(scale['mean_best_excess'],0)
            self.assertEqual(scale['positive_best_match_fraction'],0)

    def test_echo_and_canon_are_reported_as_ambiguous(self):
        a=melody();b=[dict(e,tick=e['tick']+18,channel=1) for e in a]
        edges=lane_relations(a+b)
        edge=next(e for e in edges if e['kind']=='delayed_unison_copy_candidate')
        self.assertEqual(edge['lag_ticks'],18)
        self.assertEqual(edge['f1'],1)
        self.assertIn('canon',edge['ambiguity'])

    def test_parallel_harmony_is_separate_relation(self):
        a=melody();b=[dict(e,pitch=e['pitch']+7,channel=1) for e in a]
        edges=lane_relations(a+b)
        edge=next(e for e in edges if e['kind']=='parallel_harmony_candidate' and e['source_channel']==1)
        self.assertEqual(edge['semitones_target_minus_source'],7)
        self.assertEqual(edge['f1'],1)

    def test_delayed_copy_cycle_cannot_erase_all_lanes(self):
        e=[{'tick':48*k+t+shift,'pitch':p,'channel':ch}
           for ch,shift in enumerate([0,16,32]) for k in range(20)
           for t,p in [(0,48),(6,52),(12,55)]]
        kept,removed=delayed_copy_sensitivity(e,lane_relations(e))
        self.assertEqual(removed,0)
        self.assertEqual(kept,e)

    def test_hypothetical_echo_removal_preserves_source(self):
        a=melody();b=a+[dict(e,tick=e['tick']+18,channel=1) for e in a]
        kept,removed=delayed_copy_sensitivity(b,lane_relations(b))
        self.assertEqual(removed,len(a))
        self.assertEqual(kept,a)

    def test_single_chord_is_not_summary_shape_evidence(self):
        a=[{'tick':t,'pitch':p,'channel':0} for t in [0,96] for p in range(48,60)]
        result=describe_recurrence(a,192,2)
        for scale in result['scales']:
            self.assertEqual(scale['positive_best_match_fraction'],0)
            self.assertEqual(scale['top_pairs'],[])

    def test_echo_does_change_texture_view_not_claimed_invariant(self):
        a=melody();b=a+[dict(e,tick=e['tick']+18,channel=1) for e in a]
        self.assertNotEqual(describe_recurrence(a,384,2)['scales'][0]['f1'],
                            describe_recurrence(b,402,2)['scales'][0]['f1'])

if __name__=='__main__':unittest.main()
