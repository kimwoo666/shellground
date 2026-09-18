"""Developer-only Android cross-build; no host install, downloads, or APK claim.

Use an empty mktemp directory for --build-root: upstream autotools require
space-free compiler/prefix paths. Sources and NDK stay in this workspace.
"""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import tarfile

ANDROID=Path(__file__).resolve().parents[1]
WORKSPACE=ANDROID.parent
NATIVE=ANDROID/'.native-runtime'
SOURCES=json.loads(Path(__file__).with_name('native-sources.json').read_text())


def run(argv,cwd,env):
    print('BUILD '+str(cwd.name)+': '+' '.join(map(str,argv)),flush=True)
    subprocess.run(list(map(str,argv)),cwd=cwd,env=env,check=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--abi',choices=('arm64-v8a','x86_64'),required=True)
    parser.add_argument('--build-root',type=Path,required=True)
    args=parser.parse_args()
    root=args.build_root.resolve()
    if not root.is_dir() or root.parent!=Path('/tmp') or not root.name.startswith('shellground-android-native.') or any(c.isspace() for c in str(root)):
        raise ValueError('Use a private mktemp -d /tmp/shellground-android-native.XXXXXX directory')
    marker=root/'owner.json';owner={'workspace':str(WORKSPACE),'kind':'shellground-android-native'}
    if marker.exists():
        if json.loads(marker.read_text())!=owner:raise ValueError('Unknown build directory')
    elif any(root.iterdir()):raise ValueError('New build directory must be empty')
    else:marker.write_text(json.dumps(owner)+'\n')
    try:os.nice(15)
    except OSError:pass
    ndk=WORKSPACE/'desktop/.android-tools/sdk/ndk/27.2.12479018'
    for label,target in (('ndk',ndk),('sources',NATIVE)):
        link=root/label
        if link.is_symlink():
            if link.resolve()!=target.resolve():raise ValueError('Unexpected tool link')
        else:link.symlink_to(target,target_is_directory=True)
    for name in ('libffi','pcre2','glib','proxy-libintl','dtc'):
        spec=SOURCES[name];archive=NATIVE/'downloads'/spec['archive']
        with archive.open('rb') as source:
            if hashlib.file_digest(source,'sha256').hexdigest()!=spec['sha256']:raise ValueError('Source checksum mismatch: '+name)
        target=NATIVE/(name+'-'+spec['version'])
        if not target.exists():
            with tarfile.open(archive) as source:source.extractall(NATIVE,filter='data')
    cache=NATIVE/('glib-'+SOURCES['glib']['version'])/'subprojects/packagecache';cache.mkdir(exist_ok=True)
    shutil.copy2(NATIVE/'downloads'/SOURCES['proxy-libintl']['archive'],cache/SOURCES['proxy-libintl']['archive'])
    triple,cpu=('aarch64-linux-android','aarch64') if args.abi=='arm64-v8a' else ('x86_64-linux-android','x86_64')
    binpath=root/'ndk/toolchains/llvm/prebuilt/linux-x86_64/bin'
    build=root/args.abi;build.mkdir(exist_ok=True);prefix=build/'prefix';prefix.mkdir(exist_ok=True)
    tools={'CC':binpath/(triple+'28-clang'),'CXX':binpath/(triple+'28-clang++'),'AR':binpath/'llvm-ar','RANLIB':binpath/'llvm-ranlib','STRIP':binpath/'llvm-strip'}
    env=dict(os.environ,**{k:str(v) for k,v in tools.items()},CFLAGS='-O2 -fPIC',LDFLAGS='-Wl,-z,max-page-size=16384',
             PKG_CONFIG_LIBDIR=str(prefix/'lib/pkgconfig'),PKG_CONFIG_PATH='',LC_ALL='C.UTF-8')
    env.pop('CONFIG_SITE',None)
    for name,options in (('libffi',['--disable-multi-os-directory']),
                         ('pcre2',['--disable-pcre2grep','--disable-pcre2test','--disable-jit'])):
        source=root/'sources'/(name+'-'+SOURCES[name]['version']);output=build/name;output.mkdir(exist_ok=True)
        run([source/'configure','--host='+triple,'--prefix='+str(prefix),'--libdir='+str(prefix/'lib'),
             '--disable-shared','--enable-static',*options],output,env)
        run(['make','-j2'],output,env);run(['make','install'],output,env)
    cross=build/'android.ini'
    cross.write_text('[binaries]\n'+''.join(f'{key} = {str(tools[value])!r}\n' for key,value in [('c','CC'),('cpp','CXX'),('ar','AR'),('strip','STRIP')])+
                     "pkg-config = '/usr/bin/pkg-config'\n[host_machine]\nsystem = 'android'\n"+
                     f"cpu_family = '{cpu}'\ncpu = '{cpu}'\nendian = 'little'\n"+
                     "[properties]\nneeds_exe_wrapper = true\n[built-in options]\n"+
                     f"pkg_config_path = ['{prefix}/lib/pkgconfig']\nc_args = ['-O2', '-fPIC', '-D__BIONIC__=1']\n"+
                     "c_link_args = ['-Wl,-z,max-page-size=16384']\n")
    meson=root/'sources/build-tools/bin/meson';source=root/'sources'/('glib-'+SOURCES['glib']['version']);output=build/'glib'
    command=[meson,'setup',output,source,'--cross-file',cross,'--prefix',prefix,'--libdir','lib',
             '--wrap-mode=nodownload','--default-library=static','-Dtests=false','-Dintrospection=disabled','-Dnls=disabled',
             '-Dlibmount=disabled','-Dselinux=disabled','-Dlibelf=disabled','-Dman-pages=disabled']
    if (output/'build.ninja').exists():command.append('--reconfigure')
    run(command,build,env);run(['ninja','-C',output,'-j2'],build,env);run(['ninja','-C',output,'install'],build,env)
    source=root/'sources'/('dtc-'+SOURCES['dtc']['version']);output=build/'dtc'
    command=[meson,'setup',output,source,'--cross-file',cross,'--prefix',prefix,'--libdir','lib',
             '--wrap-mode=nodownload','--default-library=static','-Dtests=false','-Dtools=false','-Dpython=disabled','-Dyaml=disabled']
    if (output/'build.ninja').exists():command.append('--reconfigure')
    run(command,build,env);run(['ninja','-C',output,'-j2'],build,env);run(['ninja','-C',output,'install'],build,env)
    report={'abi':args.abi,'api':28,'ndk':'27.2.12479018','build_root':str(root),'prefix':str(prefix),
            'sources':{name:SOURCES[name] for name in ('libffi','pcre2','glib','proxy-libintl','dtc')},'evidence':'cross-build only; no device execution'}
    (NATIVE/('dependencies-'+args.abi+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    print('ANDROID_NATIVE_DEPENDENCIES_BUILT '+args.abi,flush=True)


if __name__=='__main__':main()
