"""Six optional, real-library lessons after the foundational Python course.

The five supplied PDFs introduce these libraries' roles, not these APIs. All
lessons are supplements. Small fixture functions use the existing callable
probe mechanism to inspect real artists / real fitted estimators; they neither
simulate a library nor add an execution engine. Do not grade estimator reprs,
palette choices, harmless artist ordering, or a particular source-code string.
"""
from dataclasses import replace
from .model import Lesson, problem as P, check as C, array as A, frame as F


SNS = 'import numpy as np\nimport pandas as pd\nimport matplotlib.pyplot as plt\nimport seaborn as sns\n'
SPLIT = 'import numpy as np\nfrom sklearn.model_selection import train_test_split\n'
REGRESSION = 'import numpy as np\nfrom sklearn.linear_model import LinearRegression\n'
METRICS = REGRESSION + 'from sklearn.metrics import mean_absolute_error\n'
CLASSIFICATION = ('import numpy as np\nfrom sklearn.linear_model import LogisticRegression\n'
                  'from sklearn.metrics import accuracy_score, confusion_matrix, recall_score\n')
PIPELINE = ('import numpy as np\nfrom sklearn.pipeline import make_pipeline, Pipeline\n'
            'from sklearn.preprocessing import StandardScaler\n'
            'from sklearn.linear_model import LinearRegression\n')
VALIDATION = ('import numpy as np\nfrom sklearn.model_selection import KFold, TimeSeriesSplit, cross_val_score\n'
              'from sklearn.linear_model import LinearRegression\n')

# These supplied observation helpers are not code the learner must recreate.
# Sorting removes irrelevant artist/row order while retaining duplicate points.
BAR_PROBE = '''
def _bar_values(axis_number):
    return sorted([[p.get_x()+p.get_width()/2, p.get_height()]
                   for p in fig.axes[axis_number].patches])
'''
HIST_PROBE = '''
def _histogram_values(axis_number):
    return sorted([[p.get_x(), p.get_x()+p.get_width(), p.get_height()]
                   for p in fig.axes[axis_number].patches])
'''
SCATTER_PROBE = '''
def _scatter_axis(axis_number):
    # Inspect visual order, not the order in which Axes happened to be created.
    return sorted(fig.axes, key=lambda a: (-a.get_position().y1, a.get_position().x0))[axis_number]

def _marker_rgb(line):
    from matplotlib.colors import to_rgba
    candidates=[line.get_markerfacecolor()]
    if line.get_markeredgewidth()>0: candidates.append(line.get_markeredgecolor())
    for color in candidates:
        if str(color).lower()=='auto': color=line.get_color()
        rgba=to_rgba(color,alpha=line.get_alpha())
        if rgba[3]>0: return tuple(round(c,6) for c in rgba[:3])
    return None

def _scatter_marks(axis_number):
    from matplotlib.collections import PathCollection
    from matplotlib.colors import to_rgba
    axis = _scatter_axis(axis_number)
    fig.canvas.draw()
    marks=[]
    for collection in axis.collections:
        if not isinstance(collection, PathCollection) or not collection.get_visible() or collection.get_alpha()==0:
            continue
        points=collection.get_offsets().tolist()
        colors=collection.get_facecolors().tolist() or collection.get_edgecolors().tolist()
        for i, point in enumerate(points):
            if colors:
                color=colors[0] if len(colors)==1 else colors[i]
                if len(color)<4 or color[3]>0:
                    marks.append((point, tuple(round(c,6) for c in color[:3])))
    for line in axis.lines:
        if not len(line.get_xdata()) or not line.get_visible() or line.get_alpha()==0:
            continue
        if line.get_linestyle().lower() not in ('none',' ','') and line.get_linewidth()>0:
            raise ValueError('산점도의 관측값을 별도 선으로 연결하지 마세요.')
        if str(line.get_marker()).lower() in ('none',' ','') or line.get_markersize()<=0:
            continue
        rgb=_marker_rgb(line)
        if rgb is not None:
            marks.extend(([float(x),float(y)],rgb) for x,y in zip(line.get_xdata(),line.get_ydata()))
    return marks

def _scatter_points(axis_number):
    return sorted(point for point,color in _scatter_marks(axis_number))

def _scatter_color_groups(axis_number):
    groups={}
    for point,color in _scatter_marks(axis_number):
        groups.setdefault(color,[]).append(point)
    return sorted([sorted(points) for points in groups.values()])

def _scatter_legend_groups(axis_number):
    from matplotlib.colors import to_rgba
    groups={}
    for point,color in _scatter_marks(axis_number): groups.setdefault(color,[]).append(point)
    legend=_scatter_axis(axis_number).get_legend()
    if legend is None: return []
    result=[]
    for text,handle in zip(legend.get_texts(),legend.legend_handles):
        if hasattr(handle,'get_facecolors'):
            colors=handle.get_facecolors()
            if len(colors)==0: colors=handle.get_edgecolors()
            color=colors[0]
        else:
            rgb=_marker_rgb(handle)
            result.append([text.get_text(),sorted(groups.get(rgb,[]))])
            continue
        rgb=tuple(round(c,6) for c in to_rgba(color)[:3])
        result.append([text.get_text(),sorted(groups.get(rgb,[]))])
    return result

def _scatter_layout():
    result=[]
    for number in range(len(fig.axes)):
        axis=_scatter_axis(number)
        spec=axis.get_subplotspec()
        grid=None if spec is None else [*spec.get_gridspec().get_geometry(),spec.rowspan.start,spec.rowspan.stop,spec.colspan.start,spec.colspan.stop]
        result.append([grid,axis.get_title(),list(axis.get_ylim())])
    return result
'''
MODEL_PROBE = '''
# 채점용 관찰 함수입니다. 학습자는 아래 함수를 수정할 필요가 없습니다.
# 모델 이름 문자열이 아니라 실제 LinearRegression의 새 예측을 검사합니다.
def _model_predictions(rows):
    if not isinstance(model, LinearRegression):
        raise TypeError('model은 실제 LinearRegression 객체여야 합니다.')
    return model.predict(np.asarray(rows, dtype=float))
'''
CLASSIFIER_PROBE = '''
def _classifier_predictions(rows):
    if not isinstance(model, LogisticRegression):
        raise TypeError('model은 실제 LogisticRegression 객체여야 합니다.')
    return model.predict(np.asarray(rows, dtype=float))
'''
PIPELINE_PROBE = '''
def _pipeline_predictions(rows):
    if not isinstance(model, Pipeline) or not isinstance(model.steps[0][1], StandardScaler):
        raise TypeError('model은 훈련 데이터에 맞춘 StandardScaler 파이프라인이어야 합니다.')
    return model.predict(np.asarray(rows, dtype=float))
'''

SEABORN_NOTE = (
    '보충 과정: PDF는 Seaborn의 역할 소개 수준이며 여기의 API 실습은 추가 내용입니다. '
    'Python 함수, pandas 표·집계, Matplotlib Axes를 먼저 익힙니다. '
    '공식 근거: https://seaborn.pydata.org/generated/seaborn.barplot.html ; '
    'https://seaborn.pydata.org/generated/seaborn.histplot.html ; '
    'https://seaborn.pydata.org/generated/seaborn.scatterplot.html'
)
SKLEARN_NOTE = (
    '보충 과정: PDF는 scikit-learn의 역할 소개 수준이며 모델 학습·평가는 추가 내용입니다. '
    'Python 함수와 NumPy의 행·열/shape를 익힌 뒤 수행합니다. '
    '공식 근거: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html ; '
    'https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html ; '
    'https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html ; '
    'https://scikit-learn.org/stable/modules/cross_validation.html ; '
    'https://scikit-learn.org/stable/modules/compose.html ; '
    'https://scikit-learn.org/stable/common_pitfalls.html'
)


def _ax(expected, path, label, number=0, feedback=None):
    return C('fig', expected, ['axes', number, *path], label, feedback)


def _figure(axes=1):
    return (C('fig', 'figure', ['kind'], '실제 Figure'),
            C('fig', axes, ['axis_count'], '그림 영역 수'))


def _bars(values, categories):
    return _figure() + (
        C('__probes__', [[i, v] for i, v in enumerate(values)],
          ['_bar_values', 0], '범주별 실제 막대 높이',
          '각 행을 그대로 그리거나 count·합계·평균·중앙값을 혼동하지 않았는지 확인하세요.'),
        _ax(categories, ['named_xticklabels'], '범주 순서'),
        _ax(0, ['line_count'], '오차 막대 없는 요약'),
    )


def _hist(edges, heights, ylabel):
    return _figure() + (
        C('__probes__', [[a, b, h] for a, b, h in zip(edges, edges[1:], heights)],
          ['_histogram_values', 0], '실제 구간 경계와 높이',
          'bins 경계와 count/density 의미를 확인하세요. 밀도에서는 막대 면적의 합이 1입니다.'),
        _ax(ylabel, ['ylabel'], '세로축 통계량'),
        _ax(0, ['line_count'], '추가 곡선 없는 히스토그램'),
    )


def _points(points, number=0, probe_number=0):
    return (
        C('__probes__', sorted(points), ['_scatter_points', probe_number],
          '관측값의 실제 좌표', '평균으로 줄이거나 x와 y를 뒤집지 않고 각 관측값을 보존하세요.'),
        _ax(0, ['patch_count'], '막대 대신 산점도', number),
    )


def _model_checks(expected_predictions, probe='_model_predictions'):
    checks = []
    for i, expected in enumerate(expected_predictions):
        checks.extend((
            C('__probes__', 'array', [probe, i, 'kind'],
              '실제 학습 모델의 예측 배열'),
            C('__probes__', [len(expected)], [probe, i, 'shape'],
              '새 표본별 예측 shape'),
            C('__probes__', expected, [probe, i, 'data'],
              '새 입력에 대한 실제 모델 예측',
              'model을 훈련 자료로 fit했는지 확인하세요. 예측 숫자만 적거나 시험 정답을 학습에 넣지 않습니다.'),
        ))
    return tuple(checks)


def lessons():
    """Return three Seaborn units, then six scikit-learn units (27 problems)."""
    result = []

    result.append(Lesson(
        'sns_summary', 'Seaborn', '긴 표에서 집단을 요약해 그리기',
        'Seaborn은 pandas의 열 이름을 그래프의 의미에 연결하는 도구이며 실제 Matplotlib Axes에 그립니다. '
        'tidy(긴 형식) 표는 한 행이 한 관측값, 한 열이 한 변수입니다. 같은 집단의 여러 행은 중복 오류가 아니라 서로 다른 관측일 수 있습니다. '
        'barplot(data=표, x=범주열, y=수치열)는 기본적으로 집단별 평균을 그립니다. estimator는 mean·median·sum처럼 어떤 요약을 할지 고릅니다. '
        'order는 범주 순서, ax는 그릴 영역입니다. errorbar=None은 이번 요약 연습에서 불확실성 막대만 생략하며 불확실성이 없다는 뜻은 아닙니다.\n'
        '작게 실행: ① 표에서 관측 단위를 읽습니다. ② 질문에 맞는 요약을 고릅니다. ③ 만들어 둔 Axes에 그리고 세로축의 의미를 붙입니다.',
        "fig, ax = plt.subplots()\nsns.barplot(data=readings, x='region', y='reading', estimator='mean',\n"
        "            order=['North','South'], errorbar=None, ax=ax)\nax.set_ylabel('Mean reading')",
        '평균 막대의 높이는 사람 수가 아닙니다. 합계가 필요한 질문에 평균을 쓰지 않습니다. '
        '자동 관찰 함수 _bar_values는 실제 막대 정보를 검사하는 도구이며 직접 다시 작성할 필요가 없습니다.',
        'supplement', (), (
            P('관측 표 readings를 North, South 순서로 요약한 fig를 만드세요. 높이는 각 지역의 평균 reading이며 오차 막대는 생략합니다. y축 이름은 Mean reading입니다.',
              SNS + "readings=pd.DataFrame({'region':['North','North','South','South','South'], 'reading':[4,8,3,3,9]})\n" + BAR_PROBE,
              "fig,ax=plt.subplots()\nsns.barplot(data=readings,x='region',y='reading',order=['North','South'],estimator='mean',errorbar=None,ax=ax)\nax.set_ylabel('Mean reading')",
              _bars([6,5], ['North','South']) + (_ax('Mean reading',['ylabel'],'평균을 나타내는 축 이름'),),
              probes={'_bar_values': [[0]]}),
            P('한 번의 매우 긴 대기가 평균에 미치는 영향을 줄여 비교하려 합니다. waits에서 Desk A, Desk B 순서의 중앙값 대기시간 막대를 fig에 그리세요. 오차 막대 없이 y축을 Median minutes로 표시하세요.',
              SNS + "waits=pd.DataFrame({'desk':['Desk A']*3+['Desk B']*3,'minutes':[1,2,15,4,5,6]})\n" + BAR_PROBE,
              "fig,ax=plt.subplots()\nsns.barplot(data=waits,x='desk',y='minutes',order=['Desk A','Desk B'],estimator='median',errorbar=None,ax=ax)\nax.set_ylabel('Median minutes')",
              _bars([2,5], ['Desk A','Desk B']) + (_ax('Median minutes',['ylabel'],'중앙값의 단위'),),
              probes={'_bar_values': [[0]]}),
            P('주문 한 건당 평균이 아니라 팀별 총 처리량이 필요합니다. orders를 Red, Blue 순서의 quantity 합계 막대로 fig에 그리세요. 오차 막대 없이 y축은 Total items입니다.',
              SNS + "orders=pd.DataFrame({'team':['Red','Red','Blue','Blue','Blue'],'quantity':[2,5,1,3,4]})\n" + BAR_PROBE,
              "fig,ax=plt.subplots()\nsns.barplot(data=orders,x='team',y='quantity',order=['Red','Blue'],estimator='sum',errorbar=None,ax=ax)\nax.set_ylabel('Total items')",
              _bars([7,8], ['Red','Blue']) + (_ax('Total items',['ylabel'],'합계를 나타내는 축 이름'),),
              probes={'_bar_values': [[0]]}),
        ), ('py_functions','pd_groupby','plot_bar'), SEABORN_NOTE))

    result.append(Lesson(
        'sns_distribution', 'Seaborn', '분포: 구간의 개수와 밀도',
        'histplot은 개별 관측값이 어느 구간에 얼마나 모였는지 보여 줍니다. data와 x로 수치 열을 선택하고 bins에 경계를 지정합니다. '
        'stat="count"는 구간별 관측 개수, stat="density"는 전체 막대 면적이 1이 되는 밀도입니다. 구간 폭이 다르면 밀도 높이만 더해서는 안 됩니다. '
        'kde=False로 별도 추정 곡선을 생략해 이번에는 실제 구간 통계에 집중합니다. 필터한 표를 그리면 원본 전체가 아니라 선택된 관측의 분포입니다.\n'
        '작게 실행: ① 어떤 행이 관측 대상인지 정합니다. ② 구간 경계와 count/density를 고릅니다. ③ 개수 합 또는 면적 합으로 해석을 점검합니다.',
        "fig,ax=plt.subplots()\nsns.histplot(data=samples,x='value',bins=[0,2,4,6],stat='count',kde=False,ax=ax)",
        '밀도는 확률 그 자체가 아니라 단위 구간당 값입니다. 특정 구간 밖의 관측은 그 구간 그림에 포함되지 않습니다. '
        'Seaborn의 온라인 예제 자료 다운로드는 사용하지 않고 준비된 작은 표만 다룹니다.',
        'supplement', (), (
            P('samples의 value를 경계 [0,2,4,6]인 세 구간의 관측 개수로 fig에 그리세요. 추가 곡선 없이 y축 이름은 Count입니다.',
              SNS + "samples=pd.DataFrame({'value':[0.5,1.0,2.2,3.9,4.1,5.2]})\n" + HIST_PROBE,
              "fig,ax=plt.subplots()\nsns.histplot(data=samples,x='value',bins=[0,2,4,6],stat='count',kde=False,ax=ax)",
              _hist([0,2,4,6], [2,2,2], 'Count'), probes={'_histogram_values': [[0]]}),
            P('같은 개수가 들어도 폭이 다른 구간의 높이가 달라지는지 확인하세요. samples의 value를 [0,1,3,6] 구간의 밀도로 fig에 그리세요. 추가 곡선 없이 y축 이름은 Density입니다.',
              SNS + "samples=pd.DataFrame({'value':[0.2,0.8,1.2,2.8,3.5,4.5]})\n" + HIST_PROBE,
              "fig,ax=plt.subplots()\nsns.histplot(data=samples,x='value',bins=[0,1,3,6],stat='density',kde=False,ax=ax)",
              _hist([0,1,3,6], [1/3,1/6,1/9], 'Density'), probes={'_histogram_values': [[0]]}),
            P('records에서 status가 ok인 행만 원래 순서의 selected 표로 남기세요. selected의 seconds 분포를 [0,2,4,10] 구간의 개수로 fig에 그리세요. 추가 곡선 없이 y축은 Count입니다.',
              SNS + "records=pd.DataFrame({'status':['ok','bad','ok','ok','bad','ok'],'seconds':[0.5,8.0,1.5,2.5,9.0,3.5]})\n" + HIST_PROBE,
              "selected=records.loc[records['status']=='ok']\nfig,ax=plt.subplots()\nsns.histplot(data=selected,x='seconds',bins=[0,2,4,10],stat='count',kde=False,ax=ax)",
              tuple(check for check in F('selected', [['ok',0.5],['ok',1.5],['ok',2.5],['ok',3.5]], [0,2,3,5], ['status','seconds']) if check['path']!=['index']) + _hist([0,2,4,10], [2,2,0], 'Count'),
              probes={'_histogram_values': [[0]]}),
        ), ('sns_summary','plot_hist','pd_filter'), SEABORN_NOTE))

    result.append(Lesson(
        'sns_relationship', 'Seaborn', '관측값의 관계와 집단 구분',
        'scatterplot은 각 행의 두 수치 변수를 점 하나의 x·y 위치로 연결합니다. 같은 x를 가진 여러 관측도 평균으로 줄이지 않습니다. '
        'hue에 범주 열을 주면 집단을 색으로 구별하며 범례가 의미를 설명합니다. hue_order로 표시할 집단 순서를 지정할 수 있습니다. '
        '두 그림을 비교할 때는 같은 축 범위를 써야 작은 차이가 과장되지 않습니다. 관계가 보인다는 것만으로 한 변수가 다른 변수의 원인이라고 결론내리지는 않습니다.\n'
        '작게 실행: ① 한 행의 x와 y를 읽습니다. ② 필요할 때만 집단 열을 색에 연결합니다. ③ 원래 점의 개수와 범례·축 단위를 확인합니다.',
        "fig,ax=plt.subplots()\nsns.scatterplot(data=observations,x='hours',y='score',ax=ax)\nax.set_xlabel('Hours')\nax.set_ylabel('Score')",
        '점들을 선으로 잇거나 집단 평균만 표시하면 다른 질문을 답하게 됩니다. 색상 팔레트 자체는 정답이 아니며 실제 집단 구분을 검사합니다.',
        'supplement', (), (
            P('observations의 모든 행을 hours–score 산점도로 fig에 그리세요. 같은 hours의 관측도 각각 남기고 x축은 Hours, y축은 Score로 표시하세요.',
              SNS + "observations=pd.DataFrame({'hours':[1,1,2,2,3],'score':[2,4,3,7,8]})\n" + SCATTER_PROBE,
              "fig,ax=plt.subplots()\nsns.scatterplot(data=observations,x='hours',y='score',ax=ax)\nax.set_xlabel('Hours')\nax.set_ylabel('Score')",
              _figure() + _points([[1,2],[1,4],[2,3],[2,7],[3,8]]) + (_ax('Hours',['xlabel'],'가로축 의미'),_ax('Score',['ylabel'],'세로축 의미')),
              probes={'_scatter_points': [[0]]}),
            P('trials의 x–y 관계를 fig에 그리되 같은 group은 같은 색, 다른 group은 다른 색으로 나타내세요. 범례는 A, B 순서입니다. 구체적인 색상은 자유입니다.',
              SNS + "trials=pd.DataFrame({'x':[1,2,1,2],'y':[3,5,6,8],'group':['A','A','B','B']})\n" + SCATTER_PROBE,
              "fig,ax=plt.subplots()\nsns.scatterplot(data=trials,x='x',y='y',hue='group',hue_order=['A','B'],ax=ax)",
              _figure() + _points([[1,3],[2,5],[1,6],[2,8]]) + (
                  C('__probes__', [[[1,3],[2,5]],[[1,6],[2,8]]], ['_scatter_color_groups',0], '실제 점 색상의 집단 대응', '범례만 추가하지 말고 점의 색을 각 group에 연결하세요.'),
                  C('__probes__', [['A',[[1,3],[2,5]]],['B',[[1,6],[2,8]]]], ['_scatter_legend_groups',0], '범례 이름·색·관측 집단의 일치', '범례의 A와 B가 실제 점의 집단을 가리키는지 확인하세요.'),
                  _ax(['A','B'],['legend'],'집단 범례')),
              probes={'_scatter_points': [[0]], '_scatter_color_groups': [[0]], '_scatter_legend_groups': [[0]]}),
            P('measurements에 raw-2인 adjusted 열을 추가하세요. fig의 1행 2열 중 왼쪽에는 time–raw, 오른쪽에는 time–adjusted 산점도를 그리고 제목은 Before, After로 표시하세요. 두 세로축 범위는 모두 0~16입니다.',
              SNS + "measurements=pd.DataFrame({'time':[0,1,2],'raw':[10,13,15]})\n" + SCATTER_PROBE,
              "measurements['adjusted']=measurements['raw']-2\nfig,axes=plt.subplots(1,2)\nsns.scatterplot(data=measurements,x='time',y='raw',ax=axes[0])\nsns.scatterplot(data=measurements,x='time',y='adjusted',ax=axes[1])\naxes[0].set_title('Before')\naxes[1].set_title('After')\naxes[0].set_ylim(0,16)\naxes[1].set_ylim(0,16)",
              F('measurements', [[0,10,8],[1,13,11],[2,15,13]], [0,1,2], ['time','raw','adjusted']) + _figure(2) +
              _points([[0,10],[1,13],[2,15]]) + _points([[0,8],[1,11],[2,13]],1,1) + (
                  C('__probes__',[1,2,0,1,0,1],['_scatter_layout',0,0,0],'왼쪽 영역'), C('__probes__',[1,2,0,1,1,2],['_scatter_layout',0,1,0],'오른쪽 영역'),
                  C('__probes__','Before',['_scatter_layout',0,0,1],'보정 전 제목'), C('__probes__','After',['_scatter_layout',0,1,1],'보정 후 제목'),
                  C('__probes__',[0,16],['_scatter_layout',0,0,2],'보정 전 세로축'), C('__probes__',[0,16],['_scatter_layout',0,1,2],'보정 후 세로축')),
              probes={'_scatter_points': [[0],[1]], '_scatter_layout': [[]]}),
        ), ('sns_distribution','plot_scatter','plot_subplots','pd_computed'), SEABORN_NOTE))

    result.append(Lesson(
        'sk_split', 'scikit-learn', '특성과 정답을 함께 훈련·테스트로 나누기',
        'scikit-learn에서는 보통 X의 행이 표본, 열이 특성이며 y는 각 행의 정답입니다. 특성이 하나여도 X는 (표본 수,1)의 2차원 배열, y는 보통 (표본 수,)입니다. '
        'train_test_split(X,y,...)은 두 자료의 대응 행을 함께 나누고 X_train, X_test, y_train, y_test 순서로 반환합니다. '
        'test_size는 정수이면 시험 표본 수, 0~1 사이 실수이면 시험 비율입니다. random_state는 무작위 분할을 재현할 기준이지 점수를 좋게 만드는 값이 아닙니다. '
        '시간 순서 자료에서 미래를 먼저 학습하지 않으려면 shuffle=False로 앞부분을 훈련, 뒷부분을 테스트로 남길 수 있습니다.\n'
        '작게 실행: ① X와 y의 행 대응·shape를 봅니다. ② 분할 기준을 정합니다. ③ 네 결과의 대응과 크기를 확인합니다.',
        'X_train,X_test,y_train,y_test = train_test_split(X,y,test_size=0.25,random_state=7)\n'
        'X_train,X_test,y_train,y_test = train_test_split(X,y,test_size=2,shuffle=False)',
        'X와 y를 따로 섞으면 입력과 정답이 엇갈립니다. train과 test의 역할을 바꾸지 않습니다. '
        '이 작은 인공 자료는 API 학습용이며 실제 프로젝트의 충분한 평가 크기를 뜻하지 않습니다.',
        'supplement', (), (
            P('8개 표본의 X와 y를 함께 무작위 분할하세요. test_size=0.25, random_state=7을 사용하고 결과를 X_train, X_test, y_train, y_test에 담으세요. 함수가 돌려준 행 순서를 유지합니다.',
              SPLIT + 'X=np.arange(8).reshape(-1,1)\ny=10+X[:,0]\n',
              'X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=0.25,random_state=7)',
              A('X_train', [[0],[6],[3],[1],[4],[7]], (6,1)) + A('X_test', [[2],[5]], (2,1)) +
              A('y_train', [10,16,13,11,14,17], (6,)) + A('y_test', [12,15], (2,))),
            P('시간순 X와 y에서 마지막 2개 관측을 미래 테스트 자료로 남기세요. 순서를 섞지 말고 X_train, X_test, y_train, y_test에 담으세요.',
              SPLIT + 'X=np.array([[1],[2],[3],[4],[5],[6]])\ny=np.array([3,4,6,7,9,10])\n',
              'X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=2,shuffle=False)',
              A('X_train', [[1],[2],[3],[4]], (4,1)) + A('X_test', [[5],[6]], (2,1)) +
              A('y_train', [3,4,6,7], (4,)) + A('y_test', [9,10], (2,))),
            P('두 특성을 가진 X의 열을 모두 유지하면서 y와 함께 분할하세요. 테스트는 정확히 2개, random_state=0이며 결과 이름은 X_train, X_test, y_train, y_test입니다. 반환된 행 순서를 유지하세요.',
              SPLIT + 'X=np.array([[0,10],[1,11],[2,12],[3,13],[4,14],[5,15]])\ny=np.array([100,101,102,103,104,105])\n',
              'X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=2,random_state=0)',
              A('X_train', [[1,11],[3,13],[0,10],[4,14]], (4,2)) + A('X_test', [[5,15],[2,12]], (2,2)) +
              A('y_train', [101,103,100,104], (4,)) + A('y_test', [105,102], (2,))),
        ), ('py_functions','np_reshape','np_slicing','pd_frame'), SKLEARN_NOTE))

    result.append(Lesson(
        'sk_fit_predict', 'scikit-learn', '모델 생성·학습·새 입력 예측',
        'LinearRegression()은 아직 학습되지 않은 회귀 모델을 만듭니다. 회귀는 연속적인 수치를 예측하는 작업입니다. '
        'model.fit(X_train,y_train)이 훈련 자료의 관계를 학습하고 model.predict(X_new)가 새 행마다 예측 한 개를 반환합니다. '
        'predict에 y_new를 넣지 않습니다. 여러 특성이 있으면 새 입력도 학습 때와 같은 열 수와 의미·순서를 가져야 합니다. '
        '여기서는 작은 직선 관계로 호출 순서와 배열 형태를 익히며 최적화 수식이나 알고리즘 전체로 범위를 넓히지 않습니다.\n'
        '작게 실행: ① model을 만듭니다. ② 훈련 자료만 fit합니다. ③ 새 입력을 predict하고 예측 개수를 확인합니다.',
        'model=LinearRegression()\nmodel.fit(X_train,y_train)\npredictions=model.predict(X_new)',
        '모델을 만들기만 하면 학습이 끝난 것이 아닙니다. 테스트 정답을 fit에 넣으면 이후 평가는 독립적인 테스트가 아닙니다. '
        '제공된 _model_predictions는 실제 객체에 새 입력을 넣는 채점용 함수이므로 수정하지 않아도 됩니다.',
        'supplement', (), (
            P('X_train,y_train으로 실제 LinearRegression 모델 model을 학습하고 X_new의 예측 배열 predictions를 만드세요. 새 표본의 입력 순서를 유지하세요.',
              REGRESSION + 'X_train=np.array([[0],[1],[2],[3]])\ny_train=np.array([1,3,5,7])\nX_new=np.array([[1.5],[5]])\n' + MODEL_PROBE,
              'model=LinearRegression()\nmodel.fit(X_train,y_train)\npredictions=model.predict(X_new)',
              A('predictions', [4,11], (2,)) + _model_checks([[-3,1,13],[2]]),
              probes={'_model_predictions': [[[[-2],[0],[6]]], [[[0.5]]]]}),
            P('두 특성을 가진 훈련 자료로 model을 학습하세요. X_new의 두 열을 같은 순서로 사용하여 예측 배열 predictions를 만드세요.',
              REGRESSION + 'X_train=np.array([[0,0],[2,0],[0,2],[2,2]])\ny_train=np.array([1,7,5,11])\nX_new=np.array([[1,1],[3,1]])\n' + MODEL_PROBE,
              'model=LinearRegression()\nmodel.fit(X_train,y_train)\npredictions=model.predict(X_new)',
              A('predictions', [6,12], (2,)) + _model_checks([[3,7,13],[0]]),
              probes={'_model_predictions': [[[[0,1],[2,0],[2,3]]], [[[-1,1]]]]}),
            P('훈련 자료만 사용해 model을 학습하고 X_test의 predictions를 만드세요. y_test는 나중의 평가용이며 모델 학습에 합치면 안 됩니다.',
              REGRESSION + 'X_train=np.array([[0],[1],[2]])\ny_train=np.array([0,2,4])\nX_test=np.array([[3],[4]])\ny_test=np.array([30,40])\n' + MODEL_PROBE,
              'model=LinearRegression()\nmodel.fit(X_train,y_train)\npredictions=model.predict(X_test)',
              A('predictions', [6,8], (2,)) + _model_checks([[-2,1,10],[3]]),
              probes={'_model_predictions': [[[[-1],[0.5],[5]]], [[[1.5]]]]}),
        ), ('sk_split',), SKLEARN_NOTE))

    result.append(Lesson(
        'sk_evaluation', 'scikit-learn', '학습 점수와 새 자료의 오차 구별',
        '평균 절대 오차 MAE는 예측과 정답 차이의 절댓값을 평균 낸 값입니다. mean_absolute_error(y_true,y_pred)로 구하며 낮을수록 좋고 정답과 같은 단위를 씁니다. '
        '양수·음수 오차가 서로 지워지도록 단순 차이를 평균 내는 것과 다릅니다. 훈련 오차는 이미 본 자료의 성적이므로 0이어도 새 자료에서 완벽하다는 보장이 없습니다. '
        '모델 평가는 학습에 넣지 않은 테스트 정답과 그 입력에 대한 예측을 비교합니다. 훈련 정답의 평균만 늘 예측하는 단순 기준선과도 비교하면 점수의 의미를 읽기 쉽습니다.\n'
        '작게 실행: ① 훈련 자료만 fit합니다. ② 테스트 입력을 predict합니다. ③ 테스트 정답과 MAE를 구하고 훈련 오차·기준선과 구분합니다.',
        'model=LinearRegression().fit(X_train,y_train)\npredictions=model.predict(X_test)\n'
        'mae=mean_absolute_error(y_test,predictions)\n'
        'baseline=np.full(len(y_test),y_train.mean())',
        'MAE를 정확도 비율이라고 부르지 않습니다. 테스트 점수를 보고 반복적으로 모델을 조정하면 검증용 자료를 별도로 두어야 합니다. '
        '이 작은 연습의 한 번 비교를 실제 서비스 성능 보장으로 확대하지 않습니다.',
        'supplement', (), (
            P('훈련 자료만 사용한 model과 X_test의 predictions를 만드세요. y_test와 비교한 평균 절대 오차를 mae에 담으세요.',
              METRICS + 'X_train=np.array([[-2],[-1],[0],[1]])\ny_train=np.array([-3,-1,1,3])\nX_test=np.array([[2],[3]])\ny_test=np.array([6,6])\n' + MODEL_PROBE,
              'model=LinearRegression().fit(X_train,y_train)\npredictions=model.predict(X_test)\nmae=mean_absolute_error(y_test,predictions)',
              A('predictions', [5,7], (2,)) + (C('mae',1.0,label='테스트 MAE',feedback='훈련 정답이 아니라 y_test와 예측을 비교하고 절댓값을 평균 내세요.'),) + _model_checks([[1,9]]),
              probes={'_model_predictions': [[[[0],[4]]]]}),
            P('훈련 자료로만 model을 학습하세요. 훈련 예측 train_predictions와 테스트 예측 predictions를 만들고 errors 사전에 train, test 각각의 MAE를 담으세요. 훈련 오차 0만으로 새로운 자료에서도 완벽함이 보장되는지 generalization_guaranteed에 bool로 답하세요.',
              METRICS + 'X_train=np.array([[0],[1],[2],[3]])\ny_train=np.array([1,3,5,7])\nX_test=np.array([[4],[5],[6]])\ny_test=np.array([11,9,15])\n' + MODEL_PROBE,
              "model=LinearRegression().fit(X_train,y_train)\ntrain_predictions=model.predict(X_train)\npredictions=model.predict(X_test)\nerrors={'train':mean_absolute_error(y_train,train_predictions),'test':mean_absolute_error(y_test,predictions)}\ngeneralization_guaranteed=False",
              A('train_predictions', [1,3,5,7], (4,)) + A('predictions', [9,11,13], (3,)) + (
                  C('errors',{'train':0.0,'test':2.0},label='훈련/테스트 오차의 분리',feedback='두 오차에 같은 입력·정답을 재사용하지 않았는지 확인하세요.'),
                  C('generalization_guaranteed',False,label='훈련 성적 해석',feedback='이미 본 자료의 오차만으로 새로운 자료의 오차를 보장할 수 없습니다.')) + _model_checks([[-1,15]]),
              probes={'_model_predictions': [[[[-1],[7]]]]}),
            P('훈련 자료로 model을 학습하고 테스트 예측 predictions를 만드세요. 훈련 y의 평균만 늘 예측하는 baseline 배열도 만드세요. scores 사전에 linear와 baseline의 테스트 MAE를 각각 담고, MAE가 더 작은 쪽의 이름을 better_model에 적으세요.',
              METRICS + 'X_train=np.array([[0],[1],[2],[3]])\ny_train=np.array([2,4,6,8])\nX_test=np.array([[4],[5]])\ny_test=np.array([11,11])\n' + MODEL_PROBE,
              "model=LinearRegression().fit(X_train,y_train)\npredictions=model.predict(X_test)\nbaseline=np.full(len(y_test),y_train.mean())\nscores={'linear':mean_absolute_error(y_test,predictions),'baseline':mean_absolute_error(y_test,baseline)}\nbetter_model='linear' if scores['linear']<scores['baseline'] else 'baseline'",
              A('predictions',[10,12],(2,)) + A('baseline',[5,5],(2,)) + (
                  C('scores',{'linear':1.0,'baseline':6.0},label='같은 테스트 자료에서 기준선 비교',feedback='기준선의 평균은 테스트 정답이 아니라 훈련 정답에서 구합니다. MAE에서는 작은 값이 좋습니다.'),
                  C('better_model','linear',label='오차가 더 작은 예측기')) + _model_checks([[0,14]]),
              probes={'_model_predictions': [[[[-1],[6]]]]}),
        ), ('sk_fit_predict',), SKLEARN_NOTE))

    result.append(Lesson(
        'sk_classification', 'scikit-learn', '분류 모델과 예측 결과 읽기',
        '회귀는 수치를 예측하고 분류는 범주를 예측합니다. LogisticRegression은 이름에 Regression이 있지만 분류 모델입니다. '
        'X는 표본×특성의 2차원 배열이고 y는 표본별 범주입니다. 훈련 자료로 fit한 뒤 새 X만 predict에 넣습니다. '
        '정확도는 맞힌 비율이지만, 특정 범주가 드문 자료에서는 그 범주를 전부 놓쳐도 높게 나올 수 있습니다. '
        '혼동 행렬은 행이 실제 범주, 열이 예측 범주입니다. recall은 실제 양성 중 찾은 비율입니다.\n'
        '작게 실행: ① X와 y의 행을 맞춥니다. ② 훈련 자료로 분류기를 학습합니다. ③ 새 자료를 예측하고 오분류 종류를 봅니다.',
        'model=LogisticRegression().fit(X_train,y_train)\npredictions=model.predict(X_test)\n'
        'matrix=confusion_matrix(y_test,predictions,labels=[0,1])',
        '정확도 하나만 보고 드문 양성을 잘 찾는다고 결론 내리지 않습니다. 정답을 fit에 넣은 자료와 독립 평가 자료를 구분합니다.',
        'supplement', (), (
            P('두 범주를 실제 LogisticRegression model로 학습하고 X_test의 predictions를 만드세요.',
              CLASSIFICATION + 'X_train=np.array([[-3],[-2],[-1],[1],[2],[3]])\n'
              'y_train=np.array([0,0,0,1,1,1])\nX_test=np.array([[-2],[2]])\n' + CLASSIFIER_PROBE,
              'model=LogisticRegression().fit(X_train,y_train)\npredictions=model.predict(X_test)',
              A('predictions',[0,1],(2,)) + _model_checks([ [0,1] ],'_classifier_predictions'),
              probes={'_classifier_predictions': [[[[-4],[4]]]]}),
            P('두 특성 모두를 사용해 model을 학습하고 X_test 두 행의 predictions를 만드세요.',
              CLASSIFICATION + 'X_train=np.array([[0,0],[0,1],[1,0],[3,3],[3,4],[4,3]])\n'
              'y_train=np.array([0,0,0,1,1,1])\nX_test=np.array([[0,2],[4,4]])\n' + CLASSIFIER_PROBE,
              'model=LogisticRegression().fit(X_train,y_train)\npredictions=model.predict(X_test)',
              A('predictions',[0,1],(2,)) + _model_checks([[0,1]],'_classifier_predictions'),
              probes={'_classifier_predictions': [[[[0,0],[4,3]]]]}),
            P('양성이 1개뿐인 평가 자료에서 모두 0으로 예측했을 때 accuracy와 양성 recall, matrix를 구하세요. 높은 정확도가 양성 탐지를 뜻하는지도 positive_detected에 bool로 답하세요.',
              CLASSIFICATION + 'y_true=np.array([0,0,0,0,0,0,0,0,0,1])\n'
              'y_pred=np.zeros(10,dtype=int)\n',
              'accuracy=accuracy_score(y_true,y_pred)\nrecall=recall_score(y_true,y_pred)\n'
              'matrix=confusion_matrix(y_true,y_pred,labels=[0,1])\npositive_detected=False',
              (C('accuracy',0.9,label='전체 정확도'), C('recall',0.0,label='양성 재현율'),
               C('positive_detected',False,label='드문 양성 탐지 해석')) +
              A('matrix',[[9,0],[1,0]],(2,2))),
        ), ('sk_evaluation',), SKLEARN_NOTE))

    result.append(Lesson(
        'sk_pipeline', 'scikit-learn', '훈련 자료만으로 전처리하고 같은 규칙으로 예측하기',
        '표준화는 훈련 자료에서 평균과 표준편차를 배운 다음 그 기준으로 값을 바꿉니다. 테스트 자료까지 섞어 평균을 구하면 미래 정보가 학습에 새어 들어갑니다. '
        'Pipeline은 StandardScaler와 LinearRegression을 연결합니다. fit(X_train,y_train)은 훈련 자료로만 두 단계를 맞추고, predict(X_test)는 같은 변환을 테스트 입력에 적용합니다. '
        '전처리를 직접 따로 fit하거나 테스트 입력의 특성 열 순서를 바꾸지 않습니다.\n'
        '작게 실행: ① 훈련·테스트를 나눕니다. ② 모델을 파이프라인으로 묶습니다. ③ 훈련 자료만 fit하고 테스트 입력을 predict합니다.',
        'model=make_pipeline(StandardScaler(),LinearRegression())\n'
        'model.fit(X_train,y_train)\npredictions=model.predict(X_test)',
        '테스트 자료에 scaler.fit이나 fit_transform을 다시 호출하면 학습 때의 좌표계가 달라집니다. '
        '작은 인공 자료의 완벽한 직선 예측은 실제 성능 보장이 아닙니다.',
        'supplement', (), (
            P('StandardScaler와 LinearRegression을 연결한 model을 훈련 자료로만 학습하세요. X_test의 predictions와 scaler_mean을 저장하세요.',
              PIPELINE + 'X_train=np.array([[0],[1],[2],[3]])\ny_train=np.array([1,3,5,7])\n'
              'X_test=np.array([[4],[5]])\n' + PIPELINE_PROBE,
              'model=make_pipeline(StandardScaler(),LinearRegression())\nmodel.fit(X_train,y_train)\n'
              'predictions=model.predict(X_test)\nscaler_mean=model.steps[0][1].mean_',
              A('predictions',[9,11],(2,)) + A('scaler_mean',[1.5],(1,)) +
              _model_checks([[13]],'_pipeline_predictions'),
              probes={'_pipeline_predictions': [[[[6]]]]}),
            P('테스트에 큰 값 100이 있어도 표준화 평균은 훈련 자료만으로 구하세요. model을 만들고 predictions와 scaler_mean을 저장하세요.',
              PIPELINE + 'X_train=np.array([[0],[1],[2],[3]])\ny_train=np.array([1,3,5,7])\n'
              'X_test=np.array([[100]])\n' + PIPELINE_PROBE,
              'model=make_pipeline(StandardScaler(),LinearRegression())\nmodel.fit(X_train,y_train)\n'
              'predictions=model.predict(X_test)\nscaler_mean=model.steps[0][1].mean_',
              A('predictions',[201],(1,)) + A('scaler_mean',[1.5],(1,)) +
              _model_checks([[11]],'_pipeline_predictions'),
              probes={'_pipeline_predictions': [[[[5]]]]}),
            P('특성 두 열을 가진 자료로 같은 파이프라인을 학습하세요. 새 행의 predictions와 훈련 데이터의 scaler_mean을 저장하세요.',
              PIPELINE + 'X_train=np.array([[0,0],[1,0],[0,1],[1,1]])\n'
              'y_train=np.array([1,3,4,6])\nX_test=np.array([[2,1]])\n' + PIPELINE_PROBE,
              'model=make_pipeline(StandardScaler(),LinearRegression())\nmodel.fit(X_train,y_train)\n'
              'predictions=model.predict(X_test)\nscaler_mean=model.steps[0][1].mean_',
              A('predictions',[8],(1,)) + A('scaler_mean',[0.5,0.5],(2,)) +
              _model_checks([[8]],'_pipeline_predictions'),
              probes={'_pipeline_predictions': [[[[2,1]]]]}),
        ), ('sk_classification',), SKLEARN_NOTE))

    result.append(Lesson(
        'sk_cross_validation', 'scikit-learn', '교차 검증과 시간 순서 검증',
        '한 번의 훈련·테스트 분할은 어떤 표본이 테스트에 들어갔는지에 따라 점수가 달라집니다. '
        'KFold는 자료를 여러 구간으로 나누어 각 구간을 한 번씩 평가에 사용합니다. cross_val_score는 각 구간에서 모델을 새로 학습해 점수 배열을 돌려줍니다. '
        'scoring="neg_mean_absolute_error"는 큰 점수가 좋다는 점수 규칙 때문에 MAE에 음수를 붙입니다. 실제 MAE는 부호를 바꾸어 읽습니다. '
        '시간 순서 자료는 미래를 훈련에 넣지 않도록 TimeSeriesSplit을 씁니다.\n'
        '작게 실행: ① 훈련·검증 인덱스가 겹치지 않는지 봅니다. ② 구간별 점수를 계산합니다. ③ 시간 자료에서는 이전 관측만 훈련에 사용합니다.',
        'folds=KFold(n_splits=3)\nscores=cross_val_score(LinearRegression(),X,y,cv=folds,scoring="neg_mean_absolute_error")\n'
        'mean_mae=(-scores).mean()',
        '교차 검증을 돌린 뒤 같은 테스트 자료를 반복해서 모델 선택에 사용하면 최종 평가가 독립적이지 않습니다. '
        '시간 순서 자료를 무작위로 섞어 미래를 예측한다고 해석하지 않습니다.',
        'supplement', (), (
            P('6개 표본을 순서를 섞지 않는 3개 구간으로 나누세요. 각 구간의 테스트 인덱스를 test_indices 배열(3행 2열)로 만드세요.',
              VALIDATION + 'X=np.arange(6).reshape(-1,1)\n',
              'folds=KFold(n_splits=3,shuffle=False)\n'
              'test_indices=np.array([test for _,test in folds.split(X)])',
              A('test_indices',[[0,1],[2,3],[4,5]],(3,2))),
            P('선형 자료의 3구간 교차 검증 점수 scores와 각 구간 MAE의 평균 mean_mae를 구하세요. scoring은 neg_mean_absolute_error를 사용하세요.',
              VALIDATION + 'X=np.arange(9).reshape(-1,1)\ny=2*X[:,0]+1\n',
              "scores=cross_val_score(LinearRegression(),X,y,cv=3,scoring='neg_mean_absolute_error')\nmean_mae=(-scores).mean()",
              A('scores',[0,0,0],(3,)) + (C('mean_mae',0.0,label='구간별 MAE 평균'),)),
            P('시간 순서가 있는 8개 표본을 TimeSeriesSplit 3구간으로 나누세요. fold_sizes에 각 구간의 훈련·테스트 개수를, last_test에 마지막 평가 인덱스를 담으세요.',
              VALIDATION + 'X=np.arange(8).reshape(-1,1)\n',
              'folds=list(TimeSeriesSplit(n_splits=3).split(X))\n'
              'fold_sizes=np.array([[len(train),len(test)] for train,test in folds])\nlast_test=folds[-1][1]',
              A('fold_sizes',[[2,2],[4,2],[6,2]],(3,2)) + A('last_test',[6,7],(2,))),
        ), ('sk_pipeline',), SKLEARN_NOTE))

    # Keep real probe helpers in executable initial, but show only the imports
    # and observation data in the learner's prepared-data panel.
    def visible_initial(initial):
        for helper in (BAR_PROBE, HIST_PROBE, SCATTER_PROBE, MODEL_PROBE,
                       CLASSIFIER_PROBE, PIPELINE_PROBE):
            initial = initial.replace(helper, '')
        return initial.strip()

    return tuple(replace(unit, problems=tuple(
        replace(problem, display_initial=visible_initial(problem.initial))
        for problem in unit.problems)) for unit in result)


def validation_cases():
    """Author-side regression cases; these are not extra learner problems.

    Execute initial + wrong/equivalent in fresh Kernels, then use each Problem's
    targets/probes/checks. No custom grader is required. These variants document
    which misconceptions must fail and which implementation choices stay free.
    """
    units = {unit.key: unit for unit in lessons()}
    cases = []

    def add(key, number, wrong, equivalent, reason):
        cases.append({'lesson': key, 'problem': number,
                      'wrong': wrong, 'equivalent': equivalent, 'reason': reason})

    p = units['sns_summary'].problems
    add('sns_summary', 0,
        p[0].solution.replace("estimator='mean'", "estimator='sum'"),
        p[0].solution.replace("estimator='mean'", "estimator=np.mean,width=0.5,color='orange'"),
        '집단 평균 대신 합계는 거부하며, 같은 평균의 폭·색·callable estimator 차이는 허용합니다.')
    add('sns_summary', 1,
        p[1].solution.replace("estimator='median'", "estimator='mean'"),
        p[1].solution.replace("estimator='median'", "estimator=np.median,width=0.6"),
        '큰 관측값을 포함한 평균을 중앙값으로 오해한 결과를 거부합니다.')
    add('sns_summary', 2,
        p[2].solution.replace("estimator='sum'", "estimator='mean'"),
        "totals=orders.groupby('team',as_index=False)['quantity'].sum()\nfig,ax=plt.subplots()\nsns.barplot(data=totals,x='team',y='quantity',order=['Red','Blue'],errorbar=None,ax=ax)\nax.set_ylabel('Total items')",
        '평균 처리량은 거부하며 미리 합산한 표에서 같은 합계를 그린 결과는 허용합니다.')

    p = units['sns_distribution'].problems
    add('sns_distribution', 0,
        p[0].solution.replace('bins=[0,2,4,6]', 'bins=[0,3,6]'),
        p[0].solution.replace("data=samples,x='value'", "x=samples['value']"),
        '잘못된 구간 경계는 거부하며 열 벡터를 직접 전달하는 방식은 허용합니다.')
    add('sns_distribution', 1,
        p[1].solution.replace("stat='density'", "stat='probability'") + "\nax.set_ylabel('Density')",
        p[1].solution.replace("data=samples,x='value'", "x=samples['value']").replace('kde=False', "kde=False,color='purple'"),
        '폭이 다른 구간의 확률과 밀도 혼동을 축 이름이 같아도 거부합니다.')
    add('sns_distribution', 2,
        p[2].solution.replace("selected=records.loc[records['status']=='ok']", 'selected=records.copy()'),
        p[2].solution.replace("selected=records.loc[records['status']=='ok']", "selected=records[records['status']=='ok']"),
        '원본 전체를 그리는 오류를 거부하며 동등한 pandas 행 선택을 허용합니다.')

    p = units['sns_relationship'].problems
    add('sns_relationship', 0,
        p[0].solution.replace('data=observations', "data=observations.groupby('hours',as_index=False)['score'].mean()"),
        p[0].solution.replace('data=observations', 'data=observations.iloc[::-1]'),
        '같은 x의 관측을 평균으로 줄이면 거부하며 그리는 행 순서만 반대인 경우는 허용합니다.')
    add('sns_relationship', 1,
        "fig,ax=plt.subplots()\nsns.scatterplot(data=trials,x='x',y='y',color='black',ax=ax)\nax.scatter([],[],color='black',label='A')\nax.scatter([],[],color='gray',label='B')\nax.legend()",
        p[1].solution.replace("hue_order=['A','B']", "hue_order=['A','B'],palette={'A':'purple','B':'orange'}"),
        '범례 글자만 맞추고 실제 점의 집단 색이 모두 같으면 거부하며 팔레트는 자유입니다.')
    add('sns_relationship', 2,
        p[2].solution.replace("measurements['raw']-2", "measurements['raw']+2"),
        p[2].solution.replace("measurements['adjusted']=measurements['raw']-2", "measurements=measurements.assign(adjusted=measurements['raw']-2)"),
        '보정 방향 오류는 거부하며 동일 열을 반환하는 표 구성 방법은 허용합니다.')

    # Quiz-agent audit: preserve semantic freedom while rejecting misleading visuals.
    selected = units['sns_distribution'].problems[2]
    add('sns_distribution', 2,
        selected.solution.replace("selected=records.loc[records['status']=='ok']", "selected=records.loc[records['status']=='ok'].iloc[::-1]"),
        selected.solution.replace("selected=records.loc[records['status']=='ok']", "selected=records.loc[records['status']=='ok'].reset_index(drop=True)"),
        '목표의 원래 행 순서는 검사하지만 요구하지 않은 인덱스 번호는 강제하지 않습니다.')
    add('sns_relationship', 0,
        p[0].solution.replace("sns.scatterplot(data=observations,x='hours',y='score',ax=ax)", "ax.plot(observations['hours'],observations['score'],marker='o')"),
        p[0].solution.replace("sns.scatterplot(data=observations,x='hours',y='score',ax=ax)", "ax.plot(observations['hours'],observations['score'],marker='o',linestyle='None')"),
        '점을 잇는 선은 거부하지만 연결선 없이 같은 점을 그리는 Matplotlib 표현은 허용합니다.')
    add('sns_relationship', 0,
        p[0].solution.replace("sns.scatterplot(data=observations,x='hours',y='score',ax=ax)", "ax.plot(observations['hours'],observations['score'],marker='o',linestyle='None',color=(0,0,1,0))"),
        p[0].solution.replace("sns.scatterplot(data=observations,x='hours',y='score',ax=ax)", "ax.plot(observations['hours'],observations['score'],marker='o',linestyle='None',markerfacecolor='none',markeredgecolor='purple')"),
        '완전히 투명한 점은 그림으로 인정하지 않지만 테두리가 보이는 빈 마커는 허용합니다.')
    add('sns_relationship', 1,
        p[1].solution + "\nhandles,_=ax.get_legend_handles_labels()\nax.legend(handles[::-1],['A','B'])",
        "fig,ax=plt.subplots()\na=trials[trials['group']=='A']\nb=trials[trials['group']=='B']\nax.scatter(a['x'],a['y'],color='purple',label='A')\nax.scatter(b['x'],b['y'],color='orange',label='B')\nax.legend()",
        '색 범례의 이름이 뒤바뀐 경우를 거부하며 집단별 scatter 호출은 허용합니다.')
    add('sns_relationship', 2,
        p[2].solution.replace('fig,axes=plt.subplots(1,2)', 'fig,axes=plt.subplots(2,1)'),
        p[2].solution.replace('fig,axes=plt.subplots(1,2)', 'fig=plt.figure()\nright=fig.add_subplot(1,2,2)\nleft=fig.add_subplot(1,2,1)\naxes=[left,right]'),
        '위아래 배치는 거부하지만 실제 좌우 배치가 같으면 Axes 생성 순서는 자유입니다.')

    p = units['sk_split'].problems
    add('sk_split', 0,
        'X_train,X_test=train_test_split(X,test_size=0.25,random_state=7)\ny_train,y_test=train_test_split(y,test_size=0.25,random_state=0)',
        'X_train,X_test,y_train,y_test=train_test_split(X,y,train_size=6,test_size=2,random_state=7)',
        '입력과 정답의 서로 다른 섞임을 거부하며 동일한 표본 수를 지정한 분할은 허용합니다.')
    add('sk_split', 1,
        p[1].solution.replace('shuffle=False', 'shuffle=True,random_state=7'),
        'X_train,X_test=X[:-2].copy(),X[-2:].copy()\ny_train,y_test=y[:-2].copy(),y[-2:].copy()',
        '미래 관측을 섞은 분할을 거부하며 같은 연속 구간을 유지하는 NumPy 분할은 허용합니다.')
    add('sk_split', 2,
        p[2].solution.replace('train_test_split(X,y,', 'train_test_split(X[:,0],y,'),
        p[2].solution.replace('test_size=2', 'train_size=4,test_size=2'),
        '특성 열 하나를 잃어버린 1차원 입력을 거부하고 동등한 분할 크기는 허용합니다.')

    p = units['sk_fit_predict'].problems
    add('sk_fit_predict', 0,
        "model={'name':'LinearRegression'}\npredictions=np.array([4,11])",
        'model=LinearRegression(fit_intercept=True).fit(X_train,y_train)\npredictions=model.predict(X_new)',
        '예측 숫자만 맞춘 가짜 모델을 거부하며 같은 실제 추정기의 생성·fit 연결 표현은 허용합니다.')
    add('sk_fit_predict', 1,
        p[1].solution.replace('model.predict(X_new)', 'model.predict(X_new[:,::-1])'),
        p[1].solution.replace('LinearRegression()', 'LinearRegression(copy_X=True,n_jobs=1)'),
        '예측 때 특성 순서를 바꾼 오류를 거부하며 계산 의미가 같은 실제 모델 옵션은 허용합니다.')
    add('sk_fit_predict', 2,
        p[2].solution.replace('model.fit(X_train,y_train)', 'model.fit(np.vstack([X_train,X_test]),np.concatenate([y_train,y_test]))'),
        'model=LinearRegression().fit(X_train,y_train)\npredictions=model.predict(X_test)',
        '테스트 정답을 학습에 합친 모델은 새 입력 예측에서도 달라져 거부됩니다.')

    p = units['sk_evaluation'].problems
    add('sk_evaluation', 0,
        p[0].solution.replace('mean_absolute_error(y_test,predictions)', 'np.mean(y_test-predictions)'),
        p[0].solution.replace('mae=mean_absolute_error(y_test,predictions)', 'mae=np.mean(np.abs(y_test-predictions))'),
        '양수·음수 오차를 서로 지우는 단순 차이 평균을 거부하며 같은 MAE 정의의 직접 계산은 허용합니다.')
    add('sk_evaluation', 1,
        p[1].solution.replace("'test':mean_absolute_error(y_test,predictions)", "'test':mean_absolute_error(y_train,train_predictions)"),
        p[1].solution.replace("errors={'train':mean_absolute_error(y_train,train_predictions),'test':mean_absolute_error(y_test,predictions)}", "errors={'test':mean_absolute_error(y_test,predictions),'train':mean_absolute_error(y_train,train_predictions)}"),
        '두 칸에 훈련 오차를 재사용하면 거부하며 사전 키를 작성한 순서 차이는 허용합니다.')
    add('sk_evaluation', 2,
        p[2].solution.replace('y_train.mean()', 'y_test.mean()'),
        p[2].solution.replace('np.full(len(y_test),y_train.mean())', 'np.repeat(np.mean(y_train),len(X_test))'),
        '테스트 정답 평균으로 기준선을 만든 누출을 거부하며 동등한 기준선 배열 생성은 허용합니다.')

    p = units['sk_classification'].problems
    add('sk_classification', 0,
        "model={'type':'LogisticRegression'}\npredictions=np.array([0,1])",
        p[0].solution.replace('LogisticRegression()', 'LogisticRegression(C=10)'),
        '예측 숫자만 적은 가짜 모델은 거부하고 실제 분류기의 설정 차이는 허용합니다.')
    p = units['sk_pipeline'].problems
    add('sk_pipeline', 1,
        p[1].solution.replace('scaler_mean=model.steps[0][1].mean_',
                              'scaler_mean=StandardScaler().fit(np.vstack([X_train,X_test])).mean_'),
        p[1].solution.replace('make_pipeline(StandardScaler(),LinearRegression())',
                              "Pipeline([('scale',StandardScaler()),('regression',LinearRegression())])"),
        '테스트 값을 표준화 평균에 섞으면 거부하고 동등한 파이프라인 표현은 허용합니다.')
    p = units['sk_cross_validation'].problems
    add('sk_cross_validation', 1,
        p[1].solution.replace("scoring='neg_mean_absolute_error'", "scoring='r2'"),
        p[1].solution.replace('cv=3', 'cv=KFold(n_splits=3,shuffle=False)'),
        'R²와 음의 MAE를 혼동하면 거부하고 같은 구간을 명시한 방식은 허용합니다.')
    return tuple(cases)
