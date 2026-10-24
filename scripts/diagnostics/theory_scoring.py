"""Versioned experimental static thematic scoring features; no learned model.

A falsifiable theory-led score, plus raw entropy, repetition, supported variation,
interval, scale-collection, and rhythm/phrase descriptors. Never a universal
binary judgment of catchiness. No seed or channel is required for primary scoring.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from itertools import islice
from pathlib import Path
import statistics
from .motif_events import (points,windows,similarity,shuffle_pitches,bitset,translate_bits)
from .structure_extraction import load_trusted_sources,extract_xm_events

SPEC_PATH=Path(__file__).with_name('theory_score_spec.json')
SPEC_BYTES=SPEC_PATH.read_bytes()
SPEC=json.loads(SPEC_BYTES)
METHOD=SPEC['method']

def entropy(values):
    counts=Counter(values);n=sum(counts.values())
    return -sum((c/n)*math.log2(c/n) for c in counts.values()) if n else 0.

def onset_sets(pts):
    grouped=defaultdict(set)
    for t,p in pts:grouped[t].add(p)
    return sorted((t,tuple(sorted(p))) for t,p in grouped.items())

def core_content(pts):
    groups=onset_sets(pts);pc=[p%12 for _,ps in groups for p in ps]
    h=entropy(pc)
    signatures=[tuple(sorted({p%12 for p in ps})) for _,ps in groups]
    change=sum(a!=b for a,b in zip(signatures,signatures[1:]))/max(1,len(signatures)-1)
    return {'pitch_class_entropy_bits':h,'effective_pitch_classes':2**h if pc else 0.,
            'onset_pitch_set_change_rate':change,
            'gate':min(1.,h/SPEC['core_pitch_entropy_saturation_bits'])*change,
            'entropy_preference':math.exp(-.5*((h-SPEC['entropy_preference_center_bits'])/SPEC['entropy_preference_sigma_bits'])**2) if pc else 0.}

def period_fit(events):
    """Near-periodic overlap, including 15/16/17-beat loops; no hard exact gate.

    Candidate periods are differences of observed onset positions from the first
    onset. Comparison conditions on overlap so leading/trailing silence cannot
    turn an exact loop into development. A partial observation is explicit.
    """
    pts=points(events)
    if not pts:return {'fit':0.,'period_ticks':None,'candidates':0,'scope':'empty'}
    start=min(t for t,p in pts);pts={(t-start,p) for t,p in pts}
    onsets=sorted({t for t,p in pts});extent=onsets[-1]+1
    maxlag=min(SPEC['period_scan_max_ticks'],(extent-1)//max(1,SPEC['period_min_copies']-1))
    candidates=[t for t in onsets if SPEC['period_min_ticks']<=t<=maxlag]
    bits=bitset(pts);best=(0.,None)
    for lag in candidates:
        overlap=(bits & (bits << (lag*128))).bit_count()
        eligible=sum(t>=lag for t,p in pts)
        fit=overlap/eligible if eligible else 0.
        if fit>best[0]:best=(fit,lag)
    return {'fit':best[0],'period_ticks':best[1],'candidates':len(candidates),
            'scope':'nominal point repetition; not a monotony or enjoyment verdict'}

def raw_descriptors(events):
    pts=points(events);groups=onset_sets(pts);pitches=[p%12 for _,ps in groups for p in ps]
    times=[t for t,ps in groups];gaps=[b-a for a,b in zip(times,times[1:]) if b>a]
    centroids=[statistics.mean(ps) for t,ps in groups]
    jumps=[b-a for a,b in zip(centroids,centroids[1:])]
    median_gap=statistics.median(gaps) if gaps else None
    major={0,2,4,5,7,9,11};minor={0,2,3,5,7,8,10}
    scale_fit=max((sum((p-root)%12 in scale for p in pitches)/len(pitches)
                   for root in range(12) for scale in [major,minor]),default=0.) if pitches else 0.
    return {'unique_pitch_classes':len(set(pitches)), 'pitch_class_entropy_bits':entropy(pitches),
            'modal_pitch_class_fraction':max(Counter(pitches).values(),default=0)/len(pitches) if pitches else None,
            'onset_gap_entropy_bits':entropy(gaps),
            'onset_set_centroid_interval_entropy_bits':entropy(jumps),
            'centroid_step_fraction':sum(0<abs(x)<=2 for x in jumps)/len(jumps) if jumps else None,
            'centroid_large_leap_fraction':sum(abs(x)>7 for x in jumps)/len(jumps) if jumps else None,
            'major_or_natural_minor_collection_fit':scale_fit,
            'long_gap_boundary_proxy_fraction':sum(g>2*median_gap for g in gaps)/len(gaps) if gaps else None,
            'beat_grid_onset_fraction':sum(t%24==0 for t in times)/len(times) if times else None,
            'nominal_unique_points':len(pts),'onset_count':len(groups),
            'interpretation':'Nominal mixture/selected-part descriptors; gap boundaries are not vocal prosody or sounding durations.'}

def _scale(events,total_ticks,width,period):
    groups=windows(events,total_ticks,width);n=len(groups);observed=similarity(groups)
    nulls=[similarity(windows(shuffle_pitches(events,SPEC['control_seed']+k),total_ticks,width)) for k in range(SPEC['controls'])]
    null_partner=[max((c['f1'][i][j] for c in nulls for j in range(n) if i!=j),default=0.) for i in range(n)]
    copies=Counter(tuple(sorted(g)) for g in groups)
    pairs=[]
    for j in range(n):
        for i in range(j):
            f=observed['f1'][i][j];mi=observed['support'][i][j]
            if not groups[i] or not groups[j] or mi<SPEC['min_core_points']:continue
            l,r=mi/len(groups[i]),mi/len(groups[j])
            if min(l,r)<SPEC['minimum_pair_coverage']:continue
            dt,dp=observed['shifts'][f'{i},{j}']
            core=groups[i]&{(t+dt,p+dp) for t,p in groups[j]}
            ts={t for t,p in core}
            if len(ts)<SPEC['min_core_onsets'] or max(ts)-min(ts)<SPEC['min_core_span_ticks']:continue
            floor=max(null_partner[i],null_partner[j])
            recurrence=max(0.,f-floor)/(1-floor) if floor<1 else 0.
            content=core_content(core)
            repeated=min(copies[tuple(sorted(groups[i]))],copies[tuple(sorted(groups[j]))])>=SPEC['variant_min_exact_occurrences']
            variant=0.
            if dt==0 and repeated:
                if f<1 and max(len(groups[i])-mi,len(groups[j])-mi)>=SPEC['minimum_variant_residual_points_one_side']:
                    variant=min(l,r)*min(1.,(1-f)/SPEC['edit_fraction_full_credit'])
                elif dp!=0:variant=SPEC['literal_transposition_variation_credit']
            pairs.append({'left':i,'right':j,'f1':f,'left_coverage':l,'right_coverage':r,
                          'matched':mi,'transform':[dt,dp],'recurrence_support':recurrence,
                          'core':content,'confirmed_variant_strength':variant})
    # Corroborated altered shape is a family attribute, not a bonus for one-off residuals.
    variation=[0.]*n
    for p in pairs:
        if p['recurrence_support']>0:
            for k in [p['left'],p['right']]:variation[k]=max(variation[k],p['confirmed_variant_strength']*p['recurrence_support'])
    period_discount=0.
    if period['period_ticks'] is not None and period['period_ticks']%width:
        period_discount=max(0.,(period['fit']-SPEC['period_variant_discount_start'])/(1-SPEC['period_variant_discount_start']))
    scores=[0.]*n;ablated=[0.]*n;development=[0.]*n;rec=[0.]*n;gates=[0.]*n
    for p in pairs:
        for k in [p['left'],p['right']]:
            v=variation[k]*(1-period_discount)
            value=p['core']['gate']*p['recurrence_support']*(SPEC['recurrence_only_ceiling']+(1-SPEC['recurrence_only_ceiling'])*v)
            development[k]=max(development[k],p['core']['gate']*p['recurrence_support']*v*p['core']['entropy_preference'])
            ablated[k]=max(ablated[k],value)
            scores[k]=max(scores[k],value*p['core']['entropy_preference'])
            rec[k]=max(rec[k],p['recurrence_support']);gates[k]=max(gates[k],p['core']['gate'])
    mean=lambda a:statistics.mean(a) if a else 0.
    pairs.sort(key=lambda p:-(p['core']['gate']*p['recurrence_support']))
    return {'width_ticks':width,'windows':n,'score':100*mean(scores),'score_without_entropy_preference':100*mean(ablated),
            'evolution_required_score':100*mean(development), 'saturated_recurrence_support':mean(rec),'supported_core_content':mean(gates),
            'confirmed_variant_support':mean(variation),'period_adjusted_variant_support':mean(variation)*(1-period_discount), 'phase_walk_discount':period_discount,
            'witness_pairs':pairs[:20]}

def score_events(events,total_ticks):
    # Canonicalize before any sampling or shuffled controls; metadata never defines identity.
    events=list(islice(events,65537))
    if len(events)>65536:raise ValueError('event count exceeds bounded analysis limit')
    if not isinstance(total_ticks,int) or isinstance(total_ticks,bool) or total_ticks<0:raise ValueError('total_ticks must be a nonnegative integer')
    for e in events:
        if any(not isinstance(e.get(k),int) or isinstance(e.get(k),bool) for k in ['tick','pitch']):raise ValueError('tick and pitch must be integers')
        if not 0<=e['tick']<total_ticks or not 0<=e['pitch']<=95:raise ValueError('event outside declared tick/pitch bounds')
    canonical=[{'tick':t,'pitch':p,'channel':0} for t,p in sorted(points(events))]
    for width in SPEC['windows_ticks']:windows(canonical,total_ticks,width)  # bound work before global bitsets
    period=period_fit(canonical)
    scales=[_scale(canonical,total_ticks,w,period) for w in SPEC['windows_ticks']]
    avg=lambda key:statistics.mean(s[key] for s in scales)
    return {'method':METHOD,'spec_sha256':hashlib.sha256(SPEC_BYTES).hexdigest(),
            'status':'experimental','structural_score':avg('score'),
            'score_without_entropy_preference':avg('score_without_entropy_preference'),
            'evolution_required_score':avg('evolution_required_score'),
            'evolution_required_method':'supported-thematic-development-v1',
            'evolution_required_formula':'100*core_content*recurrence_support*confirmed_variant_support*entropy_preference',
            'evolution_required_status':'exploratory follow-up after recurrence-ceiling failure; zero means no supported evolution, not bad music',
            'attributes':{k:avg(k) for k in ['saturated_recurrence_support','supported_core_content','confirmed_variant_support','period_adjusted_variant_support']},
            'periodicity':period,'descriptors':raw_descriptors(canonical),'scales':scales,
            'interpretation':'Theory-led thematic organization hypothesis, not calibrated pleasure or universal musical goodness.'}

def analyze_xm(path,root,pitched_instruments=None,melody_channels=None):
    parse,sequence,provenance=load_trusted_sources(root);data=Path(path).read_bytes();xm=parse(data)
    rows,_,_,_,seconds,reason,warnings,times,total=sequence._sequence(xm)
    _,_,eligibility=extract_xm_events(xm,sequence)
    if not eligibility['extraction_complete']:raise ValueError('incomplete traversal: score unavailable')
    allowed=set(pitched_instruments) if pitched_instruments is not None else None
    channels=set(melody_channels) if melody_channels is not None else None
    if allowed is not None and any(not isinstance(i,int) or not 1<=i<=len(xm['instruments']) for i in allowed):raise ValueError('instrument selection out of range')
    if channels is not None and any(not isinstance(i,int) or not 1<=i<=xm['channels'] for i in channels):raise ValueError('channel selection out of range')
    events=[{'tick':t,'pitch':note-1,'channel':ch,'instrument':ins} for t,row in zip(times,rows) for ch,note,ins,sa in row
            if (allowed is None or ins in allowed) and (channels is None or ch+1 in channels)]
    return {'file':Path(path).name,'title':xm['name'],'input_sha256':hashlib.sha256(data).hexdigest(),
            'source_provenance':provenance,'eligibility':eligibility,
            'selection':{'pitched_instruments':sorted(allowed) if allowed is not None else None,
                         'melody_channels':sorted(channels) if channels is not None else None,
                         'scope':'all nominal onsets' if allowed is None and channels is None else 'explicit caller selection'},
            'seconds':seconds,'total_ticks':total,'result':score_events(events,total)}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('xm',type=Path);p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--pitched-instruments');p.add_argument('--melody-channels');a=p.parse_args()
    ids=lambda x:None if x is None else [int(v) for v in x.split(',') if v]
    a.out.write_text(json.dumps(analyze_xm(a.xm,a.root,ids(a.pitched_instruments),ids(a.melody_channels)),indent=2))
if __name__=='__main__':main()
