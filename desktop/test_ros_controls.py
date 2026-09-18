import copy
import subprocess
import unittest
from guest.ros_controls_lab import player_outcome, teleop_outcome
from ros_controls_course import KEYS, make_mission
from mode_curriculum import curriculum
from learning_steps import learning_steps
from course_topics import unit_number, topic_of


def sample(rate, count, paused=True, stable=True):
    return dict(rate=rate, count=count, paused=paused, stable=stable)


def player(samples, count):
    return dict(alive=False, samples=samples, messages=[dict(topic='/turtle1/cmd_vel', x=.25 + i * .01, z=0.) for i in range(count)], extra_messages=[])


class RosControlsTests(unittest.TestCase):
    def test_graph_attribution_refuses_duplicate_names_endpoints_and_wrong_namespace(self):
        from unittest.mock import Mock
        from guest.ros_controls_lab import graph_owner
        node = Mock(); endpoint = Mock(node_name='player', node_namespace='/team', endpoint_gid=[1, 2, 3])
        node.get_publishers_info_by_topic.return_value = [endpoint]
        node.get_node_names_and_namespaces.return_value = [('player', '/team')]
        active = dict(players={'p:time': dict(name='player', namespace='/team')}, teleops={})
        self.assertEqual(graph_owner(node, '/turtle1/cmd_vel', active), (('players', 'p:time'), '010203'))
        node.get_node_names_and_namespaces.return_value *= 2
        self.assertIsNone(graph_owner(node, '/turtle1/cmd_vel', active))
        node.get_node_names_and_namespaces.return_value = [('player', '/team')]
        node.get_publishers_info_by_topic.return_value *= 2
        self.assertIsNone(graph_owner(node, '/turtle1/cmd_vel', active))
        node.get_publishers_info_by_topic.return_value = [endpoint]
        active['players']['p:time']['namespace'] = '/wrong'
        self.assertIsNone(graph_owner(node, '/turtle1/cmd_vel', active))

    def test_shared_explicit_selector_constructs_only_requested_new_case(self):
        from verify_ros_acceptance import selected_cases
        rows = selected_cases(cases=['ros_controls_pause:2'])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1]().review['ros_controls'], 'pause')
        self.assertEqual(rows[0][1]().practice, 2)

    def test_three_appended_units_twelve_steps_nine_distinct_tasks(self):
        units, reviews = curriculum('real')
        self.assertEqual(len(units), 138); self.assertEqual(len(reviews), 27)
        ros = [u for u in units if topic_of(u) == 'ROS 2']
        self.assertEqual(tuple(u.key for u in ros[-3:]), KEYS)
        for number, u in enumerate(ros[-3:], 21):
            self.assertEqual(unit_number(units, units.index(u)), number)
            missions = [make_mission(u.key, 7251, v) for v in range(3)]
            self.assertEqual(len({m.prompt for m in missions}), 3)
            self.assertEqual(len({m.solution for m in missions}), 3)
            self.assertEqual(len(learning_steps(u, 'real', missions[0])), 4)
            for m in missions:
                self.assertNotIn('F5', m.prompt)
                self.assertEqual(subprocess.run(['bash', '-n'], input=m.solution, text=True, capture_output=True).returncode, 0)

    def test_pause_requires_observed_transition_and_stable_stop_not_exit(self):
        p = player([sample(1., 0), sample(1., 1, False, False), sample(1., 2)], 2)
        self.assertTrue(player_outcome(p, 'pause', 0))
        for mutate in (lambda x: x.update(alive=True), lambda x: x['samples'].pop(1),
                       lambda x: x['samples'][-1].update(stable=False), lambda x: x['extra_messages'].append({})):
            q = copy.deepcopy(p); mutate(q); self.assertFalse(player_outcome(q, 'pause', 0))

    def test_single_steps_require_counts_payload_order_and_no_play(self):
        p = player([sample(1., i) for i in range(3)], 2)
        self.assertTrue(player_outcome(p, 'pause', 2)); self.assertFalse(player_outcome(p, 'pause', 1))
        q = copy.deepcopy(p); q['messages'].reverse(); self.assertFalse(player_outcome(q, 'pause', 2))
        q = copy.deepcopy(p); q['samples'][1]['paused'] = False; self.assertFalse(player_outcome(q, 'pause', 2))
        q = copy.deepcopy(p); q['samples'].pop(1); self.assertFalse(player_outcome(q, 'pause', 2))
        q = copy.deepcopy(p); q['messages'][0]['topic'] = '/guard/turtle1/cmd_vel'; self.assertFalse(player_outcome(q, 'pause', 2))
        q = copy.deepcopy(p); q['ambiguous'] = True; self.assertFalse(player_outcome(q, 'pause', 2))
        q = copy.deepcopy(p); q['samples'][0]['stable'] = q['samples'][1]['stable'] = False
        self.assertTrue(player_outcome(q, 'pause', 2))

    def test_rate_repair_is_ordered_within_one_player(self):
        p = player([sample(1.2, 0), sample(1.2, 1), sample(1.1, 1), sample(1., 1), sample(1., 2)], 2)
        self.assertTrue(player_outcome(p, 'rate', 1))
        for samples in (p['samples'][:2], p['samples'][2:], list(reversed(p['samples'])),
                        [sample(1.2, 0), sample(1., 0), sample(1., 1), sample(1., 2)]):
            self.assertFalse(player_outcome(player(samples, 2), 'rate', 1))

    def test_rate_does_not_scale_twist_or_accept_point_ninety_nine(self):
        p = player([sample(1., 0), sample(1.1, 0), sample(1., 0), sample(1., 1, False, False), sample(1., 2)], 2)
        self.assertTrue(player_outcome(p, 'rate', 0))
        p['samples'][2]['rate'] = .99; self.assertFalse(player_outcome(p, 'rate', 0))
        p = player([sample(1., 0), sample(1.2, 0), sample(1.2, 1)], 1)
        self.assertTrue(player_outcome(p, 'rate', 2))
        p['messages'][0]['x'] = .3; self.assertFalse(player_outcome(p, 'rate', 2))

    def test_teleop_needs_real_movement_order_and_stopped_program(self):
        s = dict(poses={'': dict(distance=.2, turn=.3, stopped=True)}, teleops={'pid:time': dict(alive=False, messages=[
            dict(topic='/turtle1/cmd_vel', x=0., z=2.), dict(topic='/turtle1/cmd_vel', x=2., z=0.)])})
        self.assertTrue(teleop_outcome(s, '', 1))
        self.assertFalse(teleop_outcome(s, '/team', 2))
        s['teleops']['pid:time']['messages'].reverse(); self.assertFalse(teleop_outcome(s, '', 1))
        s['teleops']['pid:time']['alive'] = True; self.assertFalse(teleop_outcome(s, '', 0))


if __name__ == '__main__': unittest.main()
