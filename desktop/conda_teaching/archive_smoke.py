"""Explicit developer recovery: preserve two proven smoke fixtures, never delete.

The CLI is only for the marked offline builder guest. No arbitrary CLI paths,
recursive removal, host Conda, or automatic recovery during ordinary startup.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile


EXPECTED = {
    'sg-proof': '# cmd: /opt/shellground/miniconda/bin/conda create -n sg-proof python=3.12 training-math=1.0 -y',
    'sg-copy': '# cmd: /opt/shellground/miniconda/bin/conda env create -n sg-copy -f environment.yml -y',
}


def archive_failed_smoke(state, environments, archives):
    state, environments, archives = map(Path, (state, environments, archives))
    # Resolve every input before any mutation. Refuse links and unrelated or
    # partially known environments rather than treating names alone as proof.
    for path in (state, environments, archives):
        if path.resolve()!=path.absolute():raise ValueError('Unexpected linked archive path')
    exit_file=state/'conda-provision-exit';log_file=state/'conda-provision.log'
    for path in (exit_file,log_file):
        if path.is_symlink() or not path.is_file():raise ValueError('Missing failed-build evidence')
    log=log_file.read_text(errors='replace')
    if exit_file.read_text().strip()!='1' or not (
        ('TimeoutExpired' in log and '/mnt/sg-conda/runtime_smoke.sh' in log)
        or 'Conda smoke timeout;' in log):
        raise ValueError('Not a recognized failed smoke run')
    records=[]
    for name, command in EXPECTED.items():
        source=environments/name;history=source/'conda-meta/history'
        if source.resolve()!=source.absolute() or history.resolve()!=history.absolute() or not history.is_file():
            raise ValueError('Unrecognized smoke environment: '+name)
        content=history.read_bytes()
        if command not in content.decode(errors='replace').splitlines():
            raise ValueError('Smoke creation history does not match: '+name)
        records.append({'source':str(source),'name':name,'history_sha256':hashlib.sha256(content).hexdigest(),
                        'moved':False})
    archives.mkdir(parents=True,exist_ok=True)
    destination=Path(tempfile.mkdtemp(prefix='failed-smoke-',dir=archives))
    record={'schema':1,'kind':'preserved-smoke-fixtures-not-validation',
            'destination':str(destination),'items':records}
    journal=destination/'archive.json'
    def save():
        journal.write_text(json.dumps(record,indent=2)+'\n')
    save()
    for item in records:
        Path(item['source']).rename(destination/item['name'])
        item['moved']=True;save()
    return record


def main():
    import sys
    sys.path.insert(0,'/opt/shellground')
    from agent import require_guest
    require_guest()
    if os.getuid()!=0:raise RuntimeError('Only the owned image-builder guest may archive these fixtures')
    print(json.dumps(archive_failed_smoke('/opt/shellground','/home/learner/conda-envs',
        '/opt/shellground/conda-smoke-archives'),indent=2),flush=True)


if __name__=='__main__':main()
