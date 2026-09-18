"""Validate Android executable metadata; this is not a device boot test."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

MACHINES = {'arm64-v8a': 'AArch64', 'x86_64': 'Advanced Micro Devices X86-64'}
SYSTEM_LIBRARIES = {'libc.so', 'libm.so', 'libdl.so', 'liblog.so', 'libandroid.so', 'libz.so'}


def validate_elf(text, abi):
    if abi not in MACHINES:
        raise ValueError('Unsupported ABI: ' + abi)
    machine = re.search(r'^\s*Machine:\s*(.+)$', text, re.M)
    if not machine or machine.group(1).strip() != MACHINES[abi]:
        raise ValueError('ELF machine does not match Android host ABI')
    if not re.search(r'^\s*Type:\s+DYN\b', text, re.M):
        raise ValueError('Android candidate must be a position-independent executable')
    if '[Requesting program interpreter: /system/bin/linker64]' not in text:
        raise ValueError('Candidate must use the Android system linker')
    loads = re.findall(r'^\s*LOAD\s+(.+)$', text, re.M)
    if not loads:
        raise ValueError('No ELF load segments')
    alignments = []
    for row in loads:
        fields = row.split()
        if len(fields) < 7:
            raise ValueError('Expected wide readelf program headers')
        offset, address = int(fields[0], 16), int(fields[1], 16)
        alignment = int(fields[-1], 16)
        if alignment < 16384 or alignment & (alignment - 1) or offset % 16384 != address % 16384:
            raise ValueError('ELF load segment is not 16KB page compatible')
        alignments.append(alignment)
    needed = sorted(set(re.findall(r'\(NEEDED\).*?\[([^\]]+)\]', text)))
    if not needed or set(needed) - SYSTEM_LIBRARIES:
        raise ValueError('Unbundled or unexpected Android libraries: ' + repr(needed))
    if re.search(r'\((?:RPATH|RUNPATH|TEXTREL)\)', text):
        raise ValueError('Candidate contains a runtime search path or text relocations')
    return {'host_abi': abi, 'machine': machine.group(1).strip(),
            'interpreter': '/system/bin/linker64', 'load_alignments': alignments,
            'needed_system_libraries': needed, 'elf_16kb_aligned': True,
            'evidence': 'ELF metadata only; Android execution and Linux boot are separate gates'}


def inspect(binary, readelf, abi):
    text = subprocess.check_output([str(readelf), '--wide', '-h', '-l', '-d', str(binary)], text=True)
    report = validate_elf(text, abi)
    report['sha256'] = hashlib.sha256(binary.read_bytes()).hexdigest()
    return report, text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--abi', choices=tuple(MACHINES), required=True)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--readelf', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.binary, args.readelf, args.abi)[0], indent=2))


if __name__ == '__main__':
    main()
