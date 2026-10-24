"""End-to-end public feature API on generated nominal XM, without paid inference."""
from pathlib import Path
import struct
import tempfile
import unittest
from scripts.diagnostics.scoring_features import score_xm,SCHEMA

ROOT=Path(__file__).resolve().parents[3]
def synthetic_xm():
    h=bytearray(336);h[:17]=b'Extended Module: ';h[17:37]=b'Synthetic feature QA';h[37]=26
    struct.pack_into('<H',h,58,0x104);struct.pack_into('<I',h,60,276)
    struct.pack_into('<8H',h,64,4,0,2,2,1,1,6,125);h[80:84]=bytes([0,1,0,1])
    out=bytearray(h)
    for shift in [0,2]:
        cells=bytearray()
        for r in range(16):
            for ch in range(2):
                note=49+[0,4,7,2,5,9,4,7][r//2]+shift+ch*4 if r%2==0 else 0
                cells.extend(bytes([note,1 if note else 0,0,0,0]))
        out.extend(struct.pack('<IBHH',9,0,16,len(cells)));out.extend(cells)
    ins=bytearray(263);struct.pack_into('<I',ins,0,263);struct.pack_into('<H',ins,27,1);struct.pack_into('<I',ins,29,40)
    sh=bytearray(40);struct.pack_into('<I',sh,0,32);sh[12]=40;sh[15]=128
    return bytes(out+ins+sh+bytes(32))

class ScoringFeatureApiTests(unittest.TestCase):
    def test_list_and_iterator_selections_reach_every_component(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic.xm';p.write_bytes(synthetic_xm())
            a=score_xm(p,ROOT,pitched_instruments=[1],melody_channels=[1],source_visit=0,source_channel=1)
            b=score_xm(p,ROOT,pitched_instruments=iter([1]),melody_channels=iter([1]),source_visit=0,source_channel=1)
        self.assertEqual(a,b);self.assertEqual(a['schema'],SCHEMA)
        self.assertTrue(a['harmonic_attributes']['relations']);self.assertIsNotNone(a['motif_query'])
    def test_no_seed_still_emits_numeric_separate_features(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic.xm';p.write_bytes(synthetic_xm());r=score_xm(p,ROOT)
        self.assertIsNone(r['motif_query']);self.assertIsInstance(r['features']['supported_thematic_development']['value'],float)
        self.assertIn('falsified',r['features']['thematic_organization_v1']['status'])
    def test_invalid_selection_is_not_a_zero_score(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic.xm';p.write_bytes(synthetic_xm())
            with self.assertRaises(ValueError):score_xm(p,ROOT,melody_channels=[99])
            with self.assertRaises(ValueError):score_xm(p,ROOT,pitched_instruments=[99])
            with self.assertRaises(ValueError):score_xm(p,ROOT,source_visit=0)
if __name__=='__main__':unittest.main()
