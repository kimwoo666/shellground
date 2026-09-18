"""Small lecture API/decision gaps, without renumbering or deleting old units."""
from .model import Lesson, problem as P, check as C, frame as F, series as S

PD='import pandas as pd\nimport numpy as np\n'
N={'special':'nan'}

CHART_OBSERVER='''
def chart_state():
    from matplotlib.patches import Rectangle, Wedge
    result=[]
    if not fig.get_visible(): return []
    axes=sorted(fig.axes,key=lambda a:(-a.get_position().y1,a.get_position().x0))
    if len(axes)==2:
        left,right=[a.get_position() for a in axes]
        if left.x1>=right.x0 or abs((left.y0+left.y1)-(right.y0+right.y1))>.05: return []
    for ax in axes:
        if not ax.get_visible(): return []
        ticks=list(zip(ax.get_xticks(),[t.get_text() for t in ax.get_xticklabels()]))
        bars=[];pies=[]
        for p in ax.patches:
            visible=p.get_visible() and p.get_alpha()!=0
            visible=visible and (p.get_facecolor()[3]>0 or (p.get_linewidth()>0 and p.get_edgecolor()[3]>0))
            if not visible: continue
            if isinstance(p,Rectangle):
                if p.get_width()<=0 or p.get_height()<=0: return []
                center=p.get_x()+p.get_width()/2
                labels=[label for tick,label in ticks if abs(tick-center)<1e-6]
                if len(labels)!=1 or abs(p.get_y())>1e-6: return []
                bars.append([labels[0],float(p.get_height())])
            elif isinstance(p,Wedge):
                if p.r<=0: return []
                from matplotlib.colors import to_rgba
                labels={t.get_text() for t in ax.texts if t.get_visible() and t.get_alpha()!=0 and to_rgba(t.get_color())[3]>0}
                if p.get_label() not in labels: return []
                pies.append([p.get_label(),round(float(p.theta2-p.theta1),4)])
            else: return []
        if ax.lines or ax.collections or ax.images: return []
        result.append([sorted(bars),sorted(pies)])
    return result
'''


def chart_problem(goal,initial,solution,expected):
    return P(goal,initial+'\n'+CHART_OBSERVER,solution,
             [C('__probes__',expected,['chart_state',0],'보이는 차트의 범주·값·배치')],
             probes={'chart_state':[[]]},display_initial=initial)


def weather_problem(goal, dates, winds, solution, checks):
    public=PD+f"weather=pd.DataFrame({{'wind':{winds}}},index=pd.to_datetime({dates!r}))"
    initial=public+'\n_original=weather.copy(deep=True)\ndef source_ok():\n    return weather.equals(_original)'
    return P(goal+' 원본 weather의 값·날짜·결측은 유지하세요.',initial,solution,
             tuple(checks)+(C('__probes__',True,['source_ok',0],'원본·결측 보존'),),
             probes={'source_ok':[[]]},display_initial=public)


def lessons():
    topic='강의 범위 보완'
    result=[]
    def add(key,title,explanation,syntax,pitfall,pages,problems,prerequisites):
        result.append(Lesson(key,topic,title,explanation,syntax,pitfall,'week_3_1_handout.pdf',tuple(pages),
                             tuple(problems),tuple(prerequisites),'강의 API와 판단을 작은 새 데이터로 연습합니다. 기존 단원·완료 기록은 유지합니다.'))
    add('pd_datetime_index','날짜 열과 날짜 인덱스 구분',
        '날짜가 열이면 Series.dt.year처럼 접근하지만, 행 인덱스가 DatetimeIndex이면 df.index.year와 df.index.month입니다. '
        '인덱스가 문자열이면 먼저 pd.to_datetime으로 바꿉니다. month는 1~12이므로 여러 해의 같은 달을 구분하려면 year도 함께 사용합니다.',
        "df.index=pd.to_datetime(df.index)\nyears=df.index.year.tolist()\nmonths=df.index.month.tolist()\ncurrent=df.loc[df.index.year==2026]",
        '날짜 인덱스에는 .dt를 붙이지 않습니다. 연도 구분 없는 month 집계는 다른 해의 같은 달을 합칩니다.',[45,46],[
            P('df의 문자열 인덱스를 DatetimeIndex로 바꾸세요. 연도 목록 years와 월 목록 months를 원래 순서대로 만드세요.',
              PD+"df=pd.DataFrame({'wind':[2,5]},index=['2025-12-31','2026-01-02'])",
              'df.index=pd.to_datetime(df.index)\nyears=df.index.year.tolist()\nmonths=df.index.month.tolist()',
              [C('years',[2025,2026]),C('months',[12,1]),C('__probes__',True,['is_date_index',0],'날짜 인덱스')],
              probes={'is_date_index':[[]]},
              display_initial=PD+"df=pd.DataFrame({'wind':[2,5]},index=['2025-12-31','2026-01-02'])"),
            P('이미 날짜 인덱스인 df에서 2026년 1월 행만 선택하여 result로 만드세요. 다른 해의 1월과 다른 달은 제외하세요.',
              PD+"df=pd.DataFrame({'wind':[99,2,7]},index=pd.to_datetime(['2025-01-01','2026-01-03','2026-02-01']))",
              'result=df.loc[(df.index.year==2026)&(df.index.month==1)]',
              F('result',[[2]],['2026-01-03 00:00:00'],['wind'])),
            P('2026년 날짜 인덱스인 df를 월 번호로 묶어 wind 평균 Series result를 만드세요. 관측 수가 다른 달을 구분하세요.',
              PD+"df=pd.DataFrame({'wind':[2,6,9]},index=pd.to_datetime(['2026-01-01','2026-01-02','2026-02-01']))",
              "result=df.groupby(df.index.month)['wind'].mean()",S('result',[4,9],[1,2])),
        ],['pd_datetime','pd_groupby'])
    # The prepared observer evaluates the real index object; a returned list
    # alone must not satisfy the explicit conversion goal.
    from dataclasses import replace
    first=result[-1].problems[0]
    fixed=replace(first,initial=first.initial+'\ndef is_date_index():\n    return isinstance(df.index,pd.DatetimeIndex)')
    result[-1]=replace(result[-1],problems=(fixed,*result[-1].problems[1:]))
    add('pd_weather_audit','월별 평균·유효 개수·결측 정책',
        'mean은 결측을 제외한 값의 평균이고 count는 유효 값의 개수입니다. size는 결측행까지 센다는 점이 다릅니다. '
        "groupby(...).agg(['mean','count'])로 두 값을 나란히 확인하세요. 측정되지 않은 풍속은 0m/s라고 단정할 수 없습니다. "
        '월 평균의 기준을 적용할 때는 관측행을 먼저 거르는 것과 월별 평균을 낸 뒤 월을 고르는 것을 구분합니다.',
        "monthly=weather.groupby(weather.index.month)['wind'].agg(['mean','count'])\n"
        "both=weather.groupby([weather.index.year,weather.index.month])['wind'].agg(['mean','count'])\n"
        "selected=monthly.loc[monthly['mean']>15]",
        '결측을 임의로 0으로 채우거나 count 대신 전체 행 수를 쓰면 평균과 유효 관측 수의 의미가 달라집니다. 여러 해는 연도·월을 함께 묶으세요.',[45,46],[
            weather_problem('2026년의 월별 wind 평균과 유효 관측 수를 result에 담으세요. 행 인덱스는 월 번호, 열 순서는 mean,count입니다. 결측을 0으로 대체하지 마세요.',
                ['2026-01-01','2026-01-02','2026-01-03','2026-02-01'],'[2,np.nan,6,10]',
                "result=weather.groupby(weather.index.month)['wind'].agg(['mean','count'])",
                F('result',[[4,2],[10,1]],[1,2],['mean','count'])),
            weather_problem('서로 다른 해의 같은 달을 합치지 말고 연도·월별 wind 평균과 유효 관측 수를 result로 만드세요. 행 인덱스는 (연도,월), 열은 mean,count 순서이며 날짜순으로 정렬하세요.',
                ['2025-01-01','2025-01-03','2026-01-01','2026-01-03','2026-02-01'],'[20,40,2,np.nan,8]',
                "result=weather.groupby([weather.index.year,weather.index.month])['wind'].agg(['mean','count'])",
                F('result',[[30,2],[2,1],[8,1]],[[2025,1],[2026,1],[2026,2]],['mean','count'])),
            weather_problem('2026년 자료에서 월별 wind 평균과 유효 개수를 먼저 구하고, 월 평균이 15보다 큰 달만 result로 남기세요. 개별 관측값이 15보다 큰 행을 먼저 고르는 것이 아닙니다. 인덱스는 월, 열은 mean,count입니다.',
                ['2026-01-01','2026-01-02','2026-02-01','2026-02-02','2026-02-03'],'[0,20,16,np.nan,20]',
                "monthly=weather.groupby(weather.index.month)['wind'].agg(['mean','count'])\nresult=monthly.loc[monthly['mean']>15]",
                F('result',[[18,2]],[2],['mean','count'])),
        ],['pd_datetime_index','pd_missing','pd_group_filter'])
    add('pd_series_charts','Series에서 막대·원그래프 그리기',
        'Series.plot(kind=...)는 pandas의 데이터 라벨을 이용해 Matplotlib 그림을 만듭니다. 반환값은 Axes이므로 ax.figure로 Figure를 얻습니다. '
        'bar는 범주별 크기 비교, pie는 음수가 없는 전체에서의 구성비를 보여줍니다. 원그래프는 관측값의 절대 차이를 정밀하게 비교하는 데에는 적합하지 않습니다.',
        "ax=counts.plot(kind='bar')\nfig=ax.figure\n# 원그래프는 별도 Figure에서\nax=counts.plot(kind='pie')\nfig=ax.figure",
        '한 Figure에 이전 그림이 남으면 여러 차트가 겹칠 수 있습니다. 비교용 두 그림은 plt.subplots로 각각의 축에 그리세요.',[22,23,24],[
            chart_problem('counts를 막대그래프로 그리고 Figure를 fig에 담으세요. A,B,C의 크기 2,5,3을 비교하세요.',
              PD+"counts=pd.Series([2,5,3],index=['A','B','C'])",
              "ax=counts.plot(kind='bar')\nfig=ax.figure",
              [[[['A',2],['B',5],['C',3]],[]]]),
            chart_problem('counts의 A:B 구성비 1:3을 원그래프로 그리고 fig에 담으세요. A,B 이름을 표시하세요.',
              PD+"counts=pd.Series([1,3],index=['A','B'])",
              "ax=counts.plot(kind='pie')\nfig=ax.figure",
              [[[],[['A',90],['B',270]]]]),
            chart_problem('counts를 왼쪽에는 막대, 오른쪽에는 원그래프로 그린 1행 2열 Figure fig를 만드세요. 두 그림 모두 north,south의 같은 자료 [3,1]을 쓰세요.',
              PD+"import matplotlib.pyplot as plt\ncounts=pd.Series([3,1],index=['north','south'])",
              "fig,axes=plt.subplots(1,2)\ncounts.plot(kind='bar',ax=axes[0])\ncounts.plot(kind='pie',ax=axes[1])",
              [[[['north',3],['south',1]],[]],[[],[['north',270],['south',90]]]]),
        ],['pd_plot','plot_bar','plot_pie'])
    add('pd_concat_labels','연결할 때 원래 라벨을 유지할지 결정',
        'pd.concat은 기본적으로 입력 행 라벨을 그대로 유지합니다. 같은 라벨이 여러 번 나와도 오류가 아닙니다. '
        'ignore_index=True는 연결된 행에 0부터 새 번호를 붙입니다. 행을 연결할 때 열은 기본 outer(합집합), join="inner"는 공통 열입니다. 행 라벨 정책과 열 정책은 별개입니다.',
        "kept=pd.concat([first,second])\nnumbered=pd.concat([first,second],ignore_index=True)\ncommon=pd.concat([first,second],join='inner')",
        '중복 라벨을 유지하라는 목표에서 reset_index나 ignore_index를 쓰면 정보가 달라집니다. 중복 행 제거와 라벨 재설정은 다른 작업입니다.',[36,37,38],[
            P('first 뒤에 second를 붙인 result를 만드세요. 두 행의 원래 r 라벨을 모두 유지하세요.',
              PD+"first=pd.DataFrame({'score':[3]},index=['r'])\nsecond=pd.DataFrame({'score':[8]},index=['r'])",
              'result=pd.concat([first,second])',F('result',[[3],[8]],['r','r'],['score'])),
            P('first,second 순서로 붙인 kept는 원래 라벨을 보존하고 numbered는 0부터 새 번호를 붙이세요. 같은 값이어도 두 결과의 인덱스 정책은 달라야 합니다.',
              PD+"first=pd.DataFrame({'score':[4,6]},index=['r','s'])\nsecond=pd.DataFrame({'score':[9]},index=['r'])",
              'kept=pd.concat([first,second])\nnumbered=pd.concat([first,second],ignore_index=True)',
              F('kept',[[4],[6],[9]],['r','s','r'],['score'])+F('numbered',[[4],[6],[9]],[0,1,2],['score'])),
            P('first,second의 공통 열만 연결한 result를 만드세요. 원래 행 라벨 r,r을 모두 유지하고 각 표에만 있는 열은 제외하세요.',
              PD+"first=pd.DataFrame({'score':[3],'memo':['old']},index=['r'])\nsecond=pd.DataFrame({'score':[8],'flag':[True]},index=['r'])",
              "result=pd.concat([first,second],join='inner')",F('result',[[3],[8]],['r','r'],['score'])),
        ],['pd_concat'])
    return tuple(result)


def validation_cases():
    """Wrong and equivalent real-object answers; no source-string checks."""
    course={u.key:u for u in lessons()}
    def case(key,variant,wrong,equivalent=None):
        return dict(lesson=key,problem=variant,wrong=wrong,equivalent=equivalent or course[key].problems[variant].solution)
    charts=course['pd_series_charts'].problems
    weather=course['pd_weather_audit'].problems
    return [
        case('pd_datetime_index',0,'years=[2025,2026]\nmonths=[12,1]',
             'df.index=pd.DatetimeIndex(df.index)\nyears=list(df.index.year)\nmonths=list(df.index.month)'),
        case('pd_datetime_index',1,'result=df.loc[df.index.month==1]'),
        case('pd_weather_audit',0,"result=weather.fillna(0).groupby(weather.index.month)['wind'].agg(['mean','count'])"),
        case('pd_weather_audit',0,"result=weather.groupby(weather.index.month)['wind'].agg(mean='mean',count='size')"),
        case('pd_weather_audit',1,"result=weather.groupby(weather.index.month)['wind'].agg(['mean','count'])"),
        case('pd_weather_audit',2,"filtered=weather.loc[weather['wind']>15]\nresult=filtered.groupby(filtered.index.month)['wind'].agg(['mean','count'])"),
        case('pd_series_charts',0,"ax=counts.plot(kind='bar',alpha=0)\nfig=ax.figure",
             "ax=counts.plot(kind='bar',width=.8,color='orange')\nfig=ax.figure"),
        case('pd_series_charts',0,"ax=counts.plot(kind='bar',width=0)\nfig=ax.figure"),
        case('pd_series_charts',0,charts[0].solution+"\nax.bar([0],[2])"),
        case('pd_series_charts',1,"ax=counts.iloc[::-1].plot(kind='pie',labels=['A','B'])\nfig=ax.figure",
             "ax=counts.iloc[::-1].plot(kind='pie',autopct='%1.0f%%',startangle=90)\nfig=ax.figure"),
        case('pd_series_charts',2,charts[2].solution.replace('plt.subplots(1,2)','plt.subplots(2,1)'),
             charts[2].solution.replace("kind='pie',ax=axes[1]","kind='pie',autopct='%1.0f%%',ax=axes[1]")),
        case('pd_concat_labels',0,'result=pd.concat([first,second],ignore_index=True)'),
        case('pd_concat_labels',2,'result=pd.concat([first,second])'),
    ]
