import unittest
from scripts.diagnostics.phrase_relationships import (query_section,fragment_occurrences,
    common_onset_relation,motif_harmonic_context,traverse_with_locations)
from scripts.diagnostics.structure_extraction import load_trusted_sources
from pathlib import Path


def events(pitches,channel=1,instrument=1,ticks=None):
    ticks=ticks or [i*12 for i in range(len(pitches))]
    return [{'tick':t,'pitch':p,'channel':channel,'instrument':instrument,'row':t//6,'slide_target':False} for t,p in zip(ticks,pitches)]


class PhraseRelationshipTests(unittest.TestCase):
    def test_motif_identity_survives_channel_and_instrument_handoff(self):
        seed=events([48,52,55,53,50,48])
        target=events([48,52,55,53,50,48],channel=9,instrument=18)
        result=query_section(seed,target)
        self.assertEqual(result['left_coverage'],1)
        self.assertEqual(result['right_coverage'],1)
        self.assertTrue(result['channel_handoff_possible'])
        self.assertTrue(result['instrument_handoff_possible'])

    def test_within_phrase_channel_handoff_preserves_primary_match(self):
        a=events([48,52,55,53,50,48]);b=[dict(e,channel=3 if i<3 else 7,instrument=2 if i<3 else 4) for i,e in enumerate(a)]
        m=query_section(a,b)
        self.assertEqual(m['left_coverage'],1)
        self.assertEqual(m['target_channels_at_matched_points'],[3,7])

    def test_start_ornament_keeps_core_without_first_note_normalization(self):
        a=events([48,52,55,53,50,48]);b=[dict(e,instrument=3) for e in a]+events([82],channel=2,ticks=[6])
        m=query_section(a,b)
        self.assertEqual(m['left_coverage'],1)
        self.assertAlmostEqual(m['right_coverage'],6/7)

    def test_fragment_moves_in_section_and_changes_timbre(self):
        a=events([69,68,66,64],ticks=[264,288,300,312])
        b=events([74,73,71,69],channel=5,instrument=18,ticks=[0,24,36,48])
        sections=[{'visit':0,'order':1,'pattern':1,'events':a},{'visit':1,'order':5,'pattern':5,'events':b}]
        hits=fragment_occurrences(sections,0,1)[0]['matches']
        hit=hits[0];self.assertEqual(hit['notes'],4);self.assertEqual(hit['pitch_shift_target_minus_source'],5)
        self.assertEqual(hit['single_lane_realizations'],[5]);self.assertTrue(hit['possible_instrument_change'])

    def test_other_lane_instrument_does_not_fake_realization_change(self):
        a=events([48,52,55,60]);b=a+events([48,52,55,60],channel=2,instrument=4)
        sections=[{'visit':0,'order':0,'pattern':0,'events':a},{'visit':1,'order':1,'pattern':1,'events':b}]
        h=fragment_occurrences(sections,0,1)[0]['matches'][0]
        own=next(r for r in h['single_lane_realizations_detail'] if r['channel']==1)
        self.assertFalse(own['instrument_ids_changed'])

    def test_diatonic_thirds_are_visible_with_variable_semitone_size(self):
        a=events([48,50,52,53,55,57,59,60]);b=events([52,53,55,57,59,60,62,64],channel=2)
        m=common_onset_relation(a,b)
        self.assertEqual(m['interval_histogram_semitones'],{3:4,4:4})
        self.assertEqual(m['third_sixth_fraction'],1)
        self.assertEqual(m['usable_singleton_onsets'],8)

    def test_contrary_oblique_and_parallel_motion_remain_distinct(self):
        self.assertEqual(common_onset_relation(events([48,50]),events([60,58],2))['motion_transition_counts'],{'contrary':1})
        self.assertEqual(common_onset_relation(events([48,48]),events([60,62],2))['motion_transition_counts'],{'oblique':1})
        self.assertEqual(common_onset_relation(events([48,50]),events([60,62],2))['motion_transition_counts'],{'parallel_equal_interval':1})

    def test_harmonic_context_follows_matched_channel_handoff(self):
        a=events([48,52,55,60]);b=[dict(e,channel=7 if i<2 else 9) for i,e in enumerate(a)]
        source=a+events([55,59,62,67],channel=2)
        target=b+events([52,56,59,64],channel=3)
        result=query_section(a,b);ctx=motif_harmonic_context(source,target,result)
        self.assertEqual([w['target_carrier_channel'] for w in ctx['witnesses']],[7,7,9,9])
        self.assertEqual(ctx['changed_context_fraction'],1)

    def test_dense_chromatic_foil_preserves_core_but_has_low_purity(self):
        a=events([48,50,52,55,53,50]);b=[dict(e,pitch=p,channel=p-47) for e in a for p in range(48,72)]
        m=query_section(a,b)
        self.assertEqual(m['left_coverage'],1)
        self.assertAlmostEqual(m['right_coverage'],1/24)
        self.assertEqual(m['duplicate_provenance_fraction'],0)

    def test_excluded_carrier_has_no_harmonic_context(self):
        a=events([48,52,55,60]);b=events([48,52,55,60],channel=7,instrument=99)
        match=query_section(a,b)
        source=a+events([55,59,62,67],channel=2)
        filtered_target=events([52,56,59,64],channel=3)
        context=motif_harmonic_context(source,filtered_target,match)
        self.assertEqual(context['single_carrier_context_points'],0)
        self.assertIsNone(context['changed_context_fraction'])

    def test_distinct_time_translation_is_not_suppressed_as_nested(self):
        a=events([48]*8,ticks=list(range(0,96,12)))
        b=events([48]*15,ticks=list(range(0,90,6)))
        sections=[{'visit':0,'order':0,'pattern':0,'events':a},{'visit':1,'order':1,'pattern':1,'events':b}]
        hits=fragment_occurrences(sections,0,1)[0]['matches']
        self.assertTrue(any(h['target_start_tick']-h['source_start_tick']==6 for h in hits))

    def test_reused_stored_pattern_has_separate_played_visits(self):
        _,sequence,_=load_trusted_sources(Path(__file__).resolve().parents[3])
        xm={'channels':1,'speed':6,'bpm':125,'song_length':2,'order':[0,0],
            'patterns':[{'rows':4,'cells':[(0,0,49,1,0,0,0)]}],
            'instruments':[{'sample_map':[0]*96,'samples':[{'frames':100,'volume':40}]}]}
        located=traverse_with_locations(xm,sequence)
        self.assertEqual(located[:-1],sequence._sequence(xm))
        self.assertEqual(located[-1][0][:3],(0,0,0));self.assertEqual(located[-1][4][:3],(1,0,0))

if __name__=='__main__':unittest.main()
