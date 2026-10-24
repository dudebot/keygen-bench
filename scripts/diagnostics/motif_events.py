"""Experimental channel-free nominal onset/pitch recurrence, not a quality score.

A deliberately small matcher: unique point sets; one constant time/pitch
translation; bidirectional coverage; matched witnesses. No voice reconstruction,
no chroma/register collapse, no learned weights, and no enjoyment inference.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
from .structure_extraction import load_trusted_sources, extract_xm_events

METHOD = 'event-translation-recurrence-experimental-v1'
TRANSPOSES = tuple(range(-12, 13))
OFFSETS = tuple(range(-18, 19, 6))
WIDTHS = (96, 192)  # conventional 4/8 beat passages, 24 tracker ticks per beat
PAD = 24
STRIDE = 128
MAX_WINDOWS = 256

def points(events):
    """Collapse exact simultaneous unison doubling, retaining absolute register."""
    return {(int(e['tick']), int(e['pitch'])) for e in events}

def bitset(pts):
    result = 0
    for t, p in pts:
        if t < 0 or not 0 <= p <= 95:
            raise ValueError('expected nonnegative tick and nominal XM pitch 0..95')
        result |= 1 << ((t + PAD) * STRIDE + p + 16)
    return result

def translate_bits(bits, dt, dp):
    shift = dt * STRIDE + dp
    return bits << shift if shift >= 0 else bits >> -shift

def align_points(left, right, offsets=OFFSETS, transposes=TRANSPOSES):
    """Align right to left. A bijective translation gives exact 1:1 matching.

    Return source recall and target purity separately: inserting unrelated
    events must preserve the matched core but cannot preserve purity.
    """
    a, b = set(left), set(right)
    ab, bb = bitset(a), bitset(b)
    # Prefer zero offset and zero pitch shift when matched support ties.
    transforms = sorted(((dt, dp) for dt in offsets for dp in transposes),
                        key=lambda x: (abs(x[0]) + abs(x[1]), abs(x[0]), x))
    best = (-1, 0, 0)
    for dt, dp in transforms:
        n = (ab & translate_bits(bb, dt, dp)).bit_count()
        if n > best[0]:
            best = (n, dt, dp)
    n, dt, dp = best
    witness = sorted(a & {(t + dt, p + dp) for t, p in b})
    assert len(witness) == n
    return {'matched': n, 'left_count': len(a), 'right_count': len(b),
            'left_coverage': n / len(a) if a else 0.,
            'right_coverage': n / len(b) if b else 0.,
            'f1': 2 * n / (len(a) + len(b)) if a or b else 0.,
            'time_shift_right_to_left': dt, 'pitch_shift_right_to_left': dp,
            'matched_left_points': witness}

def windows(events, total_ticks, width):
    # Last onset defines support. Trailing silence alone creates no new passage.
    extent = max((e['tick'] for e in events), default=-1) + 1
    count = math.ceil(extent / width)
    if count > MAX_WINDOWS:
        raise ValueError('too many windows; refusing silent truncation')
    groups = [set() for _ in range(count)]
    for e in events:
        idx = e['tick'] // width
        groups[idx].add((e['tick'] % width, e['pitch']))
    return groups

def similarity(groups):
    """All-window same transform search; no first-note anchor or channel field."""
    encoded = [bitset(g) for g in groups]
    sizes = [len(g) for g in groups]
    n = len(groups)
    f1 = [[0.] * n for _ in range(n)]
    support = [[0] * n for _ in range(n)]
    shifts = {}
    transforms = sorted(((dt, dp) for dt in OFFSETS for dp in TRANSPOSES),
                        key=lambda x: (abs(x[0]) + abs(x[1]), abs(x[0]), x))
    for j, b in enumerate(encoded):
        variants = [(translate_bits(b, dt, dp), dt, dp) for dt, dp in transforms]
        if sizes[j]: f1[j][j], support[j][j] = 1., sizes[j]
        for i in range(j):
            best = (-1, 0, 0)
            for shifted, dt, dp in variants:
                match = (encoded[i] & shifted).bit_count()
                if match > best[0]: best = (match, dt, dp)
            match, dt, dp = best
            denom = sizes[i] + sizes[j]
            f1[i][j] = f1[j][i] = 2 * match / denom if denom else 0.
            support[i][j] = support[j][i] = match
            shifts[f'{i},{j}'] = [dt, dp]
    return {'f1': f1, 'support': support, 'sizes': sizes, 'shifts': shifts}

def shuffle_pitches(events, seed):
    """Channel-free control: permute whole simultaneous pitch sets.

    Strata preserve onset cardinality and tick modulo 24. Each onset retains
    its event count; chord geometry and global pitch marginals are preserved.
    Canonical point-set sorting makes seed results invariant to channels, event
    order, and simultaneous unison duplicates. Degenerate strata remain unchanged.
    """
    onsets = defaultdict(set)
    for t, p in sorted(points(events)): onsets[t].add(p)
    strata = defaultdict(list)
    for t in sorted(onsets): strata[(len(onsets[t]), t % 24)].append(t)
    rng = random.Random(seed)
    out = []
    for key, times in sorted(strata.items()):
        chords = [tuple(sorted(onsets[t])) for t in times]
        rng.shuffle(chords)
        for t, chord in zip(times, chords):
            out.extend({'tick': t, 'pitch': p, 'channel': 0} for p in chord)
    return sorted(out, key=lambda e: (e['tick'], e['pitch']))

def describe_recurrence(events, total_ticks, controls=8):
    scales = []
    for width in WIDTHS:
        groups = windows(events, total_ticks, width)
        observed = similarity(groups)
        nulls = [similarity(windows(shuffle_pitches(events, 20261023 + k), total_ticks, width))
                 for k in range(controls)]
        n = len(groups)
        # Effect size reference, NOT a calibrated p-value: all pair searches rerun.
        excess = [[0.] * n for _ in range(n)]
        pairs = []
        eligible = set()
        for j in range(n):
            for i in range(j):
                noise = max((x['f1'][i][j] for x in nulls), default=0.)
                gap = observed['f1'][i][j] - noise
                excess[i][j] = excess[j][i] = gap
                dt, dp = observed['shifts'][f'{i},{j}']
                witness = groups[i] & {(t+dt,p+dp) for t,p in groups[j]}
                onset_times = {t for t,p in witness}
                span = max(onset_times)-min(onset_times) if onset_times else 0
                if observed['support'][i][j] >= 6 and len(onset_times) >= 4 and span >= 24:
                    eligible.add((i,j))
                    pairs.append({'left_window': i, 'right_window': j,
                                  'f1': observed['f1'][i][j], 'control_max': noise,
                                  'excess': gap, 'matched': observed['support'][i][j], 'matched_span_ticks': span,
                                  'left_coverage': observed['support'][i][j]/len(groups[i]),
                                  'right_coverage': observed['support'][i][j]/len(groups[j]),
                                  'transform': observed['shifts'][f'{i},{j}']})
        pairs.sort(key=lambda x: (-x['excess'], -x['matched'], x['left_window'], x['right_window']))
        best = [max((excess[i][j] for j in range(n) if (min(i,j),max(i,j)) in eligible), default=0.) for i in range(n)]
        scales.append({'width_ticks': width, 'beats': width / 24,
                       'windows': n, 'f1': observed['f1'], 'excess_over_control_max': excess,
                       'positive_best_match_fraction': sum(x > .05 for x in best) / n if n else 0.,
                       'mean_best_excess': statistics.mean(best) if best else 0.,
                       'top_pairs': pairs[:20],
                       'control_count': controls, 'minimum_match_points': 6, 'minimum_matched_onsets': 4, 'minimum_matched_span_ticks':24})
    return {'method': METHOD, 'scales': scales,
            'interpretation': 'Set recurrence witnesses; not voice identity, development, intention, or enjoyment.',
            'limits': ['Fixed 4/8-beat grid, exact onset matching, bounded translation only.',
                       'Window edges can fragment motifs; long-range order is not reduced to a scalar.',
                       'Dense backing can obscure a melody. A point match does not prove a coherent voice.',
                       'Control maximum is descriptive; no calibrated significance or multiple-search correction.',
                       'Events inherit source nominal timing and audibility limitations.']}

def lane_relations(events):
    """Provisional within-channel delayed-copy and synchronous harmony evidence.

    Channels are only witness labels, not inputs to channel-free recurrence.
    A canon and a sheet-coded delay may be observationally indistinguishable.
    """
    lanes = defaultdict(set)
    for e in events: lanes[e['channel']].add((e['tick'], e['pitch']))
    reports = []
    for source, a in sorted(lanes.items()):
        if len(a) < 6: continue
        for target, b in sorted(lanes.items()):
            if source == target or len(b) < 6: continue
            best = (0., 0, 0)
            for lag in range(1, 25):
                match = len(a & {(t-lag, p) for t, p in b})
                f = 2 * match / (len(a)+len(b))
                if f > best[0]: best = (f, lag, match)
            if best[0] >= .7:
                reports.append({'source_channel': source+1, 'target_channel': target+1,
                                'kind': ('delayed_unison_copy_candidate' if len({p for t,p in a}) >= 3 and len({p for t,p in b}) >= 3 else 'rhythmic_copy_candidate'), 'lag_ticks': best[1],
                                'matched': best[2], 'f1': best[0],
                                'ambiguity': 'Echo, canon, or imitative response requires additional evidence.'})
            # Constant simultaneous thirds, sixths, octave or other parallel shift.
            best_h = (0., 0, 0)
            for shift in [-12,-9,-8,-7,-5,-4,-3,3,4,5,7,8,9,12]:
                matched = len(a & {(t,p-shift) for t,p in b})
                f = 2*matched/(len(a)+len(b))
                if f > best_h[0]:best_h=(f,shift,matched)
            if best_h[0] >= .7:
                reports.append({'source_channel': source+1,'target_channel':target+1,
                                'kind':'parallel_harmony_candidate','semitones_target_minus_source':best_h[1],
                                'matched':best_h[2],'f1':best_h[0],
                                'ambiguity':'Parallel interval evidence; not a harmonic correctness judgment.'})
    return reports

def delayed_copy_sensitivity(events, relations):
    """Hypothetical removal, never a claim about echo intent.

    Remove only target events witnessed at a high-coverage short delay. Keep
    unmatched material. Ambiguous directed cycles are not removed.
    """
    strong = [r for r in relations if r['kind'] == 'delayed_unison_copy_candidate' and r['f1'] >= .9]
    pairs = {(r['source_channel'], r['target_channel']) for r in strong}
    graph = defaultdict(set)
    for a,b in pairs: graph[a].add(b)
    def reachable(start, goal):
        pending, seen = [start], set()
        while pending:
            node = pending.pop()
            if node == goal: return True
            if node not in seen:
                seen.add(node); pending.extend(graph[node])
        return False
    lanes = defaultdict(set)
    for e in events: lanes[e['channel']+1].add((e['tick'],e['pitch']))
    removed = set()
    for r in strong:
        a,b = r['source_channel'],r['target_channel']
        if reachable(b,a): continue  # retain every edge within a directed cycle
        lag = r['lag_ticks']
        for t,p in lanes[b]:
            if (t-lag,p) in lanes[a]: removed.add((b-1,t,p))
    kept = [e for e in events if (e['channel'],e['tick'],e['pitch']) not in removed]
    return kept, len(removed)

def carrier_candidates(events, xm):
    """Evidence table only. Default sample volume is not realized loudness."""
    by = defaultdict(list)
    for e in events: by[e['channel']].append(e)
    result=[]
    for ch, es in sorted(by.items()):
        ps=[x['pitch'] for x in es]; insts=Counter(x.get('instrument',0) for x in es)
        names=[xm['instruments'][i-1]['name'] for i in insts if i>0]
        result.append({'channel':ch+1,'events':len(es),'distinct_pitches':len(set(ps)),
                       'median_tracker_pitch':statistics.median(ps),'pitch_span':max(ps)-min(ps),
                       'instrument_names':names,
                       'role':'candidate only; lead/bass/arpeggio/percussion roles not certified'})
    return result

def analyze_file(path, root, controls=8):
    parse, sequence, provenance = load_trusted_sources(root)
    data=Path(path).read_bytes();xm=parse(data)
    rows,_,_,_,seconds,reason,warnings,rowticks,ticks=sequence._sequence(xm)
    events=[{'tick':t,'pitch':note-1,'channel':ch,'instrument':ins,'sample':sample}
            for t,row in zip(rowticks,rows) for ch,note,ins,sample in row]
    _,_,eligibility=extract_xm_events(xm,sequence)
    if not eligibility['extraction_complete']:
        raise ValueError('incomplete traversal; whole-song recurrence unavailable')
    relations = lane_relations(events)
    kept, removed = delayed_copy_sensitivity(events, relations)
    return {'file':Path(path).name,'title':xm['name'],'sha256':hashlib.sha256(data).hexdigest(),
            'provenance':provenance,'total_ticks':ticks,'seconds':seconds,'event_count':len(events),
            'eligibility':eligibility,'baseline':sequence._development(rows,rowticks,ticks),
            'recurrence':describe_recurrence(events,ticks,controls),
            'lane_relations':relations,'carrier_candidates':carrier_candidates(events,xm),
            'delayed_copy_sensitivity': {'removed_nominal_events':removed,
                 'interpretation':'Hypothetical pitched delayed-copy removal, not certified echoes; channel-dependent witness heuristic.',
                 'recurrence':describe_recurrence(kept,ticks,controls)}}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('xm',type=Path);ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--controls',type=int,default=8);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if not 1<=args.controls<=64:ap.error('--controls must be 1..64')
    result=analyze_file(args.xm,args.root,args.controls)
    args.out.write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
