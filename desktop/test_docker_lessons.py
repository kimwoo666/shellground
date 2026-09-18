import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

from checkpoints import make_checkpoint
from course_topics import topic_indices, unit_number
from docker_lessons import SPECS, make_docker_mission
from engine import LabError
from missions import UNITS, lesson_text
from mode_curriculum import ADMIN_UNITS, DOCKER_UNITS, ROS_UNITS, curriculum
from real_vm import RealEngine


class DockerLessonsTests(unittest.TestCase):
    def test_stable_ids_numbering_and_real_only_coverage(self):
        real, reviews = curriculum('real')
        sim, sim_reviews = curriculum('simulation')
        self.assertTrue({u.key for u in UNITS}.issubset({u.key for u in real}))
        self.assertEqual(real[75:], ROS_UNITS)
        self.assertEqual(tuple(u for u in real if u.key in {a.key for a in ADMIN_UNITS}), ADMIN_UNITS)
        self.assertEqual(real[70:75], DOCKER_UNITS)
        self.assertEqual(len(sim), 45)
        self.assertEqual(len(sim_reviews), 9)
        self.assertFalse(any(u.key.startswith('docker_') for u in sim))
        self.assertEqual([unit_number(real, i) for i in topic_indices(real, 'Docker')], list(range(1, 16)))
        review = make_checkpoint(75, 7654)
        self.assertEqual(review.review['checkpoint'], 'docker-checkpoint-deployment')
        self.assertEqual(review.review['units'], [u.key for u in DOCKER_UNITS])
        self.assertEqual(next(c for c in reviews if c.key == 'docker-checkpoint-deployment').units, DOCKER_UNITS)

    def test_variants_are_distinct_and_examples_are_individually_typeable(self):
        for unit in DOCKER_UNITS:
            self.assertIn('직접 해볼 예시', lesson_text(unit, 'real'))
            variants = [make_docker_mission(unit.key, 7654, n) for n in range(3)]
            self.assertEqual(len({json.dumps(m.review, sort_keys=True) for m in variants}), 3)
            for m in variants + [make_checkpoint(75, 7654)]:
                self.assertNotRegex(m.prompt, r'F[1-8]|채점|힌트|버튼')
                self.assertEqual(m.review['file_goals']['keep.txt'], 'unrelated document\n')
                self.assertIn('sgd7654-keep', m.prompt)
                for line in m.solution.splitlines():
                    self.assertTrue(shlex.split(line), (m.kind, line))

    def test_old_runtime_refuses_before_resetting_current_work(self):
        engine = RealEngine()
        engine.boot = Mock()
        engine.channel = Mock()
        for key, *_ in SPECS:
            with self.assertRaises(LabError): engine.start(make_docker_mission('docker_' + key, 1234))
        engine.channel.request.assert_not_called()

    def test_bounded_probe_is_removed_even_when_command_times_out(self):
        from guest.docker_lab import DockerLab
        lab = DockerLab(Mock())
        lab.docker = Mock(side_effect=[subprocess.TimeoutExpired('docker run', 8), (0, '', '')])
        self.assertIsNone(lab.probe_image('training/slow:v1'))
        creation = lab.docker.call_args_list[0].args
        removal = lab.docker.call_args_list[1].args
        self.assertEqual(removal, ('rm', '-f', creation[2]))
        self.assertIn('--memory', creation)
        self.assertIn('--pids-limit', creation)

    def test_non_regular_report_is_not_read_as_goal_text(self):
        from guest.docker_lab import DockerLab
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertIsNone(DockerLab.read(root))
            self.assertIsNone(DockerLab.read(root / 'missing'))
            (root / 'large').write_bytes(b'x' * 1048577)
            self.assertIsNone(DockerLab.read(root / 'large'))

    def test_cleanup_preserves_baseline_resources(self):
        from guest.docker_lab import DockerLab
        lab = DockerLab(Mock())
        lab.baseline = {key: {'old-' + key} for key in ('containers', 'volumes', 'networks', 'images', 'tags')}
        current = {key: values | {'new-' + key} for key, values in lab.baseline.items()}
        lab.inventory = Mock(return_value=current)
        lab.docker = Mock(return_value=(0, '', ''))
        lab.close()
        self.assertEqual(lab.docker.call_count, 5)
        for call in lab.docker.call_args_list:
            self.assertFalse(any(str(arg).startswith('old-') for arg in call.args))
        self.assertIsNone(lab.baseline)


if __name__ == '__main__': unittest.main()
