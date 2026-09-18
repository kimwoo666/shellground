# 시스템·네트워크·시계 조사

2026-09-18 · 실제 Linux86–90와 복습. 기존 저장 키·가상 엔진을 유지하며 새 실행파일 배포는 아직 아니다.

| 단원 | 네 소단계 범위 | 활용 문제 차이 |
| --- | --- | --- |
| 86 시스템 정보 | uname -s/-r/-m/-a, hostname, os-release | 이전 보고 백업·갱신 / 커널·배포판을 혼동한 인계 검증 |
| 87 링크 | ip link, -brief, 관리 UP와 동작 상태, ifconfig -a | 옛 형식과 새 형식 대조 / 인터페이스 하나의 상태 보고 |
| 88 주소 | dev, -4/-6, 접두 길이, DOWN 장치의 설정 주소 | IPv4·IPv6 분리 / 두 장치와 원문 인계 |
| 89 시각 | epoch, UTC, -d 조회, -r 수정 시각 | 시간대 있는 예정 시각 변환 / 수정 시각과 조사 시각 구분 |
| 90 시계 지원 | timedatectl status/show/-p, RTC, 출력·오류·종료 상태 | 실제 RTC 지원 조사 / 성공 범위를 과장하지 않는 결론 |

veth 두 개를 전용 guest 안에 실제 생성한다. 개인 PC 네트워크·계정·시계 설정은 바꾸지 않는다. 링크 복구 때 주소도 원상 복구할 수 있도록 이 두 장치의 IPv6 자동 주소 생성만 끄고 명시적 실습 주소를 배정한다. 초기 ID/별칭을 보존 검사와 정리에 사용하며 모호한 다른 장치는 삭제하지 않는다.

조회 결과와 설정 보존은 구분한다. NTP 활성과 동기화는 다르며 자동 동기화 상태 변화는 사용자 설정 변경으로 판정하지 않는다. 조사 시점의 초기/현재 상태를 허용하고 결론은 제출한 관측값과 일치해야 한다. RTC 성공 시 시스템 시계와 같다고 가정하지 않고 RTC 관측값·단조 경과시간으로 검사한다. 현재 VM의 RTC는 실제 조회 실패(종료1)였으며, 이 조사 완료를 RTC 읽기 성공으로 세지 않는다.

형식 미지정 링크 목표는 ip 상세/요약 및 ifconfig 상세를 허용한다. 형식을 지정한 활용 문제만 구분한다. IP 상세/brief/한 줄 형식의 인터페이스·주소 종류·접두 길이를 비교한다. 원본 내용/권한/mtime, 네트워크/호스트 이름/시간 설정을 확인한다. NTP 활성 환경에서는 자연스러운 시각 보정을 수동 조작으로 단정하지 않으며 모든 일시적 시각 조작을 추적하는 감사기는 아니다. 복습도 공통 미복귀 포함 최대7항목이다.

## 새 범위의 증분 증거

- `.jupyter-build/system-new.json`: 정보3변형과 잘못된 배포판 값 거부 PASS. 링크 기본 풀이 뒤 오답 복구에서 자동 IPv6 주소 잔류 발견, 전체 실패로 보존(19.67초).
- `.jupyter-build/system-network-and-remaining.json`: 링크 기본 풀이 PASS 뒤 별칭 변경이 주소 조회에 안 나오는 점 발견, 전체 실패로 보존(15.27초).
- `.jupyter-build/system-alias-and-remaining.json`: 별칭을 별도 링크 조회에서 읽도록 수정 후 영향받은 링크1개와 미실행12개, **13/13 PASS, 35.64초**, 오답/대안/정리7묶음 PASS. 앞 정보3개를 반복하지 않았다. 합계 신규16개와 오답·대안8묶음이며 전체16 재실행 증거가 아니다.
- 마지막39496 exit0, scope `system-alias-and-remaining-20260918`, invocation `6943ca09fe75458a8058268561e61593`. 소스 해시 전후 일치, VM 종료·임시디스크 제거 true. CPU60%/nice15/검사 동안만 절전 방지, 관측43–54°C, 종료 후40–41°C.
- 새 계약8+등록/영향3 PASS 뒤 감사 수정4개 및 링크 출력 차이/JSON 전송2개만 PASS. NTP 자동 변화·RTC 시계 차이는 단위 검사이며 실제 동기화·RTC 성공 증거는 아니다.

## 근거

사용자 appendix 인쇄16–17쪽을 대조했다. PDF/본문은 재배포하지 않는다. [uname](https://manpages.debian.org/bookworm/coreutils/uname.1.en.html), [ip-address](https://manpages.debian.org/bookworm/iproute2/ip-address.8.en.html), [date](https://manpages.debian.org/bookworm/coreutils/date.1.en.html), [timedatectl](https://manpages.debian.org/bookworm/systemd/timedatectl.1.en.html), [hwclock](https://manpages.debian.org/bookworm/util-linux-extra/hwclock.8.en.html)의 명령 의미를 따른다.
