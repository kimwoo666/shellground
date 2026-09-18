"""Create a small explicit source manifest, never a workspace-wide git add."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
IGNORED_DIRS={'build','__pycache__','tmp','ui-previews','node_modules'}
SUFFIXES={'.py','.md','.json','.txt','.sh','.ps1','.java','.xml','.kts','.properties','.patch','.ttc','.cs','.nsi','.svg'}
PRIVATE_DOCS={'RESUME_NOTES.md','WORK_STATUS.md','DEVELOPMENT_GOALS.md','CLEANUP_2026-09-18.md'}

def included(path):
    relative=path.relative_to(ROOT)
    if any(part.startswith('.') or part.startswith('dist-') or part in IGNORED_DIRS for part in relative.parts):return False
    if path.name in PRIVATE_DOCS or path.name=='local.properties' or path.name.endswith('.spec'):return False
    if path.name in ('bashrc','Dockerfile'):return True
    return path.suffix in SUFFIXES

def records():
    selected=[ROOT/name for name in ('README.md','README.ko.md','THIRD_PARTY_NOTICES.md','.gitattributes','.gitignore')]
    for directory in ('desktop','android'):
        for folder,dirs,names in os.walk(ROOT/directory):
            dirs[:]=[name for name in dirs if not name.startswith('.') and not name.startswith('dist-')
                and name not in IGNORED_DIRS and not (Path(folder)/name).is_symlink()]
            selected.extend(Path(folder)/name for name in names if not (Path(folder)/name).is_symlink() and included(Path(folder)/name))
    selected.extend(p for p in (ROOT/'docs').rglob('*') if p.is_file() and p.suffix in {'.md','.png','.json'})
    rows=[]
    for path in sorted(set(selected)):
        data=path.read_bytes()
        if path.suffix not in {'.png','.ttc'}:
            text=data.decode('utf-8')
            if any(marker in text for marker in ('-----BEGIN PRIVATE KEY-----','-----BEGIN RSA PRIVATE KEY-----','ghp_','github_pat_')):
                # This script itself names the patterns, never a credential.
                if path!=Path(__file__).resolve():raise ValueError('Inspect sensitive pattern in '+str(path))
        rows.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=len(data),
            git_sha=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),
            binary=path.suffix in {'.png','.ttc'},mode='100755' if path.suffix=='.sh' else '100644'))
    return rows

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--batch',type=int);args=parser.parse_args()
    rows=records();out=ROOT/'publish/4.7.4-source';out.mkdir(exist_ok=True)
    if args.batch is None:
        (out/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(dict(files=len(rows),bytes=sum(x['bytes'] for x in rows),manifest=str(out/'manifest.json'))))
    else:
        batch=[];size=0;batches=[]
        for row in rows:
            if row['binary']:continue
            text=(ROOT/row['path']).read_text()
            if size+len(text)>180000 and batch:batches.append(batch);batch=[];size=0
            batch.append(dict(path=row['path'],mode=row['mode'],type='blob',content=text));size+=len(text)
        if batch:batches.append(batch)
        print(json.dumps(dict(index=args.batch,total=len(batches),entries=batches[args.batch]),ensure_ascii=False))
