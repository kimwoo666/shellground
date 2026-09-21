"""Teach pandas syntax before assessing it; keep existing unit IDs and tasks.

Examples are independent of the scored fixtures and of previous cells. Importing
this authoring module never imports pandas or starts an interpreter.
"""
from dataclasses import replace
from functools import lru_cache

from .model import GuidedStep, problem as P, check as C, frame as F, series as S

PD = 'import pandas as pd\n'
NAN = {'special': 'nan'}


def step(title, explanation, code, observation, checks, *, files=None):
    return GuidedStep(title, explanation, observation,
                      P(title, '', PD + code, checks, files=files or {}))


@lru_cache(maxsize=1)
def sequences():
    table = "df = pd.DataFrame({'score':[6,9,4], 'visits':[2,1,3]}, index=['Kim','Lee','Park'])\n"
    scores = "df = pd.DataFrame({'math':[10,20], 'english':[30,40]}, index=['Kim','Lee'])\n"
    seq = {}
    seq['pd_series'] = (
        step('pandas 코드의 기호부터 읽기',
             'import pandas as pd는 pandas를 pd라는 짧은 이름으로 불러옵니다. pd.Series는 pandas의 Series 생성 기능입니다. '
             '() 안에 재료를 넣어 호출하며 [6, 9]는 순서가 있는 값 목록입니다. '
             'result = ...는 오른쪽 결과를 result라는 변수에 보관합니다. print(result)는 화면에 보여 줄 뿐 저장을 대신하지 않습니다. '
             '문제에서 result를 만들라고 하면 그 이름의 변수가 있어야 합니다.',
             'result = pd.Series([6, 9])\nprint(result)',
             '왼쪽 0, 1은 자동 행 라벨이고 오른쪽 6, 9가 값입니다. dtype은 값의 자료형 표시입니다. '
             '값 목록을 [6, 9, 12]로 바꾸면 라벨 2가 추가되는지 확인하세요.', S('result',[6,9],[0,1])),
        step('index=로 값에 이름 붙이기',
             "index=['Kim','Lee']에서 index는 인자 이름, = 뒤의 목록은 전달할 값입니다. "
             "'Kim' 같은 따옴표는 문자열을 뜻합니다. 값 목록과 라벨 목록의 길이가 같아야 하며 순서대로 대응합니다.",
             "result = pd.Series([6, 9], index=['Kim', 'Lee'])\nprint(result)",
             'Kim 옆은 6, Lee 옆은 9입니다. index는 데이터에 덧붙인 세 번째 값이 아닙니다. '
             "라벨을 ['Lee','Kim']으로 바꾸면 값의 이름만 순서대로 바뀝니다.", S('result',[6,9],['Kim','Lee'])),
        step('loc는 라벨, iloc는 0부터 센 위치',
             's.loc[라벨]은 이름으로 값을 찾고 s.iloc[위치]는 순서로 찾습니다. 선택에는 ()가 아닌 []를 씁니다. '
             '위치는 첫 번째가 0, 두 번째가 1입니다. 숫자 라벨도 위치 번호와 구분해야 합니다.',
             's = pd.Series([6, 9, 12], index=[30, 10, 20])\nselected = s.loc[30]\nsecond = s.iloc[1]\nprint(selected, second)',
             '6과 9가 출력됩니다. 라벨 30은 첫 번째 값이고, 위치 1은 라벨 10의 값입니다. '
             's.iloc[30]으로 바꾸면 범위를 벗어납니다.', (C('selected',6), C('second',9))),
        step('여러 라벨을 원하는 순서로 선택하기',
             "s.loc[['Lee','Kim']]의 안쪽 []는 라벨 목록이고 바깥쪽 []는 loc의 선택 기호입니다. "
             '하나를 고르면 값 하나, 목록을 주면 라벨을 가진 Series가 됩니다.',
             "s = pd.Series([6, 9, 12], index=['Kim','Lee','Park'])\nresult = s.loc[['Lee','Kim']]\nprint(result)",
             'Lee 9, Kim 6 순서입니다. 원래 s의 순서를 바꾸는 것이 아니라 선택 결과를 result에 저장합니다.',
             S('result',[9,6],['Lee','Kim'])),
        step('선택한 Series의 합계 구하기',
             'result.sum()의 점은 result가 가진 기능에 접근하고 ()는 합계 계산을 실행합니다. '
             'sum 뒤에 ()가 없으면 계산 결과가 아닙니다. 라벨이 아니라 선택된 값들만 더합니다.',
             "s = pd.Series([6, 9, 12], index=['Kim','Lee','Park'])\nresult = s.loc[['Lee','Kim']]\ntotal = result.sum()\nprint(result)\nprint(total)",
             '두 라벨과 함께 값 9, 6이 보이고 합계 15가 출력됩니다. result는 Series, total은 숫자 하나입니다.',
             S('result',[9,6],['Lee','Kim']) + (C('total',15),)),
    )
    seq['pd_frame'] = (
        step('사전의 키는 열, 목록은 그 열의 값',
             "{'score':[6,9], 'visits':[2,1]}은 Python 사전입니다. {} 안에서 키:값을 짝짓고 쉼표로 구분합니다. "
             'score와 visits는 열 이름, 각 목록은 위에서 아래로 들어갈 값입니다. pd.DataFrame(...)은 이를 2차원 표로 만듭니다.',
             "data = {'score':[6,9], 'visits':[2,1]}\nresult = pd.DataFrame(data)\nprint(result)",
             '0행은 score 6 / visits 2, 1행은 score 9 / visits 1입니다. 각 열의 목록 길이가 달라지면 표를 만들 수 없습니다.',
             F('result',[[6,2],[9,1]],[0,1],['score','visits'])),
        step('행 라벨은 index=로 지정하기',
             'DataFrame(data, index=라벨목록)에서 첫 번째 인자는 표의 재료이고 index는 행 이름입니다. '
             '사전을 먼저 data에 저장해도, () 안에 직접 써도 같은 방식입니다. 열 이름은 사전의 키에서 가져옵니다.',
             "data = {'score':[6,9], 'visits':[2,1]}\nresult = pd.DataFrame(data, index=['Kim','Lee'])\nprint(result)",
             'Kim, Lee는 왼쪽 행 라벨입니다. score, visits라는 두 데이터 열 외에 이름 열이 추가되는 것은 아닙니다.',
             F('result',[[6,2],[9,1]],['Kim','Lee'],['score','visits'])),
        step('shape·index·columns와 tolist()',
             'df.shape는 (행 수, 열 수)이고 df.index는 행 라벨, df.columns는 열 라벨입니다. 이 속성들에는 ()를 붙이지 않습니다. '
             '반면 .tolist()는 Index를 일반 Python 목록으로 바꾸는 메서드라 ()가 필요합니다. '
             'labels = df.index.tolist()는 행 라벨 목록을 labels에 보관한다는 뜻입니다.',
             table + 'labels = df.index.tolist()\nnames = df.columns.tolist()\nshape = df.shape\nprint(labels)\nprint(names)\nprint(shape)',
             "['Kim','Lee','Park'], ['score','visits'], (3,2)가 순서대로 나옵니다. 행 라벨은 shape의 열 수에 포함되지 않습니다.",
             (C('labels',['Kim','Lee','Park']),C('names',['score','visits']),C('shape',[3,2]))),
    )
    seq['pd_csv'] = (
        step('파일 이름을 전달해 CSV 읽기',
             'pd.read_csv(파일이름)는 쉼표로 구분된 파일을 읽어 DataFrame을 반환합니다. 파일이름은 문자열로 씁니다. '
             '기본 설정에서는 첫 줄을 열 이름으로 읽고 숫자 행 라벨을 붙입니다. 이 예제의 mini.csv는 실습 폴더에 준비되어 있습니다.',
             "result = pd.read_csv('mini.csv')\nprint(result)",
             '파일 첫 줄 name,score가 두 열 이름이 되고 이어지는 두 줄이 데이터가 됩니다.',
             F('result',[['Kim',6],['Lee',9]],[0,1],['name','score']),
             files={'mini.csv':{'text':'name,score\nKim,6\nLee,9\n'}}),
        step('index_col: 한 열을 행 라벨로 쓰기',
             "index_col='name'은 name 열을 행 라벨로 쓰라는 인자입니다. "
             'CSV 안의 열 이름과 정확히 맞아야 합니다. 이 열은 일반 데이터 열에서 빠집니다.',
             "result = pd.read_csv('mini.csv', index_col='name')\nprint(result)",
             '행 라벨은 Kim, Lee이고 데이터 열은 score 하나입니다.', F('result',[[6],[9]],['Kim','Lee'],['score']),
             files={'mini.csv':{'text':'name,score\nKim,6\nLee,9\n'}}),
        step('header=None과 names: 첫 줄도 데이터일 때',
             '열 이름 줄이 없는 파일에서 기본 설정을 쓰면 첫 관측값을 열 이름으로 잘못 읽습니다. '
             'header=None은 헤더가 없다는 뜻이고 names=[...]는 열 이름을 지정합니다. None은 문자열이 아니므로 따옴표를 붙이지 않습니다.',
             "result = pd.read_csv('mini-raw.csv', header=None, names=['name','score'])\nprint(result)",
             'Kim,6이 첫 데이터 행으로 남습니다. index_col을 지정하지 않았으므로 행 라벨은 0,1입니다.',
             F('result',[['Kim',6],['Lee',9]],[0,1],['name','score']),
             files={'mini-raw.csv':{'text':'Kim,6\nLee,9\n'}}),
        step('encoding: 파일에 맞는 문자 인코딩',
             "encoding='cp949'는 CP949로 저장된 파일을 해석하는 방식입니다. 한글 파일이라고 항상 CP949인 것은 아닙니다. "
             'UTF-8 파일에는 기본 UTF-8을 사용하세요. 인자 여러 개는 쉼표로 구분합니다. CSV 셀 안의 쉼표는 파일의 쌍따옴표로 보호됩니다.',
             "result = pd.read_csv('mini-ko.csv', encoding='cp949', index_col='이름')\nprint(result)",
             '가온의 메모 서울,종로는 한 셀입니다. 파일을 split으로 직접 나누면 이 구조를 잃습니다.',
             F('result',[[6,'서울,종로']],['가온'],['점수','메모']),
             files={'mini-ko.csv':{'text':'이름,점수,메모\n가온,6,"서울,종로"\n','encoding':'cp949'}}),
    )
    seq['pd_columns'] = (
        step('열 이름 하나: Series',
             "df['score']는 열 이름으로 한 열을 선택합니다. [] 안의 문자열은 변수 이름이 아니라 열 라벨입니다. "
             '결과에는 원래 행 라벨이 남으며 1차원 Series가 됩니다.',
             table + "result = df['score']\nprint(result)",
             'Kim 6, Lee 9, Park 4가 표시됩니다. 한 열의 값과 행 라벨을 가져옵니다.', S('result',[6,9,4],['Kim','Lee','Park'])),
        step('열 이름 목록: DataFrame',
             "df[['score']]의 안쪽 []는 열 이름 목록입니다. 목록으로 선택하면 열이 하나여도 2차원 표입니다. "
             '여러 열을 적으면 적은 순서로 열을 배열합니다.',
             table + "single = df[['score']]\nresult = df[['visits','score']]\nprint(single)\nprint(result)",
             'single은 score 한 열짜리 표입니다. result는 visits, score 순서이고 원본 df의 열 순서는 그대로입니다.',
             F('single',[[6],[9],[4]],['Kim','Lee','Park'],['score']) + F('result',[[2,6],[1,9],[3,4]],['Kim','Lee','Park'],['visits','score'])),
        step('Series를 일반 목록으로 바꾸기',
             "df['score'].tolist()는 먼저 열을 선택한 뒤 값만 목록으로 변환합니다. "
             'Series와 달리 일반 목록에는 Kim 등의 라벨이 없습니다. DataFrame 전체에는 tolist()를 쓰지 않습니다.',
             table + "values = df['score'].tolist()\nprint(values)",
             '[6, 9, 4]가 출력됩니다. 앞서 배운 df.index.tolist()는 값이 아니라 행 라벨을 추출한다는 차이가 있습니다.', (C('values',[6,9,4]),)),
    )
    seq['pd_argmax'] = (
        step('max()와 argmax(): 값인가 위치인가',
             's.max()는 가장 큰 값, s.argmax()는 그 값의 0부터 센 위치입니다. 같은 최댓값이 여러 개면 argmax는 첫 위치입니다.',
             "s = pd.Series([6,12,12], index=['Kim','Lee','Park'])\nvalue = s.max()\nposition = s.argmax()\nprint(value, position)",
             '12와 1입니다. 1은 라벨이 아니라 두 번째라는 위치 번호입니다.', (C('value',12),C('position',1))),
        step('idxmax(): 가장 큰 값의 라벨',
             's.idxmax()는 최대인 행의 이름을 반환합니다. 숫자 라벨도 이름으로 해석합니다. 원래 Series를 정렬하지 않아도 찾을 수 있습니다.',
             's = pd.Series([6,12,9], index=[50,30,10])\nlabel = s.idxmax()\nposition = s.argmax()\nprint(label, position)',
             '라벨 30, 위치 1입니다. idxmax()와 argmax()를 바꾸면 찾는 대상이 달라집니다.', (C('label',30),C('position',1))),
        step('찾은 행에서 다른 열의 값 읽기',
             'DataFrame은 2차원이므로 df.loc[행라벨, 열라벨]처럼 두 대상을 쉼표로 구분합니다. '
             'winner에는 찾은 행 라벨이 저장되어 있으므로 따옴표 없이 씁니다. visits는 실제 열 이름이므로 따옴표를 씁니다. '
             '더 자세한 범위 선택은 뒤의 loc 단원에서 다룹니다.',
             table + "winner = df['score'].idxmax()\nvisit_count = df.loc[winner, 'visits']\nprint(winner, visit_count)",
             'Lee와 1이 나옵니다. score의 최댓값 9를 구한 뒤, 같은 행의 visits를 읽은 결과입니다.', (C('winner','Lee'),C('visit_count',1))),
    )
    seq['pd_computed'] = (
        step('열의 계산 결과를 새 열에 대입하기',
             "df['total'] = ...는 오른쪽 결과를 total 열에 저장합니다. 없는 열 이름이면 새 열을 만듭니다. "
             '열끼리 더하면 행 라벨을 맞추어 계산하므로 사람별 합계를 구할 수 있습니다.',
             scores + "df['total'] = df['math'] + df['english']\nprint(df)",
             'Kim은 10+30=40, Lee는 20+40=60입니다. 기존 두 과목 열도 유지됩니다.', F('df',[[10,30,40],[20,40,60]],['Kim','Lee'],['math','english','total'])),
        step('sum(axis=1): 선택한 열을 가로로 합치기',
             'df[열목록].sum(axis=1)은 각 행에서 선택한 열을 가로로 더합니다. axis=0(기본값)은 각 열을 세로로 더합니다. '
             '이미 total 열이 있으면 표 전체가 아닌 원래 과목 열만 선택해야 중복 합산을 피합니다.',
             scores + "df['total'] = 999\ndf['total'] = df[['math','english']].sum(axis=1)\nprint(df)",
             '잘못된 total 999는 40,60으로 교체됩니다. axis=0으로 바꾸면 사람별 합계가 아닌 과목별 합계가 됩니다.',
             F('df',[[10,30,40],[20,40,60]],['Kim','Lee'],['math','english','total'])),
        step('mean(axis=1): 선택한 열의 행별 평균',
             'mean()은 평균을 계산합니다. mean(axis=1)도 먼저 원래 과목 열을 선택합니다. 기존 total을 평균 계산에 넣지 않습니다.',
             scores + "df['total'] = 999\ndf['mean'] = df[['math','english']].mean(axis=1)\nprint(df)",
             'mean은 Kim 20, Lee 30이고 기존 total 999는 유지됩니다.',
             F('df',[[10,30,999,20],[20,40,999,30]],['Kim','Lee'],['math','english','total','mean'])),
        step('셀 수정 후 계산 열도 다시 계산하기',
             "df.loc['Kim','math'] = 50은 Kim행의 math 한 셀만 바꿉니다. "
             '이전에 만든 total은 값이지 자동 갱신 수식이 아닙니다. 과목을 고친 뒤 합계 계산도 다시 실행해야 합니다.',
             scores + "df['total'] = df[['math','english']].sum(axis=1)\ndf.loc['Kim','math'] = 50\nprint(df['total'])\ndf['total'] = df[['math','english']].sum(axis=1)\nprint(df)",
             '첫 출력에는 예전 합계 40이 남습니다. 재계산 후 Kim의 total은 80, Lee는 60입니다.',
             F('df',[[50,30,80],[20,40,60]],['Kim','Lee'],['math','english','total'])),
    )
    seq['pd_drop'] = (
        step('drop(columns=...): 원본을 남기고 열 제거',
             "df.drop(columns=['visits'])는 visits 없는 새 표를 반환합니다. result에 받아야 이후에 쓸 수 있습니다. "
             'columns는 열 이름 목록을 받는 인자입니다. 원래 df는 그대로입니다.',
             table + "result = df.drop(columns=['visits'])\nprint(result)\nprint(df)",
             'result에는 score만, df에는 score와 visits가 모두 남습니다.',
             F('result',[[6],[9],[4]],['Kim','Lee','Park'],['score']) + F('df',[[6,2],[9,1],[4,3]],['Kim','Lee','Park'],['score','visits'])),
        step('drop(index=...): 행 이름으로 제거',
             'index=목록은 제거할 행 라벨입니다. index와 columns를 함께 지정하면 행과 열을 동시에 제외할 수 있습니다.',
             table + "result = df.drop(index=['Lee'], columns=['visits'])\nprint(result)",
             'Kim, Park행의 score만 남습니다. 나머지 행을 다시 0,1로 번호 매기지 않습니다.', F('result',[[6],[4]],['Kim','Park'],['score'])),
        step('inplace=True는 반환값 대신 원본 변경',
             'inplace=True는 df 자체를 변경하고 None을 반환합니다. True는 참을 나타내며 따옴표를 붙이지 않습니다. '
             'df = df.drop(..., inplace=True)로 쓰면 df가 None이 되는 오류를 만듭니다.',
             table + "returned = df.drop(index=['Lee'], inplace=True)\nprint(df)\nprint(returned)",
             'df에서 Lee만 없어지고 returned는 None입니다. 반환된 새 표를 받는 방식과 원본 변경 방식을 구분하세요.',
             F('df',[[6,2],[4,3]],['Kim','Park'],['score','visits']) + (C('returned',None),)),
    )
    seq['pd_loc'] = (
        step('행·열 이름 하나 또는 목록 선택',
             "df.loc['Lee','score']는 셀 하나입니다. df.loc[['Lee'],['score']]는 행 목록과 열 목록을 주므로 1행 1열 표를 유지합니다. "
             '쉼표 앞은 행, 뒤는 열입니다. 열 부분을 생략하면 모든 열입니다.',
             table + "value = df.loc['Lee','score']\nresult = df.loc[['Lee'],['score']]\nprint(value)\nprint(result)",
             '숫자 9와 Lee행 score열의 작은 표가 출력됩니다.', (C('value',9),) + F('result',[[9]],['Lee'],['score'])),
        step('라벨 범위는 끝도 포함',
             "'Kim':'Lee'는 Kim부터 Lee까지의 라벨 범위입니다. 이처럼 정렬된 고유 라벨에서 loc 범위의 끝 Lee도 포함합니다. "
             '선택할 열은 목록으로 주어 표를 유지합니다.',
             table + "result = df.loc['Kim':'Lee',['score']]\nprint(result)",
             'Kim과 Lee가 모두 남습니다. 숫자 위치를 사용하는 iloc의 끝 제외 규칙과 다릅니다.', F('result',[[6],[9]],['Kim','Lee'],['score'])),
        step('목록 순서로 재배열하고 셀 수정',
             '라벨 목록의 순서대로 행·열이 선택됩니다. loc[...] = 값으로 원본의 특정 셀을 수정합니다. '
             "df['score']['Lee'] 같은 연속 대괄호 대입 대신 행·열을 한 번의 loc로 지정하세요.",
             table + "df.loc['Lee','score'] = 15\nresult = df.loc[['Park','Lee'],['visits','score']]\nprint(result)",
             'Park의 [3,4], Lee의 [1,15]가 visits,score 순서로 출력됩니다.',
             F('result',[[3,4],[1,15]],['Park','Lee'],['visits','score']) + (C('df',15,['data',1,0]),)),
    )
    seq['pd_iloc'] = (
        step('숫자 위치와 끝 제외 슬라이스',
             'df.iloc[행위치, 열위치]는 0부터 센 번호를 씁니다. 0:2는 위치 0,1이고 끝 2는 제외합니다. '
             ':2는 0:2와 같습니다. 열 하나도 1:2처럼 범위로 고르면 DataFrame입니다.',
             table + 'result = df.iloc[:2,1:2]\nprint(result)',
             '처음 두 사람 Kim,Lee의 두 번째 열 visits만 남습니다.', F('result',[[2],[1]],['Kim','Lee'],['visits'])),
        step('음수 위치와 위치 목록',
             '-1은 마지막 위치입니다. [2,0]은 세 번째, 첫 번째 순서의 위치 목록입니다. '
             '숫자 인덱스 라벨이 있더라도 iloc는 그것을 이름으로 찾지 않습니다.',
             table + 'last = df.iloc[-1]\nresult = df.iloc[[2,0],:2]\nprint(last)\nprint(result)',
             'last는 Park의 행 값 Series이고 result는 Park,Kim 순서의 두 열 표입니다.',
             S('last',[4,3],['score','visits']) + F('result',[[4,3],[6,2]],['Park','Kim'],['score','visits'])),
        step('head(n), tail(n): 앞·뒤 n행',
             'head(2)는 처음 두 행, tail(2)는 마지막 두 행을 원래 순서로 반환합니다. tail은 역순 정렬이 아닙니다.',
             table + 'first = df.head(2)\nresult = df.tail(2)\nprint(first)\nprint(result)',
             'first는 Kim,Lee이고 result는 Lee,Park입니다. 두 경우 모두 모든 열을 유지합니다.',
             F('first',[[6,2],[9,1]],['Kim','Lee'],['score','visits']) + F('result',[[9,1],[4,3]],['Lee','Park'],['score','visits'])),
    )
    seq['pd_filter'] = (
        step('비교식으로 행마다 True/False 만들기',
             "df['score'] >= 6은 각 행의 점수를 비교한 Boolean Series입니다. df.loc[조건]은 True인 행만 남깁니다. "
             '=는 대입, ==는 같음 비교이고 >=는 이상입니다. 조건 변수 이름에는 따옴표를 붙이지 않습니다.',
             table + "mask = df['score'] >= 6\nresult = df.loc[mask]\nprint(mask)\nprint(result)",
             'mask는 True,True,False이고 Kim,Lee만 남습니다.', S('mask',[True,True,False],['Kim','Lee','Park']) + F('result',[[6,2],[9,1]],['Kim','Lee'],['score','visits'])),
        step('여러 조건: 괄호와 &·|',
             '두 조건을 동시에 만족하면 &이고 하나라도 만족하면 |입니다. 각 비교식을 ()로 감쌉니다. '
             'Python and/or는 Series 전체를 참/거짓 하나로 해석하려고 하므로 사용할 수 없습니다.',
             table + "both = df.loc[(df['score'] >= 6) & (df['visits'] >= 2), ['score']]\neither = df.loc[(df['score'] >= 9) | (df['visits'] >= 3)]\nprint(both)\nprint(either)",
             'both는 Kim의 score만, either는 Lee와 Park의 모든 열입니다. 쉼표 뒤 열 목록으로 결과의 열도 제한합니다.',
             F('both',[[6]],['Kim'],['score']) + F('either',[[9,1],[4,3]],['Lee','Park'],['score','visits'])),
        step('계산 열을 만든 다음 조건 적용',
             '먼저 평균 열을 저장하고, 그 평균 열의 조건으로 전체 표를 고릅니다. 계산과 선택을 두 줄로 나누면 어느 단계가 잘못됐는지 확인하기 쉽습니다.',
             scores + "df['mean'] = df[['math','english']].mean(axis=1)\nresult = df.loc[df['mean'] >= 25]\nprint(result)",
             '평균이 30인 Lee만 남고 math,english,mean 세 열이 모두 보입니다.', F('result',[[20,40,30]],['Lee'],['math','english','mean'])),
    )
    _later_sequences(seq)
    return seq


def _later_sequences(seq):
    missing = "import numpy as np\ndf = pd.DataFrame({'score':[10,np.nan,30], 'visits':[np.nan,2,4]}, index=['Kim','Lee','Park'])\n"
    pair = "a = pd.DataFrame({'score':[6]}, index=['Kim'])\nb = pd.DataFrame({'score':[9], 'memo':['ok']}, index=['Lee'])\n"
    merge = "a = pd.DataFrame({'id':[10,20], 'score':[6,9]})\nb = pd.DataFrame({'id':[20,30], 'team':['Blue','Red']})\n"
    groups = "df = pd.DataFrame({'team':['Blue','Red','Blue'], 'score':[6,12,10], 'visits':[2,4,3]})\n"
    pivot = "df = pd.DataFrame({'day':['Fri','Fri','Sat'], 'sensor':['X','Y','X'], 'value':[2,8,5]})\n"
    repeated = "df = pd.DataFrame({'team':['Blue','Blue','Red'], 'kind':['x','x','y'], 'count':[2,6,10]})\n"
    dates = "df = pd.DataFrame({'date':['2025-01-01','2026-01-02','2026-01-05','2026-02-01'], 'amount':[100,3,5,7]})\n"
    seq['pd_missing'] = (
        step('np.nan과 isna(): 결측 여부를 먼저 확인',
             'import numpy as np로 불러온 np.nan은 값이 빠졌다는 표시입니다. 0과는 의미가 다릅니다. '
             'df.isna()는 결측인 셀을 True로 표시합니다. NaN과 ==로 비교하지 마세요. '
             'isna().sum()은 True를 1로 세어 열별 결측 개수를 구합니다.',
             missing + 'mask = df.isna()\ncounts = mask.sum()\nprint(mask)\nprint(counts)',
             'score는 Lee, visits는 Kim에서 결측입니다. 두 열의 결측 개수는 각각 1입니다.',
             F('mask',[[False,True],[True,False],[False,False]],['Kim','Lee','Park'],['score','visits']) + S('counts',[1,1],['score','visits'])),
        step('dropna(subset=...): 필요한 열만 기준으로 제거',
             "df.dropna(subset=['score'])는 score가 빠진 행만 제외합니다. subset은 검사할 열 목록입니다. "
             'df.count()는 반대로 각 열의 결측 아닌 값 개수입니다. 두 연산 모두 원본을 자동으로 바꾸지 않습니다.',
             missing + "result = df.dropna(subset=['score'])\ncounts = df.count()\nprint(result)\nprint(counts)",
             'Kim과 Park가 남습니다. Kim의 visits 결측은 제거 기준이 아니므로 유지됩니다. 유효 개수는 각 열 2입니다.',
             F('result',[[10,NAN],[30,4]],['Kim','Park'],['score','visits']) + S('counts',[2,2],['score','visits'])),
        step('fillna: 열별 대체값과 평균 대체',
             "df.fillna({'score':0})에서 사전의 키는 채울 열, 값은 대체값입니다. "
             "df['score'].mean()은 결측을 제외한 평균이므로 이를 대체값으로 쓸 수 있습니다. 원본을 보존하려면 새 변수에 받습니다.",
             missing + "average = df['score'].mean()\nresult = df.fillna({'score':average})\nprint(average)\nprint(result)",
             '평균 20이 Lee의 score에 들어갑니다. Kim의 visits는 여전히 결측이고 원본 score의 결측도 그대로입니다.',
             F('result',[[10,NAN],[20,2],[30,4]],['Kim','Lee','Park'],['score','visits']) + (C('average',20),C('df',NAN,['data',1,0]))),
    )
    seq['pd_concat'] = (
        step('concat([a,b]): 아래로 이어 붙이기',
             'pd.concat은 표들의 목록을 받아 순서대로 연결합니다. 기본 axis=0은 행을 늘립니다. '
             '기본 join="outer"는 양쪽의 모든 열을 남기고 없는 셀은 NaN입니다. ignore_index=True는 행 라벨을 새로 0부터 매깁니다.',
             pair + 'result = pd.concat([a,b], ignore_index=True)\nprint(result)',
             '첫 행은 score 6 / memo 결측, 다음 행은 score 9 / memo ok입니다. 라벨은 Kim,Lee 대신 0,1입니다.',
             F('result',[[6,NAN],[9,'ok']],[0,1],['score','memo'])),
        step('axis=1: 행 라벨을 맞추어 옆으로 연결',
             'axis=1은 열을 늘립니다. 같은 줄 번호가 아니라 같은 행 라벨끼리 맞춥니다. '
             '한 표에만 있는 라벨도 기본 outer 설정으로 남고 반대쪽 값은 결측입니다.',
             "a = pd.DataFrame({'score':[6,9]}, index=['Kim','Lee'])\nb = pd.DataFrame({'visits':[2,4]}, index=['Lee','Park'])\nresult = pd.concat([a,b], axis=1)\nprint(result)",
             'Lee만 두 값 9,2가 모두 있습니다. Kim의 visits와 Park의 score는 결측입니다.',
             F('result',[[6,NAN],[9,2],[NAN,4]],['Kim','Lee','Park'],['score','visits'])),
        step('join="inner": 공통 열만 행 연결',
             'axis=0일 때 join="inner"는 양쪽 표에 모두 있는 열만 남깁니다. '
             '열을 고르는 join과 행 라벨을 새로 매기는 ignore_index는 서로 다른 결정입니다.',
             pair + "result = pd.concat([a,b], join='inner', ignore_index=True)\nprint(result)",
             '공통 열 score만 남고 값은 6,9입니다. memo는 b에만 있어 제외됩니다.', F('result',[[6],[9]],[0,1],['score'])),
    )
    seq['pd_merge'] = (
        step('on: 같은 키 값을 찾아 연결',
             "pd.merge(a,b,on='id',how='inner')에서 a는 왼쪽 표, b는 오른쪽 표입니다. on은 맞춰 볼 키 열 이름입니다. "
             'inner는 두 표에 모두 있는 키만 남깁니다. 행 위치가 다르더라도 id가 같으면 연결합니다.',
             merge + "result = pd.merge(a,b,on='id',how='inner')\nprint(result)",
             '공통 id 20에 score 9와 team Blue가 붙습니다. id 10과 30은 양쪽에 모두 있지 않아 빠집니다.',
             F('result',[[20,9,'Blue']],[0],['id','score','team'])),
        step('how="left": 왼쪽의 행을 잃지 않기',
             'left는 왼쪽 표의 키를 모두 보존하고 대응하는 오른쪽 데이터를 붙입니다. '
             '대응이 없는 것은 0이 아니라 결측입니다. concat과 달리 지정한 키 열을 사용합니다.',
             merge + "result = pd.merge(a,b,on='id',how='left')\nprint(result)",
             'id 10은 score 6 / team 결측, id 20은 score 9 / team Blue입니다.',
             F('result',[[10,6,NAN],[20,9,'Blue']],[0,1],['id','score','team'])),
        step('병합 결과에 이미 배운 조건 적용',
             '병합을 joined에 받은 다음 joined의 열로 조건을 만듭니다. 서로 다른 표의 조건을 섞지 마세요. '
             'loc 필터는 기존 행 라벨을 유지합니다.',
             merge + "joined = pd.merge(a,b,on='id',how='left')\nresult = joined.loc[joined['score'] >= 8]\nprint(result)",
             'id 20만 남습니다. 결과 행 라벨은 원래 병합 결과의 1이고 자동으로 0으로 바뀌지 않습니다.',
             F('result',[[20,9,'Blue']],[1],['id','score','team'])),
    )
    seq['pd_merge_detail'] = (
        step('suffixes: 같은 열 이름의 출처 표시',
             "키가 아닌 열 이름이 겹치면 suffixes=('_before','_after')처럼 접미사 두 개를 튜플로 줍니다. "
             '첫 값은 왼쪽 표, 두 번째는 오른쪽 표에 붙습니다. 키 열 id는 한 열로 남습니다.',
             "a = pd.DataFrame({'id':[10], 'score':[6]})\nb = pd.DataFrame({'id':[10], 'score':[9]})\nresult = pd.merge(a,b,on='id',suffixes=('_before','_after'))\nprint(result)",
             'id, score_before, score_after 세 열이며 10,6,9가 들어 있습니다.', F('result',[[10,6,9]],[0],['id','score_before','score_after'])),
        step('중복 키는 대응 조합만큼 행이 늘어남',
             '같은 id가 왼쪽 2행, 오른쪽 2행이면 2×2=4가지 대응을 만듭니다. 중복을 임의로 삭제하면 데이터를 잃습니다. '
             '기대하는 키 관계가 확실하면 validate 인자로 일대일/일대다 여부를 검사할 수도 있습니다.',
             "a = pd.DataFrame({'id':[10,10], 'name':['Kim','Lee']})\nb = pd.DataFrame({'id':[10,10], 'kind':['x','y']})\nresult = pd.merge(a,b,on='id')\nprint(result)",
             'Kim-x, Kim-y, Lee-x, Lee-y 네 행입니다. 줄 수가 늘어나는 이유는 키 중복입니다.',
             F('result',[[10,'Kim','x'],[10,'Kim','y'],[10,'Lee','x'],[10,'Lee','y']],[0,1,2,3],['id','name','kind'])),
        step('left_index/right_index: 행 라벨을 키로 쓰기',
             '키가 데이터 열이 아닌 인덱스에 있으면 left_index=True, right_index=True로 각각 지정합니다. '
             '기본 how는 inner이므로 공통 라벨을 연결합니다.',
             "a = pd.DataFrame({'score':[6,9]}, index=['Kim','Lee'])\nb = pd.DataFrame({'visits':[2,4]}, index=['Lee','Kim'])\nresult = pd.merge(a,b,left_index=True,right_index=True)\nprint(result)",
             'Kim은 6,4 / Lee는 9,2입니다. 오른쪽 행 순서가 달라도 이름으로 연결됩니다.', F('result',[[6,4],[9,2]],['Kim','Lee'],['score','visits'])),
    )
    seq['pd_merge_coverage'] = (
        step('표.merge(다른표): 오른쪽 기준 병합',
             'a.merge(b,...)는 pd.merge(a,b,...)와 같은 호출 방식입니다. how="right"는 오른쪽 b의 키를 모두 보존합니다.',
             merge + "result = a.merge(b,on='id',how='right')\nprint(result)",
             'id 20과 30이 남습니다. 30의 score는 a에 없어 결측입니다.', F('result',[[20,9,'Blue'],[30,NAN,'Red']],[0,1],['id','score','team'])),
        step('outer와 sort=True: 전체 키를 순서대로',
             'how="outer"는 양쪽 키의 합집합을 남깁니다. sort=True는 병합 키를 정렬하라는 뜻입니다. '
             '없는 값을 채우지 않아야 정보가 없다는 사실이 유지됩니다.',
             merge + "result = a.merge(b,on='id',how='outer',sort=True)\nprint(result)",
             'id 10,20,30 순서입니다. id 10의 team, id 30의 score가 결측입니다.',
             F('result',[[10,6,NAN],[20,9,'Blue'],[30,NAN,'Red']],[0,1,2],['id','score','team'])),
        step('병합 후 특정 값이 없는 행 찾기',
             "merged['score'].isna()는 score가 빠진 행의 조건입니다. 그 조건을 merged.loc[...]에 넣습니다. "
             '결측 검사와 행 선택을 결합하는 것으로, 새로운 종류의 병합은 아닙니다.',
             merge + "merged = a.merge(b,on='id',how='outer',sort=True)\nresult = merged.loc[merged['score'].isna()]\nprint(result)",
             'id 30의 행만 남고 기존 병합 인덱스 2도 유지됩니다.', F('result',[[30,NAN,'Red']],[2],['id','score','team'])),
    )
    seq['pd_pivot'] = (
        step('index·columns·values로 배치 정하기',
             'df.pivot(index=...,columns=...,values=...)에서 index는 결과 행을 구분할 열, columns는 결과 열을 구분할 열, '
             'values는 각 셀에 넣을 값을 가진 열입니다. 세 인자 모두 원본의 열 이름을 문자열로 받습니다.',
             pivot + "result = df.pivot(index='day',columns='sensor',values='value')\nprint(result)",
             '행은 Fri,Sat이고 열은 X,Y입니다. (Sat,Y)는 관측이 없어 NaN입니다. 자동 합계/평균 계산이 아닙니다.',
             F('result',[[2,8],[5,NAN]],['Fri','Sat'],['X','Y'])),
        step('같은 행·열 조합은 하나여야 함',
             '한 셀에 들어갈 관측이 두 개면 pivot은 어느 값을 쓸지 결정할 수 없어 오류를 냅니다. '
             '복수 관측은 다음 pivot_table 단원에서 합계·평균을 정합니다. 여기서는 넓힌 표의 열을 골라 행별 합을 복습합니다.',
             pivot + "result = df.pivot(index='day',columns='sensor',values='value')\ntotals = result[['X','Y']].sum(axis=1)\nprint(totals)",
             'Fri 합계는 10, Sat는 5입니다. sum은 기본적으로 결측을 제외합니다. 실제 관측이 없는 셀을 측정값 0으로 해석한 것은 아닙니다.',
             S('totals',[10,5],['Fri','Sat'])),
    )
    seq['pd_pivot_table'] = (
        step('aggfunc: 한 셀에 여러 값이 있으면 어떻게 모을까',
             'pivot_table은 pivot과 달리 같은 조합의 관측을 집계합니다. aggfunc="sum"은 합계, "mean"은 평균입니다. '
             '기본값은 mean이지만 목적이 드러나도록 직접 지정하세요.',
             repeated + "result = df.pivot_table(index='team',columns='kind',values='count',aggfunc='sum')\nprint(result)",
             'Blue-x의 2와 6은 8로 합쳐지고 Red-y는 10입니다. 관측 없는 조합은 결측입니다.', F('result',[[8,NAN],[NAN,10]],['Blue','Red'],['x','y'])),
        step('fill_value: 집계 후 빈 칸 채우기',
             'fill_value=0은 집계 결과에 없는 조합을 0으로 채웁니다. 원래 모든 결측 관측을 0으로 바꾸는 것과 다릅니다. '
             '목표가 빈 조합을 NaN으로 유지하라고 하면 이 인자를 생략합니다.',
             repeated + "result = df.pivot_table(index='team',columns='kind',values='count',aggfunc='mean',fill_value=0)\nprint(result)",
             'Blue-x는 평균 4, Red-y는 10이고 빈 두 칸은 0입니다.', F('result',[[4,0],[0,10]],['Blue','Red'],['x','y'])),
        step('행을 고른 뒤 피벗하기',
             '사용할 관측의 조건부터 적용해 valid에 저장하고 그 표를 집계합니다. '
             '이미 계산된 합계에 조건을 적용하는 것과 구분하세요.',
             repeated + "valid = df.loc[df['count'] > 3]\nresult = valid.pivot_table(index='team',columns='kind',values='count',aggfunc='sum',fill_value=0)\nprint(result)",
             'count 2인 행을 먼저 제외하므로 Blue-x 합계는 8이 아니라 6입니다.', F('result',[[6,0],[0,10]],['Blue','Red'],['x','y'])),
    )
    multi = "df = pd.DataFrame({'team':['Blue','Blue','Red'], 'year':[2025,2026,2026], 'kind':['x','y','x'], 'count':[2,6,10]})\n"
    seq['pd_pivot_multi'] = (
        step('index에 목록을 주어 두 기준으로 묶기',
             "index=['team','year']는 team과 year의 조합을 행 라벨로 만듭니다. 이를 MultiIndex라고 합니다. "
             '문자열 한 개와 열 이름 목록의 차이를 확인하세요. 나머지 columns, values, aggfunc는 앞 단원과 같습니다.',
             multi + "result = df.pivot_table(index=['team','year'],columns='kind',values='count',aggfunc='sum',fill_value=0)\nprint(result)",
             '(Blue,2025), (Blue,2026), (Red,2026) 세 행입니다. 같은 팀이어도 연도가 다르면 합쳐지지 않습니다.',
             F('result',[[2,0],[0,6],[10,0]],[['Blue',2025],['Blue',2026],['Red',2026]],['x','y'])),
        step('기준 순서와 집계 방법도 결과의 일부',
             "index=['year','team']이면 바깥 라벨이 year, 안쪽이 team입니다. mean은 같은 조합의 평균을 냅니다. "
             'fill_value를 생략하면 관측이 없는 조합은 결측입니다.',
             multi + "result = df.pivot_table(index=['year','team'],columns='kind',values='count',aggfunc='mean')\nprint(result)",
             '행 라벨 순서는 (2025,Blue), (2026,Blue), (2026,Red)입니다. 라벨 이름도 year,team 순서입니다.',
             F('result',[[2,NAN],[NAN,6],[10,NAN]],[[2025,'Blue'],[2026,'Blue'],[2026,'Red']],['x','y']) + (C('result',['year','team'],['index_names']),)),
        step('조건 선택과 복합 피벗 조합',
             '입력 행을 고른 뒤 동일한 복합 index 목록으로 집계합니다. 연도 기준을 빼면 서로 다른 연도의 값이 같은 행으로 합쳐집니다.',
             multi + "valid = df.loc[df['count'] > 3]\nresult = valid.pivot_table(index=['team','year'],columns='kind',values='count',aggfunc='sum',fill_value=0)\nprint(result)",
             '2025년 Blue의 관측이 제외되어 2026년의 두 행만 남습니다.',
             F('result',[[0,6],[10,0]],[['Blue',2026],['Red',2026]],['x','y'])),
    )
    seq['pd_groupby'] = (
        step('groupby → 열 선택 → 집계 순서',
             "df.groupby('team')은 같은 team의 행끼리 묶습니다. ['score']로 계산할 열을 고르고 .mean()으로 평균을 냅니다. "
             'groupby만 호출하면 아직 평균이 아닙니다. 결과 Series의 인덱스는 팀 이름입니다.',
             groups + "result = df.groupby('team')['score'].mean()\nprint(result)",
             'Blue의 (6+10)/2=8, Red는 12입니다. 집단별 평균을 다시 단순 평균하면 원래 행 전체 평균과 다를 수 있습니다.',
             S('result',[8,12],['Blue','Red'])),
        step('describe() 결과도 라벨로 읽는 Series',
             '숫자 Series.describe()는 count,mean,std,min,25%,50%,75%,max를 라벨로 가진 요약 Series입니다. '
             "summary['mean']처럼 읽습니다. count는 결측 제외 개수이고 std는 표본 표준편차(ddof=1)입니다.",
             "import numpy as np\ns = pd.Series([2,4,6,np.nan])\nsummary = s.describe()\ncount = summary['count']\nmean = summary['mean']\nstd = summary['std']\nprint(summary)",
             'count 3, mean 4, std 2입니다. 25%,50%,75%는 각각 3,4,5로 관측값 분포의 사분위 지점입니다.',
             (C('count',3),C('mean',4),C('std',2))),
        step('유효한 행을 골라 집계하기',
             "dropna(subset=['score'])로 score가 있는 행만 남긴 뒤 team별 visits를 합칩니다. "
             '한 줄로 메서드를 이어 쓰는 것은 각 단계 결과에 다음 연산을 적용한다는 뜻입니다.',
             "import numpy as np\ndf = pd.DataFrame({'team':['Blue','Blue','Red'], 'score':[6,np.nan,12], 'visits':[2,100,4]})\nvalid = df.dropna(subset=['score'])\nresult = valid.groupby('team')['visits'].sum()\nprint(result)",
             'Blue visits는 2입니다. 점수가 없는 행의 100은 합계에 들어가지 않습니다.', S('result',[2,4],['Blue','Red'])),
    )
    seq['pd_group_filter'] = (
        step('팀 합계를 만든 다음 팀을 고르기',
             '먼저 totals를 집계하고 totals 자체의 조건으로 선택합니다. totals의 라벨은 원래 행 번호가 아니라 팀 이름입니다. '
             '원래 df의 개별 방문 횟수 조건과 팀 합계 조건을 구분하세요.',
             groups + "totals = df.groupby('team')['visits'].sum()\nresult = totals.loc[totals >= 5]\nprint(totals)\nprint(result)",
             'Blue는 2+3=5이므로 남습니다. 개별 행에는 5 이상이 없어도 합계 조건은 만족합니다.', S('result',[5],['Blue'])),
        step('평균도 집계 후에 조건 판단',
             '평균 기준이면 모든 대상 점수를 평균에 포함한 다음 그 평균을 비교합니다. 낮은 점수를 먼저 제거하면 다른 질문을 푸는 셈입니다.',
             groups + "means = df.groupby('team')['score'].mean()\nresult = means.loc[means >= 10]\nprint(result)",
             'Red 12만 남습니다. Blue의 평균에는 낮은 점수 6도 포함되어 평균 8이 됩니다.', S('result',[12],['Red'])),
        step('유효 행 선택과 집계 후 선택을 따로 하기',
             "valid 열이 이미 True/False이면 df.loc[df['valid']]로 직접 조건에 쓸 수 있습니다. "
             '유효한 행만 선택 → 팀별 합계 → 합계 조건의 세 단계입니다.',
             "df = pd.DataFrame({'team':['Blue','Blue','Red'], 'visits':[3,4,100], 'valid':[True,True,False]})\nvalid_rows = df.loc[df['valid']]\ntotals = valid_rows.groupby('team')['visits'].sum()\nresult = totals.loc[totals >= 5]\nprint(result)",
             'Blue 7만 남습니다. Red의 100은 유효하지 않아서 집계 전에 제외됩니다.', S('result',[7],['Blue'])),
    )
    seq['pd_datetime'] = (
        step('문자열을 날짜로 바꾸고 연·월 읽기',
             "pd.to_datetime(df['date'])는 날짜 문자열 Series를 날짜 자료형으로 바꿉니다. 같은 열에 다시 대입해야 변환이 저장됩니다. "
             '.dt는 날짜 Series의 연·월 같은 속성에 접근하는 통로입니다. .dt.year와 .dt.month에는 ()를 붙이지 않습니다.',
             dates + "df['date'] = pd.to_datetime(df['date'])\nyears = df['date'].dt.year\nmonths = df['date'].dt.month\nprint(years)\nprint(months)",
             '연도는 2025,2026,2026,2026이고 월은 1,1,1,2입니다. 월만으로는 연도가 구분되지 않습니다.',
             S('years',[2025,2026,2026,2026],[0,1,2,3])+S('months',[1,1,1,2],[0,1,2,3])),
        step('연도를 먼저 고르기',
             '날짜의 연도를 비교한 조건도 df.loc[...]에 사용할 수 있습니다. ==는 같음 비교입니다. 원래 인덱스는 유지합니다.',
             dates + "df['date'] = pd.to_datetime(df['date'])\ncurrent = df.loc[df['date'].dt.year == 2026]\nresult = current['amount']\nprint(result)",
             '2025년 amount 100은 빠지고 인덱스 1,2,3의 값 3,5,7만 남습니다.', S('result',[3,5,7],[1,2,3])),
        step('groupby에 월 Series 전달하기',
             'groupby는 열 이름뿐 아니라 각 행의 집단을 나타내는 Series도 받습니다. '
             "current.groupby(current['date'].dt.month)는 같은 월끼리 묶습니다. 선택한 current의 날짜를 기준으로 써야 합니다.",
             dates + "df['date'] = pd.to_datetime(df['date'])\ncurrent = df.loc[df['date'].dt.year == 2026]\nresult = current.groupby(current['date'].dt.month)['amount'].sum()\nprint(result)",
             '월 라벨 1에 합계 8, 월 라벨 2에 합계 7입니다. 2025년 1월의 100이 섞이지 않습니다.', S('result',[8,7],[1,2])),
    )
    seq['pd_plot'] = (
        step('.T: 행과 열을 교환',
             'df.T는 전치한 표입니다. 원래 행 라벨은 열 이름이 되고 원래 열 이름은 행 라벨이 됩니다. T에는 ()가 없습니다.',
             "df = pd.DataFrame({'math':[10,20], 'english':[30,40]}, index=['Kim','Lee'])\nresult = df.T\nprint(result)",
             '행은 math,english / 열은 Kim,Lee입니다. math행 값은 10,20입니다.', F('result',[[10,20],[30,40]],['math','english'],['Kim','Lee'])),
        step('plot(y=...,kind=...)는 Axes 반환',
             "df.plot(y='score',kind='line')은 score 열의 선 그래프입니다. x축은 인덱스를 사용합니다. "
             'kind="bar"이면 막대입니다. 반환된 ax는 그림 영역 Axes이고 ax.figure는 이를 포함하는 Figure입니다. 문제에서 fig를 요구하면 여기에 저장합니다.',
             "import matplotlib.pyplot as plt\nplt.close('all')\ndf = pd.DataFrame({'score':[6,9,4]}, index=[10,20,30])\nax = df.plot(y='score',kind='line')\nfig = ax.figure\nprint(df)",
             '그래프 탭에서 x=10,20,30 / y=6,9,4인 선을 확인하세요. 시작의 plt.close는 이전 예시 그림만 닫습니다.',
             (C('fig',[10,20,30],['axes',0,'lines',0,'x','data']),C('fig',[6,9,4],['axes',0,'lines',0,'y','data']))),
        step('전치 후 범주 눈금의 위치와 이름',
             '전치한 표의 Kim 열을 그리면 과목별 값을 비교합니다. 문자열 인덱스의 선 그래프는 숫자 위치로 그려지므로 '
             'ax.set_xticks([0,1], labels=result.index)로 눈금 위치와 표시할 이름을 함께 지정합니다.',
             "import matplotlib.pyplot as plt\nplt.close('all')\ndf = pd.DataFrame({'math':[10,20], 'english':[30,40]}, index=['Kim','Lee'])\nresult = df.T\nax = result.plot(y='Kim',kind='line')\nax.set_xticks([0,1],labels=result.index)\nfig = ax.figure\nprint(result)",
             'x축 눈금 math,english에 Kim의 값 10,30이 이어집니다. 전치하지 않았다면 사람별 비교였을 것입니다.',
             (C('fig',[10,30],['axes',0,'lines',0,'y','data']),C('fig',['math','english'],['axes',0,'named_xticklabels']))),
    )
    _supplement_sequences(seq)


def _supplement_sequences(seq):
    index = "df = pd.DataFrame({'wind':[100,3,5,8]}, index=['2025-01-01','2026-01-02','2026-01-03','2026-02-01'])\n"
    weather = "import numpy as np\nweather = pd.DataFrame({'wind':[30,2,np.nan,6,10]}, index=pd.to_datetime(['2025-01-01','2026-01-01','2026-01-02','2026-01-03','2026-02-01']))\n"
    seq['pd_datetime_index'] = (
        step('날짜가 열이 아니라 인덱스인 경우',
             'df.index = pd.to_datetime(df.index)는 문자열 행 라벨을 DatetimeIndex로 바꿉니다. '
             '날짜 Series에는 .dt.year를 썼지만 날짜 인덱스는 바로 .year와 .month입니다. .tolist()로 일반 목록을 얻습니다.',
             index + 'df.index = pd.to_datetime(df.index)\nyears = df.index.year.tolist()\nmonths = df.index.month.tolist()\nprint(years)\nprint(months)',
             'years는 [2025,2026,2026,2026], months는 [1,1,1,2]입니다. 인덱스에 .dt를 붙이지 않습니다.',
             (C('years',[2025,2026,2026,2026]),C('months',[1,1,1,2]))),
        step('날짜 인덱스로 연도와 월 동시 선택',
             '연도 비교와 월 비교를 각각 괄호로 묶어 &로 결합합니다. 두 조건이 맞는 행만 loc로 선택합니다.',
             index + 'df.index = pd.to_datetime(df.index)\nresult = df.loc[(df.index.year == 2026) & (df.index.month == 1)]\nprint(result)',
             '2026-01-02와 2026-01-03의 wind 3,5만 남습니다. 2025년 1월은 제외됩니다.',
             F('result',[[3],[5]],['2026-01-02 00:00:00','2026-01-03 00:00:00'],['wind'])),
        step('인덱스의 월을 집계 기준으로 전달',
             'df.groupby(df.index.month)는 인덱스의 월 번호로 그룹을 만듭니다. 여러 해가 있으면 먼저 연도를 고르거나 연도·월을 함께 묶어야 합니다.',
             index + "df.index = pd.to_datetime(df.index)\ncurrent = df.loc[df.index.year == 2026]\nresult = current.groupby(current.index.month)['wind'].mean()\nprint(result)",
             '1월 평균은 4, 2월 평균은 8입니다. 결과 인덱스는 날짜 문자열이 아니라 월 번호입니다.', S('result',[4,8],[1,2])),
    )
    seq['pd_weather_audit'] = (
        step('agg([함수이름]): 평균과 개수를 함께',
             "groupby(... )['wind'].agg(['mean','count'])는 wind에 두 집계 함수를 적용합니다. "
             '문자열 목록의 순서대로 mean,count 열이 생깁니다. mean과 count는 결측을 제외하며 size는 결측행도 세므로 다릅니다.',
             weather + "current = weather.loc[weather.index.year == 2026]\nresult = current.groupby(current.index.month)['wind'].agg(['mean','count'])\nprint(result)",
             '1월은 유효 값 2,6의 평균 4 / count 2입니다. NaN을 0으로 채우면 평균과 count가 바뀌어 잘못된 해석이 됩니다.',
             F('result',[[4,2],[10,1]],[1,2],['mean','count'])),
        step('여러 해: 연도와 월 배열을 목록으로 묶기',
             'groupby([weather.index.year, weather.index.month])는 기준 두 개를 목록으로 받습니다. '
             '둘의 조합을 MultiIndex로 만들어 다른 해의 같은 달을 분리합니다. 기본 sort=True여서 연도·월 순서로 정렬됩니다.',
             weather + "result = weather.groupby([weather.index.year,weather.index.month])['wind'].agg(['mean','count'])\nprint(result)",
             '(2025,1)은 평균 30 / count 1, (2026,1)은 4 / 2, (2026,2)는 10 / 1입니다.',
             F('result',[[30,1],[4,2],[10,1]],[[2025,1],[2026,1],[2026,2]],['mean','count'])),
        step('월평균 기준은 집계한 표에 적용',
             '먼저 monthly를 계산한 뒤 monthly의 mean 열을 비교합니다. 개별 관측을 먼저 거르면 월평균 자체가 달라집니다.',
             weather + "current = weather.loc[weather.index.year == 2026]\nmonthly = current.groupby(current.index.month)['wind'].agg(['mean','count'])\nresult = monthly.loc[monthly['mean'] > 5]\nprint(result)",
             '평균 10인 2월만 남습니다. 1월의 개별 값 6은 5보다 커도 1월 평균 4는 기준을 넘지 않습니다.', F('result',[[10,1]],[2],['mean','count'])),
    )
    chart = "import matplotlib.pyplot as plt\nplt.close('all')\ncounts = pd.Series([2,6], index=['Kim','Lee'])\n"
    seq['pd_series_charts'] = (
        step('Series.plot(kind="bar"): 라벨별 크기',
             'Series.plot도 Axes를 반환합니다. kind="bar"는 인덱스를 범주 이름, 값을 막대 높이로 씁니다. '
             'Figure가 필요하면 ax.figure를 저장합니다.',
             chart + "ax = counts.plot(kind='bar')\nfig = ax.figure\nprint(counts)",
             'Kim 높이 2, Lee 높이 6인 막대 두 개입니다. 그래프 탭에서 비교하세요.',
             (C('fig',2,['axes',0,'patch_count']),C('fig',2,['axes',0,'patches',0,'height']),C('fig',6,['axes',0,'patches',1,'height']))),
        step('kind="pie": 전체 중 구성비',
             'kind="pie"는 값을 전체 합으로 나눈 비율을 부채꼴로 그립니다. 인덱스가 각 조각의 이름입니다. '
             '음수가 없는 양수 합의 자료에서 사용하며 크기 비교에는 막대가 더 정확할 수 있습니다.',
             chart + "ax = counts.plot(kind='pie')\nfig = ax.figure\nprint(counts / counts.sum())",
             'Kim은 0.25(90도), Lee는 0.75(270도)입니다. 두 값의 절대량이 아니라 구성비를 보여 줍니다.',
             (C('fig',2,['axes',0,'patch_count']),)),
        step('ax=로 원하는 subplot에 그리기',
             'fig,axes = plt.subplots(1,2)는 1행 2열 Figure와 두 Axes를 만듭니다. '
             'axes[0]은 왼쪽, axes[1]은 오른쪽입니다. counts.plot(...,ax=axes[0])처럼 어디에 그릴지 전달합니다.',
             chart + "fig, axes = plt.subplots(1,2)\ncounts.plot(kind='bar',ax=axes[0])\ncounts.plot(kind='pie',ax=axes[1])\nprint(counts)",
             '같은 자료가 왼쪽에는 막대, 오른쪽에는 원그래프로 표시됩니다. plot을 두 번 호출하기만 하면 별도 영역이 보장되지 않습니다.',
             (C('fig',2,['axis_count']),C('fig',2,['axes',0,'patch_count']),C('fig',2,['axes',1,'patch_count']))),
    )
    pair = "first = pd.DataFrame({'score':[6], 'memo':['old']}, index=['r'])\nsecond = pd.DataFrame({'score':[9], 'flag':[True]}, index=['r'])\n"
    seq['pd_concat_labels'] = (
        step('기본 concat은 중복 라벨도 보존',
             'pd.concat은 기본으로 원래 행 라벨을 유지합니다. 두 입력 모두 r이면 결과에도 r이 두 번 남습니다. '
             '같은 라벨이라는 이유로 행을 삭제하지 않습니다.',
             pair + "result = pd.concat([first,second])\nlabels = result.index.tolist()\nprint(result)\nprint(labels)",
             '행 라벨은 r,r이며 각 원본에만 있는 열도 남습니다. 없는 셀은 결측입니다.', (C('labels',['r','r']),C('result',[2,3],['shape']))),
        step('라벨 유지와 새 번호 부여를 비교',
             'ignore_index=True는 행 라벨을 새로 0부터 매기는 선택입니다. 데이터 값과 행 개수는 그대로입니다. '
             '원래 라벨을 유지하라는 목표라면 사용하지 않습니다.',
             pair + 'kept = pd.concat([first,second])\nnumbered = pd.concat([first,second],ignore_index=True)\nprint(kept.index.tolist())\nprint(numbered.index.tolist())',
             'kept의 라벨은 r,r이고 numbered는 0,1입니다. 중복 행 제거와는 다른 작업입니다.',
             (C('kept',['r','r'],['index']),C('numbered',[0,1],['index']))),
        step('공통 열 정책과 행 라벨 정책은 별개',
             'join="inner"는 행 연결 때 공통 열만 고릅니다. ignore_index를 생략하면 공통 열을 골라도 원래 행 라벨은 그대로입니다.',
             pair + "result = pd.concat([first,second],join='inner')\nprint(result)",
             'score 열의 6,9만 남고 라벨은 r,r입니다. memo와 flag는 공통 열이 아니어서 빠집니다.', F('result',[[6],[9]],['r','r'],['score'])),
    )


def teach_before_practice(unit):
    guided = sequences().get(unit.key)
    return replace(unit, guided_steps=guided) if guided else unit
