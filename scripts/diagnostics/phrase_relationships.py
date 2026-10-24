"""Section-to-section nominal motif correspondence and cross-part attributes.

Channels and instruments label witnesses; neither defines motif identity.
This module never searches short-lag copies. Its primary query pools target
channels, and requires source and target to be in different section visits.
"""
from __future__ import annotations
import ast
import argparse
from collections import Counter,defaultdict
import hashlib
import inspect
import json
from pathlib import Path
import statistics
from .structure_extraction import load_trusted_sources,extract_xm_events
from .motif_events import align_points

METHOD='section-motif-correspondence-v1'

def traverse_with_locations(xm,sequence):
    """Instrument the reviewed traverser without changing its original outputs."""
    tree=ast.parse(inspect.getsource(sequence._sequence));fn=tree.body[0]
    fn.name='_located_sequence'
    fn.body.insert(1,ast.Assign(targets=[ast.Name(id='locations',ctx=ast.Store())],value=ast.List(elts=[],ctx=ast.Load())))
    class Trace(ast.NodeTransformer):
        def visit_Expr(self,node):
            if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and isinstance(node.value.func.value,ast.Name) and node.value.func.value.id=='rows' and node.value.func.attr=='append':
                extra=ast.parse('locations.append((order_index,pattern_index,row,speed))').body[0]
                return [extra,node]
            return self.generic_visit(node)
        def visit_Return(self,node):
            if isinstance(node.value,ast.Tuple):node.value.elts.append(ast.Name(id='locations',ctx=ast.Load()))
            return node
    tree=Trace().visit(tree);ast.fix_missing_locations(tree);ns=dict(vars(sequence));exec(compile(tree,'<trusted-located-sequence>','exec'),ns)
    result=ns['_located_sequence'](xm)
    return result

def sections_from_xm(xm,sequence):
    seq=traverse_with_locations(xm,sequence)
    rows,_,_,_,seconds,reason,warnings,ticks,total,locations=seq
    cells={(pi,r,c):(n,ins,vol,eff,param) for pi,p in enumerate(xm['patterns']) for r,c,n,ins,vol,eff,param in p['cells']}
    sections=[];previous=None
    for index,(row,t,loc) in enumerate(zip(rows,ticks,locations)):
        order,pattern,source_row,speed=loc
        if previous is None or order!=previous[0] or pattern!=previous[1] or source_row!=previous[2]+1:
            sections.append({'visit':len(sections),'order':order,'pattern':pattern,'start_tick':t,'events':[]})
        sec=sections[-1]
        for ch,note,ins,sample in row:
            cell=cells.get((pattern,source_row,ch),(0,0,0,0,0))
            sec['events'].append({'tick':t-sec['start_tick'],'pitch':note-1,'channel':ch+1,'instrument':ins,'sample':sample,'row':source_row,
                                  'slide_target':cell[3] in (3,5) or cell[2]>>4==15})
        sec['end_tick']=(ticks[index+1] if index+1<len(ticks) else total)
        sec['duration_ticks']=sec['end_tick']-sec['start_tick']
        previous=loc
    return sections,{'total_ticks':total,'seconds':seconds,'stop_reason':reason,'warnings':warnings}

def query_section(seed_events,target_events):
    """One simultaneous-pitch-invariant point-set query; no channel assignment.

    No time-offset search: motif phase is relative to its section/bar start.
    Target provenance is recovered after the channel-free pitch/time match.
    """
    a={(e['tick'],e['pitch']) for e in seed_events};b={(e['tick'],e['pitch']) for e in target_events}
    result=align_points(a,b,offsets=(0,))
    shift=result['pitch_shift_right_to_left']
    source=defaultdict(list);target=defaultdict(list)
    for e in seed_events:source[(e['tick'],e['pitch'])].append(e)
    for e in target_events:target[(e['tick'],e['pitch']+shift)].append(e)
    witnesses=[]
    for t,p in result['matched_left_points']:
        witnesses.append({'tick':t,'source_pitch':p,'target_pitch':p-shift,
                          'source_channels':sorted({e['channel'] for e in source[(t,p)]}),
                          'target_channels':sorted({e['channel'] for e in target[(t,p)]}),
                          'source_instruments':sorted({e['instrument'] for e in source[(t,p)]}),
                          'target_instruments':sorted({e['instrument'] for e in target[(t,p)]}),
                          'slide_target_present':any(e.get('slide_target',False) for e in source[(t,p)]+target[(t,p)])})
    result['witnesses']=witnesses
    result['target_channels_at_matched_points']=sorted({c for w in witnesses for c in w['target_channels']})
    result['duplicate_provenance_fraction']=sum(len(w['target_channels'])>1 for w in witnesses)/len(witnesses) if witnesses else 0.
    # These flags describe actual matched events, not unrelated section sounds.
    result['channel_handoff_possible']=any(set(w['source_channels'])!=set(w['target_channels']) for w in witnesses)
    result['instrument_handoff_possible']=any(set(w['source_instruments'])!=set(w['target_instruments']) for w in witnesses)
    result['role']='nominal correspondence; pooled matches do not establish a unique perceptual voice'
    return result

def motif_harmonic_context(source_section_events,target_section_events,match):
    """Context follows each matched carrier, including a channel handoff.

    Newly written pitches at a shared onset only, not sustained sonority.
    Multiple possible carrier lanes are retained as unavailable context.
    """
    src=defaultdict(list);dst=defaultdict(list)
    for e in source_section_events:src[e['tick']].append(e)
    for e in target_section_events:dst[e['tick']].append(e)
    records=[];changes=0;usable=0
    for w in match['witnesses']:
        if len(w['source_channels'])!=1 or len(w['target_channels'])!=1:continue
        if not any(e['channel'] in w['source_channels'] and e['pitch']==w['source_pitch'] for e in src[w['tick']]):continue
        if not any(e['channel'] in w['target_channels'] and e['pitch']==w['target_pitch'] for e in dst[w['tick']]):continue
        a=[e for e in src[w['tick']] if e['channel'] not in w['source_channels']]
        b=[e for e in dst[w['tick']] if e['channel'] not in w['target_channels']]
        av=Counter((e['pitch']-w['source_pitch'])%12 for e in a)
        bv=Counter((e['pitch']-w['target_pitch'])%12 for e in b)
        rec={'tick':w['tick'],'source_carrier_channel':w['source_channels'][0],
             'target_carrier_channel':w['target_channels'][0],
             'source_intervals_mod12':dict(sorted(av.items())),
             'target_intervals_mod12':dict(sorted(bv.items())),
             'source_other_note_attacks':len(a),'target_other_note_attacks':len(b)}
        if a and b:
            usable+=1;difference=set(av)!=set(bv);changes+=difference
            rec['pitch_class_context_changed']=difference
        records.append(rec)
    return {'matched_points':len(match['witnesses']),'single_carrier_context_points':len(records),
            'both_sides_have_other_attacks':usable,
            'changed_context_fraction':changes/usable if usable else None,
            'witnesses':records,
            'interpretation':'Onset-conditioned context follows matched channel labels; excludes sustained notes and does not certify reharmonization.'}

def phrase_occurrences(sections,source_visit,source_channel,span_ticks=None,context_sections=None):
    seedsec=sections[source_visit]
    context_sections=context_sections or sections
    span=span_ticks or seedsec['duration_ticks']
    seed=[e for e in seedsec['events'] if e['channel']==source_channel and e['tick']<span]
    if len({(e['tick'],e['pitch']) for e in seed})<4:raise ValueError('seed needs >=4 written pitch commands')
    records=[]
    for sec in sections:
        if sec['visit']==source_visit:continue
        # Compare played occurrences, not unused stored patterns. Ignore no suffix.
        target=[e for e in sec['events'] if e['tick']<span]
        pooled=query_section(seed,target)
        source_context=context_sections[source_visit]['events']
        target_context=[e for e in context_sections[sec['visit']]['events'] if e['tick']<span]
        pooled['harmonic_context']=motif_harmonic_context(source_context,target_context,pooled)
        lanes=[]
        for ch in sorted({e['channel'] for e in target}):
            es=[e for e in target if e['channel']==ch];match=query_section(seed,es)
            match['harmonic_context']=motif_harmonic_context(source_context,target_context,match)
            lanes.append({'channel':ch,**match})
        lanes.sort(key=lambda x:(-x['left_coverage'],-x['f1'],abs(x['pitch_shift_right_to_left']),x['channel']))
        records.append({'visit':sec['visit'],'order':sec['order'],'pattern':sec['pattern'],
                        'same_stored_pattern_as_seed':sec['pattern']==seedsec['pattern'],
                        'pooled':pooled,'best_lane':lanes[0] if lanes else None,
                        'lane_candidates':lanes[:3]})
    return {'source':{'visit':source_visit,'order':seedsec['order'],'pattern':seedsec['pattern'],
                      'channel':source_channel,'span_ticks':span,'events':seed},'occurrences':records}

def fragment_occurrences(sections,source_visit,source_channel,min_notes=4,max_notes=8):
    """Contiguous seed cells found anywhere in a different played section.

    Constant pitch/time translation with exact relative rhythm, allowing extra
    target notes. Four-note matches are fragment evidence, not theme identity.
    Channels only label the recovered witness set; search uses pooled points.
    """
    seed=sorted((e for e in sections[source_visit]['events'] if e['channel']==source_channel),key=lambda e:(e['tick'],e['pitch']))
    findings=[]
    for sec in sections:
        if sec['visit']==source_visit:continue
        lookup=defaultdict(list)
        for e in sec['events']:lookup[(e['tick'],e['pitch'])].append(e)
        anchors=sorted(lookup)
        hits=[]
        for length in range(max_notes,min_notes-1,-1):
            for start in range(len(seed)-length+1):
                template=seed[start:start+length];t0,p0=template[0]['tick'],template[0]['pitch']
                if template[-1]['tick']-t0<24:continue
                for tt,pp in anchors:
                    dp=pp-p0
                    if abs(dp)>12:continue
                    keys=[(e['tick']-t0+tt,e['pitch']+dp) for e in template]
                    if not all(k in lookup for k in keys):continue
                    # Prefer maximal seed/target spans, suppress nested windows.
                    if any(h['source_start_tick']<=t0 and h['source_end_tick']>=template[-1]['tick'] and h['target_start_tick']<=tt and h['target_end_tick']>=keys[-1][0] and h['pitch_shift_target_minus_source']==dp and h['target_start_tick']-h['source_start_tick']==tt-t0 for h in hits):continue
                    witnesses=[]
                    for src,key in zip(template,keys):
                        dst=lookup[key]
                        witnesses.append({'source_tick':src['tick'],'source_row':src['row'],'source_pitch':src['pitch'],
                            'source_instrument':src['instrument'],'target_tick':key[0],'target_pitch':key[1],
                            'target_rows':sorted({e['row'] for e in dst}),
                            'target_channels':sorted({e['channel'] for e in dst}),
                            'target_instruments':sorted({e['instrument'] for e in dst}),
                            'slide_target_present':src.get('slide_target',False) or any(e.get('slide_target',False) for e in dst)})
                    common_lanes=set.intersection(*(set(w['target_channels']) for w in witnesses))
                    realizations=[]
                    for lane in sorted(common_lanes):
                        target_instruments=[sorted({e['instrument'] for e in lookup[key] if e['channel']==lane}) for key in keys]
                        realizations.append({'channel':lane,'channel_changed':lane!=source_channel,
                            'instrument_ids_changed':any(set(ii)!={src['instrument']} for src,ii in zip(template,target_instruments)),
                            'target_instruments_by_note':target_instruments})
                    hits.append({'notes':length,'source_start_tick':t0,'source_end_tick':template[-1]['tick'],
                                 'target_start_tick':tt,'target_end_tick':keys[-1][0],
                                 'pitch_shift_target_minus_source':dp,'single_lane_realizations':sorted(common_lanes),
                                 'single_lane_realizations_detail':realizations,
                                 'possible_instrument_change':any(r['instrument_ids_changed'] for r in realizations),
                                 'possible_channel_change':any(set(w['target_channels'])!={source_channel} for w in witnesses),
                                 'witnesses':witnesses,
                                 'interpretation':'Exact local fragment; common scale fragments and composite paths require validation.'})
        hits.sort(key=lambda h:(-h['notes'],h['source_start_tick'],h['target_start_tick'],abs(h['pitch_shift_target_minus_source'])))
        findings.append({'visit':sec['visit'],'order':sec['order'],'pattern':sec['pattern'],'matches':hits[:30],
                         'total_bounded_maximal_matches':len(hits),'search_max_notes':max_notes})
    return findings

def _motion(a,b):
    da,db=a,b
    if da==0 and db==0:return 'both_static'
    if da==0 or db==0:return 'oblique'
    if da*db<0:return 'contrary'
    return 'parallel_equal_interval' if da==db else 'similar_unequal_interval'

def common_onset_relation(left,right):
    """Written common onsets only; no held-note or acoustic consonance claim."""
    a=defaultdict(set);b=defaultdict(set)
    for e in left:a[e['tick']].add(e['pitch'])
    for e in right:b[e['tick']].add(e['pitch'])
    common=sorted(set(a)&set(b));singleton=[t for t in common if len(a[t])==len(b[t])==1]
    pp=[(t,next(iter(a[t])),next(iter(b[t]))) for t in singleton]
    intervals=Counter(y-x for t,x,y in pp);pc=Counter((y-x)%12 for t,x,y in pp)
    motion=Counter(_motion(x2-x1,y2-y1) for (t1,x1,y1),(t2,x2,y2) in zip(pp,pp[1:]))
    n=len(pp)
    return {'left_onsets':len(a),'right_onsets':len(b),'common_onsets':len(common),
            'usable_singleton_onsets':n,'left_common_onset_coverage':len(common)/len(a) if a else 0.,
            'right_common_onset_coverage':len(common)/len(b) if b else 0.,
            'interval_histogram_semitones':dict(sorted(intervals.items())),
            'interval_histogram_mod12':dict(sorted(pc.items())),
            'third_sixth_fraction':sum(c for p,c in pc.items() if p in (3,4,8,9))/n if n else None,
            'unison_octave_fraction':pc[0]/n if n else None,
            'motion_transition_counts':dict(motion),'witnesses':pp,
            'interpretation':'interval/motion description, not harmonic quality or key validation'}

def harmonic_sections(sections,foreground_channel):
    results=[]
    for sec in sections:
        lead=[e for e in sec['events'] if e['channel']==foreground_channel]
        if len(lead)<4:continue
        for ch in sorted({e['channel'] for e in sec['events']} - {foreground_channel}):
            other=[e for e in sec['events'] if e['channel']==ch]
            rel=common_onset_relation(lead,other)
            if rel['usable_singleton_onsets']>=4:
                results.append({'visit':sec['visit'],'order':sec['order'],'pattern':sec['pattern'],
                                'reference_channel':foreground_channel,'other_channel':ch,**rel})
    return results

def analyze_phrases(path,root,source_visit,source_channel,pitched_instruments=None):
    parse,seq,provenance=load_trusted_sources(root);data=Path(path).read_bytes();xm=parse(data)
    sections,timing=sections_from_xm(xm,seq);_,_,eligibility=extract_xm_events(xm,seq)
    if not 0<=source_visit<len(sections):raise ValueError('source visit out of range')
    if not 1<=source_channel<=xm['channels']:raise ValueError('source channel out of range')
    if not eligibility['extraction_complete']:raise ValueError('incomplete traversal')
    allowed=set(pitched_instruments) if pitched_instruments is not None else None
    context_sections=[dict(sec,events=[e for e in sec['events'] if allowed is None or e['instrument'] in allowed]) for sec in sections]
    excluded=sum(len(a['events'])-len(b['events']) for a,b in zip(sections,context_sections))
    return {'method':METHOD,'file':Path(path).name,'title':xm['name'],'sha256':hashlib.sha256(data).hexdigest(),
            'provenance':provenance,'timing':timing,'eligibility':eligibility,
            'foreground_hypothesis':{'channel':source_channel,'status':'analyst hypothesis; names and nominal activity reviewed, not automatic salience inference'},
            'instruments':{i+1:ins['name'] for i,ins in enumerate(xm['instruments'])},
            'harmonic_eligibility':{'pitched_instruments_reviewed':sorted(allowed) if allowed is not None else None,
                 'excluded_nominal_events':excluded,'scope':'conditional on reviewed instrument mask; not automatic percussion classification or sounding-pitch calibration'},
            'sections':sections,'whole_phrase':phrase_occurrences(sections,source_visit,source_channel,context_sections=context_sections),
            'opening_cell':phrase_occurrences(sections,source_visit,source_channel,96,context_sections),
            'cross_part_intervals':harmonic_sections(context_sections,source_channel),
            'fragments':fragment_occurrences(sections,source_visit,source_channel)}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('xm',type=Path)
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--source-visit',type=int,required=True)
    ap.add_argument('--source-channel',type=int,required=True)
    ap.add_argument('--pitched-instruments',help='Comma-separated reviewed instrument IDs in decimal; omit for unfiltered nominal context.')
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    mask=None if args.pitched_instruments is None else [int(x) for x in args.pitched_instruments.split(',') if x.strip()]
    if mask is not None and any(not 1<=x<=128 for x in mask):ap.error('instrument IDs must be 1..128')
    result=analyze_phrases(args.xm,args.root,args.source_visit,args.source_channel,mask)
    args.out.write_text(json.dumps(result,indent=2))

if __name__=='__main__':main()
