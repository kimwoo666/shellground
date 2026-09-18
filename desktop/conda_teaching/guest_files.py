"""Read-only, bounded text viewer for the assigned Conda guest workspace."""
from collections import deque
import json
import os
from pathlib import Path
import stat
import sys

WORK=Path('/home/learner/conda-work')
MAX_ENTRIES=200
MAX_BYTES=128*1024


def workspace_file(relative,workspace=WORK):
    root=Path(workspace)
    path=root/relative
    if not relative or Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('실습 폴더 안의 상대경로만 열 수 있습니다.')
    if root.resolve()!=root or path.resolve()!=path or not path.resolve().is_relative_to(root):
        raise ValueError('심볼릭 링크나 실습 폴더 밖의 파일은 열지 않습니다.')
    if not stat.S_ISREG(path.stat().st_mode):raise ValueError('일반 텍스트 파일만 열 수 있습니다.')
    return path


def list_files(workspace=WORK):
    root=Path(workspace)
    if root.resolve()!=root or not root.is_dir():raise ValueError('실습 폴더를 확인할 수 없습니다.')
    pending=deque([root]);items=[];visited=0
    while pending:
        folder=pending.popleft()
        with os.scandir(folder) as entries:
            for entry in entries:
                visited+=1
                if visited>MAX_ENTRIES:return {'files':sorted(items),'truncated':True}
                if entry.is_symlink():continue
                if entry.is_dir(follow_symlinks=False):pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):items.append(str(Path(entry.path).relative_to(root)))
    return {'files':sorted(items),'truncated':False}


def read_file(relative,workspace=WORK):
    path=workspace_file(relative,workspace)
    with path.open('rb') as stream:content=stream.read(MAX_BYTES+1)
    if b'\0' in content:raise ValueError('바이너리 파일은 텍스트로 표시하지 않습니다.')
    return {'path':relative,'text':content[:MAX_BYTES].decode('utf-8',errors='replace'),
            'truncated':len(content)>MAX_BYTES}


if __name__=='__main__':
    sys.path.insert(0,'/opt/shellground')
    from agent import require_guest
    require_guest()
    if os.getuid()!=1100:raise RuntimeError('File viewer must use the guest learner account')
    if sys.argv[1]=='list':result=list_files()
    elif sys.argv[1]=='read':result=read_file(sys.argv[2])
    else:raise ValueError('Unknown read-only file action')
    print(json.dumps(result,ensure_ascii=False))
