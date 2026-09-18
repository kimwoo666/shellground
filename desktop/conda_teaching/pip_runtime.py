"""Actual pip fixtures/evidence inside the owned Linux guest only.

The host sends this trusted helper over the existing control channel. Learner
commands still run as ordinary Bash/Python/pip, never a simulated command set.
All executable probes and package transactions use the learner identity via
core.run; only fixture preparation and read-only observation use guest root.
"""
import json
from pathlib import Path, PurePosixPath

try:
    from pip_wheel import NUMPY_WHEEL, NUMPY_PROBE, load_numpy_wheel, inspect_install, inspect_removal
except ModuleNotFoundError as error:
    if error.name != 'pip_wheel':
        raise
    from .pip_wheel import NUMPY_WHEEL, NUMPY_PROBE, load_numpy_wheel, inspect_install, inspect_removal


WHEELS = Path('/opt/shellground/wheels')

PIP_PROBE = '''import importlib.metadata as md, json, pathlib, pip, sys
p = pathlib.Path(json.load(sys.stdin)['prefix'])
assert pathlib.Path(sys.prefix).resolve() == p
assert pathlib.Path(sys.executable).resolve().is_relative_to(p)
assert pathlib.Path(pip.__file__).resolve().is_relative_to(p)
assert pip.__version__ == md.version('pip')
print(json.dumps(dict(prefix=sys.prefix, executable=sys.executable,
                     version=pip.__version__, module=pip.__file__)))
'''


def uses_pip(problem):
    entries = problem['initial_fixture']['environments']
    flags = ['pip_distributions' in entry for entry in entries]
    if any(flags) and not all(flags):
        raise ValueError('Every environment in a pip fixture needs an explicit distribution list')
    return bool(flags) and all(flags)


def asset():
    path = WHEELS / NUMPY_WHEEL['filename']
    # A learner-writable source is not an immutable teaching asset, even if
    # its current bytes happen to match the official distribution.
    for item in (WHEELS, path):
        if item.is_symlink() or item.stat().st_uid != 0 or item.stat().st_mode & 0o022:
            raise ValueError('Official pip assets are not protected by the guest owner')
    return path, load_numpy_wheel(path)


def package_file(relative):
    path = PurePosixPath(relative)
    if not path.parts or path.is_absolute() or '..' in path.parts or '\\' in relative:
        raise ValueError('Conda package file escapes its prefix')
    # noarch records may retain the source installation scheme.
    if path.parts[0] == 'site-packages':
        path = PurePosixPath('lib/python3.12') / path
    elif path.parts[0] == 'python-scripts':
        path = PurePosixPath('bin', *path.parts[1:])
    return str(path)


def tool_files(core, name, recorded=None):
    target = core.prefix(name)
    if recorded is None:
        candidates = []
        for path in (target / 'conda-meta').glob('*.json'):
            record = json.loads(path.read_text())
            if record.get('name') == 'pip':
                candidates.append(record)
        if len(candidates) != 1:
            raise ValueError('The real Conda pip package is missing or ambiguous')
        recorded = {package_file(item) for item in candidates[0]['files']
                    if not item.endswith('.pyc') and '__pycache__' not in item.split('/')}
    result = {}
    for relative in sorted(recorded):
        path = target / package_file(relative)
        if not path.is_file() or not path.resolve().is_relative_to(target):
            raise ValueError('Python/pip tool file is missing or outside its environment: ' + relative)
        result[relative] = core.digest(path)
    if not result:
        raise ValueError('No actual pip files were recorded')
    return result


def pip_probe(core, name):
    target = core.prefix(name)
    value = json.loads(core.run([str(target / 'bin/python'), '-I', '-c', PIP_PROBE],
                               timeout=12, input=json.dumps({'prefix': str(target)})))
    # A working import alone is not a working python -m pip command.
    core.run([str(target / 'bin/python'), '-I', '-m', 'pip', '--isolated', '--version'], timeout=12)
    return value


def numpy_probe(core, name, absent=False):
    target = core.prefix(name)
    return json.loads(core.run([str(target / 'bin/python'), '-I', '-c', NUMPY_PROBE],
        timeout=15, input=json.dumps({'prefix': str(target), 'version': NUMPY_WHEEL['version'],
                                     'absent': absent})))


def numpy_observation(core, name, manifest, absent=False):
    target = core.prefix(name)
    files = (inspect_removal if absent else inspect_install)(target, manifest)
    if not files['valid']:
        raise ValueError('; '.join(files['errors']))
    return numpy_probe(core, name, absent)


def preserved_tools(core, name, baseline):
    if tool_files(core, name, baseline['files']) != baseline['files']:
        return False
    if pip_probe(core, name) != baseline['pip']:
        return False
    core.python_probe(name)
    for module, probe in baseline['modules'].items():
        core.python_probe(name, dict(probe, module=module))
    return True


def module_probes(core, name):
    snapshot = core.snapshot(name, pip_names=('numpy',))
    result = {}
    for package, data in snapshot['packages'].items():
        if package == 'training-text':
            result['training_text'] = dict(version=data['version'], assertions=[
                dict(call='normalize', args=['  draft  '], expected='DRAFT')])
        elif package == 'training-math':
            checks = [dict(call='total', args=[[2, 5]], expected=7)]
            if data['version'] == '1.1':
                checks.append(dict(call='mean', args=[[2, 8]], expected=5))
            result['training_math'] = dict(version=data['version'], assertions=checks)
    return result


def prepare(core, problem):
    """Runs after real Conda creates the fixture, before learner access."""
    wheel, manifest = asset()
    result = {}
    for entry in problem['initial_fixture']['environments']:
        name = entry['name']
        if name == 'base':
            raise ValueError('pip exercises never mutate the protected management base')
        distributions = entry['pip_distributions']
        if len(distributions) > 1 or any(item.get('name') != 'numpy' or
                item.get('version') != NUMPY_WHEEL['version'] or
                item.get('source') != 'verified_official_wheel' for item in distributions):
            raise ValueError('Only the verified official NumPy asset is supported in this fixture')
        numpy_observation(core, name, manifest, absent=True)
        before = dict(files=tool_files(core, name), pip=pip_probe(core, name),
                      modules=module_probes(core, name), numpy_present=bool(distributions))
        if distributions:
            core.run([str(core.prefix(name) / 'bin/python'), '-I', '-m', 'pip', '--isolated',
                      'install', '--no-index', '--no-deps', '--no-cache-dir',
                      '--disable-pip-version-check', str(wheel)], timeout=45)
            numpy_observation(core, name, manifest)
        if not preserved_tools(core, name, before):
            raise ValueError('Preparing NumPy changed the fixture Python/pip/training tools')
        result[name] = before
        integrity = distributions[0].get('expected_integrity') if distributions else None
        if integrity is not None:
            if integrity != 'intentionally_broken_for_repair' or name not in problem['initial_fixture']['mutable_envs']:
                raise ValueError('Invalid intentional pip fault')
            relative = next(item for item in manifest.files
                            if '/_multiarray_umath.' in item and item.endswith('.so'))
            victim = core.prefix(name) / 'lib/python3.12/site-packages' / relative
            if victim.is_symlink() or victim.resolve() != victim:
                raise ValueError('Intentional fault must stay inside the owned fixture')
            # This file was just installed in this disposable prefix, and its
            # hash was compared against the official wheel immediately above.
            victim.unlink()
            failed = False
            try:
                numpy_probe(core, name)
            except RuntimeError:
                failed = True
            if not failed:
                raise ValueError('The intended missing extension did not break actual NumPy import')
            core.run([str(core.prefix(name) / 'bin/python'), '-I', '-m', 'pip', '--isolated',
                      'show', 'numpy', '--disable-pip-version-check'], timeout=12)
            if not preserved_tools(core, name, before):
                raise ValueError('The intended NumPy fault damaged other tools')
            before['intentional_missing_file'] = relative
    return result
