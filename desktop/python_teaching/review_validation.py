"""Portable author-side regressions for the five-unit review audit.

``validation_cases()`` returns JSON-serializable dictionaries, not learner
problems or a second grader. For each case, find the named lesson and zero-based
problem, execute its initial/files and one code string in a fresh real Kernel,
then use its existing targets, probes and checks. ``wrong`` must fail grading;
``equivalent`` must pass. Both must execute successfully.

The two original in-place alternatives are now deliberately wrong: preservation
is an explicit learning goal. Their positive partners operate on copies. The
other seven original alternatives remain accepted, without requiring the
reference solution's intermediate names or artist creation order.

Importing and exporting this module requires only the standard library. Codes
are independent of the wording of the reference solution, so a changed solution
cannot silently turn a string replacement into an unmodified positive test.
"""
from textwrap import dedent


def _code(value):
    return dedent(value).strip()


def _change(code, before, after):
    if code.count(before) != 1:
        raise ValueError(f'Expected one regression transformation: {before!r}')
    return code.replace(before, after, 1)


_TOTALS = _code("""
    valid=df.loc[df['valid']]
    wide=valid.pivot_table(index=['team','year'],columns='kind',values='visits',aggfunc='sum',fill_value=0)
    sums=valid.groupby('team')['visits'].sum()
    result=sums.loc[sums>=10]
""")

_LOGS = _code("""
    all_logs=pd.concat([logs1,logs2])
    result=all_logs.merge(roster,on='id',how='right')
    result=result.fillna({'points':0})
""")

_CENTER = _code("""
    centered=a.copy()
    centered-=centered.mean(axis=0)
    stream=np.append(np.flip(centered,axis=0),[99,99])
    variances=centered.var(axis=0)
""")

_STOCK = _code("""
    left=old.copy()
    right=new.copy()
    left.columns=['id','stock_old']
    right.columns=['id','stock_new']
    result=left.merge(right,on='id',how='outer',sort=True)
    result=result.fillna({'stock_old':0,'stock_new':0})
    result['change']=result['stock_new']-result['stock_old']
""")

_COMPARISON = _code("""
    fig,ax=plt.subplots(figsize=(3,3))
    ax.plot(x,reference,color='black',linestyle='--',label='reference')
    ax.plot(x,actual,color='red',marker='o',linestyle='-',label='actual')
    ax.legend()
    ax.set_title('Comparison')
    scratch=plt.figure()
    fig.savefig('comparison.png',dpi=100)
""")

_RESIDUAL = _code("""
    fig,axes=plt.subplots(2,1)
    axes[0].scatter(x,y,s=sizes,alpha=.5)
    axes[0].set_title('Measurements')
    axes[1].bar(x,y-x,width=.8)
    axes[1].set_title('Residuals')
""")

_SITES = _code("""
    valid=data[data[:,2]>=0]
    fig,ax=plt.subplots()
    points=ax.scatter(valid[:,0],valid[:,1],c=valid[:,2],s=valid[:,2]*10,alpha=.5)
    fig.colorbar(points,ax=ax)
    ax.set_title('Valid sites')
""")

_SPLIT_SITES = _code("""
    valid=data[data[:,2]>=0][::-1]
    fig,ax=plt.subplots()
    scale=plt.Normalize(vmin=2,vmax=6)
    points=[]
    for row in valid:
        points.append(ax.scatter([row[0]],[row[1]],c=[row[2]],s=[row[2]*10],alpha=.5,norm=scale,cmap='viridis'))
    fig.colorbar(points[0],ax=ax)
    ax.set_title('Valid sites')
""")

_CUMULATIVE = _code("""
    valid=data[data>=0]
    mu,sigma=norm.fit(valid)
    fig,axes=plt.subplots(1,2)
    cumulative,edges,patches=axes[0].hist(valid,bins=[0,2,4],density=True,cumulative=True)
    axes[0].set_title('Cumulative')
    axes[1].plot(x,norm.pdf(x,loc=mu,scale=sigma))
    axes[1].set_title('Density')
""")


def validation_cases():
    """Return fresh case dictionaries using the library validation case API.

    Fields: stable ``id``, ``audit`` category, ``lesson`` key, zero-based
    ``problem`` index, complete ``wrong`` and ``equivalent`` code strings, and
    Korean ``reason``. No callable transforms, fixtures, executable assertions
    or platform paths are embedded in the returned data.
    """
    cases = []

    def add(identifier, audit, lesson, problem, wrong, equivalent, reason):
        cases.append({'id': identifier, 'audit': audit, 'lesson': lesson,
                      'problem': problem, 'wrong': wrong,
                      'equivalent': equivalent, 'reason': reason})

    # The nine alternatives from the audit, with the two preservation cases
    # correctly reclassified after the learning goals were clarified.
    add('totals_intermediate_name', 'intermediate_name', 'review_pd_04', 2,
        _change(_TOTALS, "valid=df.loc[df['valid']]", 'valid=df'), _TOTALS,
        '유효하지 않은 기록의 합산은 거부하며, 목표에 없는 중간 변수 totals 이름은 강제하지 않습니다.')
    add('concat_original_index', 'concat_index', 'review_pd_03', 2,
        _LOGS + "\nresult=result.drop_duplicates(subset=['id'])", _LOGS,
        '중복 출석 삭제는 거부하며, all_logs의 원래 행 라벨 유지는 허용합니다.')
    add('center_preserves_source', 'preservation', 'review_np_03', 2,
        _change(_CENTER, 'centered=a.copy()\ncentered-=centered.mean(axis=0)',
                'a-=a.mean(axis=0)\ncentered=a'), _CENTER,
        '목표에 명시된 원본 a 변경은 거부하며, 복사본에 제자리 연산하는 풀이를 허용합니다.')
    add('stock_preserves_sources', 'preservation', 'review_pd_03', 1,
        _change(_change(_STOCK, 'left=old.copy()', 'left=old'),
                'right=new.copy()', 'right=new'), _STOCK,
        '원본 old/new의 열 이름 변경은 거부하며, 독립 복사본의 열을 먼저 바꿔 결합하는 풀이는 허용합니다.')
    add('scratch_zero_axes', 'empty_figure', 'review_plot_01', 2,
        _change(_COMPARISON, 'scratch=plt.figure()',
                'scratch,scratch_ax=plt.subplots()\nscratch_ax.plot([0,1],[0,1])'),
        _COMPARISON,
        '내용이 있는 scratch는 거부하지만 Axes가 하나도 없는 실제 빈 Figure는 허용합니다.')
    add('vertical_axes_created_bottom_first', 'axes_position', 'review_plot_02', 1,
        _change(_RESIDUAL, 'fig,axes=plt.subplots(2,1)', 'fig,axes=plt.subplots(1,2)'),
        _change(_RESIDUAL, 'fig,axes=plt.subplots(2,1)',
                'fig=plt.figure()\nbottom=fig.add_subplot(2,1,2)\ntop=fig.add_subplot(2,1,1)\naxes=[top,bottom]'),
        '좌우 배치는 거부하며 위아래 위치가 맞으면 아래 Axes를 먼저 생성해도 허용합니다.')
    add('scatter_split_collections', 'scatter_correspondence', 'review_plot_02', 1,
        _change(_RESIDUAL, 's=sizes', 's=sizes[::-1]'),
        _change(_RESIDUAL, 'axes[0].scatter(x,y,s=sizes,alpha=.5)',
                'for i in range(3):\n    axes[0].scatter([x[i]],[y[i]],s=[sizes[i]],alpha=.5)'),
        '점별 면적 대응 오류는 거부하며 같은 점들을 여러 scatter 호출로 나누는 것은 허용합니다.')
    add('scatter_reordered_rows', 'scatter_correspondence', 'review_plot_02', 2,
        _change(_SITES, 'c=valid[:,2]', 'c=valid[::-1,2]'),
        _change(_SITES, 'valid=data[data[:,2]>=0]', 'valid=data[data[:,2]>=0][::-1]'),
        '좌표와 스칼라색 값 대응 오류는 거부하며 모든 속성이 함께 움직인 행 순서 변경은 허용합니다.')
    add('horizontal_axes_created_right_first', 'axes_position', 'review_plot_03', 2,
        _change(_CUMULATIVE, 'fig,axes=plt.subplots(1,2)', 'fig,axes=plt.subplots(2,1)'),
        _change(_CUMULATIVE, 'fig,axes=plt.subplots(1,2)',
                'fig=plt.figure()\nright=fig.add_subplot(1,2,2)\nleft=fig.add_subplot(1,2,1)\naxes=[left,right]'),
        '위아래 배치는 거부하며 좌우 위치가 맞으면 오른쪽 Axes를 먼저 생성해도 허용합니다.')

    # Empty is a visual/content requirement, not just an absence of lines.
    add('scratch_scatter_not_empty', 'empty_figure', 'review_plot_01', 2,
        _change(_COMPARISON, 'scratch=plt.figure()',
                'scratch,scratch_ax=plt.subplots()\nscratch_ax.scatter([0],[1])'),
        _change(_COMPARISON, 'scratch=plt.figure()', 'scratch,scratch_ax=plt.subplots()'),
        '산점도가 있는 scratch는 거부하며 비어 있는 Axes 하나는 허용합니다.')
    add('scratch_image_not_empty', 'empty_figure', 'review_plot_01', 2,
        _change(_COMPARISON, 'scratch=plt.figure()',
                'scratch,scratch_ax=plt.subplots()\nscratch_ax.imshow([[1,2],[3,4]])'),
        _COMPARISON,
        '이미지가 있는 scratch는 선과 막대가 없어도 빈 Figure가 아닙니다.')
    add('scratch_text_not_empty', 'empty_figure', 'review_plot_01', 2,
        _change(_COMPARISON, 'scratch=plt.figure()',
                "scratch=plt.figure()\nscratch.text(.5,.5,'not empty')"),
        _change(_COMPARISON, 'scratch=plt.figure()',
                'scratch=plt.figure()\nscratch_ax=scratch.add_subplot(1,1,1)'),
        'Figure 자체에 쓴 텍스트도 빈 그림이 아니며 빈 Axes를 별도로 추가하는 방식은 허용합니다.')

    # A tuple must retain position, size and alpha together. Merely sorting
    # every attribute separately would allow several deliberately wrong cases.
    add('scatter_uniform_alpha', 'scatter_correspondence', 'review_plot_02', 1,
        _change(_RESIDUAL, 'alpha=.5', 'alpha=.8'),
        _change(_RESIDUAL, 'alpha=.5', 'alpha=[.5,.5,.5]'),
        '잘못된 투명도는 거부하며 모든 점에 같은 0.5 배열을 지정하는 것은 허용합니다.')
    add('scatter_individual_alpha', 'scatter_correspondence', 'review_plot_02', 1,
        _change(_RESIDUAL, 'alpha=.5', 'alpha=[.5,.8,.5]'),
        _change(_RESIDUAL, 'axes[0].scatter(x,y,s=sizes,alpha=.5)',
                'order=[2,0,1]\naxes[0].scatter(x[order],y[order],s=np.array(sizes)[order],alpha=.5)'),
        '한 점만 잘못된 투명도도 거부하며 좌표·크기를 함께 순열로 옮기는 방식은 허용합니다.')
    add('scatter_transparent_points', 'scatter_visibility', 'review_plot_02', 1,
        _change(_RESIDUAL, 'alpha=.5', 'alpha=0'), _RESIDUAL,
        '좌표가 존재해도 완전히 투명한 점들은 요구된 산점도가 아닙니다.')
    add('scatter_extra_point', 'scatter_correspondence', 'review_plot_02', 1,
        _RESIDUAL + '\naxes[0].scatter([99],[99],s=[20],alpha=.5)',
        _change(_RESIDUAL, 'axes[0].scatter(x,y,s=sizes,alpha=.5)',
                'for i in [2,1,0]:\n    axes[0].scatter([x[i]],[y[i]],s=[sizes[i]],alpha=.5)'),
        '추가 관측점은 거부하며 호출 순서까지 바뀐 여러 collection은 허용합니다.')
    add('scatter_coordinate_pairing', 'scatter_correspondence', 'review_plot_02', 1,
        _change(_RESIDUAL, 'scatter(x,y,', 'scatter(x,y[::-1],'),
        _change(_RESIDUAL, 'scatter(x,y,s=sizes,', 'scatter(x[::-1],y[::-1],s=sizes[::-1],'),
        'x와 y를 독립적으로 정렬한 오판을 막으며 완전한 관측의 역순은 허용합니다.')
    add('scatter_no_visible_marker', 'scatter_visibility', 'review_plot_02', 1,
        _change(_RESIDUAL, 's=sizes,alpha=.5', "s=sizes,alpha=.5,facecolors='none',edgecolors='none'"),
        _change(_RESIDUAL, 's=sizes,alpha=.5', "s=sizes,alpha=.5,facecolors='none',edgecolors='purple'"),
        '면과 테두리가 모두 보이지 않으면 거부하며 테두리가 보이는 빈 마커는 허용합니다.')

    add('scalar_scatter_size_pairing', 'scatter_correspondence', 'review_plot_02', 2,
        _change(_SITES, 's=valid[:,2]*10', 's=valid[::-1,2]*10'),
        _change(_SITES, 'valid=data[data[:,2]>=0]', 'valid=data[data[:,2]>=0][::-1]'),
        '색 수치가 맞아도 각 좌표의 크기 대응이 바뀌면 거부합니다.')
    add('scalar_scatter_alpha', 'scatter_correspondence', 'review_plot_02', 2,
        _change(_SITES, 'alpha=.5', 'alpha=[.5,.8]'),
        _change(_SITES, 'alpha=.5', 'alpha=[.5,.5]'),
        '스칼라색 산점도도 점별 투명도를 검사하고 동등한 배열 투명도는 허용합니다.')
    add('scalar_colorbar_disconnected', 'colorbar_link', 'review_plot_02', 2,
        _change(_SITES, 'fig.colorbar(points,ax=ax)',
                'fig.colorbar(plt.cm.ScalarMappable(norm=points.norm,cmap=points.cmap),ax=ax)'),
        _change(_SITES, 'alpha=.5', "alpha=.5,cmap='plasma'"),
        '다른 mappable의 색 눈금은 거부하며 점과 실제 연결된 색 눈금의 팔레트 선택은 자유입니다.')
    add('scalar_colorbar_missing', 'colorbar_link', 'review_plot_02', 2,
        _change(_SITES, 'fig.colorbar(points,ax=ax)', 'fig.add_subplot(1,2,2)'),
        _SITES,
        '빈 Axes를 추가해 축 개수만 맞춘 것은 실제 점에 연결된 색 눈금이 아닙니다.')
    add('scalar_scatter_split_shared_scale', 'colorbar_link', 'review_plot_02', 2,
        _change(_SPLIT_SITES, 's=[row[2]*10]', 's=[20]'), _SPLIT_SITES,
        'collection을 나눠도 점별 크기는 정확해야 하며 동일 척도와 실제 연결된 색 눈금을 사용하는 분할은 허용합니다.')
    add('scalar_scatter_split_scale_mismatch', 'colorbar_link', 'review_plot_02', 2,
        _SPLIT_SITES + '\npoints[1].set_norm(plt.Normalize(vmin=0,vmax=12))',
        _change(_SPLIT_SITES, 'norm=scale', 'norm=plt.Normalize(vmin=2,vmax=6)'),
        '일부 점의 색 척도만 색 눈금과 다르면 거부하며 값이 같은 독립 Normalize 객체는 허용합니다.')
    add('scalar_scatter_hidden_artist', 'scatter_visibility', 'review_plot_02', 2,
        _SITES + '\npoints.set_visible(False)', _SITES,
        '좌표와 컬러바가 남아 있어도 실제 점 객체를 숨기면 산점도 목표를 만족하지 못합니다.')
    add('scalar_scatter_extra_point', 'scatter_correspondence', 'review_plot_02', 2,
        _SITES + '\nax.scatter([99],[99],c=[2],s=[20],alpha=.5,norm=points.norm,cmap=points.cmap)',
        _SPLIT_SITES,
        '올바른 collection 뒤에 다른 관측을 추가해도 거부하며 올바른 점만 나눈 그림은 허용합니다.')
    return tuple(cases)
