"""Reproducible local wheels; original FreeType sources remain unmodified.

Input: freetype-2.14.3.tar.xz from the official SourceForge distribution,
SHA256 36bc4f1cc413335368ee656c42afca65c5a3987e8768cc28cf11ba775e785a5f.
NDK r27c; 2 compiler jobs. Does not install into the host Python.
"""
import base64
import csv
import hashlib
import io
from pathlib import Path
import subprocess
import zipfile
from verify_android_native import load_alignments

ROOT=Path(__file__).resolve().parent
TOOLS=ROOT/'.android-tools'
VERSION='2.14.3'
SHA='36bc4f1cc413335368ee656c42afca65c5a3987e8768cc28cf11ba775e785a5f'


def build():
    source=TOOLS/f'freetype-{VERSION}'
    archive=TOOLS/f'freetype-{VERSION}.tar.xz'
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA:raise RuntimeError('FreeType source checksum differs')
    ndk=TOOLS/'sdk/ndk/27.2.12479018'
    output=TOOLS/'wheels';output.mkdir(exist_ok=True)
    for abi in ('arm64-v8a','x86_64'):
        target=TOOLS/f'freetype-build-{abi}'
        subprocess.run(['cmake','-S',str(source),'-B',str(target),'-G','Ninja',
            '-DCMAKE_BUILD_TYPE=Release','-DBUILD_SHARED_LIBS=ON',
            '-DCMAKE_TOOLCHAIN_FILE='+str(ndk/'build/cmake/android.toolchain.cmake'),
            '-DANDROID_ABI='+abi,'-DANDROID_PLATFORM=android-24','-DANDROID_SUPPORT_FLEXIBLE_PAGE_SIZES=ON',
            '-DCMAKE_SHARED_LINKER_FLAGS=-Wl,-z,max-page-size=16384',
            *['-DFT_DISABLE_'+name+'=TRUE' for name in ('ZLIB','BZIP2','PNG','HARFBUZZ','BROTLI')]],check=True)
        subprocess.run(['cmake','--build',str(target),'--parallel','2'],check=True)
        library=target/'libfreetype.so'
        if min(load_alignments(library))<16384:raise RuntimeError('FreeType load alignment failed')
        tag='py3-none-android_24_'+abi.replace('-','_')
        info=f'chaquopy_freetype-{VERSION}.dist-info'
        files={
            'chaquopy/lib/libfreetype.so':library.read_bytes(),
            info+'/METADATA':f'Metadata-Version: 2.1\nName: chaquopy-freetype\nVersion: {VERSION}\nSummary: FreeType, Shellground 16KB Android build\nHome-page: https://freetype.org\nLicense: FTL\n'.encode(),
            info+'/WHEEL':f'Wheel-Version: 1.0\nGenerator: shellground\nRoot-Is-Purelib: false\nTag: {tag}\n'.encode(),
            info+'/FTL.TXT':(source/'docs/FTL.TXT').read_bytes(),
            info+'/BUILD.txt':__doc__.encode(),
        }
        record=io.StringIO();writer=csv.writer(record,lineterminator='\n')
        for name,data in files.items():writer.writerow([name,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode(),len(data)])
        writer.writerow([info+'/RECORD','','']);files[info+'/RECORD']=record.getvalue().encode()
        wheel=output/f'chaquopy_freetype-{VERSION}-{tag}.whl'
        with zipfile.ZipFile(wheel,'w',zipfile.ZIP_DEFLATED) as stream:
            for name,data in files.items():stream.writestr(name,data)
        print(wheel)


if __name__=='__main__':build()
