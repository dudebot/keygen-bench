"""Frozen descriptive external-proxy analysis. No fitting, p-values, or tuning.

Usage: python analyze_external_proxy.py --data DIR
Dependencies: numpy, scipy, pandas, matplotlib. Reproduction uses public-safe
CSV/JSON inputs only. No network access or fitting is performed.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, platform
from pathlib import Path
from itertools import combinations
import numpy as np
import pandas as pd
import scipy
from scipy.stats import rankdata
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROTOCOL='4a0d8db07ac445f9dfb2115358cf658715940f13a434e32042064aa307ae7b0b'
FEATURES={
 'current_SSM':('Current voice SSM','full symbolic traversal'),
 'P':('Predictive organization P','full symbolic traversal'),
 'H':('Pitch transport H','full symbolic traversal'),
 'official_ce':('Official enjoyment','audio first 120 seconds'),
 'local_ce':('Local enjoyment sensitivity','audio first 120 seconds'),
 'mel_SSM':('Mel SSM nonlocal mean','audio first 120 seconds'),
 'chroma_SSM':('Chroma SSM nonlocal mean','audio first 120 seconds'),
 'symbolic_SSM':('Old symbolic SSM nonlocal mean','full symbolic traversal'),
 'prefix_current_SSM':('Current voice SSM, prefix','complete symbolic rows ending at or before 120 seconds'),
 'prefix_P':('Predictive P, prefix','complete symbolic rows ending at or before 120 seconds'),
 'prefix_H':('Pitch transport H, prefix','complete symbolic rows ending at or before 120 seconds'),
}
SYMBOLIC={'current_SSM','P','H','symbolic_SSM','prefix_current_SSM','prefix_P','prefix_H'}
BASECOLS=['id','model','family','cohort','prompt_group','complete','strict_timing','has_xm','has_audio','canonical_seconds','symbolic_status','audio_status']

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(v):
 if isinstance(v,dict): return {str(k):clean(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)): return [clean(x) for x in v]
 if isinstance(v,np.generic): return clean(v.item())
 if isinstance(v,float) and not np.isfinite(v): return None
 return v
def save_json(p,obj): p.write_bytes((json.dumps(clean(obj),indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8'))
def write_csv(p,df): df.to_csv(p,index=False,lineterminator='\n',float_format='%.17g')
def rho(x,y):
 if len(x)<3: return np.nan
 a=rankdata(np.asarray(x,dtype=float)); b=rankdata(np.asarray(y,dtype=float))
 a-=a.mean(); b-=b.mean(); den=np.linalg.norm(a)*np.linalg.norm(b)
 return float(np.clip(a@b/den,-1,1)) if den>1e-14 else np.nan
def percentile(x):
 return (rankdata(np.asarray(x,dtype=float))-1)/(len(x)-1) if len(x)>1 else np.full(len(x),np.nan)

def aggregate(df,cohort,timing):
 frame=df.copy() if cohort=='all_history' else df[df.cohort=='ranked-best-of-3'].copy()
 selected=frame if timing=='row_start' else frame[frame.complete & frame.strict_timing]
 rows=[]
 for model,g in frame.groupby('model',sort=True):
  usable=selected[selected.model==model]
  row={'cohort':cohort,'timing':timing,'model':model,'family':g.family.iloc[0],
       'attempts':len(g),'selected_attempts':len(usable),'has_xm':int(g.has_xm.sum()),'has_audio':int(g.has_audio.sum()),
       'complete_attempts':int(g.complete.sum()),'strict_attempts':int((g.complete & g.strict_timing).sum()),
       'prompt_groups':int(g.prompt_group.nunique()),'music_efforts':'|'.join(sorted(set(g.music_effort.fillna('unavailable'))))}
  for f in FEATURES:
   vals=usable.loc[usable.complete if f in SYMBOLIC else np.ones(len(usable),dtype=bool),f].dropna()
   row[f]=float(vals.median()) if len(vals) else np.nan; row[f+'_n']=len(vals)
  rows.append(row)
 return pd.DataFrame(rows)

def build_targets(external):
 result={name:g[['model','score','effort','external_model']].copy() for name,g in external.groupby('target',sort=True)}
 for window in ('latest','preceding'):
  common=result['EQ4'][['model','score']].merge(result['SWE_'+window],on='model',suffixes=('_EQ4','_SWE'),validate='one_to_one')
  common=common.sort_values('model').reset_index(drop=True)
  common['percentile_EQ4']=percentile(common.score_EQ4)
  common['percentile_SWE']=percentile(common.score_SWE)
  common['score']=(common.percentile_EQ4+common.percentile_SWE)/2
  # Ranks remain fixed on this external complete-case intersection, including
  # when a music feature is missing or one family is omitted for sensitivity.
  result['mix_'+window]=common
 return result

def associations(aggs,targets):
 rows=[]; deletions=[]; joined=[]
 for agg in aggs:
  for target,t in targets.items():
   g=agg.merge(t,on='model',validate='one_to_one')
   g['target']=target; joined.append(g)
   for f,(label,horizon) in FEATURES.items():
    sub=g.dropna(subset=[f,'score']); families=sorted(sub.family.unique())
    deleted=[]
    for family in families:
     s=sub[sub.family!=family]
     value=rho(s[f],s.score)
     deletions.append({'cohort':agg.cohort.iloc[0],'timing':agg.timing.iloc[0],'target':target,'feature':f,'omitted_family':family,'n_models':len(s),'spearman':value})
     if np.isfinite(value): deleted.append(value)
    rows.append({'cohort':agg.cohort.iloc[0],'timing':agg.timing.iloc[0],'target':target,'feature':f,'feature_label':label,'feature_horizon':horizon,'external_models':len(t),'n_models':len(sub),'n_families':len(families),'n_music_attempts':int(sub[f+'_n'].sum()),'spearman':rho(sub[f],sub.score),'family_deletion_min':min(deleted) if deleted else np.nan,'family_deletion_max':max(deleted) if deleted else np.nan,'model_names':'|'.join(sub.model),'family_names':'|'.join(families)})
 return pd.DataFrame(rows),pd.DataFrame(deletions),pd.concat(joined,ignore_index=True)

def pairwise(aggs):
 rows=[]
 for agg in aggs:
  for x,y in combinations(FEATURES,2):
   sub=agg.dropna(subset=[x,y])
   rows.append({'cohort':agg.cohort.iloc[0],'timing':agg.timing.iloc[0],'feature_a':x,'feature_b':y,'n_models':len(sub),'n_families':sub.family.nunique(),'spearman':rho(sub[x],sub[y])})
 return pd.DataFrame(rows)

def plot(folder,assoc,joined):
 labels=['EQ4','CW3','SWE_latest','mix_latest','SWE_preceding','mix_preceding']
 fs=['current_SSM','P','H','official_ce','mel_SSM','chroma_SSM','symbolic_SSM']
 primary=assoc[(assoc.cohort=='ranked_slots') & (assoc.timing=='row_start')]
 matrix=np.full((len(fs),len(labels)),np.nan); counts=np.zeros_like(matrix,dtype=int)
 for i,f in enumerate(fs):
  for j,t in enumerate(labels):
   r=primary[(primary.feature==f)&(primary.target==t)].iloc[0]
   matrix[i,j]=r.spearman;counts[i,j]=r.n_models
 fig,ax=plt.subplots(figsize=(11,6.5),layout='constrained')
 im=ax.imshow(matrix,vmin=-1,vmax=1,cmap='RdBu_r')
 ax.set_xticks(range(len(labels)),['EQ4\nsocial roleplay','CW v3\nprose','Coding\nlatest','50/50 mix\nlatest','Coding\npreceding','50/50 mix\npreceding'])
 ax.set_yticks(range(len(fs)),['Current voice SSM','Predictive P','Pitch transport H','Official enjoyment','Mel SSM','Chroma SSM','Old symbolic SSM'])
 for i in range(len(fs)):
  for j in range(len(labels)):
   v=matrix[i,j];ax.text(j,i,f'{v:+.2f}\nn={counts[i,j]}' if np.isfinite(v) else f'NA\nn={counts[i,j]}',ha='center',va='center',color='white' if np.isfinite(v) and abs(v)>.65 else 'black',fontsize=10)
 ax.set_title('External capability proxies: descriptive model-level Spearman correlations\nRanked-slot medians; named-version matches; unequal effort; no significance claim',fontsize=12)
 fig.colorbar(im,ax=ax,label='Spearman rho',shrink=.8)
 fig.savefig(folder/'associations.png',dpi=180,metadata={'Software':'analyze_external_proxy.py'});plt.close(fig)
 fig,axes=plt.subplots(2,3,figsize=(15,8.8),layout='constrained')
 for row,(cohort,label) in enumerate([('ranked_slots','Ranked-slot medians'),('all_history','All-history medians')]):
  data=joined[(joined.cohort==cohort)&(joined.timing=='row_start')&(joined.target=='mix_latest')]
  for ax,f in zip(axes[row],['current_SSM','P','H']):
   s=data.dropna(subset=[f,'score']);ax.scatter(s[f],s.score,s=30,color='#256c83')
   short={'claude-fable-5':'Fable 5','claude-opus-5':'Opus 5','claude-sonnet-5':'Sonnet 5','gpt-5.6-sol':'5.6 Sol','gpt-5.6-luna':'5.6 Luna','minimax-m3':'MiniMax M3','glm-5.2':'GLM 5.2'}
   for _,r in s.iterrows():
    offset=-12 if r.model in ('gpt-5.6-luna','claude-opus-5') else 5
    ax.annotate(short.get(r.model,r.model),(r[f],r.score),xytext=(4,offset),textcoords='offset points',fontsize=8)
   ax.margins(x=.20,y=.13)
   ax.set_xlabel(FEATURES[f][0]);ax.set_ylabel('Fixed 50/50 external percentile mix');ax.set_title(f'{label}\nn={len(s)}, rho={rho(s[f],s.score):+.3f}')
   ax.grid(alpha=.15)
 fig.suptitle('Latest fixed task window: seven named versions, four families\nH changes from +0.837 to +0.036 across cohorts; external ranks do not define musical quality',fontsize=12)
 fig.savefig(folder/'latest-mix-scatter.png',dpi=180,metadata={'Software':'analyze_external_proxy.py'});plt.close(fig)

def fmt(v): return 'NA' if pd.isna(v) else f'{v:+.3f}'
def report(folder,assoc,agg,external,pairs):
 primary=assoc[(assoc.cohort=='ranked_slots')&(assoc.timing=='row_start')]
 def value(target,feature,cohort='ranked_slots',timing='row_start'):
  return assoc[(assoc.target==target)&(assoc.feature==feature)&(assoc.cohort==cohort)&(assoc.timing==timing)].iloc[0]
 hmain=value('mix_latest','H');hhist=value('mix_latest','H','all_history');hstrict=value('mix_latest','H','all_history','strict')
 ssm_eq=value('EQ4','current_SSM');ssm_cw=value('CW3','current_SSM')
 lines=['# External proxies: frozen descriptive analysis','',
 'This analysis asks whether structural descriptors vary with external conversational and coding capabilities. Enjoyment is a separate comparator. None of these labels defines musical quality. C1/C2 remain rejected by their independent adversarial tests and were not reconsidered here.','',
 f'Current voice SSM shows positive descriptive associations with EQ4 ({fmt(ssm_eq.spearman)}, n={ssm_eq.n_models}) and prose creativity ({fmt(ssm_cw.spearman)}, n={ssm_cw.n_models}). P and H have much weaker associations with those two targets. H has a strong latest-mix association in ranked attempts ({fmt(hmain.spearman)}, n={hmain.n_models}), but this drops to {fmt(hhist.spearman)} with all-history medians and {fmt(hstrict.spearman)} with strict all-history medians. That cohort sensitivity prevents treating the strongest result as a stable capability relationship or a validated metric improvement.','',
 '## Protocol and identity','',
 f'Frozen protocol SHA256: `{PROTOCOL}`. No fitting, optimized weights, benchmark switching, p-values, or significance verdicts. Exact displayed/API release names and documented aliases were reviewed before joining music data. These are named-release matches, not proof of identical weights or deployments.','',
 'Excluded: DeepSeek V4-Pro (known unchanged-name update), Gemini3.5Flash (known redirection to3.6), and SWE-rebench Gemma31B (instruction variant unspecified). Official GPT5.4/5.5 pages document the dated snapshot aliases. The external cohort contains EQ4=21, CW3=32, latest coding=8, preceding coding=10; the equal-weight mix contains latest=7 and preceding=10 before music missingness. Latest coding alone additionally includes Grok4.5.','',
 '## Main results','',
 'Each cell is Spearman rho (number of model versions). Models contribute medians over their ranked-slot attempts, never their best outcome. Unequal available attempt counts are in the data. In the primary row-start analysis, symbolic metrics require complete extraction and their own diagnostic eligibility; audio metrics and CE retain their own available audio rows. The strict-timing sensitivity filters the entire cohort, including audio metrics and CE, to complete and strictly timed symbolic extraction. Unsupported symbolic timing remains a nominal row-start description.','',
 '| Descriptor | EQ4 | Prose CW3 | Coding latest | Mix latest | Coding preceding | Mix preceding |','| --- | --- | --- | --- | --- | --- | --- |']
 for f in FEATURES:
  cells=[]
  for t in ['EQ4','CW3','SWE_latest','mix_latest','SWE_preceding','mix_preceding']:
   r=primary[(primary.feature==f)&(primary.target==t)].iloc[0];cells.append(f'{fmt(r.spearman)} ({r.n_models})')
  lines.append('| '+FEATURES[f][0]+' | '+' | '.join(cells)+' |')
 lines+=['','## Family sensitivity for the latest mix','','The interval below is the minimum and maximum after deleting one observed name-prefix family. It is a sensitivity range, not a confidence interval. The external percentile ranks remain frozen while music rows/families are removed.','',
 '| Cohort | Timing | Descriptor | n / families | rho | Family deletion range |','| --- | --- | --- | --- | --- | --- |']
 for _,r in assoc[(assoc.target=='mix_latest')&assoc.feature.isin(['current_SSM','P','H','official_ce'])].iterrows():
  lines.append(f'| {r.cohort} | {r.timing} | {r.feature} | {r.n_models} / {r.n_families} | {fmt(r.spearman)} | {fmt(r.family_deletion_min)} to {fmt(r.family_deletion_max)} |')
 lines+=['','## What the study can establish','','Different associations describe differences within this selected corpus; they do not by themselves establish statistical independence, musical usefulness, or a causal relationship with general capability. A structural dimension earns its interpretation through controlled examples and invariance tests. Its practical usefulness would require a defined downstream decision or human comparison, not merely agreement with a model leaderboard. No replacement scoring formula is proposed.','',
 'The two coding windows use different task sets and are never pooled: latest is 2026-05-15 to 2026-07-01; preceding is 2026-03-01 to 2026-05-15. These are task-date windows, not evaluation dates. The source model release dates are metadata and not evidence of when a run occurred. SWE effort is medium where multiple configurations exist, otherwise the single recorded setting. Music often used max effort.','',
 'EQ4 evaluates simulated multi-turn social/emotional interaction; CW3 evaluates single-turn prose. Model judges, selected frontier families, provider routes, prompts, attempt failures, time, and differing effort can all confound these retrospective correlations. External uncertainty is not estimated by treating multiple music attempts as independent models. Small n and few families preclude a reliable incremental-prediction claim.','',
 '## Horizons and reproducibility','','Full symbolic metrics describe the full parsed traversal. Prefix P/H/current SSM use complete rows ending no later than120 seconds. Mel/chroma SSM and listener CE use the first120 seconds of audio. Old symbolic SSM remains full traversal. Corresponding horizon labels accompany every numerical association.','',
 '`associations.csv` contains every predeclared target, metric, ranked/all-history cohort, and row-start/strict sensitivity. `family-deletions.csv` contains each omitted family. `model-medians.csv`, `joined-models.csv`, and `external-scores.json` expose denominators and component ranks. `descriptor-pairs.csv` reports descriptor-to-descriptor model-level relationships without an external target. `identity-mapping.json` gives accepted/excluded mappings and primary source links. No raw prompts, local paths, credentials, or route configuration are required by the reproduction inputs.','',
 'Reproduce with `python analyze_external_proxy.py --data .` from this directory after installing numpy, scipy, pandas, and matplotlib. `music-input.csv` is an allowlisted730-row extract. The script uses only saved inputs and has no network calls.','',
 'Sources: [EQ4](https://eqbench.com/), [Creative Writing v3](https://eqbench.com/creative_writing.html), [SWE-rebench](https://swe-rebench.com/leaderboard), [SWE-rebench methodology](https://swe-rebench.com/about).']
 (folder/'results.md').write_bytes(('\n'.join(lines)+'\n').encode('utf-8'))

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,required=True);args=parser.parse_args();folder=args.data
 freeze=json.loads((folder/'freeze.json').read_text(encoding='utf-8'))
 assert freeze['protocol_sha256']==PROTOCOL
 assert digest(folder/'external-scores.json')==freeze['external_scores_sha256']
 assert digest(folder/'identity-mapping.json')==freeze['identity_mapping_sha256']
 df=pd.read_csv(folder/'music-input.csv');assert len(df)==730 and df.id.is_unique
 for f in FEATURES: df[f]=pd.to_numeric(df[f],errors='coerce')
 for key in ['complete','strict_timing','has_xm','has_audio']: df[key]=df[key].astype(str).str.lower().eq('true')
 ext=pd.read_json(folder/'external-scores.json')
 targets=build_targets(ext)
 aggs=[aggregate(df,c,t) for c in ['ranked_slots','all_history'] for t in ['row_start','strict']]
 assoc,deletions,joined=associations(aggs,targets);agg=pd.concat(aggs,ignore_index=True);pairs=pairwise(aggs)
 for name,frame in [('associations',assoc),('family-deletions',deletions),('model-medians',agg),('joined-models',joined),('descriptor-pairs',pairs)]:write_csv(folder/(name+'.csv'),frame)
 save_json(folder/'results.json',{'protocol_sha256':PROTOCOL,'mapping_sha256':freeze['identity_mapping_sha256'],'external_scores_sha256':freeze['external_scores_sha256'],'music_input_sha256':digest(folder/'music-input.csv'),'runtime':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'pandas':pd.__version__},'associations':assoc.to_dict('records'),'targets':{k:v.to_dict('records') for k,v in targets.items()},'cohorts':{'ranked_slots_attempts':int(df.cohort.eq('ranked-best-of-3').sum()),'all_history_attempts':len(df)},'inference':'descriptive only; family deletion is not a confidence interval'})
 report(folder,assoc,agg,ext,pairs);plot(folder,assoc,joined)
 print(assoc[(assoc.cohort=='ranked_slots')&(assoc.timing=='row_start')&assoc.feature.isin(['current_SSM','P','H','official_ce'])][['target','feature','n_models','spearman','family_deletion_min','family_deletion_max']].to_string(index=False))

if __name__=='__main__': main()
