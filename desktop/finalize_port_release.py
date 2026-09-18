"""Keep a final APK and honest compact receipts after new port checks pass."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'releases'


def digest(path):
    with path.open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()


def main():
    if '--capture-notebook' in sys.argv:return capture_notebook()
    log=ROOT/'android/.port-checks/real-port-final.log'
    text=log.read_text()
    carry=json.loads((ROOT/'android/.port-checks/notebook-carry.json').read_text())
    if carry['evidence_sha256']!=digest(log) or not carry['jupyter_passed']:
        raise ValueError('Notebook evidence changed')
    for name,sha in carry['unchanged_sources'].items():
        if digest(ROOT/name)!=sha:raise ValueError('Recheck affected notebook source: '+name)
    conda=(ROOT/'android/.port-checks/conda-final.log').read_text()
    if 'FAILURES!!!' in conda or not re.search(r'OK \(1 test\)',conda):
        raise ValueError('New Conda boundary must pass before finalizing')
    original=ROOT/'android/app/build/outputs/apk/debug/app-debug.apk'
    apk=OUT/'Shellground-4.7.4-Android.apk'
    if apk.exists():
        if not os.path.samefile(apk,original):raise FileExistsError(apk)
    else:os.link(original,apk)
    data=dict(schema=1,artifact=apk.name,bytes=apk.stat().st_size,sha256=digest(apk),
        version='4.7.4',new_real_port_tests_passed=True,native_arm_phone_executed=False,
        windows_executed=False,full_curriculum_rerun=False,
        emulator=dict(android='15',api=35,abi='x86_64',guest_architecture='aarch64',
            host_cpu_quota_percent=dict(jupyter=55,conda=[100,120]),
            host_quota_note='resource-limited emulator on an 8-thread host; not phone performance'),
        newly_executed=['actual Jupyter kernel selection, execution, failed-grade retry, save, cleanup',
            'actual Conda version command, failed-grade retry, cleanup'],
        reused_current_turn_checks=['notebook Shift+Enter without extra newline','current port catalogs',
            'four new pandas units / twelve reference problems'],
        initial_delta_batch='Three checks passed. Its Jupyter startup failure was fixed and rerun separately.',
        export_boundary_checks='Six targeted source/export checks passed; no full course replay.',
        jupyter_carry=carry,
        final_conda_only_delta='Sync conda_lab.py before lazy guest import; notebook assets and branch unchanged.',
        conda_recheck_seconds=float(re.search(r'Time: ([\d.,]+)',conda).group(1).replace(',','')),
        signing='existing private development key; not a store-reviewed release')
    (OUT/'android-build.json').write_text(json.dumps(data,indent=2)+'\n')
    pc=json.loads((OUT/'pc-build.json').read_text())
    records=[pc['linux'],pc['windows'],*pc['shared_disk']['parts'],dict(name=apk.name,sha256=data['sha256'])]
    for name in ('Shellground-4.7.4-Native-Sources.tar','Join-Windows.cmd','Join-Linux.sh','pc-build.json','android-build.json'):
        records.append(dict(name=name,sha256=digest(OUT/name)))
    (OUT/'SHA256SUMS.txt').write_text(''.join(f'{r["sha256"]}  {r["name"]}\n' for r in records))
    print(json.dumps(dict(apk_bytes=data['bytes'],apk_sha256=data['sha256'],real_port_tests=2,passed=True)))


def capture_notebook():
    log=ROOT/'android/.port-checks/real-port-final.log';text=log.read_text()
    if ('Tests run: 2,  Failures: 1' not in text or
        'Error in actualCondaVersionRetryAndCleanup' not in text or
        'Error in actualNotebookKernelRetrySaveAndCleanup' in text):
        raise ValueError('Expected the observed one-pass/one-Conda-failure batch')
    names=['android/app/src/main/java/org/shellground/learn/'+name for name in
        ('NotebookGuest.java','NotebookEditor.java','LinuxActivity.java','GuestAssets.java')]
    names+=['android/app/build/generated/portAssets/notebook-guest/'+name for name in
        ('guest_setup.py','guest_service.py','guest_lessons.py')]
    record=dict(jupyter_passed=True,conda_passed=False,evidence_sha256=digest(log),
        unchanged_sources={name:digest(ROOT/name) for name in names},
        shared_service_delta='Only non-notebook prepare timeout changed from180s to360s; notebook branch unchanged.',
        reason='Do not rerun completed Jupyter checks for a Conda-only fix')
    (ROOT/'android/.port-checks/notebook-carry.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Captured successful Jupyter evidence and unchanged source identities')


if __name__=='__main__':main()
