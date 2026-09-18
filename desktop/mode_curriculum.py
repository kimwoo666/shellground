"""Mode-specific execution coverage, separate from the preserved legacy course."""
from missions import UNITS, Unit
from checkpoints import CHECKPOINTS, Checkpoint
from ros_lessons import units
from dataclasses import replace
from real_lessons import real_text
from admin_lessons import units as admin_units
from docker_lessons import units as docker_units
from docker_guides import REGISTRY_GUIDE
from functools import lru_cache
from ros_controls_course import units as ros_control_units

ROS_UNITS = units(Unit) + ros_control_units(Unit)
ADMIN_UNITS = admin_units(Unit)
DOCKER_UNITS = docker_units(Unit)


class DockerCheckpoint(Checkpoint):
    @property
    def units(self): return DOCKER_UNITS

    @property
    def key(self): return 'docker-checkpoint-deployment'


class AdminCheckpoint(Checkpoint):
    @property
    def units(self): return ADMIN_UNITS

    @property
    def key(self): return 'admin-checkpoint-accounts'


def course_start(mode, index):
    from course_topics import topic_indices, topic_of
    course, _ = curriculum(mode)
    return topic_indices(course, topic_of(course[index]))[0]


class RosCheckpoint(Checkpoint):
    @property
    def units(self):
        return ROS_UNITS[self.end - 45:self.end - 40]


ROS_CHECKPOINTS = tuple(RosCheckpoint(end, title, 'ros_review' + str(end)) for end, title in (
    (45, '환경과 다중 노드 실행'), (50, '메시지 조사와 주기적 발행'),
    (55, '설정 보관과 메시지 기록'), (60, '기록 재생과 서비스·액션')))


@lru_cache(maxsize=2)
def curriculum(mode):
    # Simulation ROS execution is still in development. Do not offer a course
    # there whose commands are not implemented, or copy real-mode completion.
    if mode == 'real':
        real_units = tuple(replace(u, explanation=real_text(u.explanation) +
                           ('\n\n' + REGISTRY_GUIDE if u.key == 'sim_images' else '')) for u in UNITS)
        from linux_course import units as linux_units
        from course_topics import topic_of
        from real_course_checks import checkpoints
        linux = linux_units(Unit, real_units + ADMIN_UNITS)
        from apt_course import units as apt_units
        linux += apt_units(Unit)
        from auth_course import units as auth_units
        linux += auth_units(Unit)
        from shell_course import units as shell_units
        linux += shell_units(Unit)
        from process_course import units as process_units
        linux += process_units(Unit)
        from io_course import units as io_units
        linux += io_units(Unit)
        from system_course import units as system_units
        linux += system_units(Unit)
        docker = tuple(u for u in real_units if topic_of(u) == 'Docker') + DOCKER_UNITS
        from docker_sessions_course import units as docker_session_units
        docker += docker_session_units(Unit)
        from docker_runtime_course import units as docker_runtime_units
        docker += docker_runtime_units(Unit)
        return linux + docker + ROS_UNITS, checkpoints(linux, docker, ROS_UNITS)
    return UNITS + ADMIN_UNITS, CHECKPOINTS + (AdminCheckpoint(45, '계정 생성과 안전한 파일 인계', 'admin_review'),)
