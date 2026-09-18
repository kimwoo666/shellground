# 기존 통과를 반복하지 않는 배포 전 검증

최신2026-09-18: `.jupyter-build/incremental-course-manifest-441.json`은 ROS 제어9개 current+기존432개 reviewed-carry로 등록441개를 정확히 덮는다. 원432manifest/원보고서를 보존하며 `.jupyter-build/course-carry-review-441.md`에 좁은 위임/등록 변경을 기록했다. 새 빌드에는 이 파일을 `--course-manifest`로 명시한다. 이는 모든 문제를 다시 실행하는 요청이 아니다.

`incremental_acceptance.py`는 새/변경된 문제의 실제 증거와 검토된 과거 증거를 묶는 게이트다. `real_acceptance.validate_directory`는 `incremental-course-manifest.json`이 있으면 이 경로를 사용한다. 검사가 실패하면 옛 전수 보고서로 우회하지 않는다. manifest가 없을 때만 기존 전수 증거 검증을 유지한다. 어느 경로도 자동으로 전 과정을 실행하지 않는다.

## 승인 조건

- 현재 등록 문제·복습 ID 모두에 선택한 증거가 정확히 하나 있어야 한다. 단원별 검증기의 복습 별칭은 현재 등록된 복습으로만 해석한다. 모호한 이름은 거부한다.
- 원 보고서 파일의 SHA-256, 원래 소스 해시/지문, 명시적인 PASS ID, VM/임시 디스크 정리를 확인한다. 원 보고서를 새 소스 지문으로 덮어쓰지 않는다.
- `current`는 보고서에 기록된 소스가 현재와 같아야 한다. `reviewed-carry`는 변경 영향 검토와 구체적인 재사용 이유가 있어야 하며, 다시 실행했다고 세지 않는다.
- 뒤쪽에서 실패/중단한 실행의 앞선 PASS는 별도의 부분 재사용 설명이 있어야 한다. 실패한 사례는 포함할 수 없다. 실행 중 기록은 인정하지 않는다.
- manifest는 전체 관련 소스 파일 목록/해시와 변경 검토 문서의 해시를 묶는다. 이후 파일 추가·변경 또는 증거/검토문서 변경 시 승인되지 않는다. 명시한 `requires_fresh` 사례는 과거 증거로 충족할 수 없다.
- ROS 오답/복구의 필수 증거도 확인한다. 파일 경로 이탈·외부로 향하는 링크·중복 ID·누락을 거부한다.

이것은 **검토 기록을 엄격히 묶는 장치**이지, 코드의 의미가 같음을 자동 증명하는 도구가 아니다. 변경 영향 분석의 책임은 검토 문서에 남긴다. 등록 문제의 커버리지는 아직 등록되지 않은 강의 내용, 배포 실행파일, 다른 OS의 성공을 증명하지 않는다.

## 읽기 전용 재고 조사

`python incremental_acceptance.py --inventory 보고서1.json 보고서2.json`은 관찰된 PASS와 빠진 ID를 보여 준다. 일부 실패 보고서도 후보로 보이므로 출력은 항상 `accepted: false`이다. 이것을 곧바로 배포 manifest로 생성하지 않는다.

새 게이트13검사는 VM 없이0.031초에 통과했다. 전체 사례 재실행 없이 source/evidence/문서 변조, 부분 증거, 미완료 정리, 잘못된 경로, 오래된 증거의 current 위장, 변경 사례의 carry 우회를 검사했다.

## 유실된 보고서의 복구

기존 ROS 보고서 경로가 후속 실행에 재사용되어 앞선49개 PASS가 파일에서 사라져 있었다. `recover_ros_evidence.py`는 이 작업의 **완료된 터미널 이벤트47798/ordinal21653**의 정확한 PASS 줄과 종료 요약을 읽어 `.jupyter-build/ros-47798-recovered.json`에 보관했다. 원 지문 `262e1870…`, 실행 당시 실패 상태(ros_play:1),49/64,정리true와 이벤트 줄 해시를 유지한다. 현재 실행으로 표시하거나 실패를 성공으로 바꾸지 않았다. 개인 대화 전체는 복사하지 않고 해당 실행 발췌만 남긴다.

ROS 검증기는 이제 기존 보고서 파일을 덮어쓰지 않고 정확한 `--cases` 선택(복습 포함)을 지원한다. 새 선택 계약3개 PASS. 이에 따라 기존49개를 반복하지 않고 미검증10개+변경된play3개만 선택했다. 해당 실제 결과는 별도 보고서에 기록하며 이 문서의 도구 검사 통과로 대신하지 않는다.

build.py의 기본 검사는 이제 `--verification incremental`이다. 새 바이너리의 guest 자료/교육 카탈로그 무결성, 실제 bundled 과학 라이브러리 worker, 단일 창/키 입력/저장·종료와 실제 Conda/Jupyter 각1개 경로만 확인한다. 이전 전체 과정을 반복하는 검사는 명시적 `--verification full`에서만 실행한다. `release-bundle-manifest.json`과 보고서는 기존 파일을 조용히 덮어쓰지 않는다. 새 정책4정적 검사 PASS0.029초이며 **새 frozen 실행파일 검사는 아직 하지 않았다**. 게이트/정책 검사만으로 배포가 완료된 것은 아니다.

현재 Linux85/Docker15/ROS20 등록384사례에 대해 `.jupyter-build/incremental-course-manifest.json`을 작성하고 게이트를 통과했다. 현재 기록 소스와 일치하는IO16+ROS13=29개, 변경 영향 검토 후 재사용355개이며 모든 원보고서는 유지한다. 검토 문서는 `course-carry-review.md`다. 이 자료는 새 과정이나 관련 소스 변경 시 다시 승인되지 않는다. 추가ROS13개는210.31초 PASS/정리true이고, 복구 도구3검사와 변경 검토 누락 방지1검사도0.002초 PASS다.

## 416사례판과 저장 공간

후속432판: Docker21–25 새16문제225.8초·오답9묶음 실제 PASS를 `.jupyter-build/incremental-course-manifest-432.json`에 추가했다. **현재16+검토 재사용416, 오답72개 ID**이며 원384/416판은 그대로다. 빌드에는 이 새 파일을 `--course-manifest`로 지정한다. 상세 변경 검토는 `course-carry-review-432.md`다. 새 배포 실행파일의 실제 검증은 아직 별도다.

위384판은 과거 스냅샷으로 보존했다. 현재 Linux90/Docker20/ROS20은 `.jupyter-build/incremental-course-manifest-416.json`으로 **416=현재16+검토 재사용400, 오답/대안63개 ID**를 연결해 PASS했다. `course-carry-review-416.md`는 SYSTEM/새 Docker의 변경 영향과 초기 실패 tail 제외를 설명한다. 전체416개를 다시 실행한 결과가 아니다. 새 과정 추가 시 이 스냅샷도 다시 검토해야 한다.

build.py에 `--course-manifest .jupyter-build/incremental-course-manifest-416.json`을 명시하면 이전 기본384파일을 덮어쓰지 않고 해당 버전을 검증한다. Jupyter 자체 소스/UI 증거 게이트는 그대로 유지한다.

디스크 여유가 작은 로컬 개발 빌드는 `--link-runtime`을 명시할 수 있다. 같은 파일시스템의 **불변 런타임 자산만** 하드링크하며 개인 진도/쓰기 overlay는 포함하지 않는다. 원본을 제자리 수정하면 두 경로에 모두 영향을 주므로 교체는 원자적 파일 교체만 허용한다. 다른 파일시스템에서 실패하면 대용량 복사로 자동 대체하지 않는다. 일반 배포 복사의 기본 동작은 그대로다. 신규 링크/원자적 교체/실패 보존2검사 PASS0.026초. 실제 대용량 팩을 이번에 재복사하거나 연결하지 않았다.
