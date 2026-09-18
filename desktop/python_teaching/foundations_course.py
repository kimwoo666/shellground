"""Small prerequisites which make library exercises reproducible, not rote."""
from .model import Lesson, problem as P, check as C


def lessons():
    result=[]
    def add(key,title,why,syntax,pitfall,cases,pages=(24,25),source='week_1_2_handout.pdf'):
        result.append(Lesson('py_'+key,'Python 기초',title,why,syntax,pitfall,
            source,tuple(pages),tuple(cases),(result[-1].key,) if result else ('py_import',)))
    add('kernel','셀을 고쳐도 과거 계산은 바뀌지 않음',
        '노트북은 문서이고 커널은 변수를 기억하는 실행 프로세스입니다. 셀을 편집한 것과 실행한 것은 다릅니다. 이 앱도 같은 Python 프로세스에서 코드를 이어 실행합니다. 아래 코드를 한 줄씩 나눠 실행해 total이 언제 바뀌는지 확인하세요. 새 실습 시작은 변수 메모리를 비웁니다.',
        'price=8\ntotal=price*3\nprice=10\nprint(total)\ntotal=price*3',
        '변수를 바꾼다고 이미 계산된 다른 변수가 자동 갱신되지는 않습니다. 노트북을 제출하기 전 새 커널에서 위에서 아래로 재실행해 재현성을 확인하세요.',[
        P('price만 바뀐 현재 상태에서 total을 최신 price로 다시 계산하세요. 수량은3입니다. 기존 total값은 old_total에 먼저 남기세요.','price=8\ntotal=price*3\nprice=10','old_total=total\ntotal=price*3',[C('old_total',24),C('total',30)]),
        P('discount를5로 바꾸고 net을 다시 계산하세요. 기존 net은 before에 남기세요.','price=20\ndiscount=2\nnet=price-discount','before=net\ndiscount=5\nnet=price-discount',[C('before',18),C('discount',5),C('net',15)]),
        P('없어진 변수에 의존하지 않도록 price=12와 count=4부터 정의해 total을 구하세요. 이전 실습 변수는 존재하지 않습니다.','','price=12\ncount=4\ntotal=price*count',[C('price',12),C('count',4),C('total',48)]),
    ],pages=(11,12,13,14),source='Week 1_1.pdf')
    add('set','중복을 제거하는 집합',
        'set은 중복 없는 원소의 집합입니다. 합집합|, 교집합&, 차집합-를 사용할 수 있습니다. 집합에는 정해진 순서가 없으므로 화면 순서나 첫 항목으로 의미를 판단하지 않습니다. 비교·제출할 때 sorted로 순서를 명시할 수 있습니다.',
        'unique=set(values)\na & b\na | b\na - b\nsorted(unique)',
        '{}는 빈 집합이 아니라 사전입니다. 빈 집합은 set()입니다.',[
        P('values의 중복을 없애고 오름차순 목록 result를 만드세요.','values=[3,1,3,2,1]','result=sorted(set(values))',[C('result',[1,2,3])]),
        P('a와 b에 모두 있는 이름을 알파벳순 목록 common으로 만드세요.',"a={'Ann','Bo','Cy'}\nb={'Bo','De'}",'common=sorted(a & b)',[C('common',['Bo'])]),
        P('required에서 done을 제외한 이름들을 알파벳순 pending으로 만들고 남은 개수 count를 구하세요.',"required={'numpy','pandas','matplotlib'}\ndone={'numpy'}",'pending=sorted(required-done)\ncount=len(pending)',[C('pending',['matplotlib','pandas']),C('count',2)]),
    ])
    add('functions','함수의 입력과 반환값',
        'def로 여러 번 쓸 계산에 이름을 붙입니다. 인자는 입력, return은 호출한 쪽에 돌려줄 값입니다. print는 화면 출력이며 반환값을 대신하지 않습니다. 들여쓰기는 함수의 범위를 정합니다.',
        'def double(x):\n    return x*2\nresult=double(3)',
        '함수 안에서 계산만 하고 return을 빠뜨리면 None을 받습니다. 이 단원은 라이브러리 함수의 인자·반환값 이해를 위한 보충입니다.',[
        P('double(x)를 정의해 입력의2배를 반환하고 double(3),double(-2)를 results 목록에 담으세요.','','def double(x):\n    return x*2\nresults=[double(3),double(-2)]',[C('results',[6,-4]),C('__probes__',[0,10,-14],['double'],'double의 다른 입력')],probes={'double':[[0],[5],[-7]]}),
        P('area(width,height)를 정의해 직사각형 넓이를 반환하고3×4와5×2의 넓이를 results에 담으세요.','','def area(width,height):\n    return width*height\nresults=[area(3,4),area(5,2)]',[C('results',[12,10]),C('__probes__',[6,0,10],['area'],'area의 다른 입력')],probes={'area':[[2,3],[0,5],[2.5,4]]}),
        P('c_to_f(c)를 정의해 섭씨×9/5+32를 반환하고0도,20도의 결과를 results에 담으세요.','','def c_to_f(c):\n    return c*9/5+32\nresults=[c_to_f(0),c_to_f(20)]',[C('results',[32,68]),C('__probes__',[-40,212,50],['c_to_f'],'온도 변환의 다른 입력')],probes={'c_to_f':[[-40],[100],[10]]}),
    ])
    add('iteration','반복·조건과 목록 내포',
        'for는 각 값을 순서대로 처리하며 if는 조건이 맞을 때 실행합니다. 리스트 내포는 변환과 선택을 간결하게 표현합니다. 대량 수치 계산에서는 이후 NumPy 배열 연산과 결과·속도를 비교합니다.',
        'result=[]\nfor x in values:\n    if x>0:\n        result.append(x*2)\n# 같은 목적: [x*2 for x in values if x>0]',
        '반복문 안의 들여쓰기와 비교 경계를 점검하세요. 원본 목록을 돌면서 제거하는 방식은 항목을 건너뛸 수 있습니다.',[
        P('values의 양수만 두 배로 만든 목록 result를 순서대로 만드세요.','values=[-2,1,0,3]','result=[x*2 for x in values if x>0]',[C('result',[2,6])]),
        P('values 중3의 배수만 담은 selected와 그 합 total을 구하세요.','values=[1,3,4,6,9]','selected=[x for x in values if x%3==0]\ntotal=sum(selected)',[C('selected',[3,6,9]),C('total',18)]),
        P('orders에서 count가2 이상인 주문의 price×count를 amounts에 순서대로 담으세요. 주문 원본은 유지하세요.',"orders=[{'price':5,'count':1},{'price':3,'count':4},{'price':7,'count':2}]","amounts=[o['price']*o['count'] for o in orders if o['count']>=2]",[C('amounts',[12,14]),C('orders',[{'price':5,'count':1},{'price':3,'count':4},{'price':7,'count':2}])]),
    ])
    add('module_file','직접 만든 모듈 가져오기',
        '모듈은 Python 정의가 담긴 파일이고 패키지는 모듈을 조직하는 단위입니다. 같은 작업 폴더의 helpers.py를 import helpers로 불러올 수 있습니다. from helpers import 함수는 해당 이름만 가져옵니다. 설치(pip/conda)와 실행 중 import를 구분하세요.',
        'import helpers\nresult=helpers.square(3)\nfrom helpers import square',
        'numpy.py 또는 pandas.py 같은 이름으로 자기 파일을 만들면 설치된 라이브러리를 가릴 수 있습니다. import한 모듈은 프로세스에 캐시됩니다.',[
        P('helpers.py의 square를 가져와7의 제곱 result를 구하세요.','','import helpers\nresult=helpers.square(7)',[C('result',49)],files={'helpers.py':{'text':'def square(x):\n    return x*x\n'}}),
        P('unit_tools.py의 c_to_f만 가져와0도와20도를 변환한 result 목록을 만드세요.','','from unit_tools import c_to_f\nresult=[c_to_f(0),c_to_f(20)]',[C('result',[32,68])],files={'unit_tools.py':{'text':'def c_to_f(c):\n    return c*9/5+32\n'}}),
        P('price_tools.py를 pt라는 별칭으로 가져와 orders 각 주문의 금액을 amounts에 담으세요.',"orders=[{'price':4,'count':3},{'price':5,'count':2}]","import price_tools as pt\namounts=[pt.cost(o['price'],o['count']) for o in orders]",[C('amounts',[12,10])],files={'price_tools.py':{'text':'def cost(price,count):\n    return price*count\n'}}),
    ],pages=(26,27,28,29,30,34))
    add('standard','표준 라이브러리의 역할',
        'datetime은 날짜/시간, random은 난수, math는 수학 함수를 제공합니다. time은 경과 시간 측정, urllib는URL 처리·통신, turtle은 별도 그래픽 창을 사용하는 교육용 도구입니다. 이 실습은 네트워크·외부 GUI를 열지 않습니다. URL 파싱은 통신 없이 할 수 있습니다.',
        "from datetime import date\ndays=(date(2026,1,3)-date(2026,1,1)).days\nfrom urllib.parse import urlparse\nhost=urlparse('https://example.org/data').netloc",
        'random.Random과 NumPy Generator는 서로 다른 생성기입니다. turtle의 별도 GUI는 이 앱의 Matplotlib 출력창과 다릅니다.',[
        P('2026년1월1일부터1월10일까지 날짜 차이를 days에 담으세요.','','from datetime import date\ndays=(date(2026,1,10)-date(2026,1,1)).days',[C('days',9)]),
        P('url을 파싱해 호스트 host와 경로 path를 기록하세요. 서버 접속은 하지 마세요.',"url='https://example.org/data/scores.csv?year=2026'",'from urllib.parse import urlparse\nparsed=urlparse(url)\nhost=parsed.netloc\npath=parsed.path',[C('host','example.org'),C('path','/data/scores.csv')]),
        P('지정 seed0의 독립 random.Random으로 정수1~6을5번 뽑은 rolls를 만드세요. randint의 양 끝을 포함합니다.','','import random\nrng=random.Random(0)\nrolls=[rng.randint(1,6) for _ in range(5)]',[C('rolls',[4,4,1,3,5])]),
    ],pages=(26,27,28,29,30))
    add('units','픽셀·비트와 데이터 용량',
        '샘플링은 어느 시점/위치에서 측정할지, 양자화는 값을 어떤 단계로 나눌지, 인코딩은 그 단계를 비트로 어떻게 표현할지 정합니다.8비트는256단계입니다. 아래는 압축·파일 헤더를 제외한 순수 픽셀 데이터 크기입니다.1KiB=1024바이트,1kB=1000바이트입니다.',
        'levels=2**bits\nbytes_count=width*height*channels*bits_per_channel//8',
        '압축 PNG/JPEG 파일 크기는 단순 픽셀 계산과 같지 않습니다. 벡터 그림은 도형을 기술하므로 같은 방식으로 용량을 계산하지 않습니다.',[
        P('가로640,세로480의8비트 흑백 원시 이미지 바이트 수 bytes_count를 구하세요. 헤더와 압축은 없습니다.','','bytes_count=640*480',[C('bytes_count',307200)]),
        P('RGB 각 채널8비트, 가로100,세로50인 원시 이미지의 바이트 수 bytes_count와 KiB 크기 kib를 구하세요.','','bytes_count=100*50*3\nkib=bytes_count/1024',[C('bytes_count',15000),C('kib',15000/1024)]),
        P('12비트 양자화의 단계 수 levels와1초당1000개 샘플을10초간16비트 정수로 저장할 때 필요한 bytes_count를 구하세요. 채널은1개이고 헤더·압축은 없습니다.','','levels=2**12\nbytes_count=1000*10*16//8',[C('levels',4096),C('bytes_count',20000)]),
    ],pages=(13,14,15,16,17,18,19,20,21))
    return tuple(result)
