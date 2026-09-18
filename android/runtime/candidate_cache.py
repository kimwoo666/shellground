"""Keep verified cross-build outputs beyond the lifetime of /tmp build roots."""
import hashlib
from pathlib import Path
import re
import shutil


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def preserve(source, cache, expected):
    source, cache = Path(source), Path(cache)
    if not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise ValueError('Invalid candidate checksum')
    if source.is_symlink() or not source.is_file() or checksum(source) != expected:
        raise ValueError('Candidate bytes do not match the verified build')
    if cache.resolve() != cache.absolute():
        raise ValueError('Unexpected candidate cache link')
    if cache.exists():
        if not cache.is_file() or checksum(cache) != expected:
            raise ValueError('Preserve and inspect the conflicting candidate cache')
        return cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as incoming, cache.open('xb') as outgoing:
        shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
    if checksum(cache) != expected:
        raise ValueError('Candidate changed during preservation; inspect cache before retrying')
    cache.chmod(0o755)
    return cache


def select(original, cache, staged, expected):
    """Only recover exact previously verified bytes, never accept a new binary."""
    original, cache = Path(original), Path(cache)
    if original.exists() or original.is_symlink():
        return preserve(original, cache, expected)
    if cache.exists() or cache.is_symlink():
        return preserve(cache, cache, expected)
    for candidate in staged:
        candidate = Path(candidate)
        if candidate.is_file() and not candidate.is_symlink() and checksum(candidate) == expected:
            return preserve(candidate, cache, expected)
    raise ValueError('Verified native candidate is missing; rebuild from pinned sources')
