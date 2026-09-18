"""Authored five-unit reviews; importing this module needs no scientific packages.

Only original units count toward a block. Each review has an example followed by
two different applications, and tests actual values/objects rather than spelling
one approved solution. The input lesson instances and their order are preserved.
"""
from math import exp, pi, sqrt
from textwrap import dedent

from .model import Lesson, problem as P, check as C, array as A, frame as F, series as S

NP = 'import numpy as np\n'
PLT = NP + 'import matplotlib.pyplot as plt\n'
PD = NP + 'import pandas as pd\n'
NAN = {'special': 'nan'}


def _code(text):
    return dedent(text).strip()


def _problem(goal, initial, solution, checks, hint, **kwargs):
    # Feedback is shown after submission, not as an answer in the task goal.
    checks = tuple(dict(check, feedback=hint) for check in checks)
    return P(goal, _code(initial), _code(solution), checks, **kwargs)


def _ax(value, path, number=0):
    return C('fig', value, ['axes_by_position', number, *path])


def _figure(count):
    return (C('fig', 'figure', ['kind']), C('fig', count, ['axis_count']))


def _line(x, y, axes=0, number=0):
    return (_ax(x, ['lines', number, 'x', 'data'], axes),
            _ax(y, ['lines', number, 'y', 'data'], axes))


def _bars(heights, centers, width=.8, axes=0):
    checks = [_ax(len(heights), ['patch_count'], axes)]
    for index, (height, center) in enumerate(zip(heights, centers)):
        for name, value in (('x', center-width/2), ('y', 0), ('width', width), ('height', height)):
            checks.append(_ax(value, ['patches', index, name], axes))
    return tuple(checks)


def _png(name, width, height):
    return (C('__files__', 'png', [name, 'kind']),
            C('__files__', width, [name, 'width']), C('__files__', height, [name, 'height']),
            C('__files__', True, [name, 'matches_fig'], '파일이 실제 fig와 일치'))


def _normal_values(xs, mean, std):
    return [exp(-.5*((x-mean)/std)**2)/(std*sqrt(2*pi)) for x in xs]


def _py_01():
    return (
        _problem(
            'prices는 보존하고 오름차순 ordered를 만드세요. 가운데 가격을 선택해 order의 수량만큼 total을 계산하고 order에 total 키를 추가하세요.',
            "prices=[8,3,5]\norder={'item':'notebook','count':4}",
            "ordered=sorted(prices)\ntotal=ordered[1]*order['count']\norder['total']=total",
            (C('prices',[8,3,5]),C('ordered',[3,5,8]),C('total',20),
             C('order',{'item':'notebook','count':4,'total':20})),
            '원본을 바꾸는 정렬과 새 목록을 받는 정렬을 구분하고, 순서가 정해진 뒤 가운데 위치를 읽으세요.'),
        _problem(
            'measurements에 새 측정값 6을 추가한 뒤 목록 자체를 정렬하세요. 정렬 메서드의 반환값을 returned에 남기고, summary에 low·high·spread를 저장하세요.',
            'measurements=[9,2,7]',
            "measurements.append(6)\nreturned=measurements.sort()\nsummary={'low':measurements[0],'high':measurements[-1],'spread':measurements[-1]-measurements[0]}",
            (C('measurements',[2,6,7,9]),C('returned',None),C('summary',{'low':2,'high':9,'spread':7})),
            '정렬된 목록과 메서드가 반환한 값은 다릅니다. 양 끝의 차이를 계산한 뒤 사전의 이름에 연결하세요.'),
        _problem(
            'point의 두 좌표로 원점까지의 거리 distance를 구하세요. math의 제곱근 계산을 이용하고, 운임(rate×distance)을 report의 fare에 저장하세요. point는 보존합니다.',
            "point=[6,8]\nreport={'rate':2.5}",
            "import math as m\ndistance=m.sqrt(point[0]**2+point[1]**2)\nreport['fare']=report['rate']*distance",
            (C('point',[6,8]),C('distance',10),C('report',{'rate':2.5,'fare':25})),
            '좌표를 이름으로 착각하지 말고 목록의 두 값을 읽으세요. 제곱의 합과 제곱근을 거쳐 사전의 단가와 결합합니다.'),
    )


def _py_02():
    return (
        _problem(
            '중복 이름을 제거해 정렬한 목록을 반환하는 unique_names(names)를 정의하세요. arrivals에서 attendees를 만들고 기존 total을 before에 보존하세요. 제공 review_ticket_tools의 cost(price,count)로 현재 총 입장료 total을 다시 구하세요.',
            "arrivals=['Bo','Ann','Bo']\nprice=3\ntotal=price*2\nprice=4",
            '''
            import review_ticket_tools
            def unique_names(names):
                return sorted(set(names))
            before=total
            attendees=unique_names(arrivals)
            total=review_ticket_tools.cost(price,len(attendees))
            ''',
            (C('attendees',['Ann','Bo']),C('before',6),C('total',8),
             C('__probes__',[[],['Cy'],['Ann','De']],['unique_names'])),
            '커널에 남은 과거 결과를 먼저 보존하세요. 중복 제거 함수는 새 입력에서도 반환값을 만들어야 하며 총액은 바뀐 단가로 다시 계산합니다.',
            files={'review_ticket_tools.py':{'text':'def cost(price, count):\n    return price*count\n'}},
            probes={'unique_names':[[[]],[['Cy','Cy']],[['De','Ann','De']]]}),
        _problem(
            '제공 review_scale_tools의 cost(price,count)를 이용해 양수만 factor배 하는 함수 positive_scaled(values,factor)를 정의하세요. 이전 result를 before에 보존하고 현재 factor로 result를 다시 계산하세요. 입력 순서와 values는 유지합니다.',
            'values=[-2,1,0,3]\nfactor=2\nresult=[2,6]\nfactor=5',
            '''
            from review_scale_tools import cost
            def positive_scaled(values,factor):
                return [cost(factor,value) for value in values if value>0]
            before=result
            result=positive_scaled(values,factor)
            ''',
            (C('before',[2,6]),C('result',[5,15]),C('values',[-2,1,0,3]),
             C('__probes__',[[8],[],[0,0]],['positive_scaled'])),
            '선택 조건과 변환을 분리해 생각하세요. factor가 달라져도 같은 함수가 동작해야 하고, 과거 계산 목록을 새 값으로 덮기 전에 보존해야 합니다.',
            files={'review_scale_tools.py':{'text':'def cost(price, count):\n    return price*count\n'}},
            probes={'positive_scaled':[[[-1,2],4],[[],7],[[1,3],0]]}),
        _problem(
            'remaining(required,done)은 아직 끝나지 않은 이름의 정렬된 목록을 반환해야 합니다. 집합이나 목록 입력에서 모두 동작하게 만드세요. pending을 구하고 review_study_tools의 cost(price,count)에 회당 시간과 rounds의 회수를 전달해 times 및 총시간 total을 구하세요.',
            "required={'array','plot','table'}\ndone={'plot'}\nminutes_per_round=5\nrounds={'array':3,'plot':2,'table':4}",
            '''
            import review_study_tools as study
            def remaining(required,done):
                return sorted(set(required)-set(done))
            pending=remaining(required,done)
            times=[study.cost(minutes_per_round,rounds[name]) for name in pending]
            total=sum(times)
            ''',
            (C('pending',['array','table']),C('times',[15,20]),C('total',35),
             C('__probes__',[[],['array'],['plot']],['remaining'])),
            '집합의 차이를 먼저 구한 뒤 순서를 명시하세요. 사전에서 회수를 읽고 모듈로 소요 시간을 계산해 필요한 항목만 모읍니다.',
            files={'review_study_tools.py':{'text':'def cost(price, count):\n    return price*count\n'}},
            probes={'remaining':[[[],[]],[['array'],[]],[['plot','table'],['table']]]}),
    )


def _np_01():
    return (
        _problem(
            'raw에서 열별 bias를 빼고 행별 offset을 더한 int32 배열 result를 만드세요. result의 shape를 shape, 원소 저장 바이트 수를 bytes_count에 담으세요. raw는 유지합니다.',
            NP+'raw=np.array([[2,4,6],[5,7,9]],dtype=np.int32)\nbias=np.array([1,2,3],dtype=np.int32)\noffset=np.array([[10],[20]],dtype=np.int32)',
            'result=raw-bias+offset\nshape=result.shape\nbytes_count=result.nbytes',
            A('result',[[11,12,13],[24,25,26]],[2,3],'int32')+A('raw',[[2,4,6],[5,7,9]],[2,3],'int32')+(C('shape',[2,3]),C('bytes_count',24)),
            'bias는 열 수와, offset은 각 행과 대응해야 합니다. shape를 원소 수 하나로 줄이지 마세요.'),
        _problem(
            '각 행은 주문, 각 열은 상품입니다. counts를 float64로 변환한 뒤 상품별 prices를 곱하고 행별 discount를 빼서 result를 만드세요. counts는 int32로 유지하고 result의 dimensions도 기록하세요.',
            NP+'counts=np.array([[2,1],[0,3],[4,2]],dtype=np.int32)\nprices=np.array([2.5,4.])\ndiscount=np.array([[1.],[0.],[2.]])',
            'result=counts.astype(np.float64)*prices-discount\ndimensions=result.ndim',
            A('result',[[4,3],[0,12],[8,6]],[3,2],'float64')+A('counts',[[2,1],[0,3],[4,2]],[3,2],'int32')+(C('dimensions',2),),
            '형 변환한 배열과 원본은 구분하세요. 상품 가격은 열마다, 할인액은 한 행의 모든 상품에 적용합니다.'),
        _problem(
            'lengths를 한 열, extras를 한 행의 2차원 float64 배열로 만들어 모든 조합의 합 grid를 구하세요. 길이 배열은 column, 추가량 배열은 row에 담고 grid의 원소 수 count를 구하세요.',
            NP+'lengths=[2,5,8]\nextras=[0,0.5]',
            'column=np.array([[lengths[0]],[lengths[1]],[lengths[2]]],dtype=np.float64)\nrow=np.array([extras],dtype=np.float64)\ngrid=column+row\ncount=grid.size',
            A('column',[[2],[5],[8]],[3,1],'float64')+A('row',[[0,.5]],[1,2],'float64')+A('grid',[[2,2.5],[5,5.5],[8,8.5]],[3,2])+(C('count',6),),
            '두 목록을 그대로 더하면 연결됩니다. 한 열과 한 행을 명시해 두 축으로 확장되는 모양을 만드세요.'),
    )


def _np_02():
    return (
        _problem(
            '1부터 12까지의 정수를 행 우선 (3,4) grid로 만드세요. 첫 행을 제외한 처음 세 열을 crop으로 고르고, crop의 짝수만 순서대로 모은 1차원 result를 만드세요.',
            NP,
            'grid=np.arange(1,13).reshape(3,4)\ncrop=grid[1:,:3]\nresult=crop[crop%2==0]',
            A('grid',[[1,2,3,4],[5,6,7,8],[9,10,11,12]],[3,4])+A('crop',[[5,6,7],[9,10,11]],[2,3])+A('result',[6,10],[2]),
            '개수에 맞게 형태를 만든 뒤 행과 열을 한 번에 고르세요. 조건 선택은 crop 안에서만 적용합니다.'),
        _problem(
            '모두 1인 (3,4) 배열에 열별 [2,4,6,8]을 곱해 grid를 만드세요. 두 번째 열을 (3,1) column으로 유지하고, 그 독립된 1차원 flat의 첫 값만 99로 바꾸세요. 양끝을 포함한 0~1의 세 시점 times도 만드세요.',
            NP,
            'grid=np.ones((3,4))*np.array([2,4,6,8])\ncolumn=grid[:,1:2]\nflat=column.flatten()\nflat[0]=99\ntimes=np.linspace(0,1,3)',
            A('grid',[[2,4,6,8],[2,4,6,8],[2,4,6,8]],[3,4])+A('column',[[4],[4],[4]],[3,1])+A('flat',[99,4,4],[3])+A('times',[0,.5,1],[3])+(C('__memory__:column:flat',False),),
            '열 하나를 고를 때 정수와 범위의 차원을 구분하세요. 평탄화 결과를 바꿔도 column이 바뀌면 독립 복사 조건을 만족하지 못합니다.'),
        _problem(
            '10의 0·1·2제곱을 levels로 만들고, 그 값을 대각선에 둔 (3,3) matrix를 만드세요. matrix에서 0보다 큰 값만 골라 (3,1) column으로 배치하세요.',
            NP,
            'levels=np.logspace(0,2,3)\nmatrix=np.eye(3)*levels\ncolumn=matrix[matrix>0].reshape(-1,1)',
            A('levels',[1,10,100],[3])+A('matrix',[[1,0,0],[0,10,0],[0,0,100]],[3,3])+A('column',[[1],[10],[100]],[3,1]),
            '로그 간격의 인자는 값이 아니라 지수입니다. 대각선 밖의 0을 제외한 뒤 남은 개수에 맞춰 열 모양을 만드세요.'),
    )


def _np_03():
    return (
        _problem(
            'a의 각 행 합을 마지막 열에 추가한 뒤 행 순서를 뒤집어 report를 만드세요. 원본 a의 열별 모집단 분산을 variances에 담고 a는 보존하세요.',
            NP+'a=np.array([[2,4,6],[4,8,12]])',
            'totals=a.sum(axis=1)\nwith_total=np.insert(a,3,totals,axis=1)\nreport=np.flip(with_total,axis=0)\nvariances=a.var(axis=0,ddof=0)',
            A('report',[[4,8,12,24],[2,4,6,12]],[2,4])+A('variances',[1,4,9],[3])+A('a',[[2,4,6],[4,8,12]],[2,3]),
            '합계와 분산이 줄이는 축은 다릅니다. 계산 열을 추가하기 전의 원래 관측만 분산에 사용하세요.'),
        _problem(
            'a 아래에 new_row를 붙인 (3,2) combined를 만드세요. 행별 평균 means와 첫 열의 표본 표준편차 deviation을 구하세요. a와 new_row는 보존합니다.',
            NP+'a=np.array([[1,2],[3,4]])\nnew_row=np.array([[5,6]])',
            'combined=np.append(a,new_row,axis=0)\nmeans=combined.mean(axis=1)\ndeviation=combined[:,0].std(ddof=1)',
            A('combined',[[1,2],[3,4],[5,6]],[3,2])+A('means',[1.5,3.5,5.5],[3])+(C('deviation',2),)+A('a',[[1,2],[3,4]],[2,2])+A('new_row',[[5,6]],[1,2]),
            '행을 붙이는 작업에서 축을 생략하면 펼쳐집니다. 표본 표준편차는 선택한 한 열의 값과 분모 보정을 함께 확인하세요.'),
        _problem(
            'a에서 열별 평균을 뺀 centered를 구하세요. centered의 행 순서를 뒤집고 끝에 [99,99]를 붙여 1차원 전송 배열 stream을 만드세요. centered의 열별 모집단 분산 variances도 기록합니다. 원본 a는 보존하세요.',
            NP+'a=np.array([[1.,2.],[3.,6.],[5.,10.]])',
            'centered=a-a.mean(axis=0)\nstream=np.append(np.flip(centered,axis=0),[99,99])\nvariances=centered.var(axis=0)',
            A('centered',[[-2,-4],[0,0],[2,4]],[3,2])+A('stream',[2,4,0,0,-2,-4,99,99],[8])+A('variances',[8/3,32/3],[2])+A('a',[[1,2],[3,6],[5,10]],[3,2]),
            '평균을 뺄 기준은 열별입니다. 마지막 결과만 1차원으로 보내며, 순서를 뒤집는 것과 값을 정렬하는 것은 다릅니다.'),
    )


def _np_04():
    return (
        _problem(
            '전역 seed 0으로 주사위 정수 3개 legacy, seed 42의 독립 Generator로 주사위 정수 3개 modern을 만드세요. 두 배열을 각 열로 놓은 result를 만들고, 첫 행의 독립 복사본 first_copy의 첫 값만 99로 바꾸세요.',
            NP,
            'np.random.seed(0)\nlegacy=np.random.randint(1,7,size=3)\nrng=np.random.default_rng(42)\nmodern=rng.integers(1,7,size=3)\nresult=np.column_stack([legacy,modern])\nfirst_copy=result[0].copy()\nfirst_copy[0]=99',
            A('legacy',[5,6,1],[3])+A('modern',[1,5,4],[3])+A('result',[[5,1],[6,5],[1,4]],[3,2])+A('first_copy',[99,1],[2])+(C('__memory__:result:first_copy',False),),
            '두 난수 API의 생성기를 혼용하지 마세요. 1차원 입력을 두 열로 배치하고 수정할 행은 별도로 복사합니다.'),
        _problem(
            '서로 다른 seed 42 Generator a,b에서 각각 주사위 3개 first,second를 만드세요. 두 배열을 행으로 쌓은 matrix의 첫 열을 view로 잡아 view[0]만 9로 바꾸세요. 원래 추출 배열은 유지하고 두 생성기·추출 배열은 독립적이어야 합니다.',
            NP,
            'a=np.random.default_rng(42)\nb=np.random.default_rng(42)\nfirst=a.integers(1,7,size=3)\nsecond=b.integers(1,7,size=3)\nmatrix=np.stack([first,second],axis=0)\nview=matrix[:,0]\nview[0]=9',
            A('first',[1,5,4],[3])+A('second',[1,5,4],[3])+A('matrix',[[9,5,4],[1,5,4]],[2,3])+A('view',[9,1],[2])+
            (C('__generators__:a:b',True),C('__memory__:first:second',False),C('__memory__:matrix:view',True)),
            '같은 seed와 같은 객체는 다릅니다. 생성기는 둘이어야 하고, view는 matrix의 실제 메모리를 공유해야 합니다.'),
        _problem(
            '전역 seed 0의 표준정규 값 2개 noise, seed 42 Generator의 평균 10·표준편차 2 정규 값 2개 baseline을 뽑으세요. 그 순서로 연결한 row를 두 행으로 쌓아 result를 만들고, 독립 복사본 edited의 첫 열만 0으로 바꾸세요.',
            NP,
            'np.random.seed(0)\nnoise=np.random.randn(2)\nrng=np.random.default_rng(42)\nbaseline=rng.normal(10,2,size=2)\nrow=np.r_[noise,baseline]\nresult=np.vstack([row,row])\nedited=result.copy()\nedited[:,0]=0',
            A('noise',[1.764052345967664,.4001572083672233],[2])+A('baseline',[10.609434159508863,7.920031787519009],[2])+
            A('row',[1.764052345967664,.4001572083672233,10.609434159508863,7.920031787519009],[4])+
            A('result',[[1.764052345967664,.4001572083672233,10.609434159508863,7.920031787519009]]*2,[2,4])+
            A('edited',[[0,.4001572083672233,10.609434159508863,7.920031787519009]]*2,[2,4])+(C('__memory__:result:edited',False),),
            '표준정규와 평균·표준편차를 지정한 분포를 구분하세요. 연결은 길이를 늘리고 세로 쌓기는 행을 추가합니다.'),
    )


def _plot_01():
    return (
        _problem(
            '4×3인치 fig의 한 영역에 raw를 검은 실선, raw-2를 빨간 파선으로 순서대로 그리세요. 범례는 raw, corrected이고 제목 Sensor audit, 축 이름 Time (s)·Reading입니다. x범위 0~2, y범위 0~10, 양 축 격자를 넣고 review_sensor.png로 100dpi 저장하세요.',
            PLT+'t=np.array([0,1,2])\nraw=np.array([6,8,7])',
            '''
            fig,ax=plt.subplots(figsize=(4,3))
            ax.plot(t,raw,color='black',linestyle='-',label='raw')
            ax.plot(t,raw-2,color='red',linestyle='--',label='corrected')
            ax.legend()
            ax.set_title('Sensor audit')
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Reading')
            ax.set_xlim(0,2)
            ax.set_ylim(0,10)
            ax.grid(True)
            fig.savefig('review_sensor.png',dpi=100)
            ''',
            _figure(1)+_line([0,1,2],[6,8,7])+_line([0,1,2],[4,6,5],number=1)+
            (_ax(2,['line_count']),_ax('#000000',['lines',0,'color']),_ax('-',['lines',0,'linestyle']),
             _ax('#ff0000',['lines',1,'color']),_ax('--',['lines',1,'linestyle']),
             _ax(['raw','corrected'],['legend']),_ax('Sensor audit',['title']),
             _ax('Time (s)',['xlabel']),_ax('Reading',['ylabel']),_ax([0,2],['xlim']),_ax([0,10],['ylim']),
             _ax(True,['grid_x']),_ax(True,['grid_y']),C('fig',[4,3],['size']))+_png('review_sensor.png',400,300),
            '보정은 y값에만 적용합니다. 범례를 실제로 표시하고, 화면 그림과 저장 파일이 같은 Figure인지 확인하세요.'),
        _problem(
            '첫 관측을 기준으로 변화율(현재-첫 값)/첫 값×100을 change에 구하세요. 5×2인치 fig에 파란 사각 마커 실선으로 그리고 제목 Relative change, 축 이름 Step·Percent를 넣으세요. y범위는 -60~60이며 change.svg로 저장합니다.',
            PLT+'x=np.array([0,1,2])\nobserved=np.array([10.,15.,5.])',
            '''
            change=(observed-observed[0])/observed[0]*100
            fig,ax=plt.subplots(figsize=(5,2))
            ax.plot(x,change,color='blue',marker='s',linestyle='-')
            ax.set_title('Relative change')
            ax.set_xlabel('Step')
            ax.set_ylabel('Percent')
            ax.set_ylim(-60,60)
            fig.savefig('change.svg')
            ''',
            A('change',[0,50,-50],[3])+_figure(1)+_line([0,1,2],[0,50,-50])+
            (C('fig',[5,2],['size']),_ax(1,['line_count']),_ax('#0000ff',['lines',0,'color']),
             _ax('s',['lines',0,'marker']),_ax('-',['lines',0,'linestyle']),_ax('Relative change',['title']),
             _ax('Step',['xlabel']),_ax('Percent',['ylabel']),_ax([-60,60],['ylim']),
             C('__files__','svg',['change.svg','kind']),C('__files__',True,['change.svg','has_paths']),
             C('__files__',True,['change.svg','matches_fig'])),
            '차이 자체와 백분율은 다릅니다. 음의 변화도 보이는 축을 사용하고 SVG의 내용까지 저장됐는지 확인하세요.'),
        _problem(
            '3×3인치 fig에 reference와 actual을 그 순서로 그리세요. 기준선은 검은 파선, 실제선은 빨간 원 마커 실선입니다. 범례는 reference, actual, 제목은 Comparison입니다. 빈 별도 Figure scratch도 만든 뒤 fig를 comparison.png로 100dpi 저장하세요.',
            PLT+'x=[0,1,2]\nreference=[3,3,3]\nactual=[2,3,5]',
            '''
            fig,ax=plt.subplots(figsize=(3,3))
            ax.plot(x,reference,color='black',linestyle='--',label='reference')
            ax.plot(x,actual,color='red',marker='o',linestyle='-',label='actual')
            ax.legend()
            ax.set_title('Comparison')
            scratch,scratch_ax=plt.subplots()
            fig.savefig('comparison.png',dpi=100)
            ''',
            _figure(1)+_line([0,1,2],[3,3,3])+_line([0,1,2],[2,3,5],number=1)+
            (_ax(2,['line_count']),_ax('#000000',['lines',0,'color']),_ax('--',['lines',0,'linestyle']),
             _ax('#ff0000',['lines',1,'color']),_ax('o',['lines',1,'marker']),_ax('-',['lines',1,'linestyle']),
             _ax(['reference','actual'],['legend']),_ax('Comparison',['title']),C('fig',[3,3],['size']),
             C('scratch','figure',['kind']),C('scratch',True,['empty']))+_png('comparison.png',300,300),
            '마지막에 만든 Figure와 제출할 Figure는 다를 수 있습니다. 저장 결과가 빈 scratch가 아니라 비교 그림이어야 합니다.'),
    )


def _plot_02():
    return (
        _problem(
            '1행 2열 fig를 만드세요. 왼쪽에는 x의 각 범주에서 a,b를 폭 0.4로 나란히 그리되 a는 x-0.2, b는 x+0.2이고 a를 먼저 그립니다. 오른쪽에는 a와 b 전체 합의 비중을 A,B 순서의 원그래프로, 소수 1자리 백분율과 함께 표현하세요.',
            PLT+'x=np.array([0,1])\na=np.array([2,4])\nb=np.array([5,7])',
            '''
            fig,axes=plt.subplots(1,2)
            axes[0].bar(x-.2,a,width=.4)
            axes[0].bar(x+.2,b,width=.4)
            axes[1].pie([a.sum(),b.sum()],labels=['A','B'],autopct='%1.1f%%')
            ''',
            _figure(2)+_bars([2,4,5,7],[-.2,.8,.2,1.2],.4)+
            (_ax([1,2,0,1,0,1],['subplot']),_ax([1,2,0,1,1,2],['subplot'],1),
             _ax(2,['patch_count'],1),_ax(120.,['patches',0,'angle'],1),_ax(240.,['patches',1,'angle'],1),
             _ax(['A','33.3%','B','66.7%'],['texts'],1)),
            '왼쪽은 범주별 크기, 오른쪽은 전체 합의 비중입니다. 원자료를 그대로 원그래프에 넣거나 막대를 겹치지 마세요.'),
        _problem(
            '2행 1열 fig에서 위는 x,y의 산점도입니다. 점 면적은 sizes, 투명도는 0.5, 제목은 Measurements입니다. 아래에는 y-x를 x 위치의 폭 0.8 막대로 그리고 제목 Residuals를 붙이세요.',
            PLT+'x=np.array([1,2,3])\ny=np.array([2,2,5])\nsizes=[20,40,60]',
            '''
            fig,axes=plt.subplots(2,1)
            axes[0].scatter(x,y,s=sizes,alpha=.5)
            axes[0].set_title('Measurements')
            axes[1].bar(x,y-x,width=.8)
            axes[1].set_title('Residuals')
            ''',
            _figure(2)+_bars([1,0,2],[1,2,3],axes=1)+
            (_ax([2,1,0,1,0,1],['subplot']),_ax([2,1,1,2,0,1],['subplot'],1),
             _ax([[1,2,20,.5],[2,2,40,.5],[3,5,60,.5]],['scatter','points']),
             _ax('Measurements',['title']),_ax('Residuals',['title'],1)),
            '위의 위치 데이터와 아래의 차이 값을 혼동하지 마세요. 세로 배치는 축의 개수뿐 아니라 행 위치도 맞아야 합니다.'),
        _problem(
            'data에서 세 번째 값이 음수인 행은 제외하세요. 남은 첫 두 열을 x,y로, 세 번째 열을 색 수치와 점 면적(그 값의 10배)으로 표현한 fig를 만드세요. 투명도 0.5, 제목 Valid sites, 실제 점에 연결된 색 눈금도 필요합니다.',
            PLT+'data=np.array([[1,3,2],[2,9,-1],[4,5,6]])',
            '''
            valid=data[data[:,2]>=0]
            fig,ax=plt.subplots()
            points=ax.scatter(valid[:,0],valid[:,1],c=valid[:,2],s=valid[:,2]*10,alpha=.5)
            fig.colorbar(points,ax=ax)
            ax.set_title('Valid sites')
            ''',
            _figure(2)+(_ax([[1,3,20,.5],[4,5,60,.5]],['scatter','points']),
             _ax([[1,3,20,.5,2],[4,5,60,.5,6]],['scatter','mapped_points']),
             _ax(True,['scatter','colorbar_connected']),_ax('Valid sites',['title'])),
            '좌표·색·면적에 같은 행 선택을 적용하세요. 빈 영역을 추가한 것은 점의 수치 척도를 보여 주는 색 눈금이 아닙니다.'),
    )


def _plot_03():
    return (
        _problem(
            'fig의 첫 데이터 영역에 a의 열별 평균을 뺀 행렬을 이미지로 표시하고 색 눈금을 연결하세요. 두 번째 데이터 영역에는 원래 a의 모든 값으로 경계 [0,2,4,6]의 빈도 히스토그램을 그리세요. 높이는 counts, 첫 영역 제목은 Centered입니다.',
            PLT+'a=np.array([[1.,3.],[3.,5.]])',
            '''
            fig,axes=plt.subplots(1,2)
            image=axes[0].imshow(a-a.mean(axis=0))
            fig.colorbar(image,ax=axes[0])
            axes[0].set_title('Centered')
            counts,edges,patches=axes[1].hist(a.flatten(),bins=[0,2,4,6])
            ''',
            _figure(3)+A('counts',[1,2,1],[3])+_bars([1,2,1],[1,3,5],2,axes=1)+
            (_ax([[-1,-1],[1,1]],['images',0,'data']),_ax(True,['image_colorbars',0]),_ax('Centered',['title'])),
            '이미지는 중심화한 값, 히스토그램은 원래 관측값을 사용합니다. 행렬을 히스토그램에 넣기 전에 한 묶음의 원자료로 펴세요.'),
        _problem(
            'data를 정규분포로 적합한 mu,sigma를 구하세요. 한 영역의 fig에 경계 [-3,-1,1,3]의 밀도 히스토그램과 주어진 x의 적합 밀도 선을 함께 그리세요. 히스토그램 높이는 heights, y축 이름은 Density입니다.',
            PLT+'from scipy.stats import norm\ndata=np.array([-2.,0.,2.])\nx=np.array([-2.,0.,2.])',
            '''
            mu,sigma=norm.fit(data)
            fig,ax=plt.subplots()
            heights,edges,patches=ax.hist(data,bins=[-3,-1,1,3],density=True)
            ax.plot(x,norm.pdf(x,loc=mu,scale=sigma))
            ax.set_ylabel('Density')
            ''',
            _figure(1)+(C('mu',0),C('sigma',sqrt(8/3)),_ax(1,['line_count']),_ax('Density',['ylabel']))+
            A('heights',[1/6]*3,[3])+_bars([1/6]*3,[-2,0,2],2)+_line([-2,0,2],_normal_values([-2,0,2],0,sqrt(8/3))),
            '밀도 곡선과 비교하려면 막대도 밀도여야 합니다. 높이 합이 아니라 구간 폭을 곱한 면적 합을 생각하세요.'),
        _problem(
            'data의 음수는 제외하고 valid를 만드세요. 1행 2열 fig의 왼쪽에는 경계 [0,2,4]의 누적 비율 히스토그램(높이 cumulative)을, 오른쪽에는 valid로 적합한 정규분포의 x에서의 밀도 선을 그리세요. mu,sigma를 기록하고 제목은 각각 Cumulative, Density입니다.',
            PLT+'from scipy.stats import norm\ndata=np.array([-99.,0.,1.,2.,3.,4.])\nx=np.array([0.,2.,4.])',
            '''
            valid=data[data>=0]
            mu,sigma=norm.fit(valid)
            fig,axes=plt.subplots(1,2)
            cumulative,edges,patches=axes[0].hist(valid,bins=[0,2,4],density=True,cumulative=True)
            axes[0].set_title('Cumulative')
            axes[1].plot(x,norm.pdf(x,loc=mu,scale=sigma))
            axes[1].set_title('Density')
            ''',
            A('valid',[0,1,2,3,4],[5])+A('cumulative',[.4,1],[2])+_figure(2)+
            (C('mu',2),C('sigma',sqrt(2)),_ax([1,2,0,1,0,1],['subplot']),_ax([1,2,0,1,1,2],['subplot'],1),
             _ax('Cumulative',['title']),_ax('Density',['title'],1),_ax(1,['line_count'],1))+
            _bars([.4,1],[1,3],2)+_line([0,2,4],_normal_values([0,2,4],2,sqrt(2)),axes=1),
            '제외한 값은 두 계산에서 모두 빼야 합니다. 누적 비율과 확률밀도는 단위가 달라 별도 영역으로 구분합니다.'),
    )


def _pd_01():
    return (
        _problem(
            'rain.csv의 place를 행 라벨로 읽어 df를 만드세요. wind,rain 순서의 표 result와 rain 열의 Series readings를 만들고, 가장 비가 많이 온 곳의 라벨 winner와 값 peak를 구하세요.',
            PD,
            "df=pd.read_csv('rain.csv',index_col='place')\nresult=df[['wind','rain']]\nreadings=df['rain']\nwinner=readings.idxmax()\npeak=readings.max()",
            F('df',[[2,5],[9,3],[4,8]],['A','B','C'],['rain','wind'])+
            F('result',[[5,2],[3,9],[8,4]],['A','B','C'],['wind','rain'])+S('readings',[2,9,4],['A','B','C'])+(C('winner','B'),C('peak',9)),
            '첫 열은 데이터 열이 아니라 행 라벨입니다. 여러 열은 표로 유지하고, 최고 값 자체와 그 라벨은 구분하세요.',
            files={'rain.csv':{'text':'place,rain,wind\nA,2,5\nB,9,3\nC,4,8\n'}}),
        _problem(
            'labels를 인덱스로 values의 Series scores를 만드세요. 최고 값의 위치 position과 라벨 winner를 구하고, 같은 행 라벨을 가진 visits,score 순서의 DataFrame result를 만드세요.',
            PD+'labels=[30,10,20]\nvalues=[8,5,9]\nvisits=[2,1,3]',
            "scores=pd.Series(values,index=labels)\nposition=scores.argmax()\nwinner=scores.idxmax()\nresult=pd.DataFrame({'visits':visits,'score':scores.tolist()},index=labels)",
            S('scores',[8,5,9],[30,10,20])+(C('position',2),C('winner',20))+
            F('result',[[2,8],[1,5],[3,9]],[30,10,20],['visits','score']),
            '정수로 보이는 행 이름도 위치 번호와 다릅니다. 값을 일반 목록으로 옮겨도 결과 표의 라벨을 별도로 유지하세요.'),
        _problem(
            '헤더 없는 notes.csv를 name,note,score 열의 DataFrame df로 읽으세요. name 열을 행 라벨로 사용하고, note만 가진 표 result 및 score의 일반 목록 values를 만드세요. 메모 안 쉼표는 유지합니다.',
            PD,
            "df=pd.read_csv('notes.csv',header=None,names=['name','note','score'],index_col='name')\nresult=df[['note']]\nvalues=df['score'].tolist()",
            F('df',[['north,gate',7],['library',11]],['Ann','Bo'],['note','score'])+
            F('result',[['north,gate'],['library']],['Ann','Bo'],['note'])+(C('values',[7,11]),),
            '첫 줄도 관측값입니다. 한 열만 남겨도 목표가 DataFrame이면 차원을 유지해야 하며, 따옴표 안의 쉼표로 셀을 나누지 마세요.',
            files={'notes.csv':{'text':'Ann,"north,gate",7\nBo,library,11\n'}}),
    )


def _pd_02():
    return (
        _problem(
            'B의 math만 100으로 수정하고 두 과목의 평균 mean을 df에 추가하세요. mean이 80 이상인 사람의 math,english,mean 열을 result로 만드세요. 오래된 total은 평균에서 제외하되 df에는 유지합니다.',
            PD+"df=pd.DataFrame({'math':[70,60,90],'english':[80,70,90],'total':[999,999,999]},index=['A','B','C'])",
            "df.loc['B','math']=100\ndf['mean']=df[['math','english']].mean(axis=1)\nresult=df.loc[df['mean']>=80,['math','english','mean']]",
            F('df',[[70,80,999,75],[100,70,999,85],[90,90,999,90]],['A','B','C'],['math','english','total','mean'])+
            F('result',[[100,70,85],[90,90,90]],['B','C'],['math','english','mean']),
            '한 셀의 라벨을 정확히 수정하고 원래 두 과목만 평균내세요. 조건은 새로 계산한 평균에 적용합니다.'),
        _problem(
            'df는 유지하고 B행과 memo열을 뺀 trimmed를 만드세요. trimmed에 a+b 합계 total을 추가한 뒤 마지막 행,첫 행 순서로 b,total만 가진 result를 만드세요.',
            PD+"df=pd.DataFrame({'a':[2,9,5],'b':[3,8,7],'memo':['x','y','z']},index=['A','B','C'])",
            "trimmed=df.drop(index=['B'],columns=['memo'])\ntrimmed['total']=trimmed[['a','b']].sum(axis=1)\nresult=trimmed.iloc[[1,0]][['b','total']]",
            F('df',[[2,3,'x'],[9,8,'y'],[5,7,'z']],['A','B','C'],['a','b','memo'])+
            F('trimmed',[[2,3,5],[5,7,12]],['A','C'],['a','b','total'])+F('result',[[7,12],[3,5]],['C','A'],['b','total']),
            '제거 후 표에서의 위치를 사용하세요. 결과의 첫 행 라벨이 0으로 바뀌면 위치와 라벨을 혼동한 것입니다.'),
        _problem(
            'df에 income-cost 차이 net을 추가하세요. net이 양수이면서 visits가 2 이상인 행만 eligible로 고른 뒤, 그중 마지막 행의 net,visits를 1행짜리 result로 만드세요.',
            PD+"df=pd.DataFrame({'income':[10,5,20,12],'cost':[3,8,4,2],'visits':[1,3,2,4]},index=[10,30,50,70])",
            "df['net']=df['income']-df['cost']\neligible=df.loc[(df['net']>0)&(df['visits']>=2)]\nresult=eligible.tail(1)[['net','visits']]",
            F('df',[[10,3,1,7],[5,8,3,-3],[20,4,2,16],[12,2,4,10]],[10,30,50,70],['income','cost','visits','net'])+
            F('eligible',[[20,4,2,16],[12,2,4,10]],[50,70],['income','cost','visits','net'])+F('result',[[10,4]],[70],['net','visits']),
            '두 조건을 각각 비교한 뒤 결합하세요. 마지막 위치를 고르더라도 원래 라벨과 2차원 표 형태를 유지합니다.'),
    )


def _pd_03():
    return (
        _problem(
            'day1,day2를 행으로 이어 새 숫자 인덱스의 combined를 만드세요. score가 결측인 행만 제외하고 members의 team을 id로 왼쪽 결합한 result를 만드세요. 열은 id,score,team 순서, 결과 인덱스는 0부터입니다.',
            PD+"day1=pd.DataFrame({'id':[1,2],'score':[8,np.nan]})\nday2=pd.DataFrame({'id':[3],'score':[6]})\nmembers=pd.DataFrame({'id':[3,1],'team':['Y','X']})",
            "combined=pd.concat([day1,day2],ignore_index=True)\nvalid=combined.dropna(subset=['score'])\nresult=valid.merge(members,on='id',how='left')",
            F('combined',[[1,8],[2,NAN],[3,6]],[0,1,2],['id','score'])+
            F('result',[[1,8,'X'],[3,6,'Y']],[0,1],['id','score','team']),
            '행 이어 붙이기와 키 대응 결합은 다릅니다. 이름표의 순서가 달라도 id로 연결하고 결측 행 제거 기준은 score만 사용하세요.'),
        _problem(
            'old,new의 모든 id를 보존하고 오름차순으로 결합하세요. stock은 stock_old,stock_new로 구분합니다. 이번 재고 자료에서는 없는 쪽의 재고를 0으로 정의하므로 두 열만 0으로 채우고 change=new-old를 추가한 result를 만드세요. 원본 old와 new는 변경하지 마세요.',
            PD+"old=pd.DataFrame({'id':[1,2],'stock':[5,2]})\nnew=pd.DataFrame({'id':[2,3],'stock':[4,6]})",
            "result=old.merge(new,on='id',how='outer',sort=True,suffixes=('_old','_new'))\nresult=result.fillna({'stock_old':0,'stock_new':0})\nresult['change']=result['stock_new']-result['stock_old']",
            F('result',[[1,5,0,-5],[2,2,4,2],[3,0,6,6]],[0,1,2],['id','stock_old','stock_new','change'])+
            F('old',[[1,5],[2,2]],[0,1],['id','stock'])+F('new',[[2,4],[3,6]],[0,1],['id','stock']),
            '한쪽 기준 결합은 사라진 품목이나 새 품목을 놓칠 수 있습니다. 같은 이름의 두 열을 구분한 뒤 명시된 결측 정책으로 차이를 계산하세요.'),
        _problem(
            'logs1,logs2를 행으로 이어 all_logs를 만드세요. roster의 모든 id를 보존하는 오른쪽 결합을 하고 중복 출석 기록도 모두 남긴 result를 만드세요. 기록 없는 사람의 points만 0으로 채웁니다. 열은 id,points,name 순서입니다.',
            PD+"logs1=pd.DataFrame({'id':[1,2],'points':[5,8]})\nlogs2=pd.DataFrame({'id':[2],'points':[12]})\nroster=pd.DataFrame({'id':[2,3],'name':['Ann','Bo']})",
            "all_logs=pd.concat([logs1,logs2],ignore_index=True)\nresult=all_logs.merge(roster,on='id',how='right')\nresult=result.fillna({'points':0})",
            tuple(c for c in F('all_logs',[[1,5],[2,8],[2,12]],[0,1,2],['id','points']) if c['path'] != ['index'])+
            F('result',[[2,8,'Ann'],[2,12,'Ann'],[3,0,'Bo']],[0,1,2],['id','points','name']),
            '로스터가 오른쪽 기준입니다. 중복 키가 만들 수 있는 여러 대응 행을 임의로 합치거나 삭제하지 마세요.'),
    )


def _pd_04():
    return (
        _problem(
            'team을 행,kind를 열로 score 평균을 집계한 wide를 만드세요. 없는 조합은 결측으로 둡니다. 원래 관측 전체를 기준으로 team별 score 평균 means를 구하고, 평균이 80 이상인 팀만 Series result에 남기세요.',
            PD+"df=pd.DataFrame({'team':['A','A','A','B','B'],'kind':['x','x','y','x','y'],'score':[60,100,80,70,80]})",
            "wide=df.pivot_table(index='team',columns='kind',values='score',aggfunc='mean')\nmeans=df.groupby('team')['score'].mean()\nresult=means.loc[means>=80]",
            F('wide',[[80,80],[70,80]],['A','B'],['x','y'])+S('means',[80,75],['A','B'])+S('result',[80],['A']),
            '동일한 행·열 조합에 여러 관측이 있으므로 집계 기준이 필요합니다. 낮은 개별 점수를 먼저 지우면 팀 평균이 달라집니다.'),
        _problem(
            '중복 없는 day,sensor 조합을 행=day·열=sensor·값=reading인 wide로 바꾸세요. 원자료에서 sensor별 reading 평균 means를 구하고 평균 4 이상인 센서의 평균만 result로 남기세요.',
            PD+"df=pd.DataFrame({'day':['Mon','Mon','Tue','Tue'],'sensor':['A','B','A','B'],'reading':[1,5,3,7]})",
            "wide=df.pivot(index='day',columns='sensor',values='reading')\nmeans=df.groupby('sensor')['reading'].mean()\nresult=means.loc[means>=4]",
            F('wide',[[1,5],[3,7]],['Mon','Tue'],['A','B'])+S('means',[2,6],['A','B'])+S('result',[6],['B']),
            '각 조합이 유일한 재배치와 집단 평균은 서로 다른 결과입니다. 표의 두 축을 정한 뒤 조건은 센서 평균에 적용하세요.'),
        _problem(
            'valid=True인 기록만 사용하세요. team,year를 그 순서의 복합 행 라벨,kind를 열로 visits 합계를 담은 wide를 만들고 없는 조합은 0으로 채우세요. 유효 기록의 team별 visits 총합이 10 이상인 팀만 result에 남기세요.',
            PD+"df=pd.DataFrame({'team':['A','A','A','B','B'],'year':[2025,2025,2026,2026,2026],'kind':['x','y','x','x','y'],'visits':[6,5,2,100,4],'valid':[True,True,True,False,True]})",
            "valid=df.loc[df['valid']]\nwide=valid.pivot_table(index=['team','year'],columns='kind',values='visits',aggfunc='sum',fill_value=0)\ntotals=valid.groupby('team')['visits'].sum()\nresult=totals.loc[totals>=10]",
            F('wide',[[6,5],[2,0],[0,4]],[['A',2025],['A',2026],['B',2026]],['x','y'])+
            (C('wide',['team','year'],['index_names']),)+S('result',[13],['A']),
            '행별 유효 조건은 집계 전에, 팀 총합 조건은 집계 후에 적용합니다. 피벗에서는 서로 다른 연도를 하나의 행으로 합치지 마세요.'),
    )


# All keys are explicit: a curriculum reorder must be reviewed rather than
# silently giving students an exercise that uses an API they have not met.
_BLOCKS = (
    ('Python 기초','py',1,('py_values','py_sequences','py_methods','py_mapping','py_import'),
     '값·목록·사전으로 작은 계산 완성',
     '자료를 이름에 저장하고 목록에서 고른 값을 사전의 의미와 연결합니다. 정렬의 반환값과 원본 변경, 모듈의 계산을 함께 써야 결과를 올바른 형태로 남길 수 있습니다.',
     'sorted(items)\nitems.sort()\nrecord[key]\nimport math\nmath.sqrt(x)',
     '목록의 위치, 사전의 키, 함수의 반환값은 다른 역할입니다. 출력만 하지 말고 요구된 이름과 원본 상태를 남기세요.',_py_01),
    ('Python 기초','py',2,('py_kernel','py_set','py_functions','py_iteration','py_module_file'),
     '상태를 갱신하고 함수를 재사용',
     '실행 상태에 남은 과거 값을 보존하고 필요한 계산을 다시 수행합니다. 집합으로 대상을 정한 뒤 함수·반복·사용자 모듈로 여러 입력에 같은 규칙을 적용합니다.',
     'def transform(values):\n    return [x for x in values if x>0]\nsorted(set(values))\nimport helpers',
     '결과를 직접 적는 대신 새 입력에서도 동작하는 함수를 만드세요. 같은 변수를 다시 계산하기 전 필요한 과거 상태를 보존합니다.',_py_02),
    ('NumPy','np',1,('np_elementwise','np_shape','np_dtype','np_broadcast_scalar','np_broadcast_column'),
     '자료형과 행·열을 맞춘 보정 계산',
     '원소별 계산도 어떤 축에 보정값을 대응시키는지에 따라 의미가 달라집니다. 배열 형태와 자료형을 함께 결정하고 원본을 보존한 채 결과와 저장 크기를 확인합니다.',
     'a.astype(np.float64)\na + row_offset + column_offset\na.shape\na.ndim\na.nbytes',
     '아직 배우지 않은 재배열 함수 없이 한 행과 한 열을 중첩 목록으로 표현할 수 있습니다. 숫자가 같아도 shape가 다르면 다른 결과입니다.',_np_01),
    ('NumPy','np',2,('np_creation','np_ranges','np_slicing','np_mask','np_reshape'),
     '규칙적 배열에서 필요한 값 뽑기',
     '배열을 만드는 규칙, 두 축의 선택, 조건 선택, 결과 형태를 차례로 연결합니다. 생성된 값 전체가 아니라 어떤 부분을 어떤 모양으로 제출할지 먼저 계획합니다.',
     'np.arange(start,stop).reshape(rows,cols)\na[rows,cols]\na[a>0]\na.flatten()',
     '행·열 슬라이스는 쉼표로 구분하고 조건 선택 뒤 남은 원소 수를 확인하세요. 독립된 평탄화 결과의 수정이 원본으로 전파되면 안 됩니다.',_np_02),
    ('NumPy','np',3,('np_reduce','np_statistics','np_insert','np_flip','np_append'),
     '집계·통계로 보고용 배열 구성',
     '관측값에서 통계를 구한 뒤 요약 열이나 추가 관측을 결합합니다. 계산 축·표본 보정·삽입 축·출력 순서를 구분해야 보고서에 잘못된 합계나 차원이 섞이지 않습니다.',
     'a.sum(axis=1)\na.var(axis=0,ddof=0)\nnp.insert(a,index,values,axis=1)\nnp.flip(a,axis=0)\nnp.append(a,b,axis=0)',
     '계산 열을 다시 통계에 포함하지 마세요. append의 축 생략은 펼침이 필요할 때만 선택합니다.',_np_03),
    ('NumPy','np',4,('np_concatenate','np_stack_helpers','np_random_legacy','np_random_generator','np_memory'),
     '난수 실험을 재현하고 안전하게 편집',
     '난수 생성기와 호출 순서를 정한 뒤 결과를 연결하거나 쌓습니다. 같은 seed로 재현하는 것, 생성기가 독립적인 것, 배열 메모리가 독립적인 것은 각각 확인할 조건입니다.',
     'np.random.seed(seed)\nrng=np.random.default_rng(seed)\nnp.stack([a,b])\nnp.column_stack([a,b])\na.copy()\nnp.shares_memory(a,b)',
     '메모리 공유 여부는 제출자가 적은 참·거짓만 믿지 않고 실제 배열로 검사합니다. 같은 객체에 이름만 둘 붙여 독립 생성기를 대신하지 마세요.',_np_04),
    ('Matplotlib','plot',1,('plot_line','plot_style','plot_labels','plot_limits','plot_save'),
     '의미가 전달되는 그림을 저장',
     '좌표 계산부터 스타일·라벨·축 범위·파일 출력까지 연결합니다. 설명이 맞는 Figure를 만들었는지와 그 Figure가 실제 파일로 저장됐는지는 별도로 확인합니다.',
     'fig,ax=plt.subplots(figsize=(4,3))\nax.plot(x,y,label="series")\nax.legend()\nfig.savefig("report.png",dpi=100)',
     '축 범위는 자료를 바꾸지 않습니다. 다른 현재 Figure나 이름만 맞는 빈 파일을 저장하면 제출 조건을 만족하지 못합니다.',_plot_01),
    ('Matplotlib','plot',2,('plot_subplots','plot_scatter','plot_scatter_color','plot_bar','plot_pie'),
     '관계·크기·비중을 맞는 그림으로 비교',
     '산점도는 관측의 관계, 막대는 범주의 크기, 원그래프는 전체 비중에 쓰입니다. 서로 다른 질문을 여러 영역에 배치하고 색·면적의 의미를 같은 관측에 연결합니다.',
     'fig,axes=plt.subplots(1,2)\naxes[0].scatter(x,y,c=values,s=sizes)\naxes[1].bar(x,heights)\nax.pie(values,labels=labels)',
     '색 눈금은 실제 점의 수치에 연결하세요. 그룹 막대의 위치·폭과 원그래프의 비중은 서로 다른 표현입니다.',_plot_02),
    ('Matplotlib','plot',3,('plot_heatmap','plot_hist','plot_density','plot_normal','plot_fitted_hist'),
     '공간 배열과 관측 분포를 함께 해석',
     '행렬 위치를 보이는 이미지와 값의 분포를 세는 히스토그램은 같은 데이터를 다른 관점으로 보여 줍니다. 적합 곡선과 비교할 때는 밀도 단위를 맞추고 누적 비율과 구분합니다.',
     'image=ax.imshow(a)\nfig.colorbar(image,ax=ax)\nax.hist(data,bins=edges,density=True)\nmu,sigma=norm.fit(data)\nax.plot(x,norm.pdf(x,mu,sigma))',
     '누적 개수·누적 비율·밀도는 다릅니다. 관측 제외 조건을 시각화와 적합에 동일하게 적용하세요.',_plot_03),
    ('pandas','pd',1,('pd_series','pd_frame','pd_csv','pd_columns','pd_argmax'),
     '표를 읽고 값·위치·이름을 구분',
     '파일을 읽을 때 행 라벨과 헤더를 정하고, 열을 Series 또는 DataFrame으로 선택합니다. 최고 값과 그 위치·라벨을 구분하면 원자료의 의미를 잃지 않고 작은 보고서를 만들 수 있습니다.',
     'pd.read_csv(path,index_col="name")\ndf["score"]\ndf[["score"]]\ns.max()\ns.argmax()\ns.idxmax()',
     '정수 라벨은 위치와 다를 수 있습니다. 헤더 없는 첫 행이나 따옴표 속 쉼표를 잘못 해석하지 마세요.',_pd_01),
    ('pandas','pd',2,('pd_computed','pd_drop','pd_loc','pd_iloc','pd_filter'),
     '계산 열과 조건으로 보고서 만들기',
     '수정할 셀과 계산에 쓸 원래 열을 명확히 정한 뒤 필요한 행·열을 고릅니다. 제거·선택·재계산의 순서가 원본 상태와 결과 라벨을 함께 결정합니다.',
     'df.loc[label,column]=value\ndf["total"]=df[columns].sum(axis=1)\ndf.drop(columns=[name])\ndf.loc[condition,columns]\ndf.iloc[positions]',
     '오래된 계산 열을 다시 더하지 마세요. 행을 제거한 뒤의 위치와 원래 행 라벨을 구분합니다.',_pd_02),
    ('pandas','pd',3,('pd_missing','pd_concat','pd_merge','pd_merge_detail','pd_merge_coverage'),
     '누락과 중복을 보존하며 자료 결합',
     '기록을 이어 붙이는 작업과 키로 대응시키는 작업을 나눕니다. 어느 쪽 대상을 보존할지, 같은 이름의 열을 어떻게 구분할지, 결측값이 무엇을 뜻하는지 정한 뒤 결합합니다.',
     'pd.concat([a,b],ignore_index=True)\ndf.dropna(subset=[column])\na.merge(b,on="id",how="outer",suffixes=("_old","_new"))\ndf.fillna({column:0})',
     '행 번호로 키 결합을 대신하거나 중복 대응을 지우지 마세요. 결측을 0으로 채우는 것은 문제에서 의미를 정한 열에만 적용합니다.',_pd_03),
    ('pandas','pd',4,('pd_pivot','pd_pivot_table','pd_pivot_multi','pd_groupby','pd_group_filter'),
     '자료를 재배치하고 집단 조건 판단',
     '유일한 조합의 재배치와 중복 관측의 집계를 구분합니다. 여러 범주가 행을 정의하면 복합 라벨을 유지하고, 집단의 평균·총합을 판단할 때는 집계한 뒤 조건을 적용합니다.',
     'df.pivot(index=row,columns=column,values=value)\ndf.pivot_table(index=[first,second],columns=kind,values=value,aggfunc="sum")\ntotals=df.groupby(group)[value].sum()\ntotals.loc[totals>=limit]',
     '개별 값의 조건을 먼저 적용하면 집단 조건과 다른 답이 됩니다. 두 범주의 행 라벨을 문자열 하나로 합치지 마세요.',_pd_04),
)


def insert_reviews(units):
    """Return originals plus a review immediately after each authored five-unit block.

    Known reviews are reused if called again, making insertion idempotent. A
    changed five-unit sequence raises a clear error instead of teaching future
    APIs by accident. Incomplete final blocks and unrelated topics are unchanged.
    """
    units = tuple(units)
    keys = [unit.key for unit in units]
    if len(keys) != len(set(keys)):
        raise ValueError('복습 삽입 전 단원 key가 중복되어 있습니다.')
    specs = {(item[0], item[2]): item for item in _BLOCKS}
    review_keys = {f'review_{item[1]}_{item[2]:02d}' for item in _BLOCKS}
    existing = {unit.key: unit for unit in units if unit.key in review_keys}
    counts, pending, result = {}, {}, []
    for unit in units:
        if unit.key in review_keys:
            continue
        result.append(unit)
        if not any(topic == unit.topic for topic, _ in specs):
            continue
        counts[unit.topic] = counts.get(unit.topic, 0) + 1
        pending.setdefault(unit.topic, []).append(unit.key)
        if counts[unit.topic] % 5:
            continue
        number = counts[unit.topic] // 5
        spec = specs.get((unit.topic, number))
        if spec is None:
            raise ValueError(f'{unit.topic}의 {number}번째 5단원 복습을 추가로 설계해야 합니다.')
        topic, prefix, number, prerequisites, title, explanation, syntax, pitfall, factory = spec
        actual = tuple(pending[topic])
        if actual != prerequisites:
            raise ValueError(f'{topic} 복습 {number}: 예상 단원 {prerequisites}, 실제 단원 {actual}')
        pending[topic] = []
        key = f'review_{prefix}_{number:02d}'
        if key in existing:
            review = existing[key]
            if review.prerequisites != prerequisites or review.topic != topic:
                raise ValueError(f'{key}의 선수 단원 또는 분야가 현재 과정과 다릅니다.')
        else:
            review = Lesson(key, topic, f'5단원 종합복습 {number}: {title}',
                            explanation, syntax, pitfall, 'supplement', (), factory(),
                            prerequisites, '직전 5개 단원의 개념을 조합한 새 예시·활용 1·활용 2입니다. PDF 원문 문제의 복제가 아닙니다.')
        result.append(review)
    return tuple(result)
