"""Authored NumPy tasks: predict, change one concept, then combine prerequisites."""
from .model import Lesson, problem as P, check as C, array as A

NP = 'import numpy as np\n'


def lessons():
    result = []
    def add(key, title, why, syntax, pitfall, pages, cases):
        result.append(Lesson('np_' + key, 'NumPy', title, why, syntax, pitfall,
                             'week_2_1_handout.pdf', tuple(pages), tuple(cases),
                             (result[-1].key,) if result else ('py_import',)))
    add('elementwise', '리스트와 배열의 덧셈',
        '리스트의 +는 연결이고 배열의 +는 같은 위치끼리 계산합니다. np.array로 만든 ndarray를 result에 담아 비교합니다. *와 /도 배열에서는 원소별 연산입니다.',
        'np.array([값, 값])\na + b\na * b', '리스트를 그대로 더하면 원소가 늘어납니다. 곱셈 *는 행렬곱이 아닙니다.', [3,4,6], [
        P('a와 b를 원소별로 더한 배열 result를 만드세요.', NP+'a = np.array([2, 5, 8])\nb = np.array([1, 3, 4])', 'result = a + b', A('result',[3,8,12],[3])),
        P('각 가격 prices에 수량 counts를 곱해 항목별 금액 result를 만드세요.', NP+'prices = np.array([4, 7, 2])\ncounts = np.array([3, 2, 5])', 'result = prices * counts', A('result',[12,14,10],[3])),
        P('리스트를 연결하는 잘못된 풀이를 고치세요. 배송 전후 차이 result를 배열로 계산하고 원본 리스트는 유지하세요.', NP+'before = [10, 20, 30]\nafter = [13, 18, 35]', 'result = np.array(after) - np.array(before)', A('result',[3,-2,5],[3])+(C('before',[10,20,30]),C('after',[13,18,35]))),
    ])
    add('shape', '같은 원소 수, 다른 차원',
        'ndim은 축 개수, shape는 각 축 길이, size는 전체 원소 수입니다. (3,), (1,3), (3,1)은 값이 같아도 형태가 다릅니다. 대괄호 중첩을 읽어 행과 열을 구분하세요.',
        'a.ndim\na.shape\na.size\nnp.array([[1, 2, 3]])', 'shape는 곱한 값이 아니라 순서가 있는 튜플입니다. 1차원 shape의 쉼표를 빠뜨리지 마세요.', [7,8,9], [
        P('a의 축 수를 dimensions, 형태를 shape, 전체 원소 수를 count에 담으세요.', NP+'a = np.array([[1,2,3],[4,5,6]])', 'dimensions = a.ndim\nshape = a.shape\ncount = a.size', [C('dimensions',2),C('shape',[2,3]),C('count',6)]),
        P('값 3,6,9를 가진 한 행 row와 한 열 column을 각각 2차원 배열로 만드세요.', NP, 'row = np.array([[3,6,9]])\ncolumn = np.array([[3],[6],[9]])', A('row',[[3,6,9]],[1,3])+A('column',[[3],[6],[9]],[3,1])),
        P('원소별 차이 result를 구하고 그 shape를 result_shape에 기록하세요. 1차원으로 펴지 마세요.', NP+'a = np.array([[5,7],[11,13]])\nb = np.array([[1,2],[3,4]])', 'result = a - b\nresult_shape = result.shape', A('result',[[4,5],[8,9]],[2,2])+(C('result_shape',[2,2]),)),
    ])
    add('dtype', '자료형과 저장 크기',
        'dtype은 원소 자료형입니다. int32 한 원소는 4바이트입니다. itemsize는 한 원소, nbytes는 전체 배열의 원소 저장 공간입니다. Python 객체 전체 메모리와 같은 뜻은 아닙니다.',
        'np.array([1,2], dtype=np.int32)\na.itemsize\na.nbytes\na.astype(np.float64)', '자료형 변환은 새 배열을 반환합니다. 소수를 정수로 바꾸면 소수 부분이 사라집니다.', [7], [
        P('result를 int32 배열 [2,4,6]으로 만들고 한 원소 바이트 수를 item_bytes에 기록하세요.', NP, 'result = np.array([2,4,6], dtype=np.int32)\nitem_bytes = result.itemsize', A('result',[2,4,6],[3],'int32')+(C('item_bytes',4),)),
        P('a를 float64로 변환한 result를 만들고 원본 a는 int32로 유지하세요.', NP+'a = np.array([1,3], dtype=np.int32)', 'result = a.astype(np.float64)', A('result',[1.,3.],[2],'float64')+A('a',[1,3],[2],'int32')),
        P('a와 b의 합 result를 int32 형태 그대로 만들고 전체 원소 바이트 수를 total_bytes에 담으세요.', NP+'a = np.array([[1,2],[3,4]], dtype=np.int32)\nb = np.array([[4,3],[2,1]], dtype=np.int32)', 'result = a + b\ntotal_bytes = result.nbytes', A('result',[[5,5],[5,5]],[2,2],'int32')+(C('total_bytes',16),)),
    ])
    add('broadcast_scalar', '스칼라와 한 행 브로드캐스팅',
        '배열에 숫자 하나를 더하면 각 원소에 적용됩니다. (행,열) 배열에 열 수가 맞는 1차원 배열을 더하면 각 행에 같은 보정값이 적용됩니다. 실제로 복제 배열을 직접 만들 필요는 없습니다.',
        'a + 10\na + np.array([열1보정, 열2보정])', '오른쪽 축부터 비교합니다. 길이만 비슷하다고 모든 모양이 호환되는 것은 아닙니다.', [10,11,13], [
        P('측정값 a의 각 원소에 5를 더한 result를 만드세요.', NP+'a = np.array([[1,2,3],[4,5,6]])', 'result = a + 5', A('result',[[6,7,8],[9,10,11]],[2,3])),
        P('세 센서의 보정값 offsets를 매 행에 적용한 result를 만드세요.', NP+'a = np.array([[10,20,30],[40,50,60]])\noffsets = np.array([1,-2,3])', 'result = a + offsets', A('result',[[11,18,33],[41,48,63]],[2,3])),
        P('각 열의 기준 baseline을 빼고 모든 원소를 2배한 result를 만드세요. a는 그대로 유지하세요.', NP+'a = np.array([[5,8],[7,10]])\nbaseline = np.array([1,3])', 'result = (a - baseline) * 2', A('result',[[8,10],[12,14]],[2,2])+A('a',[[5,8],[7,10]],[2,2])),
    ])
    add('broadcast_column', '행마다 다른 보정값과 shape 오류',
        '(2,3)과 (2,)는 마지막 축 3과2가 달라 연산할 수 없습니다. 행마다 하나씩 보정하려면 (2,1) 열 형태가 필요합니다. 크기가 같거나 한쪽이1인 축만 호환됩니다.',
        'np.array([[10],[20]]) + np.array([1,2,3])', '오류 메시지의 두 shape를 오른쪽부터 비교하세요. 값을 반복해서 타이핑하는 대신 의도한 축을 표현합니다.', [12,13,14,15], [
        P('row와 column을 더해 (2,3) result를 만드세요.', NP+'row = np.array([1,2,3])\ncolumn = np.array([[10],[20]])', 'result = row + column', A('result',[[11,12,13],[21,22,23]],[2,3])),
        P('각 행에 100,200을 각각 더하세요. offsets를 올바른 2차원 열 배열로 만들고 result를 계산하세요.', NP+'a = np.array([[1,2,3],[4,5,6]])', 'offsets = np.array([[100],[200]])\nresult = a + offsets', A('offsets',[[100],[200]],[2,1])+A('result',[[101,102,103],[204,205,206]],[2,3])),
        P('행별 row_offset을 더한 뒤 열별 col_offset을 빼서 result를 만드세요.', NP+'a = np.array([[10,20],[30,40]])\nrow_offset = np.array([[1],[2]])\ncol_offset = np.array([3,5])', 'result = a + row_offset - col_offset', A('result',[[8,16],[29,37]],[2,2])),
    ])
    add('creation', 'zeros·ones·full·eye로 배열 준비',
        'zeros/ones/full은 shape에 맞춰 같은 값을 채웁니다. eye는 주대각선이1인 단위행렬을 만듭니다. 기본 실수형과 dtype 명시의 차이를 관찰합니다.',
        'np.zeros((행,열))\nnp.ones((행,열))\nnp.full((행,열), 값)\nnp.eye(크기)', 'shape는 튜플 하나로 전달합니다. zeros(2,3)은 shape (2,3)을 뜻하지 않습니다.', [16], [
        P('영으로 채운 (2,3) result를 만드세요.', NP, 'result = np.zeros((2,3))', A('result',[[0,0,0],[0,0,0]],[2,3])),
        P('대각선만1인 (3,3) identity와 모든 값이7인 (2,2) filled를 만드세요.', NP, 'identity = np.eye(3)\nfilled = np.full((2,2), 7)', A('identity',[[1,0,0],[0,1,0],[0,0,1]],[3,3])+A('filled',[[7,7],[7,7]],[2,2])),
        P('모두1인 (2,3) 배열에 열별 [2,4,6]을 곱해 result를 만드세요.', NP, 'result = np.ones((2,3)) * np.array([2,4,6])', A('result',[[2,4,6],[2,4,6]],[2,3])),
    ])
    add('ranges', '간격과 개수: arange·linspace·logspace',
        'arange는 간격을 지정하고 끝은 원칙적으로 제외합니다. linspace는 개수를 지정하고 기본적으로 양끝을 포함합니다. logspace의 시작과 끝은 값이 아니라 지수입니다.',
        'np.arange(시작, 끝, 간격)\nnp.linspace(시작, 끝, 개수)\nnp.logspace(시작지수, 끝지수, 개수)', '소수 간격 arange는 부동소수점 오차에 주의합니다. 개수가 중요하면 linspace가 명확합니다.', [17,18], [
        P('0 이상10 미만의 짝수를 result 배열로 만드세요.', NP, 'result = np.arange(0,10,2)', A('result',[0,2,4,6,8],[5])),
        P('양끝 포함0부터1까지5개 균등한 값 points, 10의0~3제곱4개 scales를 만드세요.', NP, 'points = np.linspace(0,1,5)\nscales = np.logspace(0,3,4)', A('points',[0,.25,.5,.75,1],[5])+A('scales',[1,10,100,1000],[4])),
        P('0부터6까지 양끝 포함4개 값을 만든 뒤 원소별 제곱 result를 계산하세요.', NP, 'points = np.linspace(0,6,4)\nresult = points ** 2', A('result',[0,4,16,36],[4])),
    ])
    add('slicing', '행·열을 한 쌍의 대괄호로 선택',
        'a[행, 열]로 두 축을 독립적으로 고릅니다. 슬라이스 끝은 제외됩니다. 정수 인덱스는 축을 없애고 범위는 축을 유지합니다. a[1:][0:2]는 행 슬라이스를 두 번 적용합니다.',
        'a[1:, :2]\na[:, 1]\na[:, 1:2]\na[::2, ::2]', '연속한 대괄호와 쉼표로 구분한 두 축 선택은 다릅니다.', [21,22,23,24,26,27], [
        P('첫 행을 제외하고 처음 두 열만 선택한 (2,2) result를 만드세요.', NP+'a = np.arange(1,10).reshape(3,3)', 'result = a[1:, :2]', A('result',[[4,5],[7,8]],[2,2])),
        P('두 번째 열을 선택하되 (3,1)의 2차원 result로 유지하세요.', NP+'a = np.array([[1,2,3],[4,5,6],[7,8,9]])', 'result = a[:,1:2]', A('result',[[2],[5],[8]],[3,1])),
        P('a의 행·열을 한 칸씩 건너뛴 부분 배열에10을 더한 result를 만드세요. a는 유지하세요.', NP+'a = np.arange(1,17).reshape(4,4)', 'result = a[::2,::2] + 10', A('result',[[11,13],[19,21]],[2,2])+A('a',[[1,2,3,4],[5,6,7,8],[9,10,11,12],[13,14,15,16]],[4,4])),
    ])
    add('mask', '조건으로 원소 선택',
        '비교식은 같은 형태의 Boolean 배열을 만듭니다. a[조건]은 True인 원소를 순서대로 모읍니다. &와 |로 조건을 합칠 때는 각 비교식을 괄호로 묶습니다.',
        'a[a % 2 == 0]\na[(a >= 3) & (a < 8)]', '배열 조건에 Python의 and/or를 쓰면 진릿값이 모호하다는 오류가 납니다.', [25], [
        P('a의 짝수만 순서대로 담은 result를 만드세요.', NP+'a = np.array([[1,2,3],[4,5,6]])', 'result = a[a % 2 == 0]', A('result',[2,4,6],[3])),
        P('a에서3 이상8 미만인 원소만 result에 담으세요.', NP+'a = np.array([9,3,1,7,8,5])', 'result = a[(a >= 3) & (a < 8)]', A('result',[3,7,5],[3])),
        P('a의 첫 두 열에서 양수인 값만 골라10배한 result를 만드세요.', NP+'a = np.array([[-1,2,99],[3,-4,99],[5,6,99]])', 'part = a[:,:2]\nresult = part[part > 0] * 10', A('result',[20,30,50,60],[4])),
    ])
    add('reshape', '원소 수를 유지하며 형태 바꾸기',
        'reshape는 원소 순서와 개수를 유지하며 축을 다시 나눕니다. -1은 한 축의 길이를 추론합니다. flatten은 독립된1차원 복사본을 만듭니다.',
        'a.reshape(2, 3)\na.reshape(-1, 2)\na.flatten()', '크기의 곱이 전체 원소 수와 같아야 합니다. -1을 두 번 쓰면 추론할 수 없습니다.', [29], [
        P('a를(2,3) 형태의 result로 바꾸세요.', NP+'a = np.arange(6)', 'result = a.reshape(2,3)', A('result',[[0,1,2],[3,4,5]],[2,3])),
        P('a를 열2개, 행은 추론하는 result로 바꾸세요.', NP+'a = np.arange(1,9)', 'result = a.reshape(-1,2)', A('result',[[1,2],[3,4],[5,6],[7,8]],[4,2])),
        P('a를 독립된1차원 result로 펴서 첫 값만99로 바꾸세요. 원본 a는 유지하세요.', NP+'a = np.array([[1,2],[3,4]])', 'result = a.flatten()\nresult[0] = 99', A('result',[99,2,3,4],[4])+A('a',[[1,2],[3,4]],[2,2])),
    ])
    return tuple(result)
