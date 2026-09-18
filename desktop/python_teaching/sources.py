"""Physical PDF pages audited against the actual five source documents.

New examples are authored here; a page reference is not a copied question.
See quiz_blueprint.md for the per-key evidence and correction audit.
"""
from dataclasses import replace

D1='Week 1_1.pdf'
D2='week_1_2_handout.pdf'
D3='week_2_1_handout.pdf'
D4='week_2_2_handout.pdf'
D5='week_3_1_handout.pdf'

OVERRIDES={
    **{k:('supplement',()) for k in ('py_values','py_sequences','py_mapping','py_set','py_functions','py_iteration','np_concatenate','np_stack_helpers','np_random_legacy','np_random_generator','np_memory')},
    'py_kernel':(D1,(11,)), 'py_module_file':(D2,(26,29,30,34)),
    'py_standard':(D2,(27,28,29)), 'py_units':(D2,(13,14,15,16,17,18)),
    'np_reduce':(D3,(30,)), 'np_statistics':(D3,(30,31,32,33)),
    'np_insert':(D3,(19,)), 'np_vectorize':(D3,(34,35,36,37,38,39,40)),
    'plot_line':(D4,(6,9,10,11,16,17,18)), 'plot_style':(D4,(7,8,15)),
    'plot_labels':(D4,(6,14)), 'plot_limits':(D4,(11,12,40,41,42)),
    'plot_subplots':(D4,(16,17,18,19)), 'plot_scatter':(D4,(5,20,21,22,23)),
    'plot_bar':(D4,(24,25)), 'plot_pie':(D4,(26,)), 'plot_density':(D4,(30,34)),
    'plot_normal':(D4,(31,32,33,34,35)), 'plot_box':(D4,(36,37,38,39)),
    'pd_series':(D5,(2,3,4,5,28,29,31)), 'pd_frame':(D5,(6,7,8,13,45)),
    'pd_csv':(D5,(10,11,12,13,45)), 'pd_columns':(D5,(13,14,16,27,32)),
    'pd_argmax':(D5,(9,)), 'pd_computed':(D5,(15,16,17)), 'pd_drop':(D5,(16,18,19,20)),
    'pd_loc':(D5,(28,31,32)), 'pd_iloc':(D5,(25,26,29,30,31,32)),
    'pd_filter':(D5,(32,46)), 'pd_missing':(D5,(4,45,46)),
    'pd_merge':(D5,(39,41,42)), 'pd_merge_detail':(D5,(39,40,44)),
    'pd_pivot':(D5,(33,34)), 'pd_pivot_table':(D5,(35,)), 'pd_groupby':(D5,(46,)),
}
NOTES={
    'py_methods':'sorted·append·sort의 반환값은 입문 보충입니다.',
    'py_module_file':'모듈 캐시와 파일 이름 충돌은 실사용 보충입니다.',
    'py_standard':'모듈 역할은 강의 범위, 개별 함수 사용법은 보충입니다.',
    'py_units':'강의 개념에 RGB·원시 용량 계산을 응용했습니다.',
    'np_dtype':'nbytes·astype과 형 변환은 보충입니다.',
    'np_mask':'여러 조건 결합은 보충입니다.',
    'np_reshape':'독립 복사와 수정 전파는 보충입니다.',
    'np_flip':'copy와 메모리 관계는 보충입니다.',
    'np_concatenate':'연결 함수는 NumPy 강의 실제41쪽 자습 지정입니다. 사용법과 stack은 보충 설명입니다.',
    'np_stack_helpers':'NumPy 강의 실제41쪽에 지정된 자습 API를 설명합니다.',
    'np_random_legacy':'NumPy 강의 실제41쪽의 자습 지정 난수 API를 설명합니다.',
    'np_random_generator':'최신 Generator API는 강의 밖 실사용 보충입니다.',
    'np_memory':'data·strides는 NumPy 강의 실제7쪽, 뷰·복사 관계는 보충입니다.',
    'np_vectorize':'강의 time.time 측정을 perf_counter로 보완했습니다.',
    'plot_save':'plt.savefig도 유효하다는 점은 강의 오류를 정정했습니다.',
    'plot_density':'누적 개수와 누적 비율의 차이는 강의 설명 오류를 정정했습니다.',
    'pd_csv':'header=None/names는 보충입니다.',
    'pd_argmax':'idxmax와 명시적인 위치/라벨 구분은 보충입니다.',
    'pd_pivot':'다중 index/values 지원 및 중복 조합 오류는 공식 API에 맞게 설명합니다.',
    'pd_pivot_table':'강의 개념에 aggfunc/fill_value를 보충했습니다.',
    'pd_datetime':'강의의 날짜 집계를 to_datetime과 Series.dt로 확장했습니다.',
}


def audited(unit):
    source,pages=OVERRIDES.get(unit.key,(unit.source,unit.pages))
    return replace(unit,source=source,pages=tuple(pages),provenance_note=NOTES.get(unit.key,
        '강의 학습에 필요한 선수 개념을 보충합니다.' if source=='supplement' else '예제·활용 문제는 새로 구성했습니다.'))
