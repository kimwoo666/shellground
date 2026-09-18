"""Shrink old build evidence before deleting obsolete validation executables.

Extracts only the two bound sources from the original verified artifact, keeps
the old review unchanged, and emits a new schema-2 review. No lesson rerun.
"""
import json
from pathlib import Path
import shutil
from conda_teaching.shared_shell_carry import ALLOWED, bound, digest, validate


def archive(root):
    from PyInstaller.archive.readers import CArchiveReader
    original=root/'.jupyter-build/conda-shared-shell-carry.json'
    review=json.loads(original.read_text())
    metadata=bound(root,review['runtime_metadata'])
    validate(original,metadata.parent,root)
    binary=bound(root,review['original_binary'])
    reader=CArchiveReader(binary)
    folder=root/'.jupyter-build/conda-baseline';folder.mkdir(exist_ok=True)
    records={}
    for name in ALLOWED:
        path=folder/Path(name).name;data=reader.extract(name)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Baseline extraction differs')
        path.write_bytes(data)
        records[name]=dict(file=path.relative_to(root).as_posix(),sha256=digest(path))
    target=folder/'runtime.json';shutil.copy2(metadata,target)
    review.update(schema=2,original_sources=records,
        runtime_metadata=dict(file=target.relative_to(root).as_posix(),sha256=digest(target)),
        extraction_provenance=dict(original_review_sha256=digest(original),original_binary=review['original_binary']))
    review.pop('original_binary')
    output=root/'.jupyter-build/conda-shared-shell-carry-compact.json'
    if output.exists():raise FileExistsError('Preserve existing compact review')
    output.write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
    result=validate(output,folder,root)
    print(json.dumps(dict(result,compact_baseline_bytes=sum(p.stat().st_size for p in folder.iterdir()))))


if __name__=='__main__':archive(Path(__file__).resolve().parent)
