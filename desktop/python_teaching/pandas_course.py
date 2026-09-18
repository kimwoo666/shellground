"""Label-aware tables with explicit fixtures, preservation goals and checks."""
from .model import Lesson, problem as P, check as C, frame as F, series as S

PD='import numpy as np\nimport pandas as pd\n'
NAN={'special':'nan'}


def lessons():
    result=[]
    def add(key,title,why,syntax,pitfall,pages,cases):
        result.append(Lesson('pd_'+key,'pandas',title,why,syntax,pitfall,
            'week_3_1_handout.pdf',tuple(pages),tuple(cases),
            (result[-1].key,) if result else ('plot_box',)))
    add('series','Series의 값과 인덱스',
        'Series는 값과 각 값의 라벨(index)을 함께 가진1차원 자료입니다. 인덱스는 데이터 값이 아니며 숫자 라벨도 위치와 다를 수 있습니다. np.nan은 결측값으로 계산·집계 시 별도 처리가 필요합니다.',
        "s=pd.Series([3,7],index=['A','B'])\ns.loc['B']\ns.iloc[1]",
        's[정수]를 라벨/위치 중 어느 뜻으로 처리하는지는 버전 변화에 영향받습니다. loc와 iloc를 명확히 사용하세요.',[2,3,4,5],[
        P('A,B,C 라벨에 값3,7,5인 Series result를 만드세요.',PD,"result=pd.Series([3,7,5],index=['A','B','C'])",S('result',[3,7,5],['A','B','C'])),
        P('s에서 라벨20의 값 selected와 두 번째 위치의 값 second를 구하세요.',PD+'s=pd.Series([4,9,2],index=[20,10,30])','selected=s.loc[20]\nsecond=s.iloc[1]',[C('selected',4),C('second',9)]),
        P('s에서 west,east 순서로 선택한 Series result를 만들고 합 total을 구하세요.',PD+"s=pd.Series([2,5,8],index=['east','north','west'])","result=s.loc[['west','east']]\ntotal=result.sum()",S('result',[8,2],['west','east'])+(C('total',10),)),
    ])
    add('frame','DataFrame 만들기와 축',
        'DataFrame은 행·열 라벨이 있는2차원 표입니다. 사전의 키가 열 이름, 각 목록이 열 값이 됩니다. index는 행 라벨이며 자동으로 숫자 데이터 열이 되지 않습니다.',
        "df=pd.DataFrame({'score':[3,7],'visits':[1,2]},index=['A','B'])\ndf.shape\ndf.columns\ndf.index",
        '같은 사전에 넣는 열의 길이를 맞추세요. 열 이름과 행 라벨을 바꾸어 해석하지 마세요.',[7,8],[
        P('행 A,B, 열 score,visits 순서의 result를 만드세요. score는3,7이고 visits는1,2입니다.',PD,"result=pd.DataFrame({'score':[3,7],'visits':[1,2]},index=['A','B'])",F('result',[[3,1],[7,2]],['A','B'],['score','visits'])),
        P('data를 DataFrame result로 만들고 행 라벨을 Mon,Tue로 지정하세요.',PD+"data={'temperature':[20,22],'rain':[0,1]}","result=pd.DataFrame(data,index=['Mon','Tue'])",F('result',[[20,0],[22,1]],['Mon','Tue'],['temperature','rain'])),
        P('df의 행 라벨 목록 labels, 열 이름 목록 names, shape인 shape를 기록하세요. 라벨은 데이터 열로 넣지 마세요.',PD+"df=pd.DataFrame({'a':[1,2],'b':[3,4]},index=['x','y'])",'labels=df.index.tolist()\nnames=df.columns.tolist()\nshape=df.shape',[C('labels',['x','y']),C('names',['a','b']),C('shape',[2,2])]),
    ])
    add('csv','CSV 읽기: 인덱스·헤더·인코딩',
        'read_csv는 구분자·헤더·인코딩 규칙으로 텍스트를 표로 해석합니다. index_col은 행 라벨로 사용할 열입니다. header=None은 첫 줄도 데이터인 파일에 씁니다. UTF-8과 CP949를 혼동하면 오류 또는 잘못된 글자가 생깁니다.',
        "pd.read_csv('scores.csv',index_col='name')\npd.read_csv('raw.csv',header=None,names=['name','score'])\npd.read_csv('korean.csv',encoding='cp949')",
        '따옴표로 둘러싼 쉼표는 셀 내부 데이터일 수 있습니다. split으로 직접 나누지 마세요. 실습은 제공된 작은 오프라인 파일을 씁니다.',[9,10,11],[
        P('scores.csv를 읽어 name을 행 라벨로 사용하는 result를 만드세요.',PD,"result=pd.read_csv('scores.csv',index_col='name')",F('result',[[80],[95]],['Ann','Bo'],['score']),files={'scores.csv':{'text':'name,score\nAnn,80\nBo,95\n'}}),
        P('헤더 없는 raw.csv를 name,score 두 열의 result로 읽으세요. 기본 숫자 인덱스를 유지하세요.',PD,"result=pd.read_csv('raw.csv',header=None,names=['name','score'])",F('result',[['Ann',80],['Bo',95]],[0,1],['name','score']),files={'raw.csv':{'text':'Ann,80\nBo,95\n'}}),
        P('CP949인 korean.csv를 읽어 이름을 행 라벨로 사용하는 result를 만드세요. 메모 속 쉼표도 한 셀로 유지하세요.',PD,"result=pd.read_csv('korean.csv',encoding='cp949',index_col='이름')",F('result',[[90,'서울,종로'],[80,'부산']],['가람','나래'],['점수','메모']),files={'korean.csv':{'text':'이름,점수,메모\n가람,90,"서울,종로"\n나래,80,부산\n','encoding':'cp949'}}),
    ])
    add('columns','열 하나와 열 목록의 반환 형태',
        'df["열"]은 Series, df[["열"]]는 DataFrame을 반환합니다. 여러 열을 고를 때도 열 이름 목록을 사용합니다. tolist는 Series 값을 일반 목록으로 바꿉니다.',
        "df['score']\ndf[['score']]\ndf[['visits','score']]\ndf['score'].tolist()",
        '대괄호가 한 겹인지 두 겹인지에 따라 차원이 달라집니다.',[12,13,14,15],[
        P('df의 score 열을 Series result로 선택하세요.',PD+"df=pd.DataFrame({'score':[4,7],'visits':[1,3]},index=['A','B'])","result=df['score']",S('result',[4,7],['A','B'])),
        P('df의 score 열 하나만 가진 DataFrame result를 만드세요.',PD+"df=pd.DataFrame({'score':[4,7],'visits':[1,3]},index=['A','B'])","result=df[['score']]",F('result',[[4],[7]],['A','B'],['score'])),
        P('df에서 visits,score 순서로 열을 선택한 result와 score의 일반 목록 values를 만드세요.',PD+"df=pd.DataFrame({'score':[4,7],'visits':[1,3],'extra':[99,99]},index=['A','B'])","result=df[['visits','score']]\nvalues=df['score'].tolist()",F('result',[[1,4],[3,7]],['A','B'],['visits','score'])+(C('values',[4,7]),)),
    ])
    add('argmax','최댓값의 위치와 라벨',
        'Series.argmax()는 최댓값의 정수 위치, idxmax()는 그 행 라벨입니다. max()는 최댓값 자체입니다. 같은 최대가 여러 개면 처음 만나는 위치/라벨을 반환합니다. 정렬하지 않아도 구할 수 있습니다.',
        's.max()\ns.argmax()\ns.idxmax()',
        '라벨이 정수여도 위치와 같다고 가정하지 마세요.',[6],[
        P('s의 최댓값 value, 위치 position, 라벨 label을 구하세요.',PD+"s=pd.Series([5,12,9],index=['north','west','east'])",'value=s.max()\nposition=s.argmax()\nlabel=s.idxmax()',[C('value',12),C('position',1),C('label','west')]),
        P('정수 라벨인 s의 최댓값 라벨 winner와 위치 position을 구하세요.',PD+'s=pd.Series([7,4,9],index=[10,20,30])','winner=s.idxmax()\nposition=s.argmax()',[C('winner',30),C('position',2)]),
        P('df에서 score가 가장 큰 사람의 라벨 winner를 구하고 그 사람의 visits를 visit_count에 담으세요.',PD+"df=pd.DataFrame({'score':[50,90,75],'visits':[8,2,5]},index=['A','B','C'])","winner=df['score'].idxmax()\nvisit_count=df.loc[winner,'visits']",[C('winner','B'),C('visit_count',2)]),
    ])
    add('computed','계산 열과 중복 합산 방지',
        '열끼리 연산하면 같은 행 라벨을 맞추어 계산합니다. axis=1은 열을 줄여 행별 결과를 만듭니다. 이미 total 같은 계산 열이 있는 표 전체를 다시 합치면 중복 계산하므로 원래 과목 열만 명시하세요. 계산된 열은 스프레드시트 수식처럼 자동 재계산되지 않습니다.',
        "df['total']=df[['math','english']].sum(axis=1)\ndf['mean']=df[['math','english']].mean(axis=1)",
        'df.sum(axis=1)로 전체 숫자 열을 무심코 합치지 마세요.',[16,17,18],[
        P('df에 math+english 합계 total 열을 추가하세요. 원래 두 과목 열을 유지하세요.',PD+"df=pd.DataFrame({'math':[80,90],'english':[70,85]},index=['A','B'])","df['total']=df[['math','english']].sum(axis=1)",F('df',[[80,70,150],[90,85,175]],['A','B'],['math','english','total'])),
        P('df의 오래된 total을 무시하고 math,english의 평균으로 mean 열을 추가하세요. 기존 열은 보존하세요.',PD+"df=pd.DataFrame({'math':[80,90],'english':[70,50],'total':[999,999]},index=['A','B'])","df['mean']=df[['math','english']].mean(axis=1)",F('df',[[80,70,999,75],[90,50,999,70]],['A','B'],['math','english','total','mean'])),
        P('A의 math를100으로 고친 뒤 두 과목 합계 total을 다시 계산하세요.',PD+"df=pd.DataFrame({'math':[80,90],'english':[70,50],'total':[150,140]},index=['A','B'])","df.loc['A','math']=100\ndf['total']=df[['math','english']].sum(axis=1)",F('df',[[100,70,170],[90,50,140]],['A','B'],['math','english','total'])),
    ])
    add('drop','행·열 제거와 inplace',
        'drop(columns=[...])은 열 제거, drop(index=[...])는 행 제거입니다. 기본은 새 표를 반환하고 원본은 유지합니다. inplace=True를 쓰면 원본을 변경하고 None을 반환합니다.',
        "result=df.drop(columns=['memo'])\ndf.drop(index=['B'],inplace=True)",
        'df=df.drop(...,inplace=True)는 df에 None을 저장하는 실수입니다.',[19,20,21],[
        P('memo 열을 제거한 result를 만들고 원본 df는 유지하세요.',PD+"df=pd.DataFrame({'score':[5,7],'memo':['x','y']},index=['A','B'])","result=df.drop(columns=['memo'])",F('result',[[5],[7]],['A','B'],['score'])+F('df',[[5,'x'],[7,'y']],['A','B'],['score','memo'])),
        P('df에서 B행만 제자리 제거하세요. df가 DataFrame으로 남아야 합니다.',PD+"df=pd.DataFrame({'score':[5,7,9]},index=['A','B','C'])","df.drop(index=['B'],inplace=True)",F('df',[[5],[9]],['A','C'],['score'])),
        P('df에서 B행과 memo열을 제외한 result를 만드세요. 원본은 보존하세요.',PD+"df=pd.DataFrame({'score':[5,7,9],'memo':['x','y','z']},index=['A','B','C'])","result=df.drop(index=['B'],columns=['memo'])",F('result',[[5],[9]],['A','C'],['score'])+F('df',[[5,'x'],[7,'y'],[9,'z']],['A','B','C'],['score','memo'])),
    ])
    add('loc','라벨로 선택하고 수정하기',
        'loc[행라벨,열라벨]은 이름으로 접근합니다. 정렬된 라벨 슬라이스에서 끝 라벨도 포함합니다. 행이나 열 하나만 고르면 차원이 줄어들 수 있고 목록으로 고르면 표 형태를 유지합니다.',
        "df.loc['B','score']\ndf.loc['A':'C',['score']]\ndf.loc[['B'],['score']]",
        '라벨 범위와 위치 범위의 끝 포함 규칙이 다릅니다. 연속 대괄호 대신 loc로 수정 대상을 명확히 지정하세요.',[27,28,29],[
        P('A부터B까지 score 열만 가진 DataFrame result를 선택하세요.',PD+"df=pd.DataFrame({'score':[3,6,9],'n':[1,2,3]},index=['A','B','C'])","result=df.loc['A':'B',['score']]",F('result',[[3],[6]],['A','B'],['score'])),
        P('C,A 순서로 n,score 순서의 열을 가진 result를 선택하세요.',PD+"df=pd.DataFrame({'score':[3,6,9],'n':[1,2,3]},index=['A','B','C'])","result=df.loc[['C','A'],['n','score']]",F('result',[[3,9],[1,3]],['C','A'],['n','score'])),
        P('df의 B행 score만10으로 고치고 B행을1행짜리 DataFrame result로 선택하세요.',PD+"df=pd.DataFrame({'score':[3,6,9],'n':[1,2,3]},index=['A','B','C'])","df.loc['B','score']=10\nresult=df.loc[['B']]",F('result',[[10,2]],['B'],['score','n'])+F('df',[[3,1],[10,2],[9,3]],['A','B','C'],['score','n'])),
    ])
    add('iloc','위치로 선택: 끝 제외',
        'iloc은0부터 시작하는 위치로 접근하며 슬라이스의 끝은 제외합니다. head(n),tail(n)은 앞/뒤 몇 행을 빠르게 확인합니다. 라벨이10,20,30이어도 위치는0,1,2입니다.',
        'df.iloc[0:2,1:3]\ndf.iloc[-1]\ndf.head(2)\ndf.tail(2)',
        'loc[10]과 iloc[10]은 전혀 다릅니다. loc의 끝 포함을 iloc에 적용하지 마세요.',[25,26,30,31,32,33],[
        P('df의 처음 두 행과 두 번째 열만 가진 DataFrame result를 선택하세요.',PD+'df=pd.DataFrame({"a":[1,2,3],"b":[4,5,6]},index=[10,20,30])','result=df.iloc[:2,1:2]',F('result',[[4],[5]],[10,20],['b'])),
        P('df의 마지막 두 행을 원래 순서대로 result에 담으세요.',PD+"df=pd.DataFrame({'score':[2,4,6,8]},index=['A','B','C','D'])",'result=df.tail(2)',F('result',[[6],[8]],['C','D'],['score'])),
        P('df에서 위치2,0 순서로 행을 선택하되 처음 두 열만 result로 만드세요.',PD+"df=pd.DataFrame({'a':[1,2,3],'b':[4,5,6],'c':[7,8,9]},index=['X','Y','Z'])",'result=df.iloc[[2,0],:2]',F('result',[[3,6],[1,4]],['Z','X'],['a','b'])),
    ])
    add('filter','여러 조건으로 행 걸러내기',
        '각 열의 비교 결과는 행 라벨이 있는 Boolean Series입니다. 조건을 &와 |로 결합할 때 각각 괄호로 묶습니다. loc[조건,열목록]으로 행과 열을 함께 고를 수 있습니다.',
        "df.loc[(df['score']>=80)&(df['visits']>=2),['score']]",
        'Python and/or는 Series 전체의 참·거짓을 요구해 오류가 납니다.',[34],[
        P('score가80 이상인 행만 result로 선택하세요.',PD+"df=pd.DataFrame({'score':[70,80,90]},index=['A','B','C'])","result=df.loc[df['score']>=80]",F('result',[[80],[90]],['B','C'],['score'])),
        P('score80 이상이면서 visits2 이상인 사람의 score열만 result로 만드세요.',PD+"df=pd.DataFrame({'score':[90,80,95],'visits':[1,3,2]},index=['A','B','C'])","result=df.loc[(df['score']>=80)&(df['visits']>=2),['score']]",F('result',[[80],[95]],['B','C'],['score'])),
        P('math,english 평균 mean 열을 추가한 후 mean75 이상인 행의 두 과목과 mean을 result에 담으세요.',PD+"df=pd.DataFrame({'math':[90,40,80],'english':[70,60,80]},index=['A','B','C'])","df['mean']=df[['math','english']].mean(axis=1)\nresult=df.loc[df['mean']>=75]",F('result',[[90,70,80],[80,80,80]],['A','C'],['math','english','mean'])),
    ])
    add('missing','결측값 검사·제거·대체',
        'isna는 결측 위치를 Boolean으로 표시합니다. count는 결측이 아닌 개수입니다. dropna(subset=[...])는 필요한 열의 결측행만 제거하고 fillna는 대체값을 지정합니다. 결측을0으로 채우는 것은 측정0과 같은 의미인지 판단해야 합니다.',
        "df.isna().sum()\ndf.dropna(subset=['score'])\ndf.fillna({'score':0})\ndf.count()",
        'NaN == NaN은 참이 아닙니다. np.nan과의 등호 비교 대신 isna를 쓰세요.',[42,43,44],[
        P('df의 열별 결측 개수를 Series missing에 담으세요.',PD+"df=pd.DataFrame({'score':[1,np.nan,3],'visits':[np.nan,2,np.nan]})",'missing=df.isna().sum()',S('missing',[1,2],['score','visits'])),
        P('score가 결측인 행만 제외한 result를 만드세요. visits의 결측은 유지하세요.',PD+"df=pd.DataFrame({'score':[1,np.nan,3],'visits':[np.nan,2,4]},index=['A','B','C'])","result=df.dropna(subset=['score'])",F('result',[[1,NAN],[3,4]],['A','C'],['score','visits'])),
        P('score 결측을 해당 열의 평균으로 대체한 result를 만들고 원본 df는 유지하세요.',PD+"df=pd.DataFrame({'score':[10,np.nan,30]},index=['A','B','C'])","result=df.fillna({'score':df['score'].mean()})",F('result',[[10],[20],[30]],['A','B','C'],['score'])+F('df',[[10],[NAN],[30]],['A','B','C'],['score'])),
    ])
    add('concat','표 이어 붙이기와 인덱스 정렬',
        'concat(axis=0)은 행을 이어 붙이고 열 이름을 맞춥니다. 기본 outer는 모든 열을 남겨 없는 값을NaN으로 채웁니다. ignore_index=True는 새 숫자 인덱스를 줍니다. axis=1은 열을 붙이면서 행 라벨을 맞춥니다.',
        'pd.concat([a,b],ignore_index=True)\npd.concat([a,b],axis=1)\npd.concat([a,b],join="inner")',
        'concat은 키 열을 찾아 관계를 결합하는 merge와 다릅니다. 같은 이름의 행 라벨이 중복될 수도 있습니다.',[36,37,38],[
        P('a,b를 순서대로 행으로 붙이고 새 숫자 인덱스의 result를 만드세요.',PD+"a=pd.DataFrame({'score':[3,5]},index=['A','B'])\nb=pd.DataFrame({'score':[7]},index=['C'])",'result=pd.concat([a,b],ignore_index=True)',F('result',[[3],[5],[7]],[0,1,2],['score'])),
        P('a,b를 열 방향으로 붙인 result를 만드세요. 행 라벨을 맞추고 없는 값은NaN으로 남기세요.',PD+"a=pd.DataFrame({'score':[3,5]},index=['A','B'])\nb=pd.DataFrame({'visits':[2,4]},index=['B','C'])",'result=pd.concat([a,b],axis=1)',F('result',[[3,NAN],[5,2],[NAN,4]],['A','B','C'],['score','visits'])),
        P('a,b를 행으로 이어 붙이되 공통 열만 남기고 새 숫자 인덱스를 사용하세요.',PD+"a=pd.DataFrame({'score':[3],'extra':[99]})\nb=pd.DataFrame({'score':[7],'memo':['ok']})","result=pd.concat([a,b],join='inner',ignore_index=True)",F('result',[[3],[7]],[0,1],['score'])),
    ])
    add('merge','키로 표 결합: inner와 left',
        'merge는 키 값이 같은 행을 대응시킵니다. inner는 양쪽에 있는 키, left는 왼쪽의 모든 행을 유지합니다. 일치하지 않는 오른쪽 값은NaN입니다. 결합 전에 키가 유일한지 확인해야 합니다.',
        "pd.merge(left,right,on='id',how='inner')\npd.merge(left,right,on='id',how='left')",
        '두 표를 같은 줄 번호끼리 붙이는 연산이 아닙니다. 오른쪽의 행 순서가 달라도 키로 찾습니다.',[39,40,41],[
        P('id를 키로 a,b에 모두 있는 사람만 result로 결합하세요.',PD+"a=pd.DataFrame({'id':[1,2],'score':[80,90]})\nb=pd.DataFrame({'id':[2,3],'team':['B','C']})","result=pd.merge(a,b,on='id',how='inner')",F('result',[[2,90,'B']],[0],['id','score','team'])),
        P('a의 모든 사람을 유지하며 id로 b의 team을 붙인 result를 만드세요.',PD+"a=pd.DataFrame({'id':[1,2],'score':[80,90]})\nb=pd.DataFrame({'id':[2,3],'team':['B','C']})","result=pd.merge(a,b,on='id',how='left')",F('result',[[1,80,NAN],[2,90,'B']],[0,1],['id','score','team'])),
        P('id로 a,b를 결합한 뒤 score80 이상인 행만 result에 남기세요. 왼쪽 순서를 유지하세요.',PD+"a=pd.DataFrame({'id':[1,2,3],'score':[90,60,85]})\nb=pd.DataFrame({'id':[3,1,2],'team':['C','A','B']})","joined=pd.merge(a,b,on='id',how='left')\nresult=joined.loc[joined['score']>=80]",F('result',[[1,90,'A'],[3,85,'C']],[0,2],['id','score','team'])),
    ])
    add('merge_detail','중복 키와 겹치는 열 이름',
        '같은 키가 양쪽에서 여러 번 나오면 가능한 조합만큼 행이 늘어납니다. 동일한 비키 열에는 suffixes로 출처를 구분합니다. left_index/right_index는 열 대신 인덱스를 결합 키로 사용합니다.',
        "pd.merge(a,b,on='id',suffixes=('_old','_new'))\npd.merge(a,b,left_index=True,right_index=True)",
        'merge 후 행 수가 늘어난 것을 무조건 버그라고 보지 말고 키 중복을 확인하세요. 데이터 손실을 막으려면 validate 인자도 활용할 수 있습니다.',[39,40,41],[
        P('id로 a,b를 합쳐 점수 열을 score_old,score_new로 구분한 result를 만드세요.',PD+"a=pd.DataFrame({'id':[1,2],'score':[70,80]})\nb=pd.DataFrame({'id':[1,2],'score':[75,85]})","result=pd.merge(a,b,on='id',suffixes=('_old','_new'))",F('result',[[1,70,75],[2,80,85]],[0,1],['id','score_old','score_new'])),
        P('중복 키를 삭제하지 말고 id를 기준으로 a,b의 모든 대응 조합을 result에 담으세요.',PD+"a=pd.DataFrame({'id':[1,1],'name':['A','B']})\nb=pd.DataFrame({'id':[1,1],'item':['X','Y']})","result=pd.merge(a,b,on='id')",F('result',[[1,'A','X'],[1,'A','Y'],[1,'B','X'],[1,'B','Y']],[0,1,2,3],['id','name','item'])),
        P('a,b의 행 인덱스를 키로 공통 라벨만 결합한 result를 만드세요.',PD+"a=pd.DataFrame({'score':[10,20]},index=['A','B'])\nb=pd.DataFrame({'visits':[3,4]},index=['B','C'])",'result=pd.merge(a,b,left_index=True,right_index=True)',F('result',[[20,3]],['B'],['score','visits'])),
    ])
    add('pivot','긴 표를 넓은 표로 바꾸기',
        'pivot의 index는 결과 행, columns는 결과 열, values는 셀 값을 결정합니다. 같은(행,열)조합이 중복되면 집계 방법을 정할 수 없어 오류가 납니다. values를 여러 열로 지정하는 것도 가능하며 다중 열 인덱스를 만듭니다.',
        "df.pivot(index='day',columns='sensor',values='value')",
        'pivot은 합계나 평균을 자동으로 계산하지 않습니다. 중복 데이터의 집계는 다음 단원의 pivot_table을 사용합니다.',[35],[
        P('day를 행, sensor를 열, value를 셀로 갖는 result를 만드세요.',PD+"df=pd.DataFrame({'day':['Mon','Mon','Tue','Tue'],'sensor':['A','B','A','B'],'value':[1,2,3,4]})","result=df.pivot(index='day',columns='sensor',values='value')",F('result',[[1,2],[3,4]],['Mon','Tue'],['A','B'])),
        P('name을 행, subject를 열, score를 셀로 갖는 result를 만드세요. 없는 조합은NaN으로 남기세요.',PD+"df=pd.DataFrame({'name':['Ann','Ann','Bo'],'subject':['math','english','math'],'score':[80,90,70]})","result=df.pivot(index='name',columns='subject',values='score')",F('result',[[90,80],[NAN,70]],['Ann','Bo'],['english','math'])),
        P('day/sensor/value 표를 넓힌 result를 만든 뒤 센서 A,B의 행별 합 totals를 구하세요.',PD+"df=pd.DataFrame({'day':['Mon','Mon','Tue','Tue'],'sensor':['A','B','A','B'],'value':[2,5,3,7]})","result=df.pivot(index='day',columns='sensor',values='value')\ntotals=result[['A','B']].sum(axis=1)",F('result',[[2,5],[3,7]],['Mon','Tue'],['A','B'])+S('totals',[7,10],['Mon','Tue'])),
    ])
    add('pivot_table','중복 관측값을 집계해 피벗하기',
        'pivot_table은 같은 조합의 여러 관측을 aggfunc로 집계합니다. 기본 평균을 무심코 사용하지 말고 sum/mean 등 목적을 지정하세요. fill_value는 집계 후 없는 조합을 채우는 값입니다.',
        "df.pivot_table(index='team',columns='kind',values='count',aggfunc='sum',fill_value=0)",
        '사람 수를 세려는지 이미 집계된 count의 합을 구하려는지 구분하세요.',[35,46],[
        P('team을 행, kind를 열로 하여 count의 합계 result를 만드세요. 없는 조합은0입니다.',PD+"df=pd.DataFrame({'team':['A','A','B'],'kind':['x','x','y'],'count':[2,3,4]})","result=df.pivot_table(index='team',columns='kind',values='count',aggfunc='sum',fill_value=0)",F('result',[[5,0],[0,4]],['A','B'],['x','y'])),
        P('team별 kind별 score 평균 result를 만드세요. 없는 조합은NaN입니다.',PD+"df=pd.DataFrame({'team':['A','A','B'],'kind':['x','x','y'],'score':[60,80,90]})","result=df.pivot_table(index='team',columns='kind',values='score',aggfunc='mean')",F('result',[[70,NAN],[NAN,90]],['A','B'],['x','y'])),
        P('count가0보다 큰 행만 골라 team/kind별 count 합계 result를 만드세요. 없는 조합은0입니다.',PD+"df=pd.DataFrame({'team':['A','A','B','B'],'kind':['x','y','x','y'],'count':[2,-9,3,4]})","valid=df.loc[df['count']>0]\nresult=valid.pivot_table(index='team',columns='kind',values='count',aggfunc='sum',fill_value=0)",F('result',[[2,0],[3,4]],['A','B'],['x','y'])),
    ])
    add('groupby','집단별 집계와 describe',
        'groupby는 범주별로 행을 모은 뒤 합·평균 등을 계산합니다. 숫자 열을 명시해 텍스트 열과 불필요한 계산 열을 섞지 마세요. describe는 개수·평균·표준편차·사분위수 등을 요약하며 표준편차는 기본 ddof=1입니다.',
        "df.groupby('team')['score'].mean()\ndf[['score']].describe()",
        'NaN은 count에서 제외됩니다. groupby의 평균을 집단 크기를 고려하지 않고 또 평균내면 전체 평균과 다를 수 있습니다.',[42,46],[
        P('team별 score 평균 Series result를 구하세요.',PD+"df=pd.DataFrame({'team':['A','B','A'],'score':[60,90,80]})","result=df.groupby('team')['score'].mean()",S('result',[70,90],['A','B'])),
        P('df.score 요약에서 결측 제외 개수 count, 평균 mean, 표본 표준편차 std를 기록하세요.',PD+"df=pd.DataFrame({'score':[1,3,5,np.nan]})","summary=df['score'].describe()\ncount=summary['count']\nmean=summary['mean']\nstd=summary['std']",[C('count',3),C('mean',3),C('std',2)]),
        P('score 결측행을 제거한 뒤 team별 visits 합계를 Series result로 만드세요. 결측 점수 행의 방문 횟수는 합계에 넣지 마세요.',PD+"df=pd.DataFrame({'team':['A','A','B','B'],'score':[80,np.nan,90,70],'visits':[2,100,3,4]})","result=df.dropna(subset=['score']).groupby('team')['visits'].sum()",S('result',[2,7],['A','B'])),
    ])
    add('datetime','날짜 변환과 월별 집계',
        '날짜 문자열은 먼저 to_datetime으로 변환해야 dt.year,dt.month 같은 날짜 속성을 사용할 수 있습니다. 여러 해의 자료에서 month만 묶으면 서로 다른 해의 같은 달이 합쳐집니다. 연도와 월을 함께 관리하세요.',
        "df['date']=pd.to_datetime(df['date'])\ndf['year']=df['date'].dt.year\ndf['month']=df['date'].dt.month",
        '문자열의 일부를 무조건 잘라 월로 삼으면 날짜 형식 변화와 잘못된 날짜를 놓칩니다.',[45,46],[
        P('df.date를 날짜로 변환하고 연도 Series years, 월 Series months를 구하세요.',PD+"df=pd.DataFrame({'date':['2025-12-31','2026-01-01']})","df['date']=pd.to_datetime(df['date'])\nyears=df['date'].dt.year\nmonths=df['date'].dt.month",S('years',[2025,2026],[0,1])+S('months',[12,1],[0,1])),
        P('2026년 자료 df에서 월별 amount 합계를 result에 담으세요. result 인덱스는 월 번호입니다.',PD+"df=pd.DataFrame({'date':['2026-01-01','2026-01-15','2026-02-01'],'amount':[2,3,4]})","df['date']=pd.to_datetime(df['date'])\nresult=df.groupby(df['date'].dt.month)['amount'].sum()",S('result',[5,4],[1,2])),
        P('df에서2026년 자료만 선택한 뒤 월별 amount 합계 result를 만드세요. 2025년의 같은 달은 합치지 마세요.',PD+"df=pd.DataFrame({'date':['2025-01-01','2026-01-02','2026-02-03'],'amount':[100,2,7]})","df['date']=pd.to_datetime(df['date'])\ncurrent=df.loc[df['date'].dt.year==2026]\nresult=current.groupby(current['date'].dt.month)['amount'].sum()",S('result',[2,7],[1,2])),
    ])
    add('plot','pandas에서 그리기와 전치',
        'DataFrame.plot은 Matplotlib Axes를 반환합니다. 행 인덱스를x축, 선택한 각 열을 데이터 계열로 사용합니다. .T로 전치하면 원래 행이 열로 바뀌어 비교 대상도 바뀝니다. kind="bar" 등으로 그래프 종류를 고릅니다.',
        "ax=df.plot(kind='bar')\nfig=ax.figure\ntransposed=df.T\n# 범주형 선 그래프의 눈금 위치와 이름 명시\nax.set_xticks([0,1],labels=['math','english'])",
        '전치하면 라벨과 데이터 역할이 모두 바뀝니다. 보기 좋은 그림보다 무엇을 비교하는지가 우선입니다.',[22,23,24],[
        P('df를 전치한 DataFrame result를 만드세요.',PD+"df=pd.DataFrame({'math':[80,90],'english':[70,85]},index=['A','B'])",'result=df.T',F('result',[[80,90],[70,85]],['math','english'],['A','B'])),
        P('df의 score를 인덱스에 따른 선 그래프로 그리고 Figure를 fig에 담으세요.',PD+"df=pd.DataFrame({'score':[3,7,5]},index=[1,2,3])","ax=df.plot(y='score',kind='line')\nfig=ax.figure",[C('fig',[1,2,3],['axes',0,'lines',0,'x','data']),C('fig',[3,7,5],['axes',0,'lines',0,'y','data'])]),
        P('df를 전치한 result에서 A열을 선으로 그려 fig에 담으세요. x좌표0,1에 과목 math,english 눈금 이름을 순서대로 표시하세요.',PD+"df=pd.DataFrame({'math':[80,90],'english':[70,85]},index=['A','B'])","result=df.T\nax=result.plot(y='A',kind='line')\nax.set_xticks([0,1],labels=result.index)\nfig=ax.figure",F('result',[[80,90],[70,85]],['math','english'],['A','B'])+(C('fig',[80,70],['axes',0,'lines',0,'y','data']),C('fig',[0,1],['axes',0,'lines',0,'x','data']),C('fig',['math','english'],['axes',0,'named_xticklabels']))),
    ])
    return tuple(result)
