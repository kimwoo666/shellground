"""Explicit backend selection. Never silently substitute simulated execution."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExecutionMode:
    key: str
    title: str
    description: str
    available: bool


SIMULATION = ExecutionMode(
    'simulation', '시뮬레이션 모드',
    '가벼운 오프라인 연습. Linux·Docker 동작을 일부 재현합니다.\n'
    '실제 Bash·nano·Docker가 아니며 지원하지 않는 명령과 옵션이 있습니다.', True)
REAL = ExecutionMode(
    'real', '실제 Linux 모드',
    '앱 전용 Linux에서 실제 Bash·nano·Docker·ROS 2 도구를 사용합니다.\n'
    '사용자 PC의 셸·Docker 소켓·개인 폴더에 연결하지 않습니다.\n'
    '실습 환경은 앱이 시작하고 종료하며, 시작 준비 시간과 메모리가 필요합니다.', False)
MODES = {mode.key: mode for mode in (SIMULATION, REAL)}


def mode_available(mode):
    if mode == REAL.key:
        from real_vm import available
        return available()
    return mode == SIMULATION.key


def mode_progress_path(simulation_path, mode):
    """Preserve existing progress without granting real-tool proficiency."""
    if mode not in MODES:
        raise ValueError('알 수 없는 실행 모드: ' + mode)
    path = Path(simulation_path)
    return path if mode == SIMULATION.key else path.with_name(path.stem + '-real' + path.suffix)


def create_engine(mode):
    if mode not in MODES:
        raise ValueError('알 수 없는 실행 모드: ' + mode)
    if mode == REAL.key:
        from real_vm import RealEngine, runtime_info
        runtime_info()
        return RealEngine()
    from sim_engine import SimEngine
    return SimEngine()
