"""Actual Python inside a separately killable Android service process."""
import json
import os
from pathlib import Path
import tempfile
import shutil

_kernel=None
_temporary=None
_unit=None
_variant=None


def dispatch(message,cache_directory):
    global _kernel,_temporary,_unit,_variant
    request=json.loads(message)
    from python_teaching.course import lesson_by_key
    from python_teaching.values import grade_snapshot
    from python_teaching.worker import Kernel,install_guardrails
    key,variant=request['unit'],int(request.get('variant',0))
    unit=lesson_by_key(key)
    problem=unit.problems[variant]
    if _kernel is None:
        # The only interpreter service is a private single process. Its previous
        # process may have been killed mid-cell; remove only our marked sessions.
        cache=Path(cache_directory).resolve()
        for old in list(cache.glob('shellground-python-*'))[:100]:
            if old.is_dir() and not old.is_symlink() and (old/'.shellground-python-session').is_file():
                shutil.rmtree(old)
        _temporary=tempfile.TemporaryDirectory(prefix='shellground-python-',dir=cache_directory)
        root=Path(_temporary.name)
        (root/'.shellground-python-session').write_text('1')
        os.chdir(root)
        os.environ.update(MPLCONFIGDIR=str(root/'.mpl-cache'),XDG_CACHE_HOME=str(root/'.cache'),
            MPLBACKEND='Agg',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        _kernel=Kernel(root)
        # Chaquopy unpacks native modules on first import. Do this trusted setup
        # before learner write restrictions, never grant writes to library dirs.
        import scipy.stats
        import seaborn
        import sklearn.linear_model
        import sklearn.model_selection
        import sklearn.metrics
        import xml.etree.ElementTree
        from PIL import Image
        import codecs
        codecs.lookup('cp949')
        for name,spec in problem.files.items():
            path=(root/name).resolve()
            if not path.is_relative_to(root): raise ValueError('잘못된 실습 파일')
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(spec['text'],encoding=spec.get('encoding','utf-8'))
        install_guardrails(root)
        prepared=_kernel.execute(problem.initial)
        if not prepared['ok']: return json.dumps(prepared,ensure_ascii=False)
        _unit,_variant=key,variant
    if (key,variant)!=(_unit,_variant):
        raise RuntimeError('문제가 바뀌었습니다. 별도 Python 프로세스를 재시작하세요.')
    action=request['action']
    if action=='start': result={'ok':True,'output':'실제 Python 환경이 준비되었습니다.'}
    elif action=='execute':
        result=_kernel.execute(request.get('code',''))
        inspection=_kernel.inspect(problem.targets,problem.probes)
        result['figures']=inspection['figures']
    elif action=='grade':
        values,errors=_kernel.inspect_values(problem.targets,problem.probes)
        result={'ok':True,'grade':grade_snapshot(values,problem.checks),'inspection_errors':errors}
    else: raise ValueError('알 수 없는 작업')
    return json.dumps(result,ensure_ascii=False,allow_nan=False)
