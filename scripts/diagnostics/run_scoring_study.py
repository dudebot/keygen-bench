"""Reproduce explicit-manifest static scoring. Offline unless --download is set."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import urllib.request
from .theory_scoring import analyze_xm,SPEC_BYTES


def _one(args):
    item,root,cache,out=args
    try:
        result=analyze_xm(cache/(item['id']+'.xm'),root)
        result['published']=item
    except (ValueError,RuntimeError,IndexError) as exc:
        result={'file':item['id'],'status':'unavailable','error_type':type(exc).__name__,'published':item}
    (out/(item['id']+'.json')).write_text(json.dumps(result,indent=2))
    return item['id'],result.get('result',{}).get('structural_score')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--workers',type=int,default=2);p.add_argument('--download',action='store_true')
    a=p.parse_args()
    if not 1<=a.workers<=8:p.error('--workers must be 1..8')
    m=json.loads(a.manifest.read_text())
    if hashlib.sha256(SPEC_BYTES).hexdigest()!=m['spec_sha256']:raise ValueError('formula specification does not match manifest')
    a.cache.mkdir(parents=True,exist_ok=True);a.out.mkdir(parents=True,exist_ok=True)
    expected={item['id'] for item in m['files']}
    if len(expected)!=len(m['files']):raise ValueError('duplicate manifest input IDs')
    if any(p.stem not in expected for p in a.out.glob('*.json')):raise ValueError('output directory contains unrelated JSON files')
    for item in m['files']:
        if Path(item['id']).name!=item['id']:raise ValueError('invalid input id')
        dest=a.cache/(item['id']+'.xm')
        if a.download and not dest.exists():urllib.request.urlretrieve(item['url'],dest)
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('input hash mismatch: '+item['id'])
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        work=[ex.submit(_one,(item,a.root,a.cache,a.out)) for item in m['files']]
        for f in as_completed(work):print(*f.result(),flush=True)
if __name__=='__main__':main()
