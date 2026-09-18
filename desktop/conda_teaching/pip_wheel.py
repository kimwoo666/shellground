"""Evidence for the next Linux pip lessons; not yet connected to the course.

Reads the pinned official NumPy wheel and compares installed files to its
RECORD, never to a learner-authored success string. The caller must run the
fresh Python probe as learner inside the owned guest, not as root. This is an
educational outcome checker, not an adversarial examination security boundary.

Wheel/installed RECORD semantics:
https://packaging.python.org/en/latest/specifications/binary-distribution-format/
"""
import base64
import configparser
import csv
from dataclasses import dataclass
from email.parser import Parser
import hashlib
import io
from pathlib import Path, PurePosixPath
import stat
import zipfile


NUMPY_WHEEL = {
    'name': 'numpy',
    'version': '2.3.5',
    'filename': 'numpy-2.3.5-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl',
    'sha256': '0d8163f43acde9a73c2a33605353a4f1bc4798745a8b1d73183b28e5b435ae28',
    'url': 'https://files.pythonhosted.org/packages/b6/23/2a1b231b8ff672b4c450dac27164a8b2ca7d9b7144f9c02d2396518352eb/numpy-2.3.5-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl',
    'tags': ('cp312-cp312-manylinux_2_27_x86_64', 'cp312-cp312-manylinux_2_28_x86_64'),
}


class WheelAssetError(ValueError):
    """Missing/wrong teacher-owned asset, not a learner's incorrect answer."""


@dataclass(frozen=True)
class WheelManifest:
    name: str
    version: str
    dist_info: str
    files: dict  # relative filename -> (hex SHA256, size)
    archive_sha256: str
    scripts: tuple = ()


def digest(stream):
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        value.update(block)
    return value.hexdigest()


def record_rows(text):
    result = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) != 3 or not row[0] or row[0] in result:
            raise ValueError('Invalid or duplicate RECORD entry')
        result[row[0]] = (row[1], row[2])
    return result


def wheel_path(name):
    path = PurePosixPath(name)
    if ('\\' in name or path.is_absolute() or '..' in path.parts
            or path.as_posix() != name or not path.parts):
        raise ValueError('Unsafe wheel path')
    return path


def record_hash(hex_digest):
    return 'sha256=' + base64.urlsafe_b64encode(bytes.fromhex(hex_digest)).decode().rstrip('=')


def load_numpy_wheel(path):
    """Load only the officially pinned cp312/Linux x86_64 asset; no download."""
    path = Path(path)
    if path.name != NUMPY_WHEEL['filename'] or path.is_symlink() or not path.is_file():
        raise WheelAssetError('Verified Linux NumPy wheel is missing')
    with path.open('rb') as stream:
        checksum = digest(stream)
    if checksum != NUMPY_WHEEL['sha256']:
        raise WheelAssetError('Official NumPy wheel checksum mismatch')
    dist_info = 'numpy-2.3.5.dist-info'
    try:
        with zipfile.ZipFile(path) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            names = [item.filename for item in members]
            if len(names) != len(set(names)):
                raise ValueError('Duplicate wheel members')
            for item in members:
                wheel_path(item.filename)
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError('Unexpected symlink in the pinned wheel')
            metadata = Parser().parsestr(archive.read(dist_info + '/METADATA').decode())
            wheel = Parser().parsestr(archive.read(dist_info + '/WHEEL').decode())
            if (metadata['Name'] != NUMPY_WHEEL['name'] or metadata['Version'] != NUMPY_WHEEL['version']
                    or metadata.get_all('Requires-Dist') or wheel['Root-Is-Purelib'] != 'false'
                    or set(wheel.get_all('Tag', [])) != set(NUMPY_WHEEL['tags'])):
                raise ValueError('Unexpected distribution identity or compatibility')
            record = record_rows(archive.read(dist_info + '/RECORD').decode())
            entry_points = configparser.ConfigParser(interpolation=None)
            entry_points.read_string(archive.read(dist_info + '/entry_points.txt').decode())
            scripts = tuple(entry_points['console_scripts'])
            if any(wheel_path(name).name != name for name in scripts):
                raise ValueError('Unsafe console script name')
            if set(record) != set(names):
                raise ValueError('Wheel files and RECORD disagree')
            files = {}
            for item in members:
                name = item.filename
                encoded, size = record[name]
                if name == dist_info + '/RECORD':
                    if (encoded, size) != ('', ''):
                        raise ValueError('RECORD must not hash itself')
                    continue
                with archive.open(item) as stream:
                    checksum_file = digest(stream)
                if encoded != record_hash(checksum_file) or size != str(item.file_size):
                    raise ValueError('Wheel member integrity mismatch: ' + name)
                if PurePosixPath(name).parts[0] not in ('numpy', 'numpy.libs', dist_info):
                    raise ValueError('Unmapped wheel installation scheme')
                files[name] = (checksum_file, item.file_size)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        raise WheelAssetError(str(error)) from error
    return WheelManifest('numpy', '2.3.5', dist_info, files, checksum, scripts)


def contained_file(path, prefix):
    return path.is_file() and path.resolve() == path and path.is_relative_to(prefix)


def generated_records(manifest):
    """Only entries pip may add for this wheel, never another package's files."""
    result = {manifest.dist_info + '/' + name
              for name in ('RECORD', 'INSTALLER', 'REQUESTED', 'direct_url.json')}
    result.update('../../../bin/' + name for name in manifest.scripts)
    for name in manifest.files:
        source = PurePosixPath(name)
        if source.suffix == '.py':
            for optimization in ('', '.opt-1', '.opt-2'):
                result.add(str(source.parent / '__pycache__' /
                               (source.stem + '.cpython-312' + optimization + '.pyc')))
    return result


def canonical_prefix(prefix):
    prefix = Path(prefix)
    try:
        if prefix.is_absolute() and prefix.resolve() == prefix:
            return prefix
    except (OSError, RuntimeError):
        pass
    raise ValueError('Environment prefix is not a distinct canonical path')


def inspect_install(prefix, manifest):
    """Read-only file evidence. Fresh Python execution is a separate requirement."""
    try:
        prefix = canonical_prefix(prefix)
    except ValueError as error:
        return {'valid': False, 'errors': [str(error)]}
    site = prefix / 'lib/python3.12/site-packages'
    record_path = site / manifest.dist_info / 'RECORD'
    errors = []
    records = {}
    try:
        if not contained_file(record_path, prefix) or record_path.stat().st_size > 1024 * 1024:
            raise ValueError('Installed RECORD is missing or outside the environment')
        records = record_rows(record_path.read_text())
        allowed = set(manifest.files) | generated_records(manifest)
        if records.get(manifest.dist_info + '/RECORD') != ('', ''):
            raise ValueError('Installed RECORD must list itself without a hash')
        for name in records:
            if ('\\' in name or Path(name).is_absolute()
                    or not (site / name).resolve().is_relative_to(prefix)):
                raise ValueError('Installed RECORD escapes the environment')
            if name not in allowed:
                raise ValueError('Installed RECORD claims a file outside this distribution: ' + name)
    except (OSError, ValueError, RuntimeError) as error:
        errors.append(str(error))
    checked = 0
    for name, (checksum, size) in manifest.files.items():
        path = site / name
        try:
            if not contained_file(path, prefix) or path.stat().st_size != size:
                raise ValueError('Missing, linked or wrong-size file: ' + name)
            with path.open('rb') as stream:
                if digest(stream) != checksum:
                    raise ValueError('Changed official file: ' + name)
            if records.get(name) != (record_hash(checksum), str(size)):
                raise ValueError('Installed RECORD identity mismatch: ' + name)
            checked += 1
        except (OSError, ValueError, RuntimeError) as error:
            errors.append(str(error))
        if len(errors) >= 8:
            break
    return {'valid': not errors and checked == len(manifest.files),
            'errors': errors, 'checked_files': checked, 'expected_files': len(manifest.files),
            'expected_location': str(site), 'expected_version': manifest.version,
            'archive_sha256': manifest.archive_sha256}


def inspect_removal(prefix, manifest):
    """File half of removal grading; also require the fresh absent probe.

    A missing import alone does not prove uninstall: native libraries/scripts
    can remain. Empty directories and generated bytecode are harmless here.
    """
    errors = []
    try:
        prefix = canonical_prefix(prefix)
        site = prefix / 'lib/python3.12/site-packages'
        names = set(manifest.files)
        names.update(manifest.dist_info + '/' + name
                     for name in ('RECORD', 'INSTALLER', 'REQUESTED', 'direct_url.json'))
        paths = [site / name for name in sorted(names)]
        paths.extend(prefix / 'bin' / name for name in manifest.scripts)
        for path in paths:
            if path.exists() or path.is_symlink():
                errors.append('Distribution file remains: ' + str(path.relative_to(prefix)))
                if len(errors) >= 8:
                    break
    except (OSError, ValueError, RuntimeError) as error:
        errors.append(str(error))
    return {'valid': not errors, 'errors': errors}


NUMPY_PROBE = '''import importlib.metadata as md, json, pathlib, sys
r = json.load(sys.stdin)
p = pathlib.Path(r['prefix'])
assert pathlib.Path(sys.prefix).resolve() == p
assert pathlib.Path(sys.executable).resolve().is_relative_to(p)
result = {'prefix': sys.prefix, 'executable': sys.executable, 'series': list(sys.version_info[:2])}
assert result['series'] == [3, 12]
if r.get('absent'):
    try:
        distribution = md.distribution('numpy')
    except md.PackageNotFoundError:
        pass
    else:
        empty_metadata = p / 'lib/python3.12/site-packages' / ('numpy-' + r['version'] + '.dist-info')
        assert empty_metadata.is_dir() and not any(empty_metadata.iterdir())
        assert pathlib.Path(distribution.locate_file('')).resolve() == empty_metadata.parent
        assert distribution.read_text('METADATA') is None and distribution.files is None
        assert distribution.version is None, 'NumPy distribution metadata still exists'
        result['empty_metadata_only'] = True
    try:
        import numpy
    except ModuleNotFoundError as error:
        assert error.name == 'numpy', 'A broken dependency is not package absence'
    else:
        # pip may leave an empty package directory or generated __pycache__.
        # Python treats it as a namespace; that is not an installed NumPy.
        spec = numpy.__spec__
        empty_root = p / 'lib/python3.12/site-packages/numpy'
        assert spec.origin is None and numpy.__file__ is None
        assert list(map(lambda x: pathlib.Path(x).resolve(), numpy.__path__)) == [empty_root]
        assert not hasattr(numpy, 'array') and not hasattr(numpy, '__version__')
        for path in empty_root.rglob('*'):
            assert path.is_dir() or (path.suffix == '.pyc' and '__pycache__' in path.parts)
        result['empty_namespace_only'] = True
    result['absent'] = True
else:
    import numpy as np
    distribution = md.distribution('numpy')
    site = p / 'lib/python3.12/site-packages'
    assert pathlib.Path(distribution.locate_file('')).resolve() == site
    assert pathlib.Path(np.__file__).resolve() == site / 'numpy/__init__.py'
    assert np.__version__ == distribution.version == r['version']
    result.update(version=np.__version__, location=str(site), module=np.__file__, sums=[])
    for values, total in (([2, 5], 7), ([1, -1, 3], 3)):
        array = np.array(values, dtype=np.int64)
        assert type(array) is np.ndarray and array.shape == (len(values),)
        assert (array + array).tolist() == [2 * value for value in values]
        assert int(array.sum()) == total
        result['sums'].append(int(array.sum()))
print(json.dumps(result))
'''
