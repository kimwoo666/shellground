"""Real-backend exercise references, explicitly showing the offline registry."""
from dataclasses import replace
import re

UBUNTU = 'localhost:5000/training/ubuntu:24.04'
ALPINE = 'localhost:5000/training/alpine:latest'


def real_text(text):
    # Python's Unicode \b does not separate an ASCII tag from Korean particles
    # (e.g. ubuntu:24.04와). Use the image-reference alphabet instead, while
    # excluding already qualified references and longer/different tags.
    text = re.sub(r'(?<![\w/:-])ubuntu:24\.04(?![A-Za-z0-9_./:@-])', UBUNTU, text)
    text = re.sub(r'(?<![\w/:-])alpine:latest(?![A-Za-z0-9_./:@-])', ALPINE, text)
    text = text.replace('docker pull alpine\n', 'docker pull ' + ALPINE + '\n')
    text = text.replace('가상 저장소', '게스트 내부 교육용 저장소')
    text = text.replace('실습 아카이브는 가상 파일이며 실제 Docker와 교환하는 파일이 아닙니다.',
                        '실제 Docker 이미지 아카이브를 만듭니다. save/load는 컨테이너의 실행 중 메모리를 저장하지 않습니다.')
    text = text.replace('시뮬레이터는 준비된 가상 저장소만 사용합니다.',
                        '이 실제 모드는 게스트 내부에 준비된 교육용 패키지 저장소를 사용합니다.')
    text = text.replace('시뮬레이터는 준비된 게스트 내부 교육용 저장소만 사용합니다.',
                        '이 실제 모드는 게스트 내부 교육용 패키지 저장소를 사용합니다.')
    text = text.replace('이 실습의 URL은 프로그램 내부의 가상 다운로드 자료입니다. 실제 네트워크 요청은 하지 않습니다.',
                        '이 실습의 URL은 게스트 내부 HTTP 서버의 실제 다운로드 자료입니다. 외부 인터넷은 연결하지 않습니다.')
    return text


def adapt_real_mission(mission):
    if mission.kind in ('list', 'recursive') and mission.practice == 2 and not mission.review.get('real_course_v2'):
        from linux_course import adjust_early_mission
        return adjust_early_mission(mission)
    if not mission.kind.startswith('sim_') or mission.review.get('real_backend'):
        return mission
    return replace(mission, prompt=real_text(mission.prompt), solution=real_text(mission.solution),
                   review=dict(mission.review, real_backend=True,
                               registry={'ubuntu': UBUNTU, 'alpine': ALPINE}))
