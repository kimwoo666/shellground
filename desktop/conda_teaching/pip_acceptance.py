"""Wrong final states and equivalent solutions in the learner's actual PTY.

Only this test's disposable environments/files are changed. No production
command parser, simulated pip output, or learner command-history requirement.
"""
import json
import shlex
from .pip_wheel import NUMPY_WHEEL

CASES={
    'pip_install_example':('refused_removal_keeps_install','missing_numpy_rejected','printed_fake_module_rejected',
                           'absolute_python_wheel_install','broken_pip_rejected','same_session_pip_restored'),
    'pip_install_target_selection':('wrong_final_environment','final_environment_repaired',
                                    'archive_numpy_loss','archive_numpy_restored'),
    'pip_install_read_existing':('wrong_package_version','wheel_is_not_location','normalized_location',
                                 'stale_active_answer','active_answer_restored'),
    'pip_remove_example':('numpy_still_installed','metadata_only_loss','actual_uninstall',
                          'native_library_leftover','native_library_removed','empty_namespace_allowed',
                          'environment_removed','environment_recreated'),
    'pip_repair_wrong_environment':('numpy_left_in_writing','wrong_environment_repaired',
                                    'training_tool_lost','training_tool_restored'),
    'pip_repair_broken_installation':('missing_extension','plain_install_not_repair',
                                     'equivalent_force_reinstall','repeat_grade_without_commands'),
}


def check_variants(channel,terminal,mission,answers):
    from .course_smoke import execute_reference
    key=mission['problem']['id']
    if key not in CASES:return []
    result=[]
    def run(*commands,actions=None):
        execute_reference(channel,terminal,list(commands),actions)
    def expect(label,expected=True,values=None):
        grade=channel.request('grade',timeout=125,mission=mission,session=terminal.sid,
                              answers=answers if values is None else values)
        if grade['passed'] is not expected:
            raise AssertionError(key+'/'+label+': '+json.dumps(grade,ensure_ascii=False))
        result.append(key+'/'+label)
        print('REAL_PIP_STATE_PASS '+result[-1],flush=True)
    def pip(name,command):return '/home/learner/conda-envs/'+name+'/bin/python -m pip '+command
    wheel='/opt/shellground/wheels/'+NUMPY_WHEEL['filename']
    install='install --no-index --no-deps '+wheel
    def python(code):return 'python -c '+shlex.quote(code)
    def site(name):return '/home/learner/conda-envs/'+name+'/lib/python3.12/site-packages'
    def hide(name,module):
        # Rename the learner prefix entry; never write through Conda hardlinks.
        run(python("from pathlib import Path;p=Path("+repr(site(name)+'/'+module+'/__init__.py')+
                   ");q=Path('test-module-proof');assert not q.exists();p.rename(q)"))
    def restore(name,module):
        run(python("from pathlib import Path;Path('test-module-proof').rename("+
                   repr(site(name)+'/'+module+'/__init__.py')+")"))
    if key=='pip_install_example':
        command=pip('sg-pip-lab','uninstall numpy')
        run(command,actions=[dict(command=command,exit_codes=[0],responses=[dict(prompt='Proceed (Y/n)?',reply='n')])])
        expect('refused_removal_keeps_install')
        run(pip('sg-pip-lab','uninstall -y numpy'));expect('missing_numpy_rejected',False)
        run(python("from pathlib import Path;Path('numpy.py').write_text('__version__ = \\\'2.3.5\\\'\\n');print('2.3.5');print(7)"))
        expect('printed_fake_module_rejected',False)
        run(python("from pathlib import Path;Path('numpy.py').unlink()"),pip('sg-pip-lab',install))
        expect('absolute_python_wheel_install')
        hide('sg-pip-lab','pip');expect('broken_pip_rejected',False)
        restore('sg-pip-lab','pip');expect('same_session_pip_restored')
    elif key=='pip_install_target_selection':
        run('conda activate sg-pip-archive');expect('wrong_final_environment',False)
        run('conda activate sg-pip-work');expect('final_environment_repaired')
        run(pip('sg-pip-archive','uninstall -y numpy'));expect('archive_numpy_loss',False)
        run(pip('sg-pip-archive',install));expect('archive_numpy_restored')
    elif key=='pip_install_read_existing':
        expect('wrong_package_version',False,dict(answers,numpy_version='3.12'))
        expect('wheel_is_not_location',False,dict(answers,numpy_location='/opt/shellground/wheels'))
        expect('normalized_location',True,dict(answers,numpy_location=answers['numpy_location']+'/./'))
        run('conda deactivate');expect('stale_active_answer',False)
        run('conda activate sg-pip-ready');expect('active_answer_restored')
    elif key=='pip_remove_example':
        run(pip('sg-pip-clean',install));expect('numpy_still_installed',False)
        run(python("from pathlib import Path;p=Path("+repr(site('sg-pip-clean'))+");(p/'numpy-2.3.5.dist-info').rename('test-metadata-proof');lib=next((p/'numpy.libs').iterdir());import shutil;shutil.copy2(lib,'test-native-proof');Path('test-native-path').write_text(str(lib))"))
        expect('metadata_only_loss',False)
        run(python("from pathlib import Path;Path('test-metadata-proof').rename("+repr(site('sg-pip-clean')+'/numpy-2.3.5.dist-info')+")"),
            pip('sg-pip-clean','uninstall -y numpy'))
        expect('actual_uninstall')
        run(python("from pathlib import Path;import shutil;p=Path(Path('test-native-path').read_text());p.parent.mkdir(exist_ok=True);shutil.copy2('test-native-proof',p)"))
        expect('native_library_leftover',False)
        run(python("from pathlib import Path;Path(Path('test-native-path').read_text()).unlink()"));expect('native_library_removed')
        run(python("from pathlib import Path;p=Path("+repr(site('sg-pip-clean'))+");(p/'numpy').mkdir(exist_ok=True);(p/'numpy-2.3.5.dist-info').mkdir(exist_ok=True)"))
        expect('empty_namespace_allowed')
        run('conda deactivate','conda env remove -n sg-pip-clean -y');expect('environment_removed',False)
        run('conda create -n sg-pip-clean python=3.12 pip training-text==1.0 -y','conda activate sg-pip-clean')
        expect('environment_recreated')
    elif key=='pip_repair_wrong_environment':
        run(pip('sg-pip-writing',install));expect('numpy_left_in_writing',False)
        run(pip('sg-pip-writing','uninstall -y numpy'));expect('wrong_environment_repaired')
        hide('sg-pip-analysis','training_math');expect('training_tool_lost',False)
        restore('sg-pip-analysis','training_math');expect('training_tool_restored')
    elif key=='pip_repair_broken_installation':
        run(python("from pathlib import Path;p=Path("+repr(site('sg-pip-repair'))+");next(p.glob('numpy/_core/_multiarray_umath.*.so')).unlink()"))
        expect('missing_extension',False)
        run(pip('sg-pip-repair',install));expect('plain_install_not_repair',False)
        run(pip('sg-pip-repair',install+' --force-reinstall'));expect('equivalent_force_reinstall')
        expect('repeat_grade_without_commands')
    if {value.split('/',1)[1] for value in result}!=set(CASES[key]):
        raise AssertionError('Missing pip final-state coverage')
    return result
