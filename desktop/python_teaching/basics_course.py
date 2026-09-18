from .model import Lesson, problem as P, check as C


def lessons():
    data = []
    def add(key, title, why, syntax, pitfall, cases, pages=(24,25)):
        data.append(Lesson('py_' + key, 'Python 기초', title, why, syntax, pitfall,
                           'week_1_2_handout.pdf', tuple(pages), tuple(cases),
                           (data[-1].key,) if data else ()))
    add('values', '값을 이름에 저장하고 계산',
        '=는 오른쪽 값을 계산해 왼쪽 이름에 저장합니다. print는 값을 보여주지만 변수에 저장하는 작업을 대신하지 않습니다. 정수/실수/문자열을 구분하며 숫자 계산과 문자열 연결은 다릅니다.',
        'count = 3\nprice = 2.5\ntotal = count * price\nprint(total)', 'result라는 이름이 목표라면 출력만 하지 말고 그 이름에 결과를 저장하세요.', [
        P('수량3, 단가2.5의 총액을 total에 저장하세요.', '', 'total = 3 * 2.5', [C('total',7.5)]),
        P('매출 revenue에서 비용 cost를 뺀 profit을 만드세요.', 'revenue = 120\ncost = 85', 'profit = revenue - cost', [C('profit',35)]),
        P('온도 celsius를 화씨 fahrenheit로 바꾸세요. 공식은 섭씨×9/5+32입니다. unit에는 문자열 F를 저장하세요.', 'celsius = 20', "fahrenheit = celsius * 9 / 5 + 32\nunit = 'F'", [C('fahrenheit',68),C('unit','F')]),
    ])
    add('sequences', '리스트·튜플과 인덱스',
        '리스트는 순서가 있는 값을 담고 0부터 인덱싱합니다. 슬라이스 [시작:끝]은 끝을 제외합니다. 튜플은 항목을 바꿀 수 없는 순서 자료형이며, shape와 함수의 여러 반환값에서 자주 만납니다.',
        'values = [2, 4, 6]\nvalues[0]\nvalues[1:]\nshape = (2, 3)', '첫 위치는1이 아니라0입니다. 리스트+리스트는 숫자별 덧셈이 아니라 연결입니다.', [
        P('values의 첫 값을 first, 마지막 두 값을 tail에 담으세요.', 'values = [4, 7, 9]', 'first = values[0]\ntail = values[1:]', [C('first',4),C('tail',[7,9])]),
        P('a와 b를 순서대로 연결한 combined, 길이 count를 만드세요.', 'a = [1,2]\nb = [8,9]', 'combined = a + b\ncount = len(combined)', [C('combined',[1,2,8,9]),C('count',4)]),
        P('values에서 위치1~3의 값으로 selected를 만들고 첫 값과 마지막 값의 차이를 difference에 저장하세요.', 'values = [10,20,30,40,50]', 'selected = values[1:4]\ndifference = selected[-1] - selected[0]', [C('selected',[20,30,40]),C('difference',20)]),
    ])
    add('methods', '객체·메서드와 원본 변경',
        '객체는 값과 사용할 동작을 함께 가집니다. object.method() 형태의 메서드는 원본을 바꾸거나 새 값을 반환할 수 있습니다. list.sort()는 원본을 정렬하고 None을 반환하며 sorted는 새 리스트를 만듭니다.',
        'items.sort()\ncopy = sorted(items)\nitems.append(값)', 'result = items.sort()는 정렬된 리스트가 아니라 None을 저장합니다.', [
        P('items 자체를 오름차순 정렬하세요.', 'items = [8,2,5]', 'items.sort()', [C('items',[2,5,8])]),
        P('원본 items는 유지하고 정렬한 별도 result를 만드세요.', 'items = [9,3,6]', 'result = sorted(items)', [C('items',[9,3,6]),C('result',[3,6,9])]),
        P('items에4를 추가하고 정렬하세요. 가장 작은 값과 가장 큰 값을 endpoints에 리스트로 담으세요.', 'items = [7,1,5]', 'items.append(4)\nitems.sort()\nendpoints = [items[0], items[-1]]', [C('items',[1,4,5,7]),C('endpoints',[1,7])]),
    ])
    add('mapping', '사전과 이름으로 값 찾기',
        'dict는 키와 값을 연결합니다. data[키]로 값을 찾고 새 키에 대입하면 항목이 추가됩니다. 나중의 pandas 열 이름 선택과 닮았지만 사전 자체가 표는 아닙니다.',
        "record = {'count': 3, 'price': 4}\nrecord['count']\nrecord['total'] = 12", '따옴표가 없는 price는 문자열 키가 아니라 변수 이름입니다. 없는 키는 KeyError가 납니다.', [
        P('record에서 name을 읽어 customer에 저장하세요.', "record = {'name':'Min', 'count':3}", "customer = record['name']", [C('customer','Min')]),
        P('record의 price×count를 total 키에 추가하세요. 기존 값은 유지하세요.', "record = {'price':7, 'count':4}", "record['total'] = record['price'] * record['count']", [C('record',{'price':7,'count':4,'total':28})]),
        P('각 주문의 수량을 counts 리스트에 순서대로 담고 총수량 total_count를 만드세요.', "orders = [{'count':2}, {'count':5}]", "counts = [orders[0]['count'], orders[1]['count']]\ntotal_count = sum(counts)", [C('counts',[2,5]),C('total_count',7)]),
    ])
    add('import', '모듈 가져오기와 별칭',
        '설치는 패키지를 환경에 준비하는 과정이고 import는 현재 Python 프로세스에서 불러오는 과정입니다. 표준 math는 Python에 포함됩니다. np·pd·plt는 import as로 정한 별칭이지 별도 패키지 이름이 아닙니다.',
        'import math\nmath.sqrt(9)\nimport math as m\nfrom math import pi', 'pip install은 Python 문법이 아니라 터미널 명령입니다. 이 코드 칸에 그대로 입력하지 않습니다. import *는 이름 충돌 때문에 피합니다.', [
        P('math를 가져와25의 제곱근 root를 만드세요.', '', 'import math\nroot = math.sqrt(25)', [C('root',5)]),
        P('math를 m이라는 별칭으로 가져와 π/2 라디안의 사인 값을 result에 저장하세요.', '', 'import math as m\nresult = m.sin(m.pi / 2)', [C('result',1)]),
        P('points의 두 좌표 차이 dx,dy를 사용해 원점에서의 거리를 distance에 담으세요. sqrt를 math에서 가져오세요.', 'points = [3,4]', 'from math import sqrt\ndx = points[0]\ndy = points[1]\ndistance = sqrt(dx**2 + dy**2)', [C('distance',5)]),
    ], pages=(26,27,28,29,30,34))
    return tuple(data)
