"""Small real Conda packages and offline channel metadata, not CLI emulation.

Format: https://docs.conda.io/projects/conda-build/en/stable/resources/package-spec.html
The official installer caches are copied unchanged, retaining package licenses.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tarfile


def hashes(path):
    sha=hashlib.sha256();md5=hashlib.md5()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):sha.update(block);md5.update(block)
    return {'sha256':sha.hexdigest(),'md5':md5.hexdigest(),'size':path.stat().st_size}


def training_package(folder,name,version,body):
    module=name.replace('-','_');member=f'site-packages/{module}/__init__.py'
    code=(f'__version__ = {version!r}\n'+body).encode()
    record={'name':name,'version':version,'build':'py_0','build_number':0,
            'depends':['python >=3.12,<3.13.0a0'],'subdir':'noarch','noarch':'python','license':'CC0-1.0'}
    files={member:code,'info/index.json':json.dumps(record).encode(),
           'info/files':(member+'\n').encode(),
           'info/link.json':json.dumps({'package_metadata_version':1,'noarch':{'type':'python','entry_points':[]}}).encode(),
           'info/about.json':json.dumps({'summary':'Shellground educational example package. Not NumPy or a replacement Conda engine.','license':'CC0-1.0'}).encode(),
           'info/license.txt':b'CC0 1.0 Universal: educational example code dedicated to the public domain.\nhttps://creativecommons.org/publicdomain/zero/1.0/\n'}
    target=folder/f'{name}-{version}-py_0.tar.bz2'
    with tarfile.open(target,'w:bz2') as archive:
        for path,data in sorted(files.items()):
            info=tarfile.TarInfo(path);info.size=len(data);info.mode=0o644;info.mtime=0
            archive.addfile(info,io.BytesIO(data))
    return target,record


def package_record(base,metadata):
    """Keep the installer's official repodata hotfixes, not obsolete build deps.

    Archive info/index.json can differ from the repository record that was
    solved when the installer was assembled (e.g. tk's zlib constraint).
    Never invent relaxed dependencies to make a solver pass.
    """
    original=json.loads(metadata.read_text())
    stem=metadata.parent.parent.name
    for path in (base/'conda-meta'/(stem+'.json'),metadata.with_name('repodata_record.json')):
        if path.is_file():
            record=json.loads(path.read_text())
            if any(record.get(key)!=original.get(key) for key in ('name','version','build','build_number')):
                raise RuntimeError('Official installed package identity differs: '+stem)
            return {key:value for key,value in record.items() if key not in
                    ('files','paths_data','link','requested_spec','extracted_package_dir','package_tarball_full_path','url','channel')}
    return original


def build_channel(base,target):
    records=[(metadata,package_record(base,metadata)) for metadata in sorted((base/'pkgs').glob('*/info/index.json'))]
    native={record.get('subdir') for _,record in records if not record.get('noarch') and record.get('subdir')!='noarch'}
    if len(native)!=1 or not native.issubset({'linux-64','linux-aarch64'}):
        raise RuntimeError('Expected one supported native guest architecture, not a mixed or missing cache: '+repr(native))
    guest_subdir=next(iter(native))
    indexes={s:{'info':{'subdir':s},'packages':{},'packages.conda':{},'repodata_version':1} for s in (guest_subdir,'noarch')}
    for subdir in indexes:(target/subdir).mkdir(parents=True,exist_ok=True)
    copied=0
    for metadata,record in records:
        subdir=record.get('subdir','noarch' if record.get('noarch') else guest_subdir)
        if subdir not in indexes:raise RuntimeError('Package architecture differs from the guest: '+str(subdir))
        stem=metadata.parent.parent.name
        source=next((base/'pkgs'/(stem+suffix) for suffix in ('.conda','.tar.bz2') if (base/'pkgs'/(stem+suffix)).is_file()),None)
        if source is None:raise RuntimeError('Official package archive missing: '+stem)
        destination=target/subdir/source.name
        if not destination.exists():
            try:os.link(source,destination)
            except OSError:shutil.copy2(source,destination)
        if hashes(destination)['sha256']!=hashes(source)['sha256']:raise RuntimeError('Cached package copy differs: '+stem)
        record.update(hashes(destination));kind='packages.conda' if source.suffix=='.conda' else 'packages'
        indexes[subdir][kind][source.name]=record;copied+=1
    if copied<10:raise RuntimeError('Official Python dependency cache is incomplete')
    bodies=[('training-math','1.0','def total(values):\n    return sum(values)\n'),
            ('training-math','1.1','def total(values):\n    return sum(values)\ndef mean(values):\n    return sum(values) / len(values)\n'),
            ('training-text','1.0','def normalize(text):\n    return text.strip().upper()\n')]
    for name,version,body in bodies:
        path,record=training_package(target/'noarch',name,version,body);record.update(hashes(path));indexes['noarch']['packages'][path.name]=record
    for subdir,data in indexes.items():
        for filename in ('repodata.json','current_repodata.json'):(target/subdir/filename).write_text(json.dumps(data,sort_keys=True)+'\n')
    return {'official_archives':copied,'training_packages':len(bodies),'channel':target.as_uri(),'subdir':guest_subdir}
