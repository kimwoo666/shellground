"""Read-only dependency evidence inside the verified Conda builder guest."""
import json
from pathlib import Path
import sys

sys.path.insert(0,'/opt/shellground')
from agent import require_guest
require_guest()
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord

records=[]
for subdir in ('linux-64','noarch'):
    data=json.loads(Path('/opt/shellground/conda-channel',subdir,'repodata.json').read_text())
    for field in ('packages','packages.conda'):
        for filename,record in data[field].items():
            records.append(PackageRecord(**dict(record,fn=filename,channel='file:///opt/shellground/conda-channel')))
missing=[]
for record in records:
    for dependency in record.depends:
        spec=MatchSpec(dependency)
        if not spec.name.startswith('__') and not any(spec.match(candidate) for candidate in records):
            missing.append({'package':record.name,'version':record.version,'dependency':dependency})
print(json.dumps({'records':len(records),'unresolved':missing,
    'selected':[record.dump() for record in records if record.name in ('python','training-math','python_abi')]},indent=2))
path=Path('/home/learner/conda-work/share/environment.yml')
if path.is_file():print('Actual last exported YAML:\n'+path.read_text())
if path.is_file():
    from conda.history import History
    from ruamel.yaml import YAML
    exported=YAML(typ='safe').load(path.read_text())
    requested=History('/home/learner/conda-envs/sg-share').get_requested_specs_map()
    print('Actual requested specs: '+repr({key:str(value) for key,value in requested.items()}))
    print('Exported MatchSpecs: '+repr([str(MatchSpec(value)) for value in exported['dependencies']]))
    print('History MatchSpecs: '+repr([str(MatchSpec(value)) for value in requested.values()]))
    print('Conda config paths:')
    for config in ('/opt/shellground/condarc','/opt/shellground/miniconda/.condarc'):
        print(config+'\n'+Path(config).read_text())
for path in Path('/home/learner/conda-envs/sg-share/conda-meta').glob('python-*.json'):
    record=json.loads(path.read_text());print(json.dumps({k:record.get(k) for k in ('name','channel','url','link')},indent=2))
