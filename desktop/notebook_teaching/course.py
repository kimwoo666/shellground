"""Native notebook lessons: real kernels, not a second Python simulator.

Week 1_1 physical p11 introduces live kernels and cells; p13–15 introduces
local environments. Registration, recovery and pip targeting are explicitly
authored practical supplements, not quotations from the lecture.
"""
from copy import deepcopy

ENV = '/home/learner/notebook-envs/'
REGISTRY = '/home/learner/notebook-jupyter'
DIAGNOSTIC = 'import sys\nprint(sys.executable)\nprint(sys.prefix)'
INSTALL = '-m pip install --no-index --find-links /opt/shellground/wheels numpy==2.3.5'
ENV_GUIDE = ('기초 환경: '+ENV+'basic (NumPy 없음)\n분석 환경: '+ENV+'data (NumPy 2.3.5)\n'
    '두 환경에는 Python 3.12와 ipykernel이 있습니다. 환경 이름과 경로를 비교하세요.\n'
    '등록 위치: '+REGISTRY+' · 작업 위치: /home/learner/notebook-work\n'
    '코드는 노트북 셀, conda/python -m 명령은 Bash 탭에 입력합니다. '
    '소단계 위치·완료만 자동 저장하며, 종료 시 임시 문서·환경은 사라집니다.')


def cells(*sources, note='실습 메모'):
    return [dict(id='note', type='markdown', source=note)] + [
        dict(id=f'cell{i+1}', type='code', source=source) for i, source in enumerate(sources)]


def register(name, env='data'):
    return f'{ENV}{env}/bin/python -m ipykernel install --prefix {REGISTRY} --name {name} --display-name "프로젝트 Python"'


def problem(goal, sources, expected, solution, *, target='basic', start='sg-basic', **extra):
    return dict(goal=goal, cells=cells(*sources), expected=expected,
                solution=cells(*solution), target=target, start=start,
                numpy_basic=False, preserve=('sg-basic','sg-data'), **extra)


def lessons():
    units = [
        dict(key='jupyter_select', title='문서와 실행할 Python 구분', source='Week 1_1.pdf · 실제 11–15쪽',
             hint='Python 버전이 같아도 sys.prefix가 다르면 별도 환경입니다. NumPy가 준비된 data를 구분하세요.',
             steps=[
                 ('코드 셀과 설명 셀', '노트북은 코드와 Markdown 설명을 함께 담는 문서입니다. 코드 셀을 선택해 실행하면 별도 커널이 계산합니다. Markdown은 Python 코드가 아닙니다.\n첫 코드 셀에서 다음 진단을 직접 실행하세요.\n'+DIAGNOSTIC),
                 ('어느 Python이 계산하는가', 'sys.executable은 Python 실행파일, sys.prefix는 그 환경의 위치입니다. 터미널의 Python과 노트북 커널은 별개입니다. 위 환경 표와 출력 경로를 비교하세요. 아직 NumPy가 없는 basic에서 import하면 ModuleNotFoundError가 나는 것이 정상입니다.'),
                 ('준비된 커널 선택', '커널 목록에서 Python (data)를 선택한 뒤 계산 셀을 실행하세요. 이 앱은 전환할 때 새 커널을 시작합니다. 셀 코드는 남고 이전 변수는 가져오지 않습니다. 일반 Jupyter의 기존 커널 재연결까지 항상 초기화된다고 일반화하지 마세요.')],
             problems=[
                 problem('이미 준비된 분석 환경 data에서 total에 [2, 5]의 NumPy 합을 계산하세요. 두 환경의 패키지는 변경하지 마세요.',
                     [DIAGNOSTIC,'import numpy as np\ntotal = int(np.array([2, 5]).sum())'], {'total':7},
                     [DIAGNOSTIC,'import numpy as np\ntotal = int(np.array([2, 5]).sum())'], target='data', numpy_result=True),
                 problem('기초 환경 basic을 선택하여 width=6, height=4인 직사각형의 area를 계산하세요. 패키지는 변경하지 마세요.',
                     ['width = 6\nheight = 4\narea = width * height'], {'width':6,'height':4,'area':24},
                     ['width = 6\nheight = 4\narea = width * height'], start='sg-data'),
                 problem('두 Python은 버전이 같습니다. 실행 경로가 '+ENV+'data인 커널을 선택하고 values=[3, 7]의 합을 result에 담으세요. 패키지는 변경하지 마세요.',
                     [DIAGNOSTIC,'values = [3, 7]\nresult = sum(values)'], {'values':[3,7],'result':10},
                     [DIAGNOSTIC,'values = [3, 7]\nresult = sum(values)'], target='data'),
             ]),
        dict(key='jupyter_order', title='셀 편집·실행·계산 순서', source='Week 1_1.pdf · 실제 11쪽 + 재현성 보충',
             hint='편집만으로 변수는 바뀌지 않습니다. 입력 정의 → 계산 순서로 문서를 구성하세요. 이미 계산된 값은 자동 갱신되지 않습니다.',
             steps=[
                 ('마지막으로 실행한 값', '준비된 상태는 price=8, total=24입니다. 첫 셀의 price를 10으로 편집만 한 뒤 다른 셀에서 print(price, total)을 실행해 보세요. 편집과 실행은 다릅니다.'),
                 ('의존 셀도 다시 실행', 'price=10 셀을 실행해도 과거 total은 24입니다. total=price*3 셀까지 실행해야 30이 됩니다. In[ ]은 실행 순서이며 문서의 줄 번호가 아닙니다.'),
                 ('위에서 아래로 재현', '정의가 사용보다 먼저 오게 셀을 이동하거나 필요한 정의를 앞에 추가하세요. 지금 커널에 우연히 남아 있는 변수로만 성공하는 문서는 새 커널에서 실패합니다. 채점의 재현 검사는 별도 임시 커널에서 문서를 실행하며 현재 커널을 바꾸지 않습니다.'),
                 ('반복 실행의 부작용', 'items.append(7)은 실행할 때마다 원본 목록을 바꿉니다. 원본을 유지하려면 result=items+[7]처럼 새 결과를 만들 수 있습니다. 활용2는 새 커널에서 각 코드 셀을 위에서 아래로, 한 셀마다 연속 두 번씩 실행해도 문서 마지막의 원본과 결과가 같아야 합니다. 맨 끝의 출력 셀만 두 번 실행하는 검사가 아닙니다.')],
             problems=[
                 problem('price를 8에서 10으로 바꾸고 total=price*3을 다시 계산하여 total=30을 만드세요. 문서도 위에서 아래로 재현 가능해야 합니다.',
                     ['price = 8','total = price * 3'], {'price':10,'total':30}, ['price = 10','total = price * 3'], seed='price=8\ntotal=price*3', replay=True),
                 problem('정의보다 사용이 앞선 문서를 고치세요. unit_price=7, quantity=4로 subtotal=28을 계산하고 새 커널에서도 문서 순서대로 재현되게 하세요.',
                     ['subtotal = unit_price * quantity','unit_price = 7\nquantity = 4'], {'unit_price':7,'quantity':4,'subtotal':28},
                     ['unit_price = 7\nquantity = 4','subtotal = unit_price * quantity'], replay=True),
                 problem('원본 items를 [2, 5]로 복구·유지하세요. 새 커널에서 각 코드 셀을 문서 순서대로 한 번씩 실행한 경우와, 한 셀마다 연속 두 번씩 실행한 경우 모두 최종 result=[2, 5, 7], total=14가 되도록 고치세요.',
                     ['items = [2, 5]','items.append(7)\ntotal = sum(items)'], {'items':[2,5],'result':[2,5,7],'total':14},
                     ['items = [2, 5]','result = items + [7]\ntotal = sum(result)'], seed='items=[2,5,7,7]\ntotal=sum(items)', replay=True, repeat_cells=True),
             ]),
        dict(key='jupyter_restart', title='재시작과 문서 재현', source='Week 1_1.pdf · 실제 11쪽 + 복구 보충',
             hint='출력 지우기나 del은 커널 재시작이 아닙니다. 재시작 후 문서의 입력 정의부터 다시 실행하세요. 코드 셀과 파일은 커널 메모리와 다릅니다.',
             steps=[
                 ('코드와 메모리', '준비된 커널에는 문서 밖 임시 변수 scratch=99가 있습니다. 코드 셀과 메모리의 현재 값은 다릅니다. print(scratch)를 실행해 확인하세요.'),
                 ('같은 환경 재시작', '커널 재시작을 선택하세요. 코드·설명·파일은 남지만 변수는 없어집니다. print(scratch)는 이제 NameError입니다. 출력 지우기는 화면만 지우며 메모리를 초기화하지 않습니다.'),
                 ('문서만으로 재실행', '입력 셀부터 전체 실행하여 total=48을 다시 만드세요. 셀에 없는 과거 변수에 의존하면 새 커널에서 실패합니다. 입력 셀을 고치고 다시 실행할 수 있습니다.'),
                 ('문서 저장의 범위', '문서 저장은 작업 폴더에 표준 .ipynb를 만듭니다. 코드·Markdown과 현재 커널에서 해당 코드로 실행한 출력만 저장하며, 편집 전·이전 커널의 오래된 출력은 제외합니다. 살아 있는 변수 전체를 저장하지는 않습니다. 커널 재시작은 이 파일을 지우지 않습니다. 앱 종료·실습 전체 초기화는 임시 파일도 지웁니다.')],
             problems=[
                 problem('같은 basic 환경의 커널을 재시작하세요. 문서에 없는 scratch는 없어야 합니다. price=12, count=4로 total=48을 문서에서 다시 계산하세요.',
                     ['price = 12\ncount = 4','total = price * count'], {'price':12,'count':4,'total':48},
                     ['price = 12\ncount = 4','total = price * count'], seed='scratch=99\nprice=12\ncount=4\ntotal=48', restart=True, absent=['scratch'], replay=True),
                 problem('현재 메모리에는 price=9, count=3이 있지만 문서에는 없습니다. 입력 정의를 문서에 남기고 같은 basic 커널을 재시작하여 total=27을 다시 만드세요. 새 문서 실행만으로도 재현되어야 합니다.',
                     ['total = price * count'], {'price':9,'count':3,'total':27}, ['price = 9\ncount = 3\ntotal = price * count'],
                     seed='price=9\ncount=3\ntotal=27', restart=True, replay=True),
                 problem('Markdown 메모에 분석 목적을 적으세요(기본 메모 문구는 바꾸세요). basic 커널을 재시작한 뒤 제공된 source.txt를 수정하지 않고 읽어 result에 글자 수 6을 담으세요. 문서를 report.ipynb로 저장하세요.',
                     ["from pathlib import Path\ntext = Path('source.txt').read_text()\nresult = len(text)"], {'result':6},
                     ["from pathlib import Path\ntext = Path('source.txt').read_text()\nresult = len(text)"], restart=True,
                     files={'source.txt':'hello\n'}, markdown=True, save='report.ipynb', replay=True),
             ]),
        dict(key='jupyter_register', title='환경을 커널 목록에 등록', source='Week 1_1.pdf · 환경 선택의 실사용 보충',
             hint='환경을 새로 만들 필요는 없습니다. data/bin/python -m ipykernel install로 지정한 name을 등록하고 새로 고침 후 선택하세요.',
             steps=[
                 ('활성 환경과 커널은 별개', 'Bash에서 다음을 실행해 분석 환경을 선택하세요.\nconda activate '+ENV+'data\npython -c "import sys; print(sys.executable)"\n터미널 활성화는 열린 노트북의 커널을 자동 변경하지 않습니다.'),
                 ('이미 있는 환경 등록', 'ipykernel은 이미 설치되어 있습니다. 다음 명령은 환경을 만드는 것이 아니라 그 Python을 커널 목록에 등록합니다.\n'+register('analysis-project')+'\n--prefix: kernelspec 파일 설치 위치(새 Conda 환경 위치가 아님)\n--name: 고유 식별자\n--display-name: 화면에 보일 이름'),
                 ('목록 새로 고침과 선택', '커널 목록 새로 고침 후 analysis-project를 선택하세요. 표시 이름만 믿지 말고 셀에서 sys.executable을 확인하세요. 같은 --name으로 등록하면 이전 항목을 바꿀 수 있습니다.'),
                 ('보존해야 할 등록', '한 환경을 여러 프로젝트 이름으로 등록할 수 있습니다. 새 이름은 별도 Python 환경을 만들지 않습니다. 기본 sg-basic, sg-data 등록을 유지하라는 목표가 있으면 기존 이름을 덮어쓰지 마세요.')],
             problems=[
                 problem('data 환경을 analysis-project 이름으로 '+REGISTRY+'에 등록·선택하여 result=6*7을 실행하세요. 기존 sg-basic 등록은 보존하세요. data 환경은 있고 sg-data 등록만 없는 상태입니다.',
                     ['result = 6 * 7'], {'result':42}, ['result = 6 * 7'], target='data',
                     hidden_data=True, registration='analysis-project', commands=[register('analysis-project')]),
                 problem('analysis-project는 표시 이름과 달리 basic을 가리킵니다. 같은 등록을 data 환경으로 고치고 선택하여 NumPy [4, 9]의 합 result=13을 계산하세요. sg-basic, sg-data는 그대로 유지하세요.',
                     ['import numpy as np\nresult = int(np.array([4, 9]).sum())'], {'result':13},
                     ['import numpy as np\nresult = int(np.array([4, 9]).sum())'], target='data',
                     misregistered=True, registration='analysis-project', numpy_result=True, commands=[register('analysis-project')]),
                 problem('기존 sg-basic, sg-data 등록을 유지하면서 data 환경을 report-project라는 별도 이름으로 '+REGISTRY+'에 등록하세요. 그 커널에서 values=[8, 3, 5]의 최댓값 result를 계산하세요.',
                     ['values = [8, 3, 5]\nresult = max(values)'], {'values':[8,3,5],'result':8},
                     ['values = [8, 3, 5]\nresult = max(values)'], target='data', registration='report-project', commands=[register('report-project')]),
             ]),
        dict(key='jupyter_package_target', title='설치한 환경과 실행 환경 맞추기', source='환경 관리·pip 실사용 보충',
             hint='Bash의 활성화와 커널 선택은 별개입니다. 이미 설치된 data를 쓸지, 지정된 basic에 설치할지 목표부터 확인하세요.',
             steps=[
                 ('터미널과 노트북 비교', 'Bash는 data, 노트북은 basic으로 시작합니다. Bash에서 python -c "import sys; print(sys.executable)"를 실행하고 노트북의 sys.executable과 비교하세요. 같은 python 표기라도 실제 경로가 다를 수 있습니다.'),
                 ('이미 설치된 환경 선택', 'NumPy를 사용한다는 이유만으로 설치부터 하지 마세요. 예시 목표는 준비된 data를 선택하는 것입니다. 설치와 import는 다르며 선택한 환경에 있는 패키지만 import됩니다.'),
                 ('지정 환경에 설치할 때', '활용1처럼 basic을 써야 한다면 Bash에서 대상 Python을 지정하세요.\n'+ENV+'basic/bin/python '+INSTALL+'\n--no-index는 온라인 인덱스를 조회하지 않고, --find-links는 준비된 공식 wheel 폴더를 지정합니다. 2.3.5는 연습용 고정 버전입니다. 설치는 np라는 변수를 만들지 않습니다.'),
                 ('새 커널에서 설치 위치 확인', '설치한 환경의 커널을 재시작한 뒤 import numpy as np와 print(np.__file__)로 확인하세요. 캐시 없이 확인하려는 절차이지 모든 최초 설치 뒤 재시작이 필수라는 뜻은 아닙니다. %pip는 현재 커널의 Python을 대상으로 하는 IPython 기능입니다.')],
             problems=[
                 problem('Bash는 data, 노트북은 basic입니다. 두 환경의 패키지를 변경하지 말고 기존 data 커널에서 NumPy [3, 6]의 평균 result=4.5를 계산하세요.',
                     [DIAGNOSTIC,'import numpy as np\nresult = float(np.mean([3, 6]))'], {'result':4.5},
                     [DIAGNOSTIC,'import numpy as np\nresult = float(np.mean([3, 6]))'], target='data', numpy_result=True),
                 problem('이 프로젝트는 basic을 사용해야 합니다. basic에 준비된 공식 NumPy 2.3.5를 설치하고 basic 커널을 재시작하여 [2, 4, 6] 평균 result=4를 계산하세요. data의 NumPy와 두 기본 등록은 유지하세요.',
                     ['import numpy as np\nresult = float(np.mean([2, 4, 6]))'], {'result':4},
                     ['import numpy as np\nresult = float(np.mean([2, 4, 6]))'], install_basic=True, restart=True,
                     numpy_result=True, commands=[ENV+'basic/bin/python '+INSTALL]),
                 problem('이번에는 두 환경 모두 NumPy 2.3.5가 있습니다. 패키지를 바꾸지 말고 data 커널에서 np.__file__을 module_path에 기록하고 np.arange(4)의 합 result=6을 계산하세요. 설치 위치는 data 환경 내부여야 합니다.',
                     [DIAGNOSTIC,'import numpy as np\nmodule_path = np.__file__\nresult = int(np.arange(4).sum())'], {'result':6},
                     [DIAGNOSTIC,'import numpy as np\nmodule_path = np.__file__\nresult = int(np.arange(4).sum())'], target='data', both_numpy=True, numpy_result=True, module_path=True),
             ]),
    ]
    review = dict(key='review_jupyter_01', title='01–05 종합 복습', source='직전 다섯 단원의 조합 문제',
                  hint='등록된 Python 경로 → 새 커널 → 입력 정의 → 계산 → 문서 저장 순으로 결과를 점검하세요.',
                  steps=[('실행 환경과 문서의 재현성', '다섯 단원을 조합합니다. 셀의 값만 맞추지 말고 어떤 환경에서 새 문서 실행으로 만들어지는지 확인하세요. 패키지 설치와 등록은 서로 다릅니다.'),
                         ('결과를 남기는 순서', '올바른 커널에서 입력 정의부터 계산을 실행하고, 필요한 메모를 적은 뒤 문서를 저장하세요. 저장된 출력만으로 현재 커널 결과를 대신할 수 없습니다.')],
                  problems=[])
    for index in range(3):
        base = deepcopy(units[3]['problems'][index])
        base.update(restart=True, replay=True, markdown=True, save='report.ipynb')
        base['goal'] += ' 선택한 data 커널을 한 번 재시작하고 문서 순서대로 재실행하세요. 기본 문구 대신 목적을 적은 Markdown 메모와 함께 report.ipynb로 저장하세요.'
        base['solution'][0]['source'] = '분석 환경에서 계산한 프로젝트 결과를 기록합니다.'
        review['problems'].append(base)
    units.append(review)
    for unit in units:
        for item in unit['problems']:
            if unit['key']=='jupyter_order':
                item['allowed_environments'] = ('basic','data')
                item['goal'] += ' basic 또는 data 중 어느 커널을 사용해도 됩니다.'
            if item.get('hidden_data'): item['preserve'] = ('sg-basic',)
            if item.get('markdown'): item['solution'][0]['source'] = '원본을 보존하며 계산 결과를 확인합니다.'
            item['goal'] += '\n목표 변수는 현재 커널에 남기세요.'
    return units
