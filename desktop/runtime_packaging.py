"""Idempotent runtime copying, preserving bundled library/firmware symlinks."""
import os
from pathlib import Path
import shutil
import tempfile


def copy_runtime_pack(source, destination, *, link_immutable=False):
    """link_immutable is an explicit local-build space optimization.

    It shares inodes: callers must only replace source assets atomically, never
    edit them in place. Runtime writable overlays stay outside this directory.
    There is no copy fallback on a different filesystem (avoid filling disk).
    """
    source, destination = Path(source), Path(destination)
    if destination.is_symlink():
        raise ValueError('Runtime destination directory must not be a symlink')
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_symlink():
            link = os.readlink(item)
            if target.is_symlink() and os.readlink(target) == link:
                continue
            if target.exists() or target.is_symlink():
                raise ValueError('Conflicting existing runtime entry: ' + str(target))
            target.symlink_to(link)
        elif item.is_dir():
            copy_runtime_pack(item, target, link_immutable=link_immutable)
        else:
            if target.is_symlink():
                raise ValueError('Refusing to copy through runtime symlink: ' + str(target))
            if target.is_file():
                before, after = item.stat(), target.stat()
                if (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns):
                    continue
            # Readers of an already running VM keep their old inode. Never
            # truncate a base image underneath QEMU while updating a build.
            descriptor, temporary = tempfile.mkstemp(prefix='.' + item.name + '-', dir=destination)
            os.close(descriptor)
            temporary = Path(temporary)
            try:
                if link_immutable:
                    temporary.unlink()
                    os.link(item, temporary)
                else:
                    shutil.copy2(item, temporary)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
