"""Remaining lecture operations, separated by the axis decision being learned."""
from .model import Lesson, problem as P, check as C, array as A
from .numpy_course import NP


def lessons():
    result = []
    def add(key, title, why, syntax, pitfall, pages, cases):
        result.append(Lesson('np_'+key, 'NumPy', title, why, syntax, pitfall,
            'week_2_1_handout.pdf', tuple(pages), tuple(cases),
            (result[-1].key,) if result else ('np_reshape',)))
    add('reduce', '합계의 축: 열별과 행별',
        'axis는 결과에서 줄어드는 축입니다. (행,열)에서 axis=0은 행을 줄여 열별 결과를, axis=1은 열을 줄여 행별 결과를 만듭니다. axis를 생략하면 전체를 합칩니다.',
        'a.sum()\na.sum(axis=0)\nnp.mean(a, axis=1)',
        'axis=0을 첫 행이라는 뜻으로 읽지 마세요. 결과 shape도 먼저 예상하세요.', [30,31], [
        P('열별 합계를 totals에 담으세요.',NP+'a = np.array([[1,2,3],[4,5,6]])','totals = a.sum(axis=0)',A('totals',[5,7,9],[3])),
        P('행별 평균 means와 전체 합계 total을 구하세요.',NP+'a = np.array([[2,4],[6,10],[8,10]])','means = a.mean(axis=1)\ntotal = a.sum()',A('means',[3,8,9],[3])+(C('total',40),)),
        P('a에서 마지막 열을 제외한 각 행의 합 result를 구하고 가장 큰 합을 peak에 담으세요.',NP+'a = np.array([[3,7,100],[8,4,200]])','result = a[:,:-1].sum(axis=1)\npeak = result.max()',A('result',[10,12],[2])+(C('peak',12),)),
    ])
    add('statistics', '분산·표준편차와 ddof',
        '분산은 평균에서 떨어진 거리의 제곱 평균, 표준편차는 그 제곱근입니다. NumPy의 기본 ddof=0은 N으로 나눕니다. ddof=1은 N-1로 나누며 pandas 기본과 비교할 때 중요합니다.',
        'a.var(ddof=0)\na.std(ddof=1)\na.min(axis=0)\na.max(axis=0)',
        '표본 보정(ddof)과 계산 축을 명시하세요. 표준편차를 분산과 혼동하지 마세요.',[30,31], [
        P('a 전체의 모집단 분산 variance와 표준편차 deviation을 구하세요.',NP+'a = np.array([1,3,5])','variance = a.var(ddof=0)\ndeviation = a.std(ddof=0)',[C('variance',8/3),C('deviation',(8/3)**.5)]),
        P('a 전체의 표본 분산 variance와 표준편차 deviation을 구하세요.',NP+'a = np.array([1,3,5])','variance = a.var(ddof=1)\ndeviation = a.std(ddof=1)',[C('variance',4),C('deviation',2)]),
        P('열별 최솟값 low, 최댓값 high, 범위 spread를 배열로 구하세요.',NP+'a = np.array([[3,8],[1,12],[5,10]])','low = a.min(axis=0)\nhigh = a.max(axis=0)\nspread = high - low',A('low',[1,8],[2])+A('high',[5,12],[2])+A('spread',[4,4],[2])),
    ])
    add('insert', '행 또는 열 삽입',
        'np.insert는 지정한 위치 앞에 값을 삽입한 새 배열을 반환합니다. axis=0은 행 삽입, axis=1은 열 삽입입니다. 원본을 자동으로 바꾸지 않습니다.',
        'np.insert(a, 1, [9,9], axis=0)\nnp.insert(a, 0, [7,8], axis=1)',
        'axis를 생략하면 배열을 먼저1차원으로 펼칩니다. 삽입할 값의 길이를 해당 축에 맞추세요.',[17,18], [
        P('a의 두 번째 행 앞에 [9,9]를 넣은 result를 만드세요.',NP+'a = np.array([[1,2],[3,4]])','result = np.insert(a,1,[9,9],axis=0)',A('result',[[1,2],[9,9],[3,4]],[3,2])),
        P('a의 맨 앞 열에 각 행의 번호10,20을 넣은 result를 만드세요.',NP+'a = np.array([[1,2],[3,4]])','result = np.insert(a,0,[10,20],axis=1)',A('result',[[10,1,2],[20,3,4]],[2,3])),
        P('a의 끝에 각 행 합계 열을 붙인 result를 만드세요. a는 그대로 두세요.',NP+'a = np.array([[2,5],[4,8]])','result = np.insert(a,2,a.sum(axis=1),axis=1)',A('result',[[2,5,7],[4,8,12]],[2,3])+A('a',[[2,5],[4,8]],[2,2])),
    ])
    add('flip', '행·열 순서 뒤집기',
        'flip은 값을 정렬하는 함수가 아니라 선택한 축의 순서를 거꾸로 만듭니다. axis=0은 위아래, axis=1은 좌우입니다. axis 생략은 모든 축을 뒤집습니다.',
        'np.flip(a, axis=0)\nnp.flip(a, axis=1)',
        '뒤집은 결과는 원본과 메모리를 공유할 수 있습니다. 독립 수정이 필요하면 copy를 붙이세요.',[20], [
        P('a의 행 순서만 뒤집은 result를 만드세요.',NP+'a = np.array([[1,2],[3,4],[5,6]])','result = np.flip(a,axis=0)',A('result',[[5,6],[3,4],[1,2]],[3,2])),
        P('a의 각 행 안에서 열 순서만 뒤집은 result를 만드세요.',NP+'a = np.array([[1,2,3],[4,5,6]])','result = np.flip(a,axis=1)',A('result',[[3,2,1],[6,5,4]],[2,3])),
        P('a를 모든 축으로 뒤집은 독립 복사본 result를 만들고 왼쪽 위 값만99로 바꾸세요. a는 유지하세요.',NP+'a = np.array([[1,2],[3,4]])','result = np.flip(a).copy()\nresult[0,0] = 99',A('result',[[99,3],[2,1]],[2,2])+A('a',[[1,2],[3,4]],[2,2])),
    ])
    add('append', 'append의 펼침과 축 유지',
        'np.append는 새 배열을 반환합니다. axis 없이 사용하면 두 입력을 펼쳐 이어 붙입니다. axis를 지정하면 그 축을 제외한 모든 차원의 크기가 같아야 합니다.',
        'np.append(a, b)\nnp.append(a, b, axis=0)',
        'Python list.append와 반환 동작이 다릅니다. 반복해서 append하면 재할당 비용이 커집니다.',[28], [
        P('a와 b의 원소를1차원으로 이어 붙인 result를 만드세요.',NP+'a = np.array([[1,2]])\nb = np.array([[3,4]])','result = np.append(a,b)',A('result',[1,2,3,4],[4])),
        P('a 아래에 b의 행을 붙여2차원 result를 만드세요.',NP+'a = np.array([[1,2],[3,4]])\nb = np.array([[5,6]])','result = np.append(a,b,axis=0)',A('result',[[1,2],[3,4],[5,6]],[3,2])),
        P('각 행 오른쪽에 flag 열을 붙인 result를 만들고 a는 유지하세요.',NP+'a = np.array([[4,5],[6,7]])\nflag = np.array([[1],[0]])','result = np.append(a,flag,axis=1)',A('result',[[4,5,1],[6,7,0]],[2,3])+A('a',[[4,5],[6,7]],[2,2])),
    ])
    add('concatenate', '기존 축 연결과 새로운 축 쌓기',
        'concatenate는 기존 축을 늘리고 stack은 새 축을 만듭니다. 두(3,) 배열을 concatenate하면(6,), stack(axis=0)이면(2,3)이 됩니다.',
        'np.concatenate([a,b], axis=0)\nnp.stack([a,b], axis=0)\nnp.stack([a,b], axis=1)',
        '같은 값이어도 shape가 다르면 다음 연산의 의미가 바뀝니다.',[35], [
        P('a와 b를 순서대로 연결한1차원 result를 만드세요.',NP+'a = np.array([1,2,3])\nb = np.array([4,5,6])','result = np.concatenate([a,b])',A('result',[1,2,3,4,5,6],[6])),
        P('a,b 각각을 한 행으로 쌓은(2,3) result를 만드세요.',NP+'a = np.array([1,2,3])\nb = np.array([4,5,6])','result = np.stack([a,b],axis=0)',A('result',[[1,2,3],[4,5,6]],[2,3])),
        P('a,b 각각을 한 열로 쌓은 result와 그 행별 합 totals를 만드세요.',NP+'a = np.array([2,4,6])\nb = np.array([1,3,5])','result = np.stack([a,b],axis=1)\ntotals = result.sum(axis=1)',A('result',[[2,1],[4,3],[6,5]],[3,2])+A('totals',[3,7,11],[3])),
    ])
    add('stack_helpers', 'vstack·hstack·column_stack',
        'vstack은 입력을 적어도2차원 행으로 해석해 세로로 쌓습니다. hstack은1차원 입력은1차원으로 연결하지만2차원 입력은 열 방향으로 연결합니다. column_stack은1차원 입력을 열로 세웁니다. r_와 c_는 각각 연결과 열 쌓기에 쓰는 간편 표기입니다.',
        'np.vstack([a,b])\nnp.hstack([a,b])\nnp.column_stack([a,b])\nnp.r_[a,b]\nnp.c_[a,b]',
        'hstack을 언제나 열2개를 만드는 함수라고 기억하면1차원 입력에서 틀립니다.',[35], [
        P('a,b를 vstack으로 두 행 result로 만드세요.',NP+'a=np.array([2,3])\nb=np.array([5,7])','result=np.vstack([a,b])',A('result',[[2,3],[5,7]],[2,2])),
        P('a,b를 hstack으로 연결한 flat과 column_stack으로 열별로 배치한 columns를 만드세요.',NP+'a=np.array([2,3])\nb=np.array([5,7])','flat=np.hstack([a,b])\ncolumns=np.column_stack([a,b])',A('flat',[2,3,5,7],[4])+A('columns',[[2,5],[3,7]],[2,2])),
        P('r_로 a,b를 연결한 flat, c_로 a,b를 열로 쌓은 columns를 만들고 columns의 열별 평균 means를 구하세요.',NP+'a=np.array([1,3])\nb=np.array([10,20])','flat=np.r_[a,b]\ncolumns=np.c_[a,b]\nmeans=columns.mean(axis=0)',A('flat',[1,3,10,20],[4])+A('columns',[[1,10],[3,20]],[2,2])+A('means',[2,15],[2])),
    ])
    add('random_legacy', '난수 분포와 재현: 강의 표기',
        'rand는[0,1) 균등분포, randn은 평균0·표준편차1의 정규분포입니다. randint(low,high)는 high를 포함하지 않습니다. seed를 고정하면 같은 호출 순서의 결과를 재현할 수 있습니다. seed는 매번 같은 숫자만 출력하라는 뜻은 아닙니다.',
        'np.random.seed(0)\nnp.random.rand(3)\nnp.random.randn(3)\nnp.random.randint(1,7,size=3)',
        '분포의 이론 평균과 작은 표본 평균은 보통 다릅니다. 새 프로젝트에서는 다음 단원의 Generator를 권합니다.',[36,37,38,39,40,41], [
        P('전역 seed0을 설정하고 [0,1) 난수3개의 배열 result를 만드세요.',NP,'np.random.seed(0)\nresult=np.random.rand(3)',A('result',[.5488135039273248,.7151893663724195,.6027633760716439],[3])),
        P('전역 seed0을 설정하고 표준정규 난수3개의 배열 result를 만드세요.',NP,'np.random.seed(0)\nresult=np.random.randn(3)',A('result',[1.764052345967664,.4001572083672233,.9787379841057392],[3])),
        P('전역 seed0을 설정해 주사위1~6을5번 던진 정수 배열 rolls와 합 total을 만드세요.',NP,'np.random.seed(0)\nrolls=np.random.randint(1,7,size=5)\ntotal=rolls.sum()',A('rolls',[5,6,1,4,4],[5])+(C('total',20),)),
    ])
    add('random_generator', '독립된 난수 생성기',
        'default_rng(seed)는 독립된 Generator를 만듭니다. random(size), integers(low,high,size), normal(loc,scale,size)의 인자를 구분합니다. normal의 scale은 분산이 아니라 표준편차입니다.',
        'rng=np.random.default_rng(42)\nrng.random(3)\nrng.integers(1,7,size=3)\nrng.normal(loc=10,scale=2,size=3)',
        'Generator와 전역 np.random은 같은 seed라도 다른 수열입니다. 재현에는 버전·생성기·호출 순서도 기록하세요.',[36,40,41], [
        P('seed42 Generator로 [0,1) 난수3개의 result를 만드세요.',NP,'rng=np.random.default_rng(42)\nresult=rng.random(3)',A('result',[.7739560485559633,.4388784397520523,.8585979199113825],[3])),
        P('seed42 Generator로 평균10·표준편차2 정규분포 난수3개의 result를 만드세요.',NP,'rng=np.random.default_rng(42)\nresult=rng.normal(10,2,size=3)',A('result',[10.609434159508863,7.920031787519009,11.500902391612914],[3])),
        P('서로 독립된 seed42 Generator a,b로 각각 주사위4개를 만든 first와 second를 만드세요. 두 배열의 값은 같고 메모리는 독립적이어야 합니다.',NP,'a=np.random.default_rng(42)\nb=np.random.default_rng(42)\nfirst=a.integers(1,7,size=4)\nsecond=b.integers(1,7,size=4)',A('first',[1,5,4,3],[4])+A('second',[1,5,4,3],[4])+(C('__generators__:a:b',True,label='독립된 실제 Generator'),C('__memory__:first:second',False,label='독립된 결과 배열'))),
    ])
    add('memory', '뷰·복사와 strides',
        '기본 슬라이스는 보통 같은 메모리를 보는 뷰입니다. copy는 독립된 배열을 만듭니다. strides는 각 축을 한 칸 이동할 때 건너뛰는 바이트 수입니다. data는 원소 메모리 버퍼이며 화면 주소 문자열로 채점하지 않습니다.',
        'view=a[:,1:]\nindependent=a.copy()\na.strides\nnp.shares_memory(a,view)',
        '변수 이름을 바꾸거나 슬라이스했다고 독립 복사본이 되지 않습니다.',[7,21,29], [
        P('a 첫 행의 독립 복사본 result를 만들고 첫 값을99로 바꾸세요. a는 보존하세요.',NP+'a=np.array([[1,2],[3,4]])','result=a[0].copy()\nresult[0]=99',A('result',[99,2],[2])+A('a',[[1,2],[3,4]],[2,2])),
        P('int32인 a의 strides를 steps, 원소 버퍼 바이트 수를 buffer_bytes에 기록하세요.',NP+'a=np.array([[1,2,3],[4,5,6]],dtype=np.int32)','steps=a.strides\nbuffer_bytes=a.data.nbytes',[C('steps',[12,4]),C('buffer_bytes',24)]),
        P('a의 두 번째 열 뷰 view를 만들고 view[0]을50으로 변경하세요. 원본의 해당 값도 바뀌는지 a로 확인하고 공유 여부 shared를 기록하세요.',NP+'a=np.array([[1,2],[3,4]])','view=a[:,1]\nview[0]=50\nshared=np.shares_memory(a,view)',A('view',[50,4],[2])+A('a',[[1,50],[3,4]],[2,2])+(C('shared',True),C('__memory__:a:view',True,label='실제 메모리 공유'))),
    ])
    add('vectorize', '배열 연산과 실행 시간 해석',
        '배열 표현으로 여러 원소를 한꺼번에 계산하면 Python 반복문을 줄일 수 있습니다. time.perf_counter로 경과 시간을 재되 준비 시간을 섞지 않고 여러 번 측정합니다. 작은 입력·첫 실행·컴퓨터 부하에 따라 속도 관계가 바뀌므로 고정 배속은 보장하지 않습니다.',
        'result=a*a+2*a\nimport time\nt0=time.perf_counter()\nresult=a*a\nelapsed=time.perf_counter()-t0',
        '빠른 오답은 정답이 아닙니다. 같은 입력의 결과부터 비교하고 큰 배열은 메모리 사용을 고려하세요.',[32,33,34], [
        P('각 원소 x에 x²+2x를 적용한 result를 배열 연산으로 구하세요.',NP+'a=np.array([1,2,3,4])','result=a*a+2*a',A('result',[3,8,15,24],[4])),
        P('좌표 x에서 y=x²-1을 계산한 result를 만들고 음수인 결과만 negative에 담으세요.',NP+'x=np.array([-2,-1,0,1,2])','result=x*x-1\nnegative=result[result<0]',A('result',[3,0,-1,0,3],[5])+A('negative',[-1],[1])),
        P('scores에서 열별 평균을 뺀 centered와 열별 평균 check_mean을 구하세요. 원본 scores는 보존하세요.',NP+'scores=np.array([[1.,4.],[3.,8.],[5.,6.]])','centered=scores-scores.mean(axis=0)\ncheck_mean=centered.mean(axis=0)',A('centered',[[-2,-2],[0,2],[2,0]],[3,2])+A('check_mean',[0,0],[2])+A('scores',[[1,4],[3,8],[5,6]],[3,2])),
    ])
    return tuple(result)
