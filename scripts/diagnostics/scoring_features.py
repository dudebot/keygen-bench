"""Reusable research feature API: static structure, motif and harmonic attributes.

No paid services, learned models, network, production-evaluator changes or
aggregate leaderboard formula. A zero development value is absence of supported
variation under this specification, not a verdict that a tune sounds bad.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .theory_scoring import analyze_xm
from .phrase_relationships import analyze_phrases,sections_from_xm,harmonic_sections
from .structure_extraction import load_trusted_sources

SCHEMA='keygen-static-features-v1'

def score_xm(path,root,*,pitched_instruments=None,melody_channels=None,source_visit=None,source_channel=None):
    pitched_instruments=None if pitched_instruments is None else tuple(pitched_instruments)
    melody_channels=None if melody_channels is None else tuple(melody_channels)
    if (source_visit is None)!=(source_channel is None):raise ValueError('source_visit and source_channel must be supplied together')
    theory=analyze_xm(path,root,pitched_instruments,melody_channels)
    r=theory['result']
    parse,sequence,_=load_trusted_sources(root);xm=parse(Path(path).read_bytes())
    sections,_=sections_from_xm(xm,sequence)
    allowed=set(pitched_instruments) if pitched_instruments is not None else None
    filtered=[dict(s,events=[e for e in s['events'] if allowed is None or e['instrument'] in allowed]) for s in sections]
    # All unordered channel pairs, no manual mainvoice needed for these descriptors.
    pairwise=[]
    for channel in sorted({e['channel'] for s in filtered for e in s['events']}):
        pairwise.extend(r for r in harmonic_sections(filtered,channel) if r['other_channel']>channel)
    features={'supported_thematic_development':{'value':r['evolution_required_score'],'range':[0,100],
                    'status':'exploratory; repeated variant evidence required; not an enjoyment rating'},
              'thematic_organization_v1':{'value':r['structural_score'],'range':[0,100],
                    'status':'retained falsified candidate: can overreward exact polyphonic loops'},
              **{k:{'value':v,'range':[0,1],'status':'experimental descriptor'} for k,v in r['attributes'].items()},
              'periodic_overlap':{'value':r['periodicity']['fit'],'range':[0,1],'status':'descriptor; repetition is not universally bad'},
              'pitch_entropy':{'value':r['descriptors']['pitch_class_entropy_bits'],'units':'bits over fixed12pitchclasses'},
              'rhythmic_gap_entropy':{'value':r['descriptors']['onset_gap_entropy_bits'],'units':'bits'},
              'long_gap_boundary_proxy':{'value':r['descriptors']['long_gap_boundary_proxy_fraction'],
                    'status':'onset-gap phrase proxy, not validated vocal prosody'}}
    motif=analyze_phrases(path,root,source_visit,source_channel,pitched_instruments) if source_visit is not None else None
    return {'schema':SCHEMA,'features':features,'theory':theory,
            'harmonic_attributes':{'status':'conditional reviewed pitched mask' if allowed is not None else 'unfiltered nominal intervals; percussion semantics unknown',
                'pitched_instruments':sorted(allowed) if allowed is not None else None,'relations':pairwise},
            'motif_query':motif,
            'motif_query_status':'available' if motif is not None else 'not requested: supply source visit/channel for occurrence witnesses',
            'aggregation':'No overall benchmark total or enjoyment verdict is defined.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('xm',type=Path);p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--pitched-instruments');p.add_argument('--melody-channels');p.add_argument('--source-visit',type=int);p.add_argument('--source-channel',type=int)
    a=p.parse_args();ids=lambda x:None if x is None else [int(v) for v in x.split(',') if v]
    a.out.write_text(json.dumps(score_xm(a.xm,a.root,pitched_instruments=ids(a.pitched_instruments),melody_channels=ids(a.melody_channels),source_visit=a.source_visit,source_channel=a.source_channel),indent=2))
if __name__=='__main__':main()
