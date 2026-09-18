"""Pure curriculum regressions; never start ROS, a terminal, or a guest.

The preservation hashes snapshot complete pre-change payloads, not acceptable
learner commands. They protect the explicitly unchanged examples, application 2,
and reviews. Actual ROS outcome checks remain the guest's responsibility.
"""
import hashlib
import json
from pathlib import PurePosixPath
import unittest

from missions import Unit
from ros_lessons import SPECS, make_ros_mission, units


KEYS = (
    'env', 'overlay', 'run', 'nodes', 'launch', 'topics', 'interface', 'echo',
    'once', 'rate', 'params', 'set', 'dump', 'load', 'record', 'baginfo',
    'play', 'domain', 'service', 'action',
)
SEEDS = (1234, 4242, 9876)
COMBINATIONS = {
    'overlay': ('env', 'overlay'), 'run': ('env', 'run'),
    'launch': ('overlay', 'launch'), 'topics': ('nodes', 'topics'),
    'interface': ('topics', 'interface'), 'echo': ('topics', 'echo'),
    'once': ('interface', 'once'), 'rate': ('interface', 'rate'),
    'set': ('set', 'params'), 'dump': ('set', 'dump'),
    'load': ('load', 'params'), 'record': ('dump', 'record'),
    'play': ('baginfo', 'play'), 'domain': ('env', 'domain'),
    'service': ('params', 'service'), 'action': ('service', 'action'),
}
REPORT_FILES = {
    'env': {'distro.txt', 'version.txt'},
    'nodes': {'nodes.txt', 'node-info.txt'},
    'params': {'params.txt', 'description.txt', 'value.txt'},
    'baginfo': {'bag-info.txt'},
}


def digest(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()


def mission(key, variant=1, seed=4242):
    return make_ros_mission('ros_' + key, seed, variant)


def preservation_payload(m):
    """Normalize the separately documented record/play timing corrections.

    Preserve old goals/fixtures/numbering; the old deadlocking reference is
    comparison data, never a command sent to a learner or verification VM.
    """
    payload=m.payload()
    if 'play' in payload['review']['ros']:
        payload['prompt']=payload['prompt'].replace(' (준비된 기록의 이동 메시지 8개 수신)','')
        payload['solution']=payload['solution'].replace('sample_bag --delay 2 --topics','sample_bag --topics')
    if 'record' in payload['review']['ros']:
        text=payload['solution'].replace('기록을 시작하고 pose 구독 로그를 확인합니다.',
                                       '기록을 시작하고 두 토픽의 구독 로그를 확인합니다.')
        text=text.replace('환경 활성화 후 이동 메시지를 계속 발행합니다.',
                          '환경 활성화 후 이동 메시지를 발행합니다.')
        text=text.replace('ros2 topic pub --rate 2','ros2 topic pub --once')
        text=text.replace('# 터미널 A의 cmd_vel 구독 로그를 확인한 뒤 몇 개 더 발행합니다.\n# 터미널 B에서 Ctrl+C로 발행을 중단합니다.\n','')
        payload['solution']=text
    return payload


class RosApplicationTests(unittest.TestCase):
    def test_original_twenty_units_order_levels_and_descriptions_preserved(self):
        self.assertEqual(tuple(row[0] for row in SPECS), KEYS)
        course = units(Unit)
        self.assertEqual(tuple(unit.key for unit in course), tuple('ros_' + key for key in KEYS))
        self.assertEqual(tuple(unit.level for unit in course), (7,) * 10 + (8,) * 10)
        self.assertEqual(digest(SPECS),
                         '335753e3d245d06c92d08dd34585a2b93a10c2f7115f3a5578f69b2e39212578')

    def test_complete_example_payloads_preserved(self):
        payloads = [preservation_payload(mission(key, 0, seed)) for seed in SEEDS for key in KEYS]
        self.assertEqual(digest(payloads),
                         '5515c26b75476c2a7a149523f0272b93a514f7bc7b6c354c86bf73425bdad9dc')

    def test_complete_application_two_and_handoff_payloads_preserved(self):
        payloads = [preservation_payload(mission(key, 2, seed)) for seed in SEEDS for key in KEYS]
        self.assertEqual(digest(payloads),
                         '30d95902435b5928f90cde55acb3264e79f42ed96ee7d9e0444d76d6e9583c73')

    def test_all_review_payloads_preserved(self):
        payloads = [preservation_payload(mission('review' + str(end), variant, seed))
                    for seed in SEEDS for end in (45, 50, 55, 60)
                    for variant in (0, 1, 2)]
        self.assertEqual(digest(payloads),
                         'ece33f0b555a41cc314163b4569cb74a822ea72adf38bb0a1c5f93b4c05bd8b8')

    def test_each_application_has_different_goal_and_grading_or_fixture_metadata(self):
        for seed in SEEDS:
            for key in KEYS:
                with self.subTest(key=key, seed=seed):
                    example, application = mission(key, 0, seed), mission(key, 1, seed)
                    self.assertNotEqual(application.prompt, example.prompt)
                    self.assertNotEqual(application.review, example.review)
                    self.assertEqual(application.kind, example.kind)
                    self.assertEqual(application.start, example.start)
                    self.assertEqual(application.practice, 1)
                    self.assertEqual(application.review['handoff'], '')
                    self.assertNotIn('F5', application.prompt)
                    # Targets and deliberately stale text belong in a goal;
                    # executable answer strings do not.
                    for answer in ('source /opt/ros/', 'ros2 ', 'printenv ', 'printf ', 'echo '):
                        self.assertNotIn(answer, application.prompt)

    def test_every_unit_has_exactly_one_application_design(self):
        self.assertFalse(set(COMBINATIONS) & set(REPORT_FILES))
        self.assertEqual(set(COMBINATIONS) | set(REPORT_FILES), set(KEYS))
        self.assertEqual(len(COMBINATIONS), 16)
        self.assertEqual(len(REPORT_FILES), 4)

    def test_combinations_add_exactly_one_previously_taught_component(self):
        for key, expected in COMBINATIONS.items():
            with self.subTest(key=key):
                actual = mission(key)
                self.assertEqual(tuple(actual.review['ros']), expected)
                self.assertEqual(len(set(expected)), 2)
                self.assertEqual(expected.count(key), 1)
                earlier = next(component for component in expected if component != key)
                self.assertLess(KEYS.index(earlier), KEYS.index(key))
                self.assertNotIn('stale_reports', actual.review)
                # Both graded objectives are disclosed, including filenames
                # and final values; no unseen third component is introduced.
                for component in expected:
                    self.assertIn(mission(component, 0).prompt, actual.prompt)

    def test_reference_solutions_only_compose_existing_taught_commands(self):
        for key, expected in COMBINATIONS.items():
            with self.subTest(key=key):
                self.assertEqual(mission(key).solution,
                                 '\n\n'.join(mission(component, 0).solution for component in expected))
        for key in REPORT_FILES:
            with self.subTest(stale=key):
                self.assertEqual(mission(key).solution, mission(key, 0).solution)

    def test_stale_reports_are_visible_and_scoped_to_the_current_folder(self):
        for key, expected_names in REPORT_FILES.items():
            with self.subTest(key=key):
                application = mission(key)
                reports = application.review['stale_reports']
                self.assertEqual(application.review['ros'], [key])
                self.assertEqual(set(reports), expected_names)
                self.assertIn(mission(key, 0).prompt, application.prompt)
                self.assertIn('실제 조회 결과', application.prompt)
                self.assertIn('틀린 보고서에 맞추려고', application.prompt)
                for name, wrong_content in reports.items():
                    path = PurePosixPath(name)
                    self.assertFalse(path.is_absolute())
                    self.assertEqual(path.name, name)
                    self.assertTrue(wrong_content.endswith('\n'))
                    self.assertIn(name, application.prompt)
                    self.assertIn(wrong_content.rstrip('\n'), application.prompt)
                # No fixture metadata leaks into the unchanged variants.
                for variant in (0, 2):
                    self.assertNotIn('stale_reports', mission(key, variant).review)
        self.assertEqual(mission('env').review['stale_reports'],
                         {'distro.txt': 'foxy\n', 'version.txt': '1\n'})

    def test_fixture_metadata_does_not_leak_between_missions(self):
        first = mission('env')
        first.review['stale_reports']['distro.txt'] = 'changed only in this payload\n'
        self.assertEqual(mission('env').review['stale_reports']['distro.txt'], 'foxy\n')

    def test_state_changes_precede_current_value_reports(self):
        for key, change in (('set', 'ros2 param set /turtlesim background_b 80'),
                            ('load', 'ros2 param load /turtlesim restore.yaml')):
            with self.subTest(key=key):
                solution = mission(key).solution
                self.assertLess(solution.index(change),
                                solution.index('ros2 param get /turtlesim background_r > value.txt'))
        self.assertLess(mission('dump').solution.index('ros2 param set /turtlesim background_b 80'),
                        mission('dump').solution.index('ros2 param dump /turtlesim > turtle.yaml'))
        self.assertLess(mission('record').solution.index('ros2 param dump /turtlesim > turtle.yaml'),
                        mission('record').solution.index('ros2 bag record'))

    def test_final_parameter_and_node_conditions_do_not_conflict(self):
        for key in KEYS:
            with self.subTest(key=key):
                components = set(mission(key).review['ros'])
                # load requires r=120,b=90; set/dump require r=150.
                if 'load' in components:
                    self.assertFalse(components & {'set', 'dump'})
                # Domain exercise intentionally runs a renamed node, not the
                # default /turtlesim required by these other components.
                if 'domain' in components:
                    self.assertEqual(components, {'env', 'domain'})
                    self.assertEqual(mission(key).review['domain'], 42)
                else:
                    self.assertEqual(mission(key).review['domain'], 0)
        # Blocking node starters are last: report creation remains reachable
        # without stopping a node that the goal asks to keep running.
        for key in ('run', 'launch', 'domain'):
            self.assertEqual(mission(key).review['ros'][-1], key)
        # Creating helper does not rotate it: the action still targets turtle1.
        self.assertEqual(mission('action').review['ros'], ['service', 'action'])
        self.assertIn('/turtle1/rotate_absolute', mission('action').solution)


if __name__ == '__main__':
    unittest.main()
