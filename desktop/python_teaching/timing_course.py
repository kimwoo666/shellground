"""Small, bounded timing exercises: never grade a hardware-dependent speedup."""
from .model import Lesson, problem as P, check as C, array as A


def timing_check(name,count):
    return dict(C(name,count,label=name+' 실제 측정값 '+str(count)+'개',
        feedback='초 단위의 유한한 양수 측정값을 지정한 횟수만큼 기록하세요. 특정 속도나 배속은 요구하지 않습니다.'),rule='positive_measurements')


def lesson():
    initial='import numpy as np\nfrom time import perf_counter\na=np.arange(1000,dtype=np.float64)\n'
    return Lesson('np_timing','NumPy','준비 시간과 첫 실행을 구분해 반복 측정',
        'perf_counter는 두 시점 사이 경과 시간을 재는 시계입니다. 배열 생성·import·출력은 측정 구간 밖에 둡니다. 첫 실행에는 초기 준비 비용이 섞일 수 있어 첫 값과 후속 측정을 분리합니다. 같은 코드를 여러 번 재고 중앙값 같은 요약을 봅니다. 작은 입력에서는 호출 비용이 커서 배열 코드가 무조건 빠르지는 않습니다.',
        'start=perf_counter()\nresult=a*a\nelapsed=perf_counter()-start\n# 가볍게 예열한 뒤 같은 구간을 반복 측정\nsamples=[]\nfor _ in range(3):\n    start=perf_counter()\n    result=a*a\n    samples.append(perf_counter()-start)',
        '측정 안에서 print하지 마세요. 초와 밀리초를 구분하며 작은 값도 0으로 반올림해 저장하지 않습니다. 정답 여부를 먼저 확인하고 측정으로 옳고 그름을 대신하지 마세요.',
        'week_2_1_handout.pdf',(34,35,36,37,38,39,40),(
            P('준비된 a를 제곱한 result를 구하는 구간을 3번 측정하세요. 각 경과 시간(초)을 samples 목록에 기록하고, 마지막 결과의 합 total을 구하세요. 준비·출력 시간은 제외합니다.',initial,
              'samples=[]\nfor _ in range(3):\n    start=perf_counter()\n    result=a*a\n    samples.append(perf_counter()-start)\ntotal=result.sum()',
              [timing_check('samples',3),C('total',332833500)]),
            P('a*2+1 계산의 첫 실행 시간만 cold 목록(원소 1개)에 기록하세요. 같은 계산을 추가로 3번 재서 warm 목록에 담고 최종 결과의 합 total을 구하세요. cold와 warm의 속도 대소는 정답 조건이 아닙니다.',initial,
              'start=perf_counter()\nresult=a*2+1\ncold=[perf_counter()-start]\nwarm=[]\nfor _ in range(3):\n    start=perf_counter()\n    result=a*2+1\n    warm.append(perf_counter()-start)\ntotal=result.sum()',
              [timing_check('cold',1),timing_check('warm',3),C('total',1000000)]),
            P('a의 각 원소 제곱을 Python 반복문 방식과 배열 방식으로 각각 한 번 계산해 예열하세요. 이후 각 방식의 계산 구간을 3번씩 재서 loop_times, array_times에 초 단위로 기록하세요. 마지막 결과의 합 loop_total, array_total을 각각 구해 두 계산의 일치도 확인하세요. 특정 배속은 요구하지 않습니다.',initial,
              'loop_result=[x*x for x in a]\narray_result=a*a\nloop_times=[]\narray_times=[]\nfor _ in range(3):\n    start=perf_counter()\n    loop_result=[x*x for x in a]\n    loop_times.append(perf_counter()-start)\n    start=perf_counter()\n    array_result=a*a\n    array_times.append(perf_counter()-start)\nloop_total=sum(loop_result)\narray_total=array_result.sum()',
              [timing_check('loop_times',3),timing_check('array_times',3),C('loop_total',332833500),C('array_total',332833500)]),
        ),('np_vectorize','py_iteration'))
