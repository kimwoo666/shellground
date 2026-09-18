"""Read ELF PT_LOAD alignment in staged Android libraries, without executing them."""
from pathlib import Path
import json
import struct
import sys


def load_alignments(path):
    with path.open('rb') as stream:
        header=stream.read(64)
        if header[:4]!=b'\x7fELF':return []
        endian='<' if header[5]==1 else '>'
        if header[4]==2:
            offset=struct.unpack_from(endian+'Q',header,32)[0]
            size,count=struct.unpack_from(endian+'HH',header,54)
            fmt=endian+'IIQQQQQQ'
        else:
            offset=struct.unpack_from(endian+'I',header,28)[0]
            size,count=struct.unpack_from(endian+'HH',header,42)
            fmt=endian+'IIIIIIII'
        values=[]
        for i in range(count):
            stream.seek(offset+i*size); fields=struct.unpack(fmt,stream.read(struct.calcsize(fmt)))
            if fields[0]==1:values.append(fields[-1])
        return values


def inspect(root):
    checked=0; failures=[]
    for path in sorted(Path(root).rglob('*.so')):
        values=load_alignments(path)
        if not values:continue
        checked+=1
        if min(values)<16384:failures.append({'path':str(path),'load_alignments':values})
    return {'checked':checked,'elf_16kb_aligned':bool(checked) and not failures,'failures':failures}


if __name__=='__main__':
    report=inspect(sys.argv[1]);print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(0 if report['elf_16kb_aligned'] else 1)
