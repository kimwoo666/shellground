"""Lecture combinations separated from the first encounter with each API."""
from .model import Lesson, problem as P, check as C, frame as F, series as S
from .plot_course import PLT, ax, line, bars
from .pandas_course import PD, NAN


def insertions():
    return {
        'plot_scatter': Lesson('plot_scatter_color','Matplotlib','세 번째 수치를 색으로 표현하기',
            '산점도 위치 x,y에 더해 c에 수치 배열을 주면 각 점의 세 번째 값을 색으로 나타냅니다. cmap은 값→색 규칙, colorbar는 그 대응을 읽는 눈금입니다. 단색 color와 수치 c는 역할이 다릅니다.',
            "points=ax.scatter(x,y,c=temperature,cmap='viridis')\nfig.colorbar(points,ax=ax)",
            'c의 길이를 점 수와 맞추세요. 다른 그림에 colorbar를 붙이거나 색 이름 목록만 주면 수치 척도가 사라집니다.',
            'week_2_2_handout.pdf',(21,22,23),(
                P('x,y 위치의 점을 value의 수치에 따라 색칠한 fig를 만들고 색 눈금을 붙이세요.',PLT+'x=[1,2,3]\ny=[2,5,4]\nvalue=[10,20,30]',
                  'fig,ax=plt.subplots()\npoints=ax.scatter(x,y,c=value)\nfig.colorbar(points,ax=ax)',
                  (ax([[1,2],[2,5],[3,4]],['collections',0,'offsets','data']),ax([10,20,30],['collections',0,'array','data']),ax(True,['collections',0,'colorbar']))),
                P('data의 첫 열을 x, 둘째 열을 y, 셋째 열을 색 수치로 표현하세요. 점 면적은 40, 색 눈금도 필요합니다.',PLT+'data=np.array([[2,3,100],[4,7,200],[6,5,150]])',
                  'fig,ax=plt.subplots()\npoints=ax.scatter(data[:,0],data[:,1],c=data[:,2],s=40)\nfig.colorbar(points,ax=ax)',
                  (ax([[2,3],[4,7],[6,5]],['collections',0,'offsets','data']),ax([100,200,150],['collections',0,'array','data']),ax([40],['collections',0,'sizes','data']),ax(True,['collections',0,'colorbar']))),
                P('data에서 셋째 열이 0 이상인 행만 사용하세요. 첫 두 열을 좌표, 셋째 열을 색 수치로 표현하고 색 눈금과 제목 Valid sensors를 붙이세요.',PLT+'data=np.array([[1,2,5],[3,9,-1],[4,6,8]])',
                  "valid=data[data[:,2]>=0]\nfig,ax=plt.subplots()\npoints=ax.scatter(valid[:,0],valid[:,1],c=valid[:,2])\nfig.colorbar(points,ax=ax)\nax.set_title('Valid sensors')",
                  (ax([[1,2],[4,6]],['collections',0,'offsets','data']),ax([5,8],['collections',0,'array','data']),ax(True,['collections',0,'colorbar']),ax('Valid sensors',['title']))),
            ),('plot_scatter',)),
        'plot_normal': Lesson('plot_fitted_hist','Matplotlib','관측 분포와 적합 곡선을 한 축에서 비교',
            '실제 관측은 밀도 히스토그램, 추정 모형은 확률밀도 곡선으로 같은 Axes에 겹칩니다. 두 표현의 단위를 밀도로 맞춰야 높이를 비교할 수 있습니다. 정규곡선이 그려진다고 자료가 정규분포라는 증거는 아닙니다.',
            'mu,sigma=norm.fit(data)\nfig,ax=plt.subplots()\nax.hist(data,bins=edges,density=True)\nax.plot(x,norm.pdf(x,loc=mu,scale=sigma))',
            '빈도 막대와 밀도 선을 그대로 비교하지 마세요. 곡선은 주어진 x마다 계산하며, 두 개의 별도 Axes로 나누지 않습니다.',
            'week_2_2_handout.pdf',(31,32,33,34,35),tuple(
                P(goal,PLT+'from scipy.stats import norm\ndata=np.array('+repr(data)+')\nx=np.array('+repr(x)+')\nedges='+repr(edges),
                  'mu,sigma=norm.fit(data)\nfig,ax=plt.subplots()\nax.hist(data,bins=edges,density=True)\nax.plot(x,norm.pdf(x,loc=mu,scale=sigma))'+extra,
                  (C('mu',mu),C('sigma',1),C('fig',1,['axis_count']))+bars([.5,.5],centers,1)+line(x,[.24197072451914337,.3989422804014327,.24197072451914337])+checks)
                for goal,data,x,edges,centers,mu,extra,checks in (
                    ('data를 적합한 평균 mu·표준편차 sigma를 구하세요. 경계 edges인 밀도 히스토그램과 주어진 x에서의 적합 밀도 선을 같은 fig의 한 영역에 그리세요.',[-1.,1.],[-1.,0.,1.],[-1.,0.,1.],[-.5,.5],0,'',()),
                    ('data의 정규 적합 mu,sigma를 구하고 edges 기준 밀도 막대와 x에서의 적합 밀도 선을 한 영역에 그리세요. 제목은 Observed and fitted입니다.',[0.,2.],[0.,1.,2.],[0.,1.,2.],[.5,1.5],1,"\nax.set_title('Observed and fitted')",(ax('Observed and fitted',['title']),)),
                    ('data를 적합한 mu,sigma와 한 영역의 밀도 막대·적합 밀도 선을 만드세요. 막대 경계는 edges, 선 좌표는 x이며 y축 이름은 Density입니다.',[1.,3.],[1.,2.,3.],[1.,2.,3.],[1.5,2.5],2,"\nax.set_ylabel('Density')",(ax('Density',['ylabel']),)),
                )),('plot_normal','plot_density')),
        'pd_merge_detail': Lesson('pd_merge_coverage','pandas','오른쪽 기준·전체 키를 보존하는 병합',
            'how="right"는 오른쪽 표의 키를 모두 보존합니다. how="outer"는 양쪽 키의 합집합을 보존합니다. 대응이 없는 셀은 NaN입니다. 결측을 0으로 채우기 전에 정말 0이라는 뜻인지 판단하세요.',
            "left.merge(right,on='id',how='right')\nleft.merge(right,on='id',how='outer',sort=True)",
            '행이 사라진 이유와 셀이 결측인 이유를 구분하세요. 양쪽 중복 키는 행 수를 늘릴 수 있습니다.',
            'week_3_1_handout.pdf',(39,40,41,42,44),(
                P('right의 모든 id를 보존해 left의 score를 연결한 result를 만드세요. 열 순서는 id,score,name입니다.',PD+"left=pd.DataFrame({'id':[1,2],'score':[80,90]})\nright=pd.DataFrame({'id':[2,3],'name':['Bo','Cy']})",
                  "result=left.merge(right,on='id',how='right')",F('result',[[2,90,'Bo'],[3,NAN,'Cy']],[0,1],['id','score','name'])),
                P('양쪽의 모든 id를 보존하는 result를 만들고 id 오름차순으로 정리하세요. 없는 값은 결측으로 유지합니다. 열은 id,score,name 순서입니다.',PD+"left=pd.DataFrame({'id':[1,2],'score':[80,90]})\nright=pd.DataFrame({'id':[2,3],'name':['Bo','Cy']})",
                  "result=left.merge(right,on='id',how='outer',sort=True)",F('result',[[1,80,NAN],[2,90,'Bo'],[3,NAN,'Cy']],[0,1,2],['id','score','name'])),
                P('양쪽 id를 모두 보존해 합친 뒤 실제 score가 없는 행만 result에 남기세요. 열은 id,score,name 순서이고 원래 병합 인덱스를 유지합니다.',PD+"left=pd.DataFrame({'id':[1,2],'score':[80,90]})\nright=pd.DataFrame({'id':[2,3],'name':['Bo','Cy']})",
                  "merged=left.merge(right,on='id',how='outer',sort=True)\nresult=merged.loc[merged['score'].isna()]",F('result',[[3,NAN,'Cy']],[2],['id','score','name'])),
            ),('pd_merge_detail','pd_missing')),
        'pd_pivot_table': Lesson('pd_pivot_multi','pandas','두 범주로 행을 구분하는 복합 피벗',
            'index에 두 열 이름을 주면 두 범주의 조합을 행 라벨로 삼는 MultiIndex가 생깁니다. 같은 team이라도 year가 다르면 다른 집단입니다. 여러 범주를 하나의 문자열로 붙이지 않고 구조를 유지합니다.',
            "df.pivot_table(index=['team','year'],columns='kind',values='count',aggfunc='sum',fill_value=0)",
            '행 라벨의 순서와 이름까지 결과의 의미입니다. year를 빼면 다른 연도의 값이 합쳐집니다.',
            'week_3_1_handout.pdf',(35,),(
                P('team,year 조합을 행, kind를 열로 삼아 count 합계 result를 만드세요. 없는 조합은 0입니다.',PD+"df=pd.DataFrame({'team':['A','A','B'],'year':[2025,2026,2026],'kind':['x','y','x'],'count':[2,3,4]})",
                  "result=df.pivot_table(index=['team','year'],columns='kind',values='count',aggfunc='sum',fill_value=0)",F('result',[[2,0],[0,3],[4,0]],[['A',2025],['A',2026],['B',2026]],['x','y'])+(C('result',['team','year'],['index_names']),)),
                P('year,team 조합을 행으로 만들고 kind별 count 평균을 result에 담으세요. 없는 조합은 NaN이며 행 라벨은 year가 먼저입니다.',PD+"df=pd.DataFrame({'team':['A','A','B'],'year':[2026,2026,2026],'kind':['x','x','y'],'count':[2,6,4]})",
                  "result=df.pivot_table(index=['year','team'],columns='kind',values='count',aggfunc='mean')",F('result',[[4,NAN],[NAN,4]],[[2026,'A'],[2026,'B']],['x','y'])+(C('result',['year','team'],['index_names']),)),
                P('count가 양수인 관측만 이용해 team,year별 kind 합계 result를 구하세요. 없는 조합은 0입니다.',PD+"df=pd.DataFrame({'team':['A','A','A','B'],'year':[2025,2025,2026,2026],'kind':['x','y','x','y'],'count':[2,-9,3,4]})",
                  "valid=df.loc[df['count']>0]\nresult=valid.pivot_table(index=['team','year'],columns='kind',values='count',aggfunc='sum',fill_value=0)",F('result',[[2,0],[3,0],[0,4]],[['A',2025],['A',2026],['B',2026]],['x','y'])+(C('result',['team','year'],['index_names']),)),
            ),('pd_pivot_table',)),
        'pd_groupby': Lesson('pd_group_filter','pandas','집계 후 조건과 집계 전 조건',
            '개별 방문 기록이 아니라 팀의 총 방문 횟수를 판단하려면 먼저 합계를 낸 뒤 그 Series를 조건으로 고릅니다. 원래 행을 먼저 거르면 다른 질문의 답이 됩니다. 작은 방문 기록 여러 개가 모여 기준을 넘을 수 있습니다.',
            "totals=df.groupby('team')['visits'].sum()\nresult=totals.loc[totals>=10]",
            'df의 한 행 조건인지 집단의 합계 조건인지 문제의 판단 대상을 확인하세요.',
            'week_3_1_handout.pdf',(46,),(
                P('팀별 visits 합계가 10 이상인 팀만 남긴 Series result를 만드세요. 값은 팀별 합계입니다.',PD+"df=pd.DataFrame({'team':['A','A','B'],'visits':[6,6,9]})",
                  "totals=df.groupby('team')['visits'].sum()\nresult=totals.loc[totals>=10]",S('result',[12],['A'])),
                P('team별 score 평균이 80 이상인 팀의 평균 Series result를 만드세요. 낮은 개별 점수도 평균 계산에 포함합니다.',PD+"df=pd.DataFrame({'team':['A','A','B','B'],'score':[60,100,70,80]})",
                  "means=df.groupby('team')['score'].mean()\nresult=means.loc[means>=80]",S('result',[80],['A'])),
                P('유효한 행(valid=True)만 사용한 팀별 visits 합계 중 10 이상인 팀만 Series result에 남기세요.',PD+"df=pd.DataFrame({'team':['A','A','B','B'],'visits':[6,7,100,3],'valid':[True,True,False,True]})",
                  "totals=df.loc[df['valid']].groupby('team')['visits'].sum()\nresult=totals.loc[totals>=10]",S('result',[13],['A'])),
            ),('pd_groupby','pd_filter')),
    }
