# Python 입문과 첫 다섯 강의 퀴즈 설계

## 2026-09-18 범위 보완

기존 60문항을 보존하고 병렬성 분류 한 문항을 더해 61문항이다. 기존 33개 개념 카드에 자료 병렬·작업 병렬·벡터화와 코어 수 구분 3개를 추가했다. 아래 본문은 최초 60문항 설계 이력이며 새 항목은 이 표가 우선한다.

| 문항 ID | 근거 | 평가와 관련 실습의 차이 |
|---|---|---|
| numpy-parallelism-versus-vectorization | D3 실제35쪽, 벡터 계산·측정 34–40쪽 | 같은 연산을 자료 분할에 적용하는 자료 병렬과 서로 다른 작업의 분담을 구분한다. 벡터화가 자동 다중 코어 실행이라는 주장을 거부한다. np_vectorize/np_timing은 관련 계산·측정 연습이지 실제 병렬 실행 구현이나 자유 서술 채점이 아니다. |

실제 Jupyter 5단원+복습과 날짜 인덱스·날씨 평균/count·Series 차트·concat 라벨 실습은 별도 등록 과정이다. 퀴즈 완료를 실습 완료로 자동 환산하지 않는다.

## 범위와 산출물

quiz_bank.json은 schema=1의 독창적인 한국어 4지선다 60문항이다. 각 문항은 안정적인 id, 개념 topic, 선행 개념 목록, 원문 파일명과 **물리 페이지**, 오개념 해설, 독립 실습 시작 코드, 기대 결과, 통과·거부 기준을 갖는다. 정답은 0 기반 인덱스이며 위치 분포는 0번 14개, 1번 16개, 2번 15개, 3번 15개다.

- 환경·Python·데이터 개념: 17문항.
- NumPy: 17문항.
- Matplotlib·통계 시각화: 14문항.
- pandas: 12문항.
- 코드 결과·객체 속성으로 확인 가능한 52문항은 실제 라이브러리로 확인했다. 나머지 8문항의 환경·연구 설계 판단은 사람이 근거와 설명을 평가한다.
- 이 문서는 문제 데이터와 수업 설계다. 앱의 진도, 시뮬레이터, 서버, VM, 계정, Conda 설치 상태를 변경하거나 설치 성공을 판정하지 않는다.
- 강의 문장·이미지를 복제하는 대신 새로운 상황과 수치, 독자적인 설명을 사용했다. 시험 날짜·담당자 연락처·평가 비율을 외우는 퀴즈는 만들지 않는다.
- 회귀·분류·군집·신경망은 이 다섯 강의에서 앞으로 배울 도구·주제의 소개 수준이다. 아직 가르치지 않은 모델 수식이나 학습 알고리즘을 오답 함정에 사용하지 않는다.

## 자료와 페이지 기준

| 문서 키 | 실제 페이지 수 | 사용자 자료 위치 |
|---|---:|---|
| Week 1_1.pdf | 15 | /home/pigeon/NAS-Obsidian/숭실대 AI소프트웨어/숭실대 2학년 2학기 과목/2학기/머신러닝/수업주차/01주차 공식자료/Week 1_1.pdf |
| week_1_2_handout.pdf | 34 | 위 01주차 공식자료 폴더 |
| week_2_1_handout.pdf | 41 | 같은 수업주차/02주차 공식자료 폴더 |
| week_2_2_handout.pdf | 42 | 같은 수업주차/02주차 공식자료 폴더 |
| week_3_1_handout.pdf | 46 | /home/pigeon/NAS/data/옵시디언/숭실대 AI소프트웨어/숭실대 2학년 2학기 과목/2학기/머신러닝/수업주차/03주차 공식자료/week_3_1_handout.pdf |

Week 1_1의 표지·섹션 구분 페이지도 센다. week_3_1은 표시 번호 18의 내용이 실제 18·19쪽에 걸쳐 있어 실제 19쪽부터 슬라이드에 표시된 번호와 1쪽 차이가 난다. 예를 들어 마지막 45번 슬라이드는 실제 46쪽이다. JSON의 source.pages를 화면에 표시할 때 “PDF 실제 페이지”라고 명시한다. 보충은 document="supplement", pages=[]로 저장하며 강의에 직접 실린 명령이라고 표시하지 않는다.

PDF 텍스트를 전체 추출해 범위를 확인했다. 디지털 변환 도식(1-2 실제 13쪽), 두 축 슬라이싱·집계(2-1 실제 23·30쪽), subplot·상자그림(2-2 실제 18·37쪽), pivot 설명(3-1 실제 35쪽)은 PNG로 렌더링하여 직접 확인했다.

## 권장 학습 순서

1. 환경과 실행 위치를 설명한다. 터미널, Python 코드, 노트북 셀은 입력 위치가 다르다. Android에서는 지원 범위와 실행 위치부터 안내한다.
2. Python 입문 보충을 먼저 제공한다. 값·이름·대입, int/float/str/bool/None, 리스트·튜플·딕셔너리·집합, 0 기반 인덱스, if, for, def, return, import, 에러 메시지의 마지막 줄을 설명한다. 딕셔너리 시작 코드를 읽을 수 있기 전에 환경 계획 딕셔너리를 작성하게 하지 않는다.
3. 첫 강의의 노트북 실행 순서와 저장 위치, 둘째 강의의 분석 질문·디지털 표현·라이브러리 역할을 학습한다.
4. NumPy는 shape/axis를 숫자 계산보다 먼저 예측하게 한다. 생성 → 원소별 계산 → 브로드캐스팅 → 선택 → 재배열 → 집계 → 통계 → 실행 성능 순으로 진행한다.
5. Matplotlib은 분석 질문 → 차트 종류 → 축·레이블 → Figure/Axes → 비교와 저장 순으로 진행한다.
6. pandas는 라벨·결측 → CSV → 선택 → 계산 열 → 시각화 → 재배치 → 결합 → 날짜별 집계 순으로 진행한다.
7. 마지막으로 아래 R5 종합복습을 새 실행 상태에서 수행한다.

각 개념은 짧은 설명과 최소 예제 → 실행 전 결과·shape 예상 → 직접 실행 → 이유 설명 → 선택형 문제 → 독립 실습의 흐름이다. 이미 설명한 개념으로 생기는 오해만 선택지에 쓴다. Python 보충에서는 복잡한 컴프리헨션·람다·고급 OOP·데코레이터를 요구하지 않는다. 수행 시간이 빠르다는 이유로 숙달을 판정하지 않는다.

동일 topic이 여러 문항에 등장한다. prerequisites는 문항 id가 아니라 아래 개념 id다. 자신의 topic이 prerequisites에 들어 있는 응용 문제는 해당 개념의 **기초 설명을 먼저 이수**한다는 뜻이다. 이를 자기 자신을 잠그는 순환 의존성으로 구현하면 안 된다. 파일의 나열 순서와 개념 설명 순서를 함께 사용한다.

## 개념 식별자

| 개념 id | 처음 설명할 내용 |
|---|---|
| notebook.kernel | 코드 셀, 커널 상태, 실행 순서, 재실행 |
| notebook.persistence | 노트북 저장과 세션 임시 파일의 차이 |
| environment.packages | 패키지 설치와 import, 인터프리터 선택 |
| environment.conda | Conda 환경 생성·활성화·의존성 분리 |
| environment.platform | 운영체제 지원과 실제 실행 위치 |
| python.assignment | 값, 이름, 대입, 재계산; 숫자·문자열·불리언 기초 |
| python.sequences | 리스트·튜플, 0 기반 위치, 끝 제외 슬라이스 |
| python.control | if 조건, for 누적, def·인수·return·들여쓰기 |
| python.objects | 클래스·객체·메서드, 제자리 변경과 반환값 |
| python.imports | 모듈·패키지, import 방식, 이름 공간과 별칭 |
| data.science | 분석 질문, 관측 근거, 사업·빅데이터와 구별 |
| data.three_vs | 양·유입 속도·형태 다양성 |
| data.information | 원자료를 목적에 맞게 처리한 정보 |
| data.digitization | 아날로그·디지털, 표본화·양자화·부호화 |
| data.images | 비트맵·벡터, 픽셀·회색조, bit·byte·단위 |
| data.paradigms | 경험·이론·계산·데이터 중심 과학 |
| environment.library_roles | 강의의 6개 라이브러리 역할 |
| numpy.elementwise | 수치 배열과 리스트, 원소별 산술 |
| numpy.metadata | dtype, itemsize, size, 데이터 크기 |
| numpy.shape | ndim, shape, (n,)·(1,n)·(n,1) |
| numpy.broadcast | 오른쪽 축 정렬, 같은 길이 또는 1 |
| numpy.creation | zeros·ones·full·eye, arange·linspace·logspace |
| numpy.axes | axis에 따른 삽입·뒤집기 |
| numpy.indexing | 행·열 선택, 연속 대괄호, 축 유지·제거 |
| numpy.mask | 불리언 마스크와 원소 선택 |
| numpy.reshape | 원소 수 보존, append·flatten·reshape |
| numpy.reduction | 집계로 없애는 축, 값과 결과 shape |
| statistics.variance | 평균·분산·표준편차, ddof와 모집단·표본 |
| numpy.vectorization | 벡터화, 자료·작업 병렬성, 측정 조건 |
| plot.selection | 질문과 차트 종류의 대응 |
| plot.lines | 입력 순서와 기본 x, 선을 이루는 점 |
| plot.styles | 색·마커·선 모양, 스타일은 데이터와 구별 |
| plot.scales | 축 범위·눈금·단위가 인상에 주는 영향 |
| plot.export | 대상 Figure와 저장 파일 |
| plot.layout | Figure·Axes·Axis, subplots·GridSpec, 크기·격자 |
| plot.scatter | 산점도, 크기·색·투명도, 관계와 인과 |
| plot.bars | 범주 비교, 중첩·그룹·누적 차이 |
| plot.pie | 부분과 전체, 비중·레이블·시각적 강조 |
| plot.heatmap | 행·열 위치, 색과 값, colorbar |
| plot.histogram | 구간·도수·누적·정규화 |
| statistics.distribution | 정규분포의 모수·표본, 밀도와 적합 |
| statistics.boxplot | 사분위수·IQR·경계·수염·이상치 후보 |
| pandas.series | Series·DataFrame, 라벨, 결측 탐지 |
| pandas.csv | CSV 헤더·구분자·인코딩·index_col |
| pandas.selection | 열 이름, Series·DataFrame, head·tail·행 필터 |
| pandas.derived | 계산 열 생성·입력 열 명시·재계산 |
| pandas.mutation | drop, axis, inplace, 반환값 |
| pandas.plot | 표의 인덱스와 계열, 전치와 시각화 |
| pandas.indexers | loc 라벨, iloc 위치, 두 축과 여러 행 선택 |
| pandas.reshape | pivot 배치, 결측 조합, 집계가 필요한 pivot_table |
| pandas.combine | concat 방향·라벨과 merge 키·조인 방식 |
| pandas.grouping | 날짜 변환·월/연 묶음, 결측 정책, 집계 |

## 필수 강의 항목별 문제·실습 매핑

| 강의와 실제 페이지 | 필수 내용 | 문항 또는 독립 실습 |
|---|---|---|
| 1-1, 4·6·8 | 데이터 분석·시각화 기반, 이론과 구현, 먼저 스스로 시도한 뒤 AI를 활용하는 학습 방식 | data-science-small-sample, R5의 독립 시도와 수정 이유 기록. 공식 과제 제출이나 성적을 대신하지 않음 |
| 1-1, 11 | 노트북 코드/Markdown·커널·실행 순서 | notebook-execution-order, L0 |
| 1-1, 12~15 | Colab·로컬 선택, 임시 파일·지속성, Python·Jupyter·Conda | cloud-session-storage, install-versus-import, conda-project-isolation, L1 |
| 1-2, 2~6 | 데이터 과학·사업·빅데이터, 3V, 활용 질문 | data-science-small-sample, bigdata-three-vs, L2 |
| 1-2, 7~10 | 수집→시각화→판단과 대체 가설 | data-science-small-sample, R5의 해석 한계 |
| 1-2, 11~13 | 데이터와 정보, 아날로그/디지털, 표본화·양자화·부호화 | data-versus-information, digital-sample-quantize-encode |
| 1-2, 14~18 | 비트맵/벡터, 픽셀, 회색조, bit/byte, 이진 단위 관례 | image-representation-storage, L2 |
| 1-2, 21~23 | 과학의 네 패러다임과 공존 | science-four-paradigms |
| 1-2, 24~25 | 내장 자료형, 객체·클래스·메서드 | python-assignment-rebind, python-slice-exclusive-stop, python-function-loop, python-method-sort, L0 |
| 1-2, 26~31 | 모듈·패키지·이름 공간·표준/외부/사용자 모듈·PyPI | python-import-namespace, package-roles, L1 |
| 1-2, 32~34 | 여섯 도구 역할, 설치와 import, pip·Conda의 위치 | package-roles, install-versus-import, L1 |
| 2-1, 2~9 | 리스트/배열 산술, 동일 dtype, ndim/shape/size/itemsize, 축 | numpy-list-array-add, numpy-dtype-memory, numpy-shape-dimensions |
| 2-1, 10~15 | 스칼라·행·열·양쪽 확장, 실패 조건 | numpy-broadcast-column-offsets, numpy-broadcast-outer-grid, numpy-broadcast-incompatible, L3 |
| 2-1, 16~20 | zeros/ones/full/eye, arange/linspace/logspace, insert/flip | numpy-array-constructors, numpy-range-spacing, numpy-logarithmic-spacing, numpy-axis-insert-flip |
| 2-1, 21~27 | 정수 선택·슬라이스·쉼표·연속 인덱싱·논리 인덱싱 | numpy-chained-slice, numpy-index-versus-slice-rank, numpy-boolean-selection |
| 2-1, 28~30 | append·평탄화·reshape·축 집계 | numpy-append-reshape, numpy-reduction-axis, L3·L4 |
| 2-1, 31~33 | 분산·표준편차·ddof·pandas 기본값 비교 | numpy-variance-ddof, L6 |
| 2-1, 34~40 | 루프/벡터화, 자료/작업 병렬성, 예열·반복·첫 실행 | numpy-vectorization-benchmark. 특정 배속은 암기하지 않음 |
| 2-1, 41 | 자습 지정: 배열 결합, 난수와 seed | L4 보충. concatenate/vstack/hstack/column_stack/r_/c_, legacy random과 Generator 관계를 설명한 후 실습 |
| 2-2, 5~10 | 차트 선택, pyplot, 스타일, 여러 점·함수 | plot-chart-question, plot-input-order, plot-style-components |
| 2-2, 11~19 | 축 범위, 저장, 제목·축 이름·범례, 스타일, Figure/Axes·small multiples·GridSpec | plot-axis-scale-interpretation, plot-save-correct-figure, plot-figure-axes-layout, L5 |
| 2-2, 20~23 | 산점도의 위치·크기·색·투명도, 양/음/비선형 관계 | plot-scatter-meaning, L5. 관계가 곧 인과라는 오해 방지 |
| 2-2, 24~27 | 그룹 막대, 원그래프, 히트맵·색 눈금 | plot-bar-grouping, plot-pie-whole, plot-heatmap-colorbar |
| 2-2, 28~35 | 히스토그램·구간·누적, 정규분포·밀도·적합 | plot-histogram-bins, plot-cumulative-count-proportion, plot-normal-density, L6 |
| 2-2, 36~42 | 상자그림·IQR·수염·이상치, 그림 크기·격자 | plot-boxplot-whisker, plot-figure-axes-layout, L5·L6 |
| 3-1, 2~9 | Series/DataFrame, 라벨, 결측, max/mean/argmax | pandas-series-missing, pandas-column-labels, L7 |
| 3-1, 10~14 | CSV·헤더·구분자·인덱스·문자열 열 이름·tolist | pandas-csv-index, pandas-column-labels, L7 |
| 3-1, 15~20 | 계산 열, 입력 열 명시, 재계산, drop·inplace | pandas-derived-recompute, pandas-drop-return |
| 3-1, 21~24 | Series/표 시각화, 인덱스와 계열, 전치 | pandas-transpose-time-plot |
| 3-1, 25~32 | head/tail, 행 범위·마스크, loc/iloc·두 축·여러 행 | pandas-column-labels, pandas-loc-iloc, L7 |
| 3-1, 33~35 | pivot·pivot_table·다층 라벨·결측 조합 | pandas-pivot-layout, pandas-pivot-duplicate-aggregation |
| 3-1, 36~44 | concat axis/join, merge on/how·suffix·index 결합 | pandas-concat-labels, pandas-merge-key-values, L8 |
| 3-1, 45~46 | 날씨 표·인코딩, describe/count/isna/dropna/fillna, 날짜·groupby·후속 필터 | pandas-weather-missing-group, L7·R5 |

개별 문항과 출처의 전체 대응은 문서 끝의 색인에 있다. 지도·LLM 사례 그림이나 외부 통계 수치를 기억하는 문항을 넣는 대신 해당 페이지가 전달하는 분석 원리를 평가한다.

## 강의 표현 보정과 보충 출처

아래는 강의 자체를 수정했다는 뜻이 아니다. 학습 자료가 잘못된 동작을 정답으로 가르치지 않도록 보정한 부분이다. 공식 문서는 2026-09-16 확인했으며 실제 검증 버전은 아래에 별도로 남긴다.

| 위치 | 수업에서 사용할 정확한 설명 | 근거 |
|---|---|---|
| 2-2 실제 13 | Figure.savefig와 pyplot.savefig 모두 있다. 전자는 지정한 Figure, 후자는 현재 Figure를 저장한다. | [Matplotlib savefig](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html), 두 PNG 실행·시각 확인 |
| 2-2 실제 18 | np.arrange는 오타이며 np.arange를 사용한다. | 설치된 NumPy에서 arange 실행, arrange 속성 없음 확인 |
| 2-2 실제 30 | cumulative=True의 기본은 누적 도수다. density=True를 함께 쓰면 마지막 누적값 1로 정규화된다. | [Matplotlib hist](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.hist.html), [3,5,6] 대 [0.5,5/6,1] 확인 |
| 2-2 실제 35 | 적합 곡선을 그리기 전에 정의한 구간에서 x 표본을 만든다. norm.fit 결과는 분포 가정이 맞다는 증명이 아니다. | 실제 SciPy fit/pdf 실행, 200점 곡선 검증 |
| 3-1 실제 35 | 현대 pivot은 복수 열 이름을 받을 수 있다. 핵심 구분은 pivot이 집계하지 않으며 중복 조합의 집계에는 pivot_table을 쓴다는 것이다. | [pandas pivot](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pivot.html), 복수 index 성공·중복 pivot 실패 확인 |
| 3-1 실제 31 | Series의 정수 대괄호 처리는 버전 차이가 있으므로 위치는 iloc, 라벨은 loc를 명시한다. “항상 이 오류”를 모든 버전에 강요하지 않는다. | [pandas 3.0 변경 기록](https://pandas.pydata.org/docs/whatsnew/v3.0.0.html), pandas 2.3.3 환경에서는 명시적 loc/iloc로 검증 |
| 1-2 실제 19 | Unicode 문자 전체가 언제나 2바이트인 것은 아니다. 인코딩과 문자에 따라 크기가 달라진다. 이 슬라이드의 대략적 규모를 정확한 용량 공식으로 출제하지 않는다. | [Python Unicode HOWTO](https://docs.python.org/3/howto/unicode.html) |
| 1-2 실제 17~18 | 강의의 KB=1024 관례와 SI의 kB=1000, 명확한 KiB=1024를 구별한다. 문제는 단위 관례를 먼저 선언한다. | 강의 자체의 실제 18쪽 주석 |
| 보충 | Conda의 공식 설치 대상은 Windows/macOS/Linux다. Android 네이티브 설치를 공식 지원·완료로 꾸미지 않는다. 브라우저나 지원 PC에서 실행하는 대안을 설명한다. | [Conda 설치 지원 범위](https://docs.conda.io/projects/conda/en/stable/user-guide/install/) |
| 보충 | 리스트 변경 메서드의 반환값, 함수 return, if/for, 자료 구조 선택을 입문 선수학습으로 제공한다. | [Python 자료 구조](https://docs.python.org/3/tutorial/datastructures.html), [제어 흐름](https://docs.python.org/3/tutorial/controlflow.html) |
| 2-1 자습 보충 | 새 예제는 default_rng(seed)의 독립 Generator를 사용한다. 같은 seed·같은 생성기·같은 호출 조건에서 비교하며 모든 미래 버전의 난수열이 영원히 같다고 보장하지 않는다. | [NumPy Generator](https://numpy.org/doc/stable/reference/random/generator.html) |

추가 설명: NumPy 배열의 dtype은 원소 표현을 정하지만 모든 배열이 C 연속 메모리인 것은 아니다. 슬라이스 view와 strides 같은 세부 동작을 아직 배우지 않았다면 그 내용을 시험 함정으로 쓰지 않는다. 벡터화도 모든 연산이 항상 여러 CPU 코어에서 병렬 실행된다는 보장이 아니다. 표준 library, pip, Conda, Anaconda 배포판을 구분한다. Seaborn 스타일 이름은 설치 버전에 따라 달라질 수 있으므로 plt.style.available을 확인하고 기본 스타일도 허용한다.

## 독립 실습과 채점 기준

모든 실습은 자신만의 입력을 다시 정의한다. 이전 문제에서 남은 변수나 그래프에 의존하지 않는다. 제공된 코드의 TODO를 채우는 연습 이후에는 빈 편집기에서 요구사항만 보고 재작성하는 단계를 둔다. 완성 코드를 먼저 보여주지 않는다.

### L0. Python으로 작은 집계 함수 만들기

보충 선수학습: 기본 값과 자료형, =와 ==, 리스트/튜플, 딕셔너리의 키, 집합의 중복 제거, if/for/def/return, 메서드 반환값, import, NameError/TypeError/IndexError의 간단한 예를 먼저 설명한다.

요구: sum_positive(values)는 양수만 합해 반환한다. 입력 [3,-1,5,0]이면 8, []이면 0, [-4,-2]이면 0이다. 원본 리스트를 바꾸지 않는다. {'name':'A','scores':[3,-1,5,0]}에서 리스트를 꺼내 함수를 호출한다. 터미널 명령과 Python 문장을 예시 카드에서 구별한다.

통과: 세 입력에서 결과와 반환 타입이 맞고 if 조건·반복·return 위치를 설명한다. 숫자 “8” 인쇄, 빈 목록 오류, 항상 같은 값 반환, for 안의 이른 return, 누적값 매회 초기화는 거부한다. 원본 유지도 확인한다. input()의 문자열과 숫자 변환은 작은 보충 예제로 따로 다룬다.

### L1. 환경과 모듈을 사실대로 확인하기

요구: 장치 OS, 코드가 실제 실행되는 위치, Python 경로, import 결과, 라이브러리 버전을 구분해 기록한다. 로컬 설치 경로를 선택한 경우 Conda 생성→활성화→설치→커널 선택→확인 순서의 명령 **계획**을 작성한다. 이미 제공된 학습 런타임에서는 그 환경의 사실만 기록한다.

여섯 도구 역할: NumPy=수치 배열, pandas=라벨 표, Matplotlib=그리기 기본 도구, Seaborn=통계 시각화 인터페이스, scikit-learn=머신러닝 모델·전처리·평가 도구, TensorFlow=딥러닝 모델·수치 계산 도구. 설치하지 않은 도구도 역할 설명은 가능하다.

통과: 실제 출력이 있을 때만 실행 성공으로 기록하며 “계획”, “모의 결과”, “실제 실행”을 구분한다. Python 실행기 경로가 환경 선택과 맞는다. Android에서 지원 PC/브라우저 런타임을 택한 경우 그 경로로 동일한 개념 목표를 달성하도록 허용한다.

거부: 실제 확인하지 않은 Conda 설치 완료, 가짜 버전, import 문을 설치 명령으로 분류, Android 브라우저 실행을 기기 네이티브 설치로 기록. 시스템 전체 설정·계정 연결·호스트 변경은 이 실습의 채점 조건이 아니다.

### L2. 데이터 질문과 디지털 표현

요구: 12×10 회색조의 원시 픽셀 데이터 크기를 bit/byte로 각각 계산하고, 압축 파일 크기는 다를 수 있음을 설명한다. 디지털 음향의 시간 간격과 값 단계의 역할을 구별한다. 같은 기록에서 만들 수 있는 서로 다른 분석 질문 두 개와 필요한 변수를 적는다.

통과: 960bit=120byte, 표본화와 양자화 구별, 관측 단위·질문 연결. 1KiB=1024byte임을 명시한 보충 계산만 사용한다.

거부: 256을 픽셀 수로 쓰기, 실제 파일 헤더와 압축을 무시하고 항상 120byte라고 주장하기, 데이터 수집량만으로 인과 결론 확정하기.

### L3. 배열의 축을 설명하며 처리하기

입력은 행=세 날짜, 열=두 센서인 [[3,8],[4,6],[5,10]]이다. shape·ndim·size를 먼저 예상한다. 센서별 평균, 날짜별 합, 6 이상 값, 첫 센서의 1D·2D 선택, 날짜별 보정 [1,0,-1] 적용을 구현한다.

통과: shape (3,2), ndim 2, size 6; 센서 평균 [4,8], 날짜 합 [11,10,15], 선택값 [8,6,10], 첫 센서 shape (3,)와 (3,1); 보정 [[4,9],[4,6],[4,9]]. 각 axis를 자료 의미로 설명한다.

거부: axis 뒤바뀜, shape 검사를 생략한 평탄화, 마스크를 결과 값으로 제출, 날짜 보정의 원소를 임의 반복해 뜻을 바꿈. 두 개 이상의 다른 shape 입력에서도 검증하여 하드코딩을 배제한다.

### L4. 결합·재배열·난수 재현

2-1 실제 41쪽의 자습 목록을 설명 예제로 먼저 보충한다. a=[1,2,3], b=[4,5,6]으로 concatenate와 hstack의 1D 결과 (6,), vstack 결과 (2,3), column_stack 결과 (3,2)를 비교한다. 같은 길이의 열 (3,1) 두 개를 hstack하면 (3,2)가 됨을 확인한다. r_·c_는 같은 목표를 표현하는 인덱서 표기라는 점을 짧게 소개한다. 모든 방법을 외워야 다음 단원으로 갈 수 있게 만들지는 않는다.

통과: 각 결과의 값·shape와 무엇을 행/열로 취급했는지 설명. reshape는 원소 수 보존. 같은 seed로 새로 만든 Generator 두 개의 같은 호출 결과는 같고, 하나의 Generator를 연속 호출하면 상태가 진행함을 확인. uniform/random, standard_normal/normal, integers의 범위를 구별한다. legacy rand/randn/randint/seed는 강의 코드 읽기용 대응표로 설명한다.

거부: 모든 난수 호출이 매번 같은 값을 낸다는 주장, seed가 더 진짜 난수를 만든다는 주장, np.random.seed가 이미 만든 독립 Generator를 자동 초기화한다는 주장. 특정 난수 배열 리터럴의 암기는 요구하지 않는다.

### L5. 읽을 수 있는 네 칸 그림

한 Figure에 순서 있는 변화선, 관계 산점도, 두 집단 그룹 막대, 2×3 히트맵을 만든다. 데이터는 직접 작은 배열로 정의한다. 각 영역에 제목·축 이름·단위, 필요한 범례와 색 눈금을 둔다. figsize와 y격자를 한 번 변경하고 데이터 자체가 유지됨을 설명한다. 이어 GridSpec(2,3)으로 한 영역을 두 칸에 걸치게 배치하는 짧은 확장 실습을 한다.

통과: 실제 Figure 안의 Axes와 artist를 확인한다. 선의 x/y 일치, 산점도 점 수, 막대 수·위치·너비, heatmap 데이터 shape·colorbar 연결, 레이블 의미가 맞는다. 저장한 PNG가 열리고 내용이 해당 Figure와 맞는다. 색 눈금용 Axes는 기본 네 데이터 영역과 구별한다.

거부: 텍스트로 “그래프 저장 완료”만 출력, 빈 파일, 다른 Figure 저장, 겹친 막대를 그룹 막대로 설명, 범위가 달라 비교가 바뀌었는데 원자료가 달라졌다고 설명. 이미지 픽셀 전체의 완전 일치를 강제하지 않는다.

### L6. 분포와 상자그림의 의미

고정 자료 [2,3,4,5,6,7,30]으로 도수 히스토그램과 상자그림을 만들고 평균·중앙값·분산의 역할을 설명한다. 사분위수는 이 실습에서 NumPy 기본 linear 방식 또는 Matplotlib 기본 boxplot 결과를 기준으로 한다. 정규 표본은 새로 만들어 loc/scale의 의미, density=True의 면적, 적합 곡선의 한계를 설명한다.

통과: 중앙값 5, Q1=3.5, Q3=6.5, IQR=3, 아래·위 수염 2·7, 이상치 후보 30. 경계와 수염이 다름을 설명한다. 밀도 막대의 높이 합이 아니라 높이×폭의 합이 1임을 확인한다.

거부: 상자그림 수염을 무조건 최소·최대로 해석, 30을 자동 삭제해야 하는 오측정으로 확정, 표본 평균을 설정한 모수와 정확히 일치하도록 강제, 도수 히스토그램에 PDF 곡선을 같은 단위라며 비교.

### L7. 읽기·선택·결측·계산 열

StringIO 또는 제공된 연습 폴더의 작은 CSV를 사용한다. 이름에 쉼표가 포함된 필드는 따옴표로 감싼다. 파일 인코딩이 제공되면 UTF-8/CP949 중 그 인코딩을 명시하며 무작위로 바꾸지 않는다. head/tail·shape·index·columns로 먼저 확인한 뒤 loc/iloc, 여러 행의 리스트 선택, 행 마스크, 숫자 열의 describe/mean/std/count를 사용한다. argmax의 위치와 idxmax의 라벨은 사전 설명 후 구별한다.

통과: 한 셀·한 열·여러 행의 값과 자료형이 맞음. df.loc[['A','B']]는 여러 행이고 df.loc['A','B']는 행/열 셀이라는 차이를 설명. 결측 개수·0과 NaN의 차이, dropna 전후 유효 행 수, 명시적 재대입 fillna의 변경 여부를 확인. 계산 열은 입력 열만 지정해 만들고 원자료 변경 후 재계산한다.

거부: Series 정수 대괄호의 특정 버전 우연한 동작을 정답으로 강요, inplace=True 반환값을 df에 대입, 합계 열까지 다시 합하기, 결측을 이유 없이 0으로 대체. 표준편차 비교에서는 NumPy/pandas의 ddof를 맞춘다. 그룹 평균 후 임계값 필터는 원자료에 먼저 필터한 것과 다른 질문임을 설명한다.

### L8. 붙이기·키 결합·피벗

열 집합이 일부 다른 두 표를 concat axis=0/1, inner/outer로 비교한다. 학생 id처럼 명시적 키가 있는 표는 merge on=...으로 결합한다. how=inner/left/right/outer를 같은 키 집합으로 비교한 후 index 결합은 left_index=True/right_index=True를 명시한다. 겹치는 비키 열의 suffix를 해석한다. 중복 키가 있으면 결과 행 수가 늘어나는 예를 먼저 설명한다.

통과: 결합 방향, 반대 축 라벨, 키 교집합/합집합, 없는 값의 NaN을 구별. pivot의 index/columns/values 의미를 설명하고 중복 조합은 의미에 맞는 aggfunc로 처리. concat으로 키 매칭을 한 척하지 않는다.

거부: 키와 무관한 행 위치로 학생 정보를 연결, 중복 키를 몰래 삭제, pivot 결측을 실제 가격 0으로 해석, how=left는 항상 입력 행 수와 같다는 일반화. 다대다 결합을 설명 없이 통과시키지 않는다.

## R5. 앞 다섯 강의 종합복습: 작은 공간 이용 기록

“앞 다섯 강의”는 Week 1_1, week_1_2, week_2_1, week_2_2, week_3_1을 뜻한다. 같은 유형 문제 다섯 개를 반복하는 복습이 아니다.

### 제공 입력

아래 자료는 이 실습을 위해 새로 만든 가상 관측값이다. 실제 공간이나 사람에 대한 자료가 아니다.

~~~csv
date,room,temp,visits
2026-01-01,A,18,10
2026-01-02,A,,14
2026-01-01,B,20,8
2026-01-02,B,22,12
2026-02-01,A,21,16
2026-02-01,B,24,18
~~~

정원 표는 순서를 의도적으로 뒤집어 제공한다: room B의 capacity=30, room A의 capacity=20. 온도 단위는 섭씨, visits는 그날 방문 횟수다. visits를 고유한 사람 수나 동시 재실 인원이라고 해석하지 않는다.

### 독립 수행 요구

1. 자신이 쓰는 환경과 실행 위치, 재현 가능한 import를 기록한다. 새 실행 상태에서 처음부터 동작하게 구성한다.
2. CSV를 읽고 날짜·수치·결측·shape를 확인한다. “온도가 높은 날 방문 횟수가 어떻게 달라 보이는가?”라는 탐색 질문과 결론 한계를 적는다.
3. 날짜별 visits를 room×date 표로 재배치하고 NumPy 배열로 변환한다. 방별 합, 날짜별 평균, 기준 이상 마스크를 만들어 축 의미를 설명한다.
4. 원자료를 보존하며 온도 결측을 탐지한다. 방문 합계에는 온도가 없는 행의 14회도 포함하고 온도-방문 산점도에는 관측된 쌍만 사용한다. 임의 대체를 했다면 다른 결과와 정책을 명시한다.
5. room 키로 정원 표를 결합한다. 월별 visits 합과 방별 관측 온도 평균·유효 개수를 구한다. 월별 합계에서 40 이상인 달을 후속 필터로 고른다.
6. 월별 방문 합계 막대와 관측 온도-방문 산점도를 한 Figure에 그린다. 제목, 축 이름, 단위를 정하고 파일을 실습 폴더에 저장한다.
7. 분석 결과 두 문장, 아직 알 수 없는 점 한 문장, 잘못된 코드 하나를 발견·고친 이유 한 문장을 작성한다. AI 도움을 받았다면 도움 전 시도와 수정 이유를 분리해 스스로 설명한다.

### 참조 결과와 객관적 채점

| 평가 영역 | 통과 조건 | 거부할 대표 오답 |
|---|---|---|
| 재현·환경 (10점) | 초기 상태에서 동작, 실제 환경 경로·버전과 계획 구별 | 숨은 커널 변수 의존, 모의 Conda 성공 |
| 읽기·자료 의미 (15점) | shape (6,4), temp 결측 1, 날짜 변환, visits 의미 정확 | 결측=0, visits=고유 인원 또는 점유율 단정 |
| 배열·축 (20점) | room A/B, 날짜 오름차순 배열 [[10,14,16],[8,12,18]], 합 [40,38], 날짜 평균 [9,13,17] | 축 혼동, 순서 설명 없이 다른 표와 대응 |
| 결측·집계 (20점) | 방 온도 평균 A=19.5/B=22, 유효 개수 A=2/B=3, 월 visits 1월44/2월34, 임계값 통과 1월 | 온도 결측행을 전체 삭제해 A 방문26·1월30으로 계산 |
| 키 결합 (10점) | 원본 순서 capacity [20,20,30,30,20,30], 키 설명 | 표의 위치 순서로 붙임 |
| 시각화·저장 (15점) | 월 막대 2개 높이 [44,34], 산점도 5쌍, 레이블·단위, 실제 파일 | “생성 완료” 문자열만 제출, 빈 PNG, 6번째 결측 점 조작 |
| 해석 (10점) | 관측 경향과 인과를 구별, 자료 규모·표본 한계 언급 | 온도가 방문을 일으켰다고 확정, 모르는 관측 사실 생성 |

권장 숙달 기준은 80점 이상이며 환경 사실성·결측 의미·배열 축·키 결합의 핵심 거부 조건이 없어야 한다. 하나라도 실패하면 관련 개념 설명과 독립 실습으로 돌아가며 이미 통과한 다른 영역을 지우지 않는다. 최초 제출·힌트 후 제출·독립 재도전 결과를 구분할 수 있지만 이 문서 자체는 진도를 기록하지 않는다.

비교 검증은 출력 문자열 한 줄 대신 값·shape·행/열 라벨·결측 위치·그래프 객체를 사용한다. 부동소수점에는 적절한 허용오차를 적용하고 범주 순서는 라벨로 정렬해 비교한다. 입력값이나 room 순서를 바꾼 추가 예제로 상수 답안을 거부한다. 난수와 성능 실습에서는 특정 샘플값·고정 시간·고정 속도비를 합격 조건으로 두지 않는다.

## 검증 기록

2026-09-16에 제공된 실제 Python 라이브러리로 검증했다.

- Python 3.12.3, NumPy 2.3.5, pandas 2.3.3, Matplotlib 3.10.8, SciPy 1.16.3, Agg backend.
- JSON schema 필드, 60개 고유 id/프롬프트, 네 선택지 고유성, 정답 인덱스, 선수개념 참조, 출처 페이지 범위, 60개 시작 코드의 문법 검사 통과.
- 실행 가능한 52문항의 참조 결과·shape·타입·그래프 객체 검사 통과.
- 잘못된 broadcast/reshape/pivot 예외, 기존 total의 중복 합산, 마스크 평균과 선택값 평균, 잘못된 축을 구분하는 확인 수행.
- concatenate/vstack/hstack/column_stack 및 같은 seed의 두 Generator 재현 확인.
- R5의 방문 합계, 온도 결측·평균, 월 집계, 정원 키 결합, 그래프 artist 개수 확인.
- fig.savefig로 저장한 첫 그래프, plt.savefig로 저장한 현재 그래프, R5의 두 영역 그림을 실제 PNG로 열어 확인했다. 앞의 두 그래프가 서로 다르고 R5에는 막대 2개와 산점도 5개가 보였다.
- L3 참조 결과 및 L6의 Q1/Q3/IQR/수염·이상치 후보도 실제 연산으로 별도 확인했다.
- 환경·연구 설계 개념 8문항은 실행만으로 타당성을 평가할 수 없어 원문과 해설을 검토했다.
- 검증 스크립트와 그림은 /tmp/python-quiz-review.LJdsEg에 생성했다. 이 임시 경로는 배포 자산이 아니며 실행 앱은 이 경로에 의존하면 안 된다.
- Conda 설치, 계정 로그인, 외부 데이터 다운로드, 서버/VM/사용자 시스템 설정 변경은 수행하지 않았다. 기존 학습 런타임을 이용한 작은 인메모리 연산과 임시 그림 생성만 했다.

추가로 desktop/test_python_quiz.py에 재사용 가능한 unittest 19개를 남겼다. 의존성 없는 자료 검사 11개는 항상 실행되며 schema·중복·안정 id·선택지·정답 범위·해설·물리 페이지·선수개념·문법·대표 정답 의미를 확인한다. 선택적 실제 라이브러리 검사 8개는 제공된 .python-runtime 또는 설치된 패키지를 사용하고 의존성이 없으면 명확히 skip한다. 해당 검사는 참조 코드만 새 임시 폴더에서 실행하며 JSON의 사용자 시작 코드를 무조건 실행하지 않는다. 대표 오답 거부, 그래프 실제 데이터·저장 대상, R5의 결측행 방문 수 보존을 포함한다.

영구 테스트 실행 명령:

~~~bash
python3 -m unittest desktop.test_python_quiz -v
python3 -S -m unittest desktop.test_python_quiz.QuizDataTests -v
~~~

첫 명령은 19개 모두 통과했다. 두 번째 명령은 site-packages를 로드하지 않는 Python에서 자료 검사 11개가 추가 라이브러리 없이 통과함을 확인했다.

재현 명령(임시 검증 파일이 유지되는 동안):

~~~bash
PYTHONPATH='/home/pigeon/문서/ChatGPT/playground/desktop/.python-runtime' MPLBACKEND=Agg MPLCONFIGDIR=/tmp/python-quiz-review.LJdsEg/mplconfig OPENBLAS_NUM_THREADS=1 python3 /tmp/python-quiz-review.LJdsEg/verify_quiz.py
~~~

최종 출력 요약:

~~~text
SCHEMA: 60 unique questions, 60 compilable starters, valid source pages, valid concept references
ANSWER DISTRIBUTION: {0: 14, 1: 16, 2: 15, 3: 15}
EXECUTABLE QUESTION CHECKS: 52 passed
NEGATIVE CASES: invalid broadcast/reshape/pivot rejected; stale total and wrong axis distinguished
ADDITIONAL LABS: stacking, seeded RNG, integrated table/merge/plot checks passed
VERSIONS: 3.12.3 2.3.5 2.3.3 3.10.8
CONDA/HOST/VM/ACCOUNT OPERATIONS: not performed
~~~

## 전체 문항 색인

| 번호 | 안정 id | 개념 | 출처 |
|---:|---|---|---|
| 1 | notebook-execution-order | notebook.kernel | Week 1_1.pdf 실제 11 |
| 2 | cloud-session-storage | notebook.persistence | Week 1_1.pdf 실제 12, 14 |
| 3 | install-versus-import | environment.packages | week_1_2_handout.pdf 실제 29, 30, 34 |
| 4 | conda-project-isolation | environment.conda | 보충 |
| 5 | conda-android-platform | environment.platform | 보충 |
| 6 | python-assignment-rebind | python.assignment | 보충 |
| 7 | python-slice-exclusive-stop | python.sequences | 보충 |
| 8 | python-function-loop | python.control | 보충 |
| 9 | python-method-sort | python.objects | week_1_2_handout.pdf 실제 24, 25 |
| 10 | python-import-namespace | python.imports | week_1_2_handout.pdf 실제 26, 27, 28, 29, 30 |
| 11 | data-science-small-sample | data.science | week_1_2_handout.pdf 실제 2, 3, 7, 8, 10 |
| 12 | bigdata-three-vs | data.three_vs | week_1_2_handout.pdf 실제 4 |
| 13 | data-versus-information | data.information | week_1_2_handout.pdf 실제 11 |
| 14 | digital-sample-quantize-encode | data.digitization | week_1_2_handout.pdf 실제 12, 13 |
| 15 | image-representation-storage | data.images | week_1_2_handout.pdf 실제 14, 15, 16, 17, 18 |
| 16 | science-four-paradigms | data.paradigms | week_1_2_handout.pdf 실제 21, 22, 23 |
| 17 | package-roles | environment.library_roles | week_1_2_handout.pdf 실제 30, 31, 32, 33 |
| 18 | numpy-list-array-add | numpy.elementwise | week_2_1_handout.pdf 실제 2, 3, 4, 6 |
| 19 | numpy-dtype-memory | numpy.metadata | week_2_1_handout.pdf 실제 5, 7 |
| 20 | numpy-shape-dimensions | numpy.shape | week_2_1_handout.pdf 실제 7, 8, 9 |
| 21 | numpy-broadcast-column-offsets | numpy.broadcast | week_2_1_handout.pdf 실제 10, 11, 13 |
| 22 | numpy-broadcast-outer-grid | numpy.broadcast | week_2_1_handout.pdf 실제 12, 13 |
| 23 | numpy-broadcast-incompatible | numpy.broadcast | week_2_1_handout.pdf 실제 13, 14, 15 |
| 24 | numpy-array-constructors | numpy.creation | week_2_1_handout.pdf 실제 16 |
| 25 | numpy-range-spacing | numpy.creation | week_2_1_handout.pdf 실제 17, 18 |
| 26 | numpy-logarithmic-spacing | numpy.creation | week_2_1_handout.pdf 실제 18 |
| 27 | numpy-axis-insert-flip | numpy.axes | week_2_1_handout.pdf 실제 19, 20 |
| 28 | numpy-chained-slice | numpy.indexing | week_2_1_handout.pdf 실제 21, 22, 23 |
| 29 | numpy-index-versus-slice-rank | numpy.indexing | week_2_1_handout.pdf 실제 24, 26, 27 |
| 30 | numpy-boolean-selection | numpy.mask | week_2_1_handout.pdf 실제 25 |
| 31 | numpy-append-reshape | numpy.reshape | week_2_1_handout.pdf 실제 28, 29 |
| 32 | numpy-reduction-axis | numpy.reduction | week_2_1_handout.pdf 실제 30 |
| 33 | numpy-variance-ddof | statistics.variance | week_2_1_handout.pdf 실제 31, 32, 33 |
| 34 | numpy-vectorization-benchmark | numpy.vectorization | week_2_1_handout.pdf 실제 34, 35, 36, 37, 38, 39, 40 |
| 35 | plot-chart-question | plot.selection | week_2_2_handout.pdf 실제 5 |
| 36 | plot-input-order | plot.lines | week_2_2_handout.pdf 실제 6, 9, 10, 11 |
| 37 | plot-style-components | plot.styles | week_2_2_handout.pdf 실제 7, 8, 15 |
| 38 | plot-axis-scale-interpretation | plot.scales | week_2_2_handout.pdf 실제 11, 12 |
| 39 | plot-save-correct-figure | plot.export | 보충 |
| 40 | plot-figure-axes-layout | plot.layout | week_2_2_handout.pdf 실제 16, 17, 18, 19, 40, 41, 42 |
| 41 | plot-scatter-meaning | plot.scatter | week_2_2_handout.pdf 실제 20, 21, 22, 23 |
| 42 | plot-bar-grouping | plot.bars | week_2_2_handout.pdf 실제 24, 25 |
| 43 | plot-pie-whole | plot.pie | week_2_2_handout.pdf 실제 26 |
| 44 | plot-heatmap-colorbar | plot.heatmap | week_2_2_handout.pdf 실제 27 |
| 45 | plot-histogram-bins | plot.histogram | week_2_2_handout.pdf 실제 28, 29, 34 |
| 46 | plot-cumulative-count-proportion | plot.histogram | 보충 |
| 47 | plot-normal-density | statistics.distribution | week_2_2_handout.pdf 실제 31, 32, 33, 34, 35 |
| 48 | plot-boxplot-whisker | statistics.boxplot | week_2_2_handout.pdf 실제 36, 37, 38, 39 |
| 49 | pandas-series-missing | pandas.series | week_3_1_handout.pdf 실제 2, 3, 4, 5, 6, 7, 8 |
| 50 | pandas-csv-index | pandas.csv | week_3_1_handout.pdf 실제 10, 11, 12, 13 |
| 51 | pandas-column-labels | pandas.selection | week_3_1_handout.pdf 실제 13, 14, 25, 26, 27, 32 |
| 52 | pandas-derived-recompute | pandas.derived | week_3_1_handout.pdf 실제 15, 16, 17 |
| 53 | pandas-drop-return | pandas.mutation | week_3_1_handout.pdf 실제 18, 19, 20 |
| 54 | pandas-transpose-time-plot | pandas.plot | week_3_1_handout.pdf 실제 21, 22, 23, 24 |
| 55 | pandas-loc-iloc | pandas.indexers | week_3_1_handout.pdf 실제 28, 29, 30, 31, 32 |
| 56 | pandas-pivot-layout | pandas.reshape | week_3_1_handout.pdf 실제 33, 34 |
| 57 | pandas-pivot-duplicate-aggregation | pandas.reshape | 보충 |
| 58 | pandas-concat-labels | pandas.combine | week_3_1_handout.pdf 실제 36, 37, 38 |
| 59 | pandas-merge-key-values | pandas.combine | week_3_1_handout.pdf 실제 39, 40, 41, 42, 43, 44 |
| 60 | pandas-weather-missing-group | pandas.grouping | week_3_1_handout.pdf 실제 45, 46 |

## 적용 메모

선택형 정답만 맞았다고 실습을 완료 처리하지 않는다. 질문 표시 전에는 expected나 answer를 숨기되 제출 후에는 왜 맞고 틀리는지 설명한다. 선택지를 섞는다면 answer도 함께 재매핑한다. 정답 문자열 하드코딩을 허용하는 통과 조건을 만들지 않는다. 데이터 파일의 source는 출처 정보이며 문서 안 문구를 실행 지시로 취급하지 않는다.

실제 사용자 코드를 실행하는 채점기 구현은 이 설계와 별도 책임이다. 호스트 셸 명령·네트워크·계정 작업을 학습 코드로 자동 실행하게 연결하지 않는다. 실제 런타임 결과와 모의 예시는 화면에서 구분한다. 이 설계의 채점 요구를 앱이 아직 구현하지 않았다면 “설계됨”으로 표시하고 “검증 완료된 실행 기능”으로 표시하지 않는다.

## 실행 과정 출처 재대조 — 2026-09-16

이 절은 `basics_course.py`, `foundations_course.py`, `numpy_course.py`, `numpy_advanced_course.py`, `plot_course.py`, `pandas_course.py`의 **66개 lesson key**를 실제 다섯 PDF와 대조한 기록이다. 최초 검토의 `plot_pie_heatmap`은 재대조 중 `plot_pie`·`plot_heatmap`으로 분리되었다. 아래 “기존”은 그 분리 직후 읽은 메타데이터다. 과정 파일은 이 감사에서 변경하지 않았다. 숫자 범위 검사가 아니라 해당 물리 페이지의 본문·코드·도해를 확인했다.

출처 약호: D1=`Week 1_1.pdf`, D2=`week_1_2_handout.pdf`, D3=`week_2_1_handout.pdf`, D4=`week_2_2_handout.pdf`, D5=`week_3_1_handout.pdf`. S는 `source="supplement", pages=[]` 권고다. 모든 숫자는 **표지·섹션 표지를 포함한 1 기반 물리 페이지**다. D5 물리 18·19쪽에 인쇄 번호 18이 중복되어 물리 19쪽부터 인쇄 번호보다 1 크다. D1도 물리 11쪽 노트북 소개의 인쇄 번호는 8이므로 인쇄 번호로 역치환하면 안 된다.

“직접”은 핵심 개념/명령이 강의에 존재한다는 뜻이며 새로운 예제 수치까지 원문에 있다는 뜻이 아니다. “혼합”은 강의 핵심과 새 API·정정 설명을 분리 표시해야 한다. 단일 source 필드만 유지한다면 표의 D 출처를 핵심 개념에 붙이고 설명에 보충 범위를 명시한다. 전부가 보충인 S 행에는 관련 강의 페이지를 출처로 둔갑시키지 않는다. “자습 보충”은 강의가 필수 자습으로 **이름을 지정했지만 사용법을 강의 슬라이드에서 가르치지 않은 항목**이다. 교재 원문은 제공되지 않았으므로 D3 41쪽에 적힌 교재 페이지를 실제 읽은 근거처럼 표시하지 않는다.

### Python 기초·선수 단원

| lesson key | 기존 source/pages | 권고 source/pages | 판정과 실제 위치 |
|---|---|---|---|
| py_values | D2:24,25 | S | 보충. 24쪽에는 int/float/str 등 이름만 있으며 대입·산술·반환/출력 차이를 가르치지 않는다. 25쪽은 객체와 sort. |
| py_sequences | D2:24,25 | S | 보충. 24쪽에 list/tuple 이름만 있다. 리스트 연결 예시는 D3:3,4에 있지만 인덱스·끝 제외·튜플 불변성 수업의 근거는 아니다. |
| py_methods | D2:24,25 | D2:24,25 | 혼합. 25쪽 object.method와 list.sort 예시 직접 확인. sorted·append·sort의 None 반환은 보충. |
| py_mapping | D2:24,25 | S | 보충. dict 이름만 24쪽에 있고 키 조회·추가·KeyError 설명은 없다. |
| py_import | D2:26,27,28,29,30,34 | D2:26,27,28,29,30,34 | 직접. 사용자 모듈 26, 표준 라이브러리 27, math 28, 네 가지 import 29, 패키지 30, 설치 34. sqrt 사용 예제는 보충 응용. |
| py_kernel | D1:11,12,13,14 | D1:11 | 직접. 커널·셀·실행 순서는 11쪽. 12~14쪽은 클라우드/로컬 환경 선택이며 현재 계산 실습의 직접 근거는 아니다. 새 커널 재현성 실천은 보충. |
| py_set | D2:24,25 | S | 보충. 24쪽에 set 이름만 있고 중복 제거·교집합·차집합은 없다. |
| py_functions | D2:24,25 | S | 보충. def/인수/return 수업은 없다. D2:26에서 def를 언급하고 D3:38에서 함수 코드를 사용하지만 입문 문법 설명을 대신하지 않는다. |
| py_iteration | D2:24,25 | S | 보충. for 예시는 D3:34,38에 있으나 if/내포/원본 보존의 입문 설명은 없다. |
| py_module_file | D2:26,27,28,29,30,34 | D2:26,29,30,34 | 혼합. 파일 모듈·재사용·이름 공간·import·설치 구분 직접. 모듈 캐시와 numpy.py 이름 가림은 보충. |
| py_standard | D2:26,27,28,29,30 | D2:27,28,29 | 혼합. 라이브러리 역할은 27쪽, math 사용은 28쪽. date 차이, urlparse, random.Random 메서드의 실제 사용법은 보충. |
| py_units | D2:13,14,15,16,17,18,19,20,21 | D2:13,14,15,16,17,18 | 혼합. 디지털화 13, 벡터/비트맵 14, 픽셀 15, 8비트 회색조 16, 단위 17~18. RGB 3채널·원시 용량 계산은 응용 보충. 19의 저장량 비유·20의 모델 데이터량·21의 과학 패러다임은 현재 목표와 다르다. |

### NumPy 단원

| lesson key | 기존 source/pages | 권고 source/pages | 판정과 실제 위치 |
|---|---|---|---|
| np_elementwise | D3:3,4,6 | D3:3,4,6 | 직접. 리스트 연결과 배열 덧셈 3~4, 사칙 원소 연산 6. |
| np_shape | D3:7,8,9 | D3:7,8,9 | 직접. 속성 표 7, 축 도해 8, 세 shape 비교 9. |
| np_dtype | D3:7 | D3:7 | 혼합. dtype·itemsize와 int32의 4바이트 직접. nbytes·astype·형 변환 보장은 보충. |
| np_broadcast_scalar | D3:10,11,13 | D3:10,11,13 | 직접. 스칼라 10, 행 11, 오른쪽 축 호환 규칙 13. |
| np_broadcast_column | D3:12,13,14,15 | D3:12,13,14,15 | 직접. 외적 모양 확장과 실패 사례·해설. |
| np_creation | D3:16 | D3:16 | 직접. zeros/ones/full/eye. |
| np_ranges | D3:17,18 | D3:17,18 | 직접. arange·소수 오차 17, linspace/logspace 18. |
| np_slicing | D3:21,22,23,24,26,27 | D3:21,22,23,24,26,27 | 직접. 행 선택, 연속 대괄호, 두 축 쉼표, 축 유지/제거, 연습·해설. |
| np_mask | D3:25 | D3:25 | 혼합. 짝수 Boolean mask 직접. 복합 조건의 &/괄호/and 오류는 보충. |
| np_reshape | D3:29 | D3:29 | 혼합. reshape/-1/flatten 직접. flatten의 독립 복사와 수정 전파 비교는 보충. |
| np_reduce | D3:30,31 | D3:30 | 직접. sum/mean/min/max와 axis는 30쪽. 31쪽은 분산 정의. |
| np_statistics | D3:30,31 | D3:30,31,32,33 | 직접. min/max는 30, 분산·표준편차 31~32, **ddof=0/1 및 pandas 기본 차이는 33**. |
| np_insert | D3:17,18 | D3:19 | 정정. 17~18은 범위 생성이고 insert의 axis=0/1·원본 유지 도해는 19쪽. |
| np_flip | D3:20 | D3:20 | 혼합. 축별 flip 직접. copy·메모리 공유는 보충. |
| np_append | D3:28 | D3:28 | 직접. 축 생략 시 펼침과 축 지정. 반복 재할당 비용 설명은 보충. |
| np_concatenate | D3:35 | S | 자습 보충. 35쪽은 작업/데이터 병렬화. concatenate는 **41쪽 자습 목록**에만 있고 stack은 그 목록에도 없다. |
| np_stack_helpers | D3:35 | S | 자습 보충. vstack/hstack/r_/c_/column_stack은 **41쪽 자습 목록**에만 있다. 사용법·1차원 차이는 보충. |
| np_random_legacy | D3:36,37,38,39,40,41 | S | 자습 보충. D3:36의 rand는 타이밍 예제 입력이며 난수 API 수업은 41의 자습 지정이다. 분포 관련 실제 코드는 D4:9,20,31,32,39(rand/randn/normal/seed)에 흩어져 있다. 현재 seed+randint 단원의 세 호출 전체를 D3:36~40 수업으로 표시하지 않는다. |
| np_random_generator | D3:36,40,41 | S | 보충. 다섯 PDF에 default_rng/Generator/integers 사용법은 없다. legacy 자습 목록 41을 최신 생성기의 직접 근거로 쓰지 않는다. |
| np_memory | D3:7,21,29 | S | 보충 중심. data/strides 명칭은 **D3:7** 직접이므로 관련 페이지로 별도 표기 가능. 하지만 슬라이스 뷰·copy·shares_memory·buffer.nbytes는 강의에 없는 확장이다. 단원을 분리한다면 속성 부분만 D3:7, 메모리 관계 부분은 S. |
| np_vectorize | D3:32,33,34 | D3:34,35,36,37,38,39,40 | 혼합. 루프/배열 34, 병렬성 35, 타이밍 36~37, 예열·반복 38, cold/warm 차이 39~40. perf_counter는 time.time 예제를 보완한 API. 32~33은 분산이다. |

### Matplotlib 단원

| lesson key | 기존 source/pages | 권고 source/pages | 판정과 실제 위치 |
|---|---|---|---|
| plot_line | D4:2,3,4,7,9,15,16,17 | D4:6,9,10,11,16,17,18 | 직접. pyplot와 plot(y)는 6, 좌표·여러 선 9~10, 자동 축 11, Figure/Axes/Axis 16, 여러 영역 17~18. 2~4는 동기/도입 차트이고 15는 스타일시트다. |
| plot_style | D4:10,14 | D4:7,8,15 | 정정. 색/선/마커 축약 7~8, style.available 15. 10은 여러 함수 곡선, 14는 제목/라벨/범례. |
| plot_labels | D4:12 | D4:6,14 | 정정. xlabel/ylabel 코드 6, 제목·축·범례 구성 14. 12는 축 스케일. legend 코드 예시를 추가 연결하려면 30도 가능. |
| plot_limits | D4:11,33,37 | D4:11,12,40,41,42 | 정정. 축 범위 11~12, 인치 figsize 40~41, grid 42. 33에도 고정 축 예시가 있으나 37은 상자그림 도해다. 인치×dpi 관계는 보충. |
| plot_save | D4:13 | D4:13 | 혼합·오류 정정. fig.savefig와 이미지 형식은 13. 원문의 plt.savefig 관련 잘못된 단정은 공식 문서·실행으로 보정한 설명이며 원문 그대로가 아니다. dpi·대상 Figure 식별은 보충. |
| plot_subplots | D4:15,16,17,18,19,20 | D4:16,17,18,19 | 직접. 객체 계층 16, small multiples 17, 2×2 subplot 18, GridSpec span 19. 15는 스타일, 20은 scatter. add_gridspec은 같은 개념의 보충 표현. |
| plot_scatter | D4:5,21,22 | D4:5,20,21,22,23 | 정정. 종류 선택 5, **s/c/alpha 코드는 20**, 양의 관계 21, 약한 관계 22, 비선형 관계 23. s의 pt² 단위 설명은 보충. |
| plot_bar | D4:6,23,24 | D4:24,25 | 정정. 덮어 그린 막대 24, width와 x 이동의 그룹 막대 25. 23은 비선형 산점도다. |
| plot_pie | D4:25,26 | D4:26 | 직접. pie/labels/autopct/explode 26. 25는 그룹 막대. startangle은 보충. |
| plot_heatmap | D4:27 | D4:27 | 직접. imshow와 colorbar. |
| plot_hist | D4:28,29 | D4:28,29 | 혼합. hist와 bins 비교 직접. 경계 포함 규칙과 반환 배열 사용은 보충. |
| plot_density | D4:29,30 | D4:30,34 | 혼합·오류 정정. 누적 hist는 30, density=True 실제 코드는 **34**. 30의 코드는 개수인데 설명은 비율이라고 한 오류를 바로잡음. 누적+정규화 조합·면적 정의는 공식 문서 보충. |
| plot_normal | D4:31,32,33 | D4:31,32,33,34,35 | 정정. NumPy 정규 난수·모수 31~33, **SciPy norm.rvs 34, norm.fit/pdf 35**. 기존 범위에는 현재 실습의 핵심 SciPy 호출이 없다. 35에서 정의되지 않은 x는 보충 생성해야 한다. |
| plot_box | D4:34,35,36,37,38,39,40,41,42 | D4:36,37,38,39 | 직접. 상자·IQR 정의 36, 관측 수염/이상치 도해 37~38, boxplot 예시 39. 34~35는 정규분포, 40~42는 크기/격자. np.percentile 수치 계산 API는 보충. |

### pandas 단원

| lesson key | 기존 source/pages | 권고 source/pages | 판정과 실제 위치 |
|---|---|---|---|
| pd_series | D5:2,3,4,5 | D5:2,3,4,5,28,29,31 | 혼합. Series/NaN/index는 2~5. 현재 과제의 loc/iloc 구분은 DataFrame 예시 28~31을 Series로 확장한다. pandas 버전별 정수키 변경 설명은 보충. |
| pd_frame | D5:7,8 | D5:6,7,8,13,45 | 직접. dict→Series는 6, DataFrame 생성/축 7~8, index/columns 속성 13, shape 출력 45. 생성만 묻는다면 7~8로 충분하나 현재 세 번째 과제는 속성도 요구한다. |
| pd_csv | D5:9,10,11 | D5:10,11,12,13,45 | 혼합. CSV 규칙 10, read_csv 11, index_col 12, 읽힌 라벨 13, **CP949 45**. header=None/names는 보충 API. 9는 argmax. |
| pd_columns | D5:12,13,14,15 | D5:13,14,16,27,32 | 직접. 문자열 열 이름 13, 단일 열/tolist 14, 열 목록 16, 대괄호 선택 27·32. 12는 index_col, 15는 계산 열. |
| pd_argmax | D5:6 | D5:9 | 혼합·정정. np.argmax(Series)의 **위치** 반환과 max/mean은 9. Series.argmax·idxmax·동률 처리의 명시적 API 설명은 보충. 6은 사전으로 Series 만들기. |
| pd_computed | D5:16,17,18 | D5:15,16,17 | 직접. total 만들기 15, 입력 열 고르기 16, 이미 계산된 열 재계산 17. 18은 inplace 도해. 수정 셀의 loc 문법은 28·31에서 연결 가능. |
| pd_drop | D5:19,20,21 | D5:16,18,19,20 | 직접. 열 drop 16, inplace 그림/코드 18~19, 행 drop 20. 21은 인덱스 정체성. columns/index 키워드 표현은 원문의 axis 표현을 확장함. |
| pd_loc | D5:27,28,29 | D5:28,31,32 | 혼합·정정. loc 행/행 목록 28, 행·열 셀 31, 라벨 슬라이스/선택 비교 32. 27은 일반 대괄호, 29는 iloc. 명시적 loc 대입은 보충 응용. |
| pd_iloc | D5:25,26,30,31,32,33 | D5:25,26,29,30,31,32 | 정정. head/tail·행 슬라이스 25~26, **iloc 행 위치 29**, 두 축 30, loc 비교 31~32. 33은 pivot. |
| pd_filter | D5:34 | D5:32,46 | 혼합·정정. Boolean 행 선택은 32, 집계 후 조건 필터는 46의 응용 목록. **34는 pivot 도해**. 복합 조건의 &/괄호/and 오류는 보충. |
| pd_missing | D5:42,43,44 | D5:4,45,46 | 정정. isna 4, 날씨 누락 개수 사례 45, count/isna/dropna/fillna 목록과 재대입 주의 46. **42~44는 merge left/right/index**. subset·열별 평균 채움은 보충 구현. |
| pd_concat | D5:36,37,38 | D5:36,37,38 | 혼합. axis/join 규칙 36, outer 37, inner 38. ignore_index=True는 보충 API. |
| pd_merge | D5:39,40,41 | D5:39,41,42 | 정정. 호출/종류 39, inner 41, **left 42**. 40은 outer이므로 현재 inner/left 수업의 직접 페이지는 42로 바꾼다. outer/right 실습 추가 시 40,43도 포함한다. |
| pd_merge_detail | D5:39,40,41 | D5:39,40,44 | 혼합·정정. merge 호출 39, 동일 이름 비키 열이 둘 남는 예시 40, **left_index/right_index 44**. suffixes 사용자 지정·중복키 곱집합·validate는 보충. |
| pd_pivot | D5:35 | D5:33,34 | 혼합·정정. pivot 코드 33, 행/열/값 도해 34. **35는 pivot_table**이며 pivot의 다중 index 불가 주장은 오류다. 중복 조합 오류·다중 values는 공식 문서 보충. |
| pd_pivot_table | D5:35,46 | D5:35 | 혼합. 다중 index pivot_table 예시 35. 중복 집계의 aggfunc, fill_value 인자는 보충이다. 46은 groupby 응용이지 pivot_table 수업이 아니다. |
| pd_groupby | D5:42,46 | D5:46 | 혼합. describe/평균/표준편차/count/groupby와 numeric_only 주의는 46의 응용 항목이다. 구체적 실행 코드는 보충 구현. 42는 left merge. |
| pd_datetime | D5:45,46 | D5:45,46 | 혼합. 날짜 인덱스 데이터 45, DatetimeIndex.month/year와 월/연 groupby 항목 46. **to_datetime과 Series.dt는 원문 호출이 아닌 보충 구현**이다. |
| pd_plot | D5:22,23,24 | D5:22,23,24 | 직접. Series bar/pie 22, DataFrame plot 23, 전치해 x축 의미 변경 24. |

### 추가 필수 범위 차이와 보완 우선순위

다음은 위 여섯 실행 과정에 대한 차이다. 객관식이나 이 blueprint에 이미 존재하는 항목까지 “전체 산출물에서 빠짐”이라고 과장하지 않는다. 객체 상태 채점으로 확인하기 어려운 해석은 짧은 개념 학습 뒤 별도 질문으로 평가할 수 있다.

| 우선순위 | 실제 근거 | 현재 상태와 필요한 보완 |
|---|---|---|
| 1 | D3:38,39,40 | np_vectorize 세 과제는 모두 수치 결과만 계산한다. 예열·반복·cold/warm 구분을 실제로 수행하지 않는다. 같은 입력·동일 결과 확인 후 두 측정 경로를 기록하고, 고정 배속을 통과 조건으로 삼지 않는 실습이 필요하다. 객관식 numpy-vectorization-benchmark에는 개념이 있다. |
| 2 | D4:20 | scatter의 c에 세 번째 수치 변수를 연결하는 과제가 없다. s·alpha만 다루므로 강의의 다변량 인코딩을 완주하지 못한다. 색 배열과 colorbar가 같은 수치를 나타내는지 검사한다. |
| 3 | D5:39,40,43 | pd_merge는 inner/left만, pd_merge_detail은 suffix·중복·index만 수행한다. **outer/right의 남는 키와 NaN 위치**를 독립 과제로 추가한다. 객관식 pandas-merge-key-values는 네 종류 구분을 포함한다. |
| 4 | D5:35 | pd_pivot_table은 중복 집계를 배웠지만 강의 직접 예시인 **두 열로 만든 다중 행 인덱스**를 생성하지 않는다. index=['상품','지점'] 같은 구조를 새 데이터로 구성하고 MultiIndex의 두 레벨·값을 검사한다. pivot이 다중 index를 못 한다고 가르치지 않는다. |
| 5 | D5:46 | pd_datetime은 연도 선택 후 월별 합계를 구하지만 **groupby 결과에 임계값 필터**를 적용하는 단계가 없다. 집계 전 행 필터와 집계 후 월 필터가 서로 다른 결과를 내는 데이터로 추가한다. |
| 6 | D4:21,22,23 | 산점도 실행은 좌표 생성 중심이고 “선형 추세 없음 ≠ 관계 없음”의 U형 사례 판단이 없다. 객관식 plot-scatter-meaning과 연결해 강의 23쪽의 해석 목표를 학습한 뒤 평가한다. |
| 7 | D4:34,35 | 밀도 히스토그램과 norm.fit/pdf가 개별로 존재하지만 같은 축 위에서 **표본 분포와 적합 곡선을 함께 비교**하는 과제는 없다. x 정의·density=True·적합 모수·동일 Axes를 검사하는 통합 과제를 권한다. |
| 8 | D2:2~11,21~23 | 데이터 과학/빅데이터/3V/데이터-정보/네 과학 패러다임은 현재 실행 과정 설명에 없다. quiz_bank의 data.* 문항은 있으므로 “미학습 상태에서 바로 시험”이 되지 않도록 짧은 설명 경로를 연결한다. 역사 수치·평가 일정 암기는 요구하지 않는다. |
| 9 | D2:32,33 | **NumPy·pandas·Matplotlib·Seaborn·scikit-learn·TensorFlow의 여섯 역할** 설명이 여섯 실행 파일에는 없다. package-roles 객관식 전에 안내를 제공한다. 뒤 학기 모델 알고리즘 전체 실습은 이 범위를 넘어간다. |
| 10 | D1:11~15; D2:34 | kernel은 있으나 Colab/로컬 파일 지속성·인터프리터/환경 선택·설치와 import의 실행 위치를 모두 실습으로 다루지는 않는다. 별도 환경/플랫폼 화면과 퀴즈를 연결한다. Android의 공식 Conda 네이티브 설치를 가짜 성공 처리하지 않는다. |

보충 API를 추가하는 것은 오류가 아니다. 오류는 해당 API가 실제로 없는 PDF 페이지에서 직접 배웠다고 표시하거나, 설명 전에 그 API만 정답으로 강제하는 것이다. 과제의 출처·설명·선수 개념·채점 요구를 같은 수준으로 맞춰야 한다.
