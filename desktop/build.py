"""Run on the target operating system: python build.py."""
from pathlib import Path
import os
import subprocess
import sys
import argparse
from platform_runtime import runtime_tag
from runtime_packaging import copy_runtime_pack
from build_layout import executable_path, runtime_directory, bundle_options

root = Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--dist-dir',type=Path,default=root/'dist')
parser.add_argument('--skip-vm-pack',action='store_true')
parser.add_argument('--with-conda-runtime',action='store_true',help='Bundle the separately verified Conda-capable real runtime')
parser.add_argument('--with-notebook-runtime',action='store_true',help='Bundle verified real Jupyter assets; requires --with-conda-runtime')
parser.add_argument('--runtime-source',type=Path,help='Explicit verified Conda runtime version; requires --with-conda-runtime')
parser.add_argument('--verification',choices=('incremental','full','build-only'),default='incremental',help='Default: new binary checks; full repeats courses; build-only explicitly produces an unexecuted candidate')
parser.add_argument('--link-runtime',action='store_true',help='Local build only: hardlink immutable runtime assets on the same filesystem; never edit source assets in place')
parser.add_argument('--course-manifest',type=Path,help='Explicit versioned incremental course evidence; requires --with-notebook-runtime')
parser.add_argument('--conda-carry-review',type=Path,help='Explicit verified carry for shared shell-only changes; never rewrites old runtime proof')
args=parser.parse_args()
if args.skip_vm_pack and args.with_conda_runtime:parser.error('--skip-vm-pack and --with-conda-runtime cannot be combined')
if args.runtime_source and not args.with_conda_runtime:parser.error('--runtime-source requires --with-conda-runtime')
if args.with_notebook_runtime and not args.with_conda_runtime:parser.error('--with-notebook-runtime requires --with-conda-runtime')
if args.course_manifest and not args.with_notebook_runtime:parser.error('--course-manifest requires --with-notebook-runtime')
if args.conda_carry_review and not args.with_conda_runtime:parser.error('--conda-carry-review requires --with-conda-runtime')
destination=args.dist_dir.resolve()
runtime_name=runtime_tag()
runtime_source = root / ('.vm-runtime-conda' if args.with_conda_runtime else '.vm-runtime') / runtime_name
if args.runtime_source:runtime_source=args.runtime_source.resolve()
if not args.skip_vm_pack and not (runtime_source / 'runtime.json').is_file():
    raise RuntimeError('Runtime pack is absent or retired. Use the current pack with '
                       '--with-conda-runtime --runtime-source PATH (and its matching evidence), '
                       'or explicitly choose --skip-vm-pack for a runtime-free build.')
if args.with_conda_runtime:
    from real_vm import runtime_info
    from conda_teaching.engine import course
    from conda_teaching.export_runtime import validate_report,validate_learning
    from conda_teaching.course_smoke import source_fingerprint
    from conda_teaching.learning_smoke import learning_fingerprint
    from conda_teaching.setup_smoke import validate_setup
    _,runtime_spec=runtime_info(runtime_source)
    if runtime_spec.get('conda_course') is not True:raise RuntimeError('Conda runtime has not passed its course validation gate')
    if args.conda_carry_review:
        if sys.platform == 'win32':
            from windows_build_evidence import validate_guest_carry as validate_carry
        else:
            from conda_teaching.shared_shell_carry import validate as validate_carry
        print(validate_carry(args.conda_carry_review, runtime_source, root), flush=True)
    else:
        validate_report(runtime_spec.get('conda_validation',{}),course(),source_fingerprint())
        validate_learning(runtime_spec.get('conda_learning_validation',{}),course(),source_fingerprint(),learning_fingerprint())
        validate_setup(runtime_spec.get('conda_setup_validation',{}))
extra = []
if args.with_notebook_runtime:
    from notebook_teaching.build_assets import options
    from real_acceptance import validate_directory
    if args.course_manifest:
        from incremental_acceptance import validate_file
        validate_file(args.course_manifest, root)
    else:
        validate_directory(root / '.jupyter-build')
    extra.extend(options(root / '.jupyter-build'))
from build_verification import guest_pip_wheel_required
if guest_pip_wheel_required(sys.platform, args.with_conda_runtime):
    from conda_teaching.pip_assets import wheel_path
    from conda_teaching.pip_wheel import load_numpy_wheel
    wheel=wheel_path();load_numpy_wheel(wheel)
    extra.extend(['--add-data',f'{wheel}:conda_teaching/wheels'])
if sys.platform == 'linux':
    cursor_library = root / '.native-libs/usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0'
    if cursor_library.exists():
        extra.extend(['--add-binary', f'{cursor_library}:.'])
from release_smoke import manifest
import json
destination.mkdir(parents=True, exist_ok=True)
bundle_manifest = destination / 'release-bundle-manifest.json'
with bundle_manifest.open('x', encoding='utf-8') as stream:
    json.dump(manifest(root), stream, ensure_ascii=False, indent=2); stream.write('\n')
extra.extend(['--add-data', f'{bundle_manifest}:.'])
subprocess.run([
    sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', *bundle_options(),
    '--name', 'Shellground', '--distpath', str(destination), '--workpath', str(root / 'build' / runtime_name),
    '--specpath', str(destination / 'build-metadata'), '--paths', str(root), '--add-data', f'{root / "lab"}:lab',
    '--add-data', f'{root / "assets"}:assets', '--collect-all', 'pyte', '--collect-all', 'wcwidth',
    '--add-data', f'{root / "guest" / "bashrc"}:guest',
    '--add-data', f'{root / "guest" / "shell_snapshot.py"}:guest',
    '--add-data', f'{root / "guest" / "ros_lab.py"}:guest',
    '--add-data', f'{root / "guest" / "ros_controls_lab.py"}:guest',
    '--add-data', f'{root / "guest" / "ros_observer.py"}:guest',
    '--add-data', f'{root / "guest" / "apt_lab.py"}:guest',
    '--add-data', f'{root / "guest" / "auth_lab.py"}:guest',
    '--add-data', f'{root / "guest" / "shell_lab.py"}:guest',
    '--add-data', f'{root / "guest" / "process_lab.py"}:guest',
    '--add-data', f'{root / "guest" / "io_lab.py"}:guest',
    '--add-data', f'{root / "guest" / "system_lab.py"}:guest',
    '--add-data', f'{root / "guest" / "docker_lab.py"}:guest',
    '--add-data', f'{root / "guest" / "docker_sessions_lab.py"}:guest',
    '--add-data', f'{root / "guest" / "docker_runtime_lab.py"}:guest',
    '--add-data', f'{root / "conda_teaching" / "course_spec.json"}:conda_teaching',
    '--add-data', f'{root / "conda_teaching" / "pip_course_spec.json"}:conda_teaching',
    '--add-data', f'{root / "conda_teaching" / "pip_runtime.py"}:conda_teaching',
    '--add-data', f'{root / "conda_teaching" / "pip_wheel.py"}:conda_teaching',
    '--add-data', f'{root / "conda_teaching" / "guest_runtime.py"}:conda_teaching',
    '--add-data', f'{root / "conda_teaching" / "guest_files.py"}:conda_teaching',
    '--add-data', f'{root / "conda_teaching" / "setup_runtime.py"}:conda_teaching',
    '--add-data', f'{root / "conda_teaching" / "installer_sources.py"}:conda_teaching',
    '--add-data', f'{root / "python_teaching" / "quiz_bank.json"}:python_teaching',
    '--add-data', f'{root / "python_teaching" / "concept_cards.json"}:python_teaching',
    '--add-data', f'{root / "python_teaching" / "quiz_practice_links.json"}:python_teaching',
    '--add-data', f'{root / "python_teaching" / "linux_docker_concept_draft.json"}:python_teaching',
    '--add-data', f'{root / "python_teaching" / "shell_concept_draft.json"}:python_teaching',
    '--add-data', f'{root / "python_teaching" / "process_concept_draft.json"}:python_teaching',
    '--add-data', f'{root / "python_teaching" / "io_concept_draft.json"}:python_teaching',
    '--add-data', f'{root / "python_teaching" / "system_info_concept_draft.json"}:python_teaching',
    '--hidden-import', 'scipy.stats', '--hidden-import', 'sklearn.linear_model',
    '--hidden-import', 'sklearn.model_selection', '--hidden-import', 'sklearn.metrics',
    '--hidden-import', 'seaborn', '--hidden-import', 'python_teaching.review_validation',
    '--hidden-import', 'matplotlib.backends.backend_agg',
    '--hidden-import', 'matplotlib.backends.backend_svg',
    *extra, str(root / 'shellground.py'),
], check=True)
binary = executable_path(destination)
if not args.skip_vm_pack and (runtime_source / 'runtime.json').is_file():
    runtime_destination = runtime_directory(binary) / runtime_name
    copy_runtime_pack(runtime_source, runtime_destination, link_immutable=args.link_runtime)
    print(f'Bundled runtime directory: {runtime_destination}')
from build_verification import verification_commands
proof_environment = dict(os.environ, SHELLGROUND_TEST_PACKAGED=str(binary), SHELLGROUND_PACKAGED_SCOPE='full' if args.verification=='full' else 'changed')
for command in verification_commands(binary, destination, runtime_directory(binary) / runtime_name, sys.executable,
                                    conda=args.with_conda_runtime, notebook=args.with_notebook_runtime, full=args.verification=='full',
                                    build_only=args.verification=='build-only'):
    subprocess.run(command, cwd=root, env=proof_environment, check=True)
(destination / 'build-status.json').write_text(json.dumps({
    'schema': 1, 'platform': runtime_name, 'executable': str(binary.relative_to(destination)),
    'verification': args.verification, 'artifact_checks_executed': args.verification != 'build-only',
    'native_platform_accepted': False,
    'note': 'Build-only is an unexecuted candidate, not a native-platform test PASS.'
}, indent=2) + '\n', encoding='utf-8')
print(f'Built: {binary}')
