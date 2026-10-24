import json,csv,math,argparse
from pathlib import Path
import numpy as np
parser=argparse.ArgumentParser(description='Reproduce fixed grouped crossvalidation from static result JSONs; requires NumPy, never model inference.')
parser.add_argument('--manifest',type=Path,default=Path(__file__).with_name('corpus-manifest.json'));parser.add_argument('--input',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
DIR=args.input
manifest=json.loads(args.manifest.read_text());expected={r['id']:r for r in manifest['files']}
if len(expected)!=len(manifest['files']):raise ValueError('duplicate manifest IDs')
rows=[];seen=set();unavailable=set()
for p in sorted(DIR.glob('*.json')):
 m=json.load(open(p))
 if p.stem not in expected:raise ValueError('unrelated result file: '+p.name)
 if 'result' not in m:
  if m.get('status')=='unavailable':
   unavailable.add(p.stem);continue
  raise ValueError('malformed result: '+p.name)
 if m['published']['id']!=p.stem or p.stem in seen:raise ValueError('duplicate or mismatched result ID')
 seen.add(p.stem)
 if m['result']['spec_sha256']!=manifest['spec_sha256']:raise ValueError('mixed or stale specification')
 if m['input_sha256']!=expected[p.stem]['sha256']:raise ValueError('input hash mismatch')
 r=m['result'];d=r['descriptors'];a=r['attributes'];z=expected[p.stem]
 rows.append({'id':z['id'],'model':z['model_key'],'maker':z['maker'],'score':r['structural_score'],'base_score':r['score_without_entropy_preference'],'entropy':d['pitch_class_entropy_bits'],'gap_entropy':d['onset_gap_entropy_bits'],'interval_entropy':d['onset_set_centroid_interval_entropy_bits'],'scale_fit':d['major_or_natural_minor_collection_fit'],'motion':d['centroid_step_fraction'] or 0.,'boundary':d['long_gap_boundary_proxy_fraction'] or 0.,'period':r['periodicity']['fit'],'variant':a['confirmed_variant_support'],'core':a['supported_core_content'],'R':a['saturated_recurrence_support'],'log_duration':math.log1p(m['seconds']),'log_density':math.log1p(d['onset_count']/max(1e-6,m['seconds'])),**z['listener']})
if seen|unavailable!=set(expected):raise ValueError('missing result files for manifest')
features={'constant':[], 'entropy_only':['entropy'],'base_score':['base_score'],'bell_score':['score'], 'duration_density':['log_duration','log_density'], 'all_static_ridge':['score','base_score','entropy','gap_entropy','interval_entropy','scale_fit','motion','boundary','period','variant','core','R']}

def predict(train,test,keys,target,ridge):
 y=np.array([r[target] for r in train]);weights=np.array([1/sum(r['model']==q['model'] for q in train) for r in train]);weights/=weights.mean()
 if not keys:return np.repeat(np.average(y,weights=weights),len(test))
 x=np.array([[r[k] for k in keys] for r in train]);xt=np.array([[r[k] for k in keys] for r in test]);mu=np.average(x,axis=0,weights=weights);sd=np.sqrt(np.average((x-mu)**2,axis=0,weights=weights));sd[sd<1e-9]=1.
 x=np.column_stack([np.ones(len(x)),(x-mu)/sd]);xt=np.column_stack([np.ones(len(xt)),(xt-mu)/sd]);w=np.sqrt(weights);pen=np.eye(x.shape[1])*ridge;pen[0,0]=0
 beta=np.linalg.pinv((x*w[:,None]).T@(x*w[:,None])+pen)@((x*w[:,None]).T@(y*w))
 return xt@beta

def r2(y,p,w=None):
 y=np.asarray(y);p=np.asarray(p);w=np.ones(len(y)) if w is None else np.array(w)
 den=np.sum(w*(y-np.average(y,weights=w))**2)
 return float(1-np.sum(w*(y-p)**2)/den) if den else None
results=[];predrows=[]
for target in ['production_complexity','content_enjoyment','production_quality','content_usefulness']:
 for grouping in ['model','maker']:
  labels=sorted(set(r[grouping] for r in rows))
  for name,keys in features.items():
   predicted=np.zeros(len(rows))
   for label in labels:
    train=[r for r in rows if r[grouping]!=label];ids=[i for i,r in enumerate(rows) if r[grouping]==label];test=[rows[i] for i in ids]
    pp=predict(train,test,keys,target,1. if name=='all_static_ridge' else 0.)
    predicted[ids]=pp
   y=[r[target] for r in rows];weights=[1/sum(r['model']==q['model'] for q in rows) for r in rows]
   results.append({'target':target,'holdout':grouping,'predictor':name,'r2':r2(y,predicted),'equal_model_r2':r2(y,predicted,weights),'rmse':float(np.sqrt(np.mean((np.array(y)-predicted)**2)))})
   if target=='production_complexity':
    predrows.extend({'id':r['id'],'model':r['model'],'holdout':grouping,'predictor':name,'observed':r[target],'predicted':float(p)} for r,p in zip(rows,predicted))
out=args.out;out.mkdir(parents=True,exist_ok=True)
summary={'input_count':len(expected),'unavailable':sorted(unavailable),'n':len(rows),'models':len(set(r['model'] for r in rows)),'makers':len(set(r['maker'] for r in rows)),'results':results,'hypothesis_r2':.8,'interpretation':'Frozenv1 predictors, exploratory selected-corpus groupedcrossvalidation; negativeR² retained. No hyperparameter search.'}
(out/'results.json').write_text(json.dumps(summary,indent=2))
for name,data in [('attributes.csv',rows),('predictions.csv',predrows),('validation.csv',results)]:
 with (out/name).open('w') as f:
  wr=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator='\n');wr.writeheader();wr.writerows(data)
print('n',summary['n'],'models',summary['models'],'makers',summary['makers'])
for r in results:
 if r['target']=='production_complexity':print(r)
