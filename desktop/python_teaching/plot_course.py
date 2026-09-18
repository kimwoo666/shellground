"""Actual Matplotlib artist data is graded, not a screenshot resemblance."""
from .model import Lesson, problem as P, check as C

PLT = 'import numpy as np\nimport matplotlib.pyplot as plt\n'


def ax(value, path, label=None, number=0):
    return C('fig',value,['axes',number,*path],label)


def line(x,y,number=0,axes=0):
    return (ax(x,['lines',number,'x','data'],'선의 x 좌표',axes),
            ax(y,['lines',number,'y','data'],'선의 y 좌표',axes))


def bars(heights, positions=None, width=.8, bottoms=None):
    positions = positions if positions is not None else list(range(len(heights)))
    bottoms = bottoms if bottoms is not None else [0]*len(heights)
    checks = [ax(len(heights),['patch_count'],'막대 개수')]
    for i,(x,y,h) in enumerate(zip(positions,bottoms,heights)):
        for prop,value in [('x',x-width/2),('y',y),('width',width),('height',h)]:
            checks.append(ax(value,['patches',i,prop],f'막대 {i+1} {prop}'))
    return tuple(checks)


def lessons():
    result=[]
    def add(key,title,why,syntax,pitfall,pages,cases):
        result.append(Lesson('plot_'+key,'Matplotlib',title,why,syntax,pitfall,
            'week_2_2_handout.pdf',tuple(pages),tuple(cases),
            (result[-1].key,) if result else ('np_vectorize',)))
    add('line','Figure와 Axes에 선 그리기',
        'Figure는 그림 전체, Axes는 데이터가 그려지는 한 영역, Axis는 x축·y축의 눈금과 축 객체입니다. fig, ax = plt.subplots()로 그림과 영역을 만들고 ax.plot(x,y)로 대응하는 좌표를 연결합니다. 화면은 실제 Matplotlib 렌더링입니다.',
        'fig, ax = plt.subplots()\nax.plot(x,y)',
        'x와 y의 길이는 같아야 합니다. y만 주면 x는0부터 시작하는 위치가 됩니다.',[2,3,4,7,9,15,16,17],[
        P('x,y 좌표를 연결한 선 하나를 가진 fig를 만드세요.',PLT+'x=[1,2,3]\ny=[2,5,4]','fig,ax=plt.subplots()\nax.plot(x,y)',line([1,2,3],[2,5,4])+(ax(1,['line_count']),)),
        P('x에 대응하는 제곱값을 선으로 그린 fig를 만드세요.',PLT+'x=np.array([-2,-1,0,1,2])','fig,ax=plt.subplots()\nax.plot(x,x*x)',line([-2,-1,0,1,2],[4,1,0,1,4])),
        P('시간 t에서 측정값 measured와 보정값 measured-2를 두 선으로 그리세요. 측정 선을 먼저 추가하세요.',PLT+'t=np.array([0,1,2])\nmeasured=np.array([4,7,6])','fig,ax=plt.subplots()\nax.plot(t,measured)\nax.plot(t,measured-2)',line([0,1,2],[4,7,6])+line([0,1,2],[2,5,4],1)+(ax(2,['line_count']),)),
    ])
    add('style','선의 색·마커·선 종류',
        'color는 색, marker는 각 측정점 모양, linestyle은 점을 잇는 선 모양입니다. r--o 같은 축약 표기도 있지만 처음에는 키워드 인자로 의미를 분리합니다. plt.style.available로 현재 설치 버전의 스타일 이름을 확인할 수 있습니다.',
        "ax.plot(x,y,color='red',marker='o',linestyle='--')\nplt.style.available",
        '스타일 이름은 버전에 따라 달라집니다. 색만으로 집단을 구분하지 말고 마커나 범례도 사용하세요.',[10,14],[
        P('x,y를 빨간 원 마커와 파선으로 그리세요.',PLT+'x=[0,1,2]\ny=[1,4,2]',"fig,ax=plt.subplots()\nax.plot(x,y,color='red',marker='o',linestyle='--')",line([0,1,2],[1,4,2])+(ax('#ff0000',['lines',0,'color']),ax('o',['lines',0,'marker']),ax('--',['lines',0,'linestyle']))),
        P('x,y를 파란 사각 마커와 실선으로 그리세요.',PLT+'x=[1,2,3]\ny=[3,1,5]',"fig,ax=plt.subplots()\nax.plot(x,y,color='blue',marker='s',linestyle='-')",line([1,2,3],[3,1,5])+(ax('#0000ff',['lines',0,'color']),ax('s',['lines',0,'marker']),ax('-',['lines',0,'linestyle']))),
        P('x와 x²를 검은 파선으로 그리되 마커는 붙이지 마세요.',PLT+'x=np.array([0,1,2,3])',"fig,ax=plt.subplots()\nax.plot(x,x*x,color='black',linestyle='--')",line([0,1,2,3],[0,1,4,9])+(ax('#000000',['lines',0,'color']),ax('--',['lines',0,'linestyle']),ax('None',['lines',0,'marker']))),
    ])
    add('labels','제목·축 이름·범례',
        '데이터를 올바르게 그려도 축의 의미와 단위가 없으면 해석하기 어렵습니다. 각 선의 label을 지정하고 ax.legend()를 호출해야 범례가 나타납니다.',
        "ax.set_title('Temperature')\nax.set_xlabel('Time (s)')\nax.set_ylabel('Celsius')\nax.plot(x,y,label='sensor')\nax.legend()",
        'label 인자만 지정하면 범례가 자동으로 보이는 것은 아닙니다.',[12],[
        P('x,y를 그리고 제목 Temperature, x축 Time (s), y축 Celsius를 붙이세요.',PLT+'x=[0,1,2]\ny=[20,22,21]',"fig,ax=plt.subplots()\nax.plot(x,y)\nax.set_title('Temperature')\nax.set_xlabel('Time (s)')\nax.set_ylabel('Celsius')",line([0,1,2],[20,22,21])+(ax('Temperature',['title']),ax('Time (s)',['xlabel']),ax('Celsius',['ylabel']))),
        P('a,b를 x에 대해 순서대로 그려 범례에 before, after를 표시하세요.',PLT+'x=[1,2,3]\na=[2,3,4]\nb=[3,3,5]',"fig,ax=plt.subplots()\nax.plot(x,a,label='before')\nax.plot(x,b,label='after')\nax.legend()",line([1,2,3],[2,3,4])+line([1,2,3],[3,3,5],1)+(ax(['before','after'],['legend']),)),
        P('raw를 x에 대해 그리고 raw-raw.mean()도 그리세요. 범례는 raw, centered 순서이며 y축은 Value로 표시하세요.',PLT+'x=np.array([0,1,2])\nraw=np.array([3,6,9])',"fig,ax=plt.subplots()\nax.plot(x,raw,label='raw')\nax.plot(x,raw-raw.mean(),label='centered')\nax.set_ylabel('Value')\nax.legend()",line([0,1,2],[3,6,9])+line([0,1,2],[-3,0,3],1)+(ax(['raw','centered'],['legend']),ax('Value',['ylabel']))),
    ])
    add('limits','축 범위·격자·그림 크기',
        'xlim과 ylim은 보이는 구간을 바꿉니다. 데이터를 삭제하는 것은 아니지만 일부를 숨길 수 있어 비교할 때 같은 범위를 쓰는 것이 중요합니다. figsize의 단위는 픽셀이 아니라 인치입니다. 픽셀 수는 인치×dpi입니다.',
        'fig,ax=plt.subplots(figsize=(6,4))\nax.set_xlim(0,10)\nax.set_ylim(0,100)\nax.grid(True)',
        '세로축을 좁혀 작은 차이를 과장하지 않도록 해석 목적을 점검하세요.',[11,33,37],[
        P('x,y를 그리고 x범위0~4, y범위0~10, 양 축 격자를 설정하세요.',PLT+'x=[1,2,3]\ny=[2,5,8]','fig,ax=plt.subplots()\nax.plot(x,y)\nax.set_xlim(0,4)\nax.set_ylim(0,10)\nax.grid(True)',line([1,2,3],[2,5,8])+(ax([0,4],['xlim']),ax([0,10],['ylim']),ax(True,['grid_x']),ax(True,['grid_y']))),
        P('8×3인치 그림에 x,y를 그리고 y범위-1~1로 설정하세요.',PLT+'x=[0,1,2]\ny=[-1,0,1]','fig,ax=plt.subplots(figsize=(8,3))\nax.plot(x,y)\nax.set_ylim(-1,1)',line([0,1,2],[-1,0,1])+(C('fig',[8,3],['size']),ax([-1,1],['ylim']))),
        P('x에서 sin(x)를 그리고 x범위0~π, y범위-1~1을 설정하세요. x축 이름은 Radians입니다.',PLT+'x=np.linspace(0,np.pi,3)',"fig,ax=plt.subplots()\nax.plot(x,np.sin(x))\nax.set_xlim(0,np.pi)\nax.set_ylim(-1,1)\nax.set_xlabel('Radians')",line([0,1.5707963267948966,3.141592653589793],[0,1,0])+(ax([0,3.141592653589793],['xlim']),ax([-1,1],['ylim']),ax('Radians',['xlabel']))),
    ])
    add('save','그림을 파일로 내보내기',
        'fig.savefig는 특정 Figure를 저장하고 plt.savefig는 현재 Figure를 저장합니다. 둘 다 유효합니다. PNG는 픽셀 이미지, SVG는 벡터 형식입니다. 이 단원에서는 실제 파일 형식과 그림 데이터를 함께 검사합니다.',
        "fig.savefig('result.png',dpi=100)\nfig.savefig('result.svg')",
        '확장자만 바꾼 빈 파일은 그림이 아닙니다. 여러 Figure가 있으면 어느 그림을 저장하는지 분명하게 하세요.',[13],[
        P('x,y 선을 담은4×3인치 fig를 만들어 report.png로100dpi 저장하세요.',PLT+'x=[0,1]\ny=[2,4]',"fig,ax=plt.subplots(figsize=(4,3))\nax.plot(x,y)\nfig.savefig('report.png',dpi=100)",line([0,1],[2,4])+(C('__files__','png',['report.png','kind']),C('__files__',400,['report.png','width']),C('__files__',300,['report.png','height']),C('__files__',True,['report.png','matches_fig'],'저장한 그림과 fig 일치'))),
        P('x,y 선을 담은 fig를 만들어 vector.svg로 저장하세요.',PLT+'x=[1,2,3]\ny=[3,2,4]',"fig,ax=plt.subplots()\nax.plot(x,y)\nfig.savefig('vector.svg')",line([1,2,3],[3,2,4])+(C('__files__','svg',['vector.svg','kind']),C('__files__',True,['vector.svg','has_paths'],'유효한 벡터 그래픽 경로'),C('__files__',True,['vector.svg','matches_fig'],'저장한 SVG와 fig 일치'))),
        P('x,x²를 그린5×2인치 fig에 제목 Squared를 붙이고 squared.png로100dpi 저장하세요.',PLT+'x=np.array([0,1,2])',"fig,ax=plt.subplots(figsize=(5,2))\nax.plot(x,x*x)\nax.set_title('Squared')\nfig.savefig('squared.png',dpi=100)",line([0,1,2],[0,1,4])+(ax('Squared',['title']),C('__files__','png',['squared.png','kind']),C('__files__',500,['squared.png','width']),C('__files__',200,['squared.png','height']),C('__files__',True,['squared.png','matches_fig'],'저장한 그림과 fig 일치'))),
    ])
    add('subplots','서브플롯과 격자 배치',
        'plt.subplots(행수,열수)는 여러 Axes를 한 Figure에 만듭니다. 1×2에서는 axes[0], axes[1], 2×2에서는 axes[행,열]로 접근합니다. subplot(2,2,1)의 마지막 번호는1부터 시작합니다. GridSpec을 쓰면 영역을 여러 칸에 걸쳐 배치할 수 있습니다.',
        'fig,axes=plt.subplots(1,2)\naxes[0].plot(x,y)\nfig=plt.figure()\ngs=fig.add_gridspec(2,2)\nleft=fig.add_subplot(gs[:,0])',
        'Figure/Axes/Axis는 서로 다른 객체입니다. np.arrange가 아니라 np.arange입니다.',[15,16,17,18,19,20],[
        P('1행2열 fig에서 왼쪽은 x와x, 오른쪽은 x와x²를 그리세요.',PLT+'x=np.array([0,1,2])','fig,axes=plt.subplots(1,2)\naxes[0].plot(x,x)\naxes[1].plot(x,x*x)',(C('fig',2,['axis_count']),ax([1,2,0,1,0,1],['subplot'],number=0),ax([1,2,0,1,1,2],['subplot'],number=1))+line([0,1,2],[0,1,2],axes=0)+line([0,1,2],[0,1,4],axes=1)),
        P('2행1열 fig에서 위는 a, 아래는 b를 x에 대해 그리세요. 각 제목은 A, B입니다.',PLT+'x=[0,1,2]\na=[2,4,3]\nb=[1,3,5]',"fig,axes=plt.subplots(2,1)\naxes[0].plot(x,a)\naxes[0].set_title('A')\naxes[1].plot(x,b)\naxes[1].set_title('B')",(C('fig',2,['axis_count']),ax([2,1,0,1,0,1],['subplot'],number=0),ax([2,1,1,2,0,1],['subplot'],number=1))+line([0,1,2],[2,4,3],axes=0)+line([0,1,2],[1,3,5],axes=1)+(ax('A',['title'],number=0),ax('B',['title'],number=1))),
        P('GridSpec2×2에서 왼쪽 두 칸을 합친 영역, 오른쪽 위, 오른쪽 아래 순서로3영역을 만드세요. 각각 x,x²,x+1을 x에 대해 그리세요.',PLT+'x=np.array([0,1,2])','fig=plt.figure()\ngs=fig.add_gridspec(2,2)\na=fig.add_subplot(gs[:,0])\nb=fig.add_subplot(gs[0,1])\nc=fig.add_subplot(gs[1,1])\na.plot(x,x)\nb.plot(x,x*x)\nc.plot(x,x+1)',(C('fig',3,['axis_count']),ax([2,2,0,2,0,1],['subplot'],number=0),ax([2,2,0,1,1,2],['subplot'],number=1),ax([2,2,1,2,1,2],['subplot'],number=2))+line([0,1,2],[0,1,2],axes=0)+line([0,1,2],[0,1,4],axes=1)+line([0,1,2],[1,2,3],axes=2)),
    ])
    add('scatter','산점도: 위치·크기·투명도',
        '산점도는 두 수치형 변수의 관계를 점으로 나타냅니다. s는 마커 면적(pt²), alpha는0~1 투명도입니다. 선으로 연결하면 관측 순서에 의미가 있는 것처럼 보일 수 있습니다.',
        'ax.scatter(x,y,s=sizes,alpha=0.5)',
        's는 반지름이 아닙니다. 점이 겹칠 때 투명도를 조절하되 데이터 자체를 바꾸지 마세요.',[5,21,22],[
        P('x,y 좌표에 면적40인 점3개를 그리세요.',PLT+'x=[1,2,3]\ny=[4,2,5]','fig,ax=plt.subplots()\nax.scatter(x,y,s=40)',(ax([[1,4],[2,2],[3,5]],['collections',0,'offsets','data']),ax([40],['collections',0,'sizes','data']))),
        P('x,y에 sizes의 면적을 적용하고 투명도0.5로 산점도를 그리세요.',PLT+'x=[1,2,3]\ny=[2,4,1]\nsizes=[10,30,60]','fig,ax=plt.subplots()\nax.scatter(x,y,s=sizes,alpha=0.5)',(ax([[1,2],[2,4],[3,1]],['collections',0,'offsets','data']),ax([10,30,60],['collections',0,'sizes','data']),ax(.5,['collections',0,'alpha']))),
        P('a의 첫 열을x, 두 번째 열을y로 산점도를 그리세요. x축 Width, y축 Height, 점 면적25입니다.',PLT+'a=np.array([[2,5],[3,7],[4,6]])',"fig,ax=plt.subplots()\nax.scatter(a[:,0],a[:,1],s=25)\nax.set_xlabel('Width')\nax.set_ylabel('Height')",(ax([[2,5],[3,7],[4,6]],['collections',0,'offsets','data']),ax([25],['collections',0,'sizes','data']),ax('Width',['xlabel']),ax('Height',['ylabel']))),
    ])
    add('bar','범주별 값과 그룹 막대',
        '막대 높이로 범주별 크기를 비교합니다. width는 막대 폭입니다. 두 집단을 나란히 놓으려면 중심을 폭의 절반만큼 좌우로 이동합니다. 같은x에 덮어 그리는 것은 그룹 막대가 아닙니다.',
        'ax.bar(x,y,width=0.8)\nax.bar(x-w/2,a,width=w)\nax.bar(x+w/2,b,width=w)',
        '빈도 분포를 구간별로 세는 hist와 이미 집계된 범주의 값 bar는 다릅니다.',[6,23,24],[
        P('x위치0,1,2에 높이3,5,2인 폭0.8 막대 fig를 만드세요.',PLT,'fig,ax=plt.subplots()\nax.bar([0,1,2],[3,5,2],width=.8)',bars([3,5,2])),
        P('x의 두 범주에서 a,b를 폭0.4로 나란히 그리세요. a는 중심에서0.2 왼쪽, b는0.2 오른쪽입니다. a를 먼저 그리세요.',PLT+'x=np.array([0,1])\na=[2,4]\nb=[3,5]','fig,ax=plt.subplots()\nax.bar(x-.2,a,width=.4)\nax.bar(x+.2,b,width=.4)',bars([2,4,3,5],[-.2,.8,.2,1.2],.4)),
        P('a의 열별 합계를 x위치0,1,2에 폭0.8 막대로 그리세요. 제목은 Totals입니다.',PLT+'a=np.array([[1,3,2],[4,2,6]])',"fig,ax=plt.subplots()\nax.bar(np.arange(3),a.sum(axis=0),width=.8)\nax.set_title('Totals')",bars([5,5,8])+(ax('Totals',['title']),)),
    ])
    add('pie','전체 중 비율을 보여주는 원그래프',
        'pie는 전체를 이루는 비음수 비율에 적합합니다. autopct는 조각의 백분율 표기이고 explode는 조각을 중심에서 띄우는 비율입니다. startangle은 시작 방향을 회전시키며 조각의 비율은 바꾸지 않습니다.',
        "ax.pie(values,labels=labels,autopct='%1.1f%%',explode=[0,0.1])",
        '조각 넓이는 입력 합으로 정규화됩니다. 음수를 넣지 마세요. 단순한 크기 비교가 목적이면 막대그래프가 더 읽기 쉬울 수 있습니다.',[25,26],[
        P('values의 비율을 원그래프로 그리세요. 첫 조각은 A, 둘째는 B이고 백분율을 소수1자리로 표시하세요.',PLT+'values=[1,3]',"fig,ax=plt.subplots()\nax.pie(values,labels=['A','B'],autopct='%1.1f%%')",(ax(2,['patch_count']),ax(90.,['patches',0,'angle']),ax(270.,['patches',1,'angle']),ax(['A','25.0%','B','75.0%'],['texts']))),
        P('같은 비중의 A,B 원그래프를 그리되 B만 중심에서 반지름의0.1만큼 띄우세요. 시작 각도0도, 반시계 방향입니다.',PLT,"fig,ax=plt.subplots()\nax.pie([1,1],labels=['A','B'],explode=[0,.1])",(ax(180.,['patches',0,'angle']),ax(180.,['patches',1,'angle']),ax([0,0],['patches',0,'center']),ax([0,-.1],['patches',1,'center']))),
        P('counts의 두 열별 합을 A,B 비중으로 원그래프로 표현하세요. 백분율은 소수1자리로 표시하세요.',PLT+'counts=np.array([[1,3],[2,6]])',"fig,ax=plt.subplots()\nax.pie(counts.sum(axis=0),labels=['A','B'],autopct='%1.1f%%')",(ax(90.,['patches',0,'angle']),ax(270.,['patches',1,'angle']),ax(['A','25.0%','B','75.0%'],['texts']))),
    ])
    add('heatmap','행렬 값과 색의 대응',
        'imshow는 행렬의 공간적 값 분포를 색으로 표시합니다. colorbar는 표시 색과 값의 대응을 보여줍니다. 이미지 배열의 행은 세로, 열은 가로 위치에 대응합니다.',
        'image=ax.imshow(a)\nfig.colorbar(image,ax=ax)',
        '빈 두 번째 그래프 영역은 colorbar가 아닙니다. 실제 이미지에 연결된 colorbar를 붙이세요.',[27],[
        P('a를 행렬 이미지로 표시한 fig를 만드세요.',PLT+'a=np.array([[1,2],[3,4]])','fig,ax=plt.subplots()\nax.imshow(a)',(ax([[1,2],[3,4]],['images',0,'data']),)),
        P('a를 행렬 이미지로 표시한 fig를 만들고 colorbar도 붙이세요.',PLT+'a=np.array([[0,1],[2,3]])','fig,ax=plt.subplots()\nimage=ax.imshow(a)\nfig.colorbar(image,ax=ax)',(ax([[0,1],[2,3]],['images',0,'data']),ax(True,['image_colorbars',0],'이미지에 연결된 colorbar'))),
        P('a의 열별 평균을 뺀 행렬을 이미지로 표시하고 colorbar와 제목 Centered를 붙이세요.',PLT+'a=np.array([[1.,3.],[5.,7.]])',"fig,ax=plt.subplots()\nimage=ax.imshow(a-a.mean(axis=0))\nfig.colorbar(image,ax=ax)\nax.set_title('Centered')",(ax([[-2,-2],[2,2]],['images',0,'data']),ax(True,['image_colorbars',0],'이미지에 연결된 colorbar'),ax('Centered',['title']))),
    ])
    add('hist','히스토그램의 구간과 빈도',
        'hist는 원자료를 구간(bin)에 나누어 개수를 셉니다. bins에 경계 배열을 주면 해석이 명확합니다. 마지막 구간을 제외하면 오른쪽 경계는 포함하지 않습니다. 반환값 n,edges는 계산된 높이와 경계입니다.',
        'n,edges,patches=ax.hist(data,bins=[0,2,4,6])',
        'bar에 원자료를 바로 넣는 것은 분포를 세는 히스토그램과 다릅니다.',[28,29],[
        P('data를 경계[0,2,4,6]인 히스토그램 fig로 그리고 구간별 개수를 counts에 담으세요.',PLT+'data=[0,1,2,3,4,5,6]','fig,ax=plt.subplots()\ncounts,edges,patches=ax.hist(data,bins=[0,2,4,6])',(C('counts',[2,2,3],['data']),)+bars([2,2,3],[1,3,5],2)),
        P('data를 경계[0,5,10]으로 나누어 그리세요. 개수 counts와 경계 edges도 기록하세요.',PLT+'data=[1,2,5,6,9,10]','fig,ax=plt.subplots()\ncounts,edges,patches=ax.hist(data,bins=[0,5,10])',(C('counts',[2,4],['data']),C('edges',[0,5,10],['data']))+bars([2,4],[2.5,7.5],5)),
        P('data에서 음수를 제외하고 경계[0,2,4]로 히스토그램을 그려 counts에 개수를 기록하세요.',PLT+'data=np.array([-9,0,1,2,3,4])','fig,ax=plt.subplots()\ncounts,edges,patches=ax.hist(data[data>=0],bins=[0,2,4])',(C('counts',[2,3],['data']),)+bars([2,3],[1,3],2)),
    ])
    add('density','밀도와 누적 비율',
        'density=True는 막대의 면적 합이1이 되게 합니다. 높이 합이 항상1인 것은 아닙니다. cumulative=True만 쓰면 누적 개수, density도 함께 쓰면 마지막 값1인 누적 비율이 됩니다.',
        'ax.hist(data,bins=edges,density=True)\nax.hist(data,bins=edges,cumulative=True,density=True)',
        '밀도 높이는 확률 그 자체가 아닙니다. 구간 폭을 곱해야 그 구간의 비율입니다.',[29,30],[
        P('data를 경계[0,2,4]로 나누어 밀도 히스토그램을 그리세요. 높이는 heights에 담으세요.',PLT+'data=[0,1,2,3]','fig,ax=plt.subplots()\nheights,edges,patches=ax.hist(data,bins=[0,2,4],density=True)',(C('heights',[.25,.25],['data']),)+bars([.25,.25],[1,3],2)),
        P('data의 누적 개수를 경계[0,2,4]로 그리세요. 높이는 heights입니다.',PLT+'data=[0,1,2,3]','fig,ax=plt.subplots()\nheights,edges,patches=ax.hist(data,bins=[0,2,4],cumulative=True)',(C('heights',[2,4],['data']),)+bars([2,4],[1,3],2)),
        P('data의 누적 비율을 경계[0,2,4]로 그리세요. 마지막 높이는1이어야 합니다. 높이를 heights에 담으세요.',PLT+'data=[0,1,2,3]','fig,ax=plt.subplots()\nheights,edges,patches=ax.hist(data,bins=[0,2,4],cumulative=True,density=True)',(C('heights',[.5,1],['data']),)+bars([.5,1],[1,3],2)),
    ])
    add('normal','SciPy 정규분포와 적합',
        'scipy.stats.norm의 loc는 평균, scale은 표준편차입니다. pdf는 x위치의 확률밀도이며 특정 한 점의 확률이 아닙니다. fit(data)는 평균과 모집단 표준편차를 추정합니다. rvs는 표본을 만듭니다. 난수 표본은 이론 분포와 정확히 일치하지 않습니다.',
        'from scipy.stats import norm\nmu,sigma=norm.fit(data)\ny=norm.pdf(x,loc=mu,scale=sigma)\nsample=norm.rvs(loc=0,scale=1,size=10,random_state=42)',
        '적합 곡선을 그리기 전에 x구간을 직접 정의해야 합니다. sigma=0인 데이터로 일반 정규밀도를 계산할 수 없습니다.',[31,32,33],[
        P('data를 정규분포로 적합해 평균 mu, 표준편차 sigma를 구하세요.',PLT+'from scipy.stats import norm\ndata=np.array([1,3,5])','mu,sigma=norm.fit(data)',[C('mu',3),C('sigma',(8/3)**.5)]),
        P('x에서 표준정규분포 밀도를 구해 선으로 그린 fig를 만드세요.',PLT+'from scipy.stats import norm\nx=np.array([-1.,0.,1.])','fig,ax=plt.subplots()\nax.plot(x,norm.pdf(x,loc=0,scale=1))',line([-1,0,1],[.24197072451914337,.3989422804014327,.24197072451914337])),
        P('data로부터 mu,sigma를 추정하고 주어진 x에서 그 분포의 밀도를 그리세요. 제목은 Fitted normal입니다.',PLT+'from scipy.stats import norm\ndata=np.array([-1.,1.])\nx=np.array([-1.,0.,1.])',"mu,sigma=norm.fit(data)\nfig,ax=plt.subplots()\nax.plot(x,norm.pdf(x,loc=mu,scale=sigma))\nax.set_title('Fitted normal')",[C('mu',0),C('sigma',1),*line([-1,0,1],[.24197072451914337,.3989422804014327,.24197072451914337]),ax('Fitted normal',['title'])]),
    ])
    add('box','상자그림: 중앙값·IQR·이상치',
        '상자는 Q1~Q3, 내부 선은 중앙값입니다. IQR=Q3-Q1이고 기본 수염은1.5IQR 경계 안에 있는 실제 관측값까지 뻗습니다. 수염 끝이 무조건 Q1-1.5IQR이나 Q3+1.5IQR인 것은 아닙니다. 경계 밖 점은 이상치 후보이지 자동 삭제 대상이 아닙니다.',
        'artists=ax.boxplot(data)\nq1,median,q3=np.percentile(data,[25,50,75])',
        '표본이 작거나 같은 값이 많을 때 사분위수와 수염의 의미를 함께 확인하세요.',[34,35,36,37,38,39,40,41,42],[
        P('data를 세로 상자그림 fig로 그리고 중앙값 median과 IQR iqr을 기록하세요.',PLT+'data=np.array([1,2,3,4,5])','fig,ax=plt.subplots()\nax.boxplot(data)\nq1,median,q3=np.percentile(data,[25,50,75])\niqr=q3-q1',[C('median',3),C('iqr',2),ax(3,['boxes',0,'median']),ax(2,['boxes',0,'q1']),ax(4,['boxes',0,'q3'])]),
        P('data의 세로 상자그림을 그려 중앙값 median과 IQR iqr을 구하세요. 먼 값20도 제거하지 마세요.',PLT+'data=np.array([1,2,3,4,20])','fig,ax=plt.subplots()\nax.boxplot(data)\nq1,median,q3=np.percentile(data,[25,50,75])\niqr=q3-q1',[C('median',3),C('iqr',2),ax([20],['boxes',0,'fliers']),ax(3,['boxes',0,'median']),ax(2,['boxes',0,'q1']),ax(4,['boxes',0,'q3'])]),
        P('a,b를 왼쪽부터 나란히 세로 상자그림으로 그리세요. 두 집단의 중앙값을 medians 배열에 담고 제목은 Groups입니다.',PLT+'a=np.array([1,2,3,4,5])\nb=np.array([3,4,5,6,7])',"fig,ax=plt.subplots()\nax.boxplot([a,b])\nmedians=np.array([np.median(a),np.median(b)])\nax.set_title('Groups')",[C('medians',[3,5],['data']),ax(3,['boxes',0,'median']),ax(5,['boxes',1,'median']),ax('Groups',['title'])]),
    ])
    return tuple(result)
