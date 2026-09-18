import json
from pathlib import Path
import unittest
from subprocess import CompletedProcess
from unittest.mock import patch
from guest import system_lab as lab
from system_course import KEYS, make_mission
from mode_curriculum import curriculum
from learning_steps import learning_steps
from real_course_checks import make_review


class SystemCourseTests(unittest.TestCase):
    def test_new_registration_and_review_preserve_old_keys(self):
        units, reviews = curriculum('real')
        self.assertEqual(tuple(u.key for u in units[85:90]), KEYS)
        self.assertEqual(make_review(next(r for r in reviews if r.end == 90), 7251).kind, 'system_review')
        self.assertFalse(any(u.key in KEYS for u in curriculum('simulation')[0]))

    def test_different_goals_and_four_small_steps_without_hidden_final_key(self):
        units = {u.key: u for u in curriculum('real')[0]}
        for key in KEYS:
            variants = [make_mission(key, 7251, v) for v in range(3)]
            self.assertEqual(len({m.prompt for m in variants}), 3)
            self.assertEqual(len({m.solution for m in variants}), 3)
            self.assertEqual(len(learning_steps(units[key], 'real', variants[0])), 4)
            for m in variants:
                lab.validate(m.payload()); self.assertNotIn('F5', m.prompt)
                self.assertNotIn('set-time', m.solution); self.assertNotIn('date -s', m.solution)
                self.assertNotIn('ip link set', m.solution)

    def test_guest_guard_and_reserved_targets(self):
        m = make_mission('system_links', 7251).payload()
        with patch.object(lab, 'guard', side_effect=RuntimeError('not guest')):
            for action in ('prepare', 'grade'):
                with self.assertRaises(RuntimeError): getattr(lab, action)(m)
            with self.assertRaises(RuntimeError): lab.cleanup()
        m['start'] = '/tmp'
        with self.assertRaises(ValueError): lab.validate(m)
        m = make_mission('system_links', 7251).payload(); m['review']['interfaces'][0] = 'eth0'
        with self.assertRaises(ValueError): lab.validate(m)

    def test_link_formats_keep_admin_up_separate_from_operstate(self):
        brief = b'sgsi1a@if3 DOWN aa:bb:cc:dd:ee:ff <BROADCAST,MULTICAST,UP>\nsgsi1b@if2 DOWN 11:22:33:44:55:66 <BROADCAST,MULTICAST>\n'
        detailed = b'2: sgsi1a@if3: <BROADCAST,MULTICAST,UP> mtu 1500 state DOWN\n    link/ether aa:bb:cc:dd:ee:ff\n3: sgsi1b@if2: <BROADCAST,MULTICAST> mtu 1500 state DOWN\n'
        expected = {'sgsi1a': True, 'sgsi1b': False}
        self.assertEqual(lab.parse_links(brief), expected); self.assertEqual(lab.parse_links(detailed), expected)
        self.assertEqual(lab.parse_links(b'sgsi1a: flags=4163<UP,BROADCAST> mtu 1500\nsgsi1b: flags=4098<BROADCAST> mtu 1500\n', legacy=True), expected)
        self.assertIsNone(lab.parse_links(b'sgsi1a UP\n'))

    def test_address_scope_prefix_and_equivalent_ip_formats(self):
        expected = {'sgsi1a': [['inet', '192.0.2.10/24'], ['inet6', '2001:db8:1::1/64']]}
        detailed = b'2: sgsi1a@if3: <UP> mtu 1500\n    inet 192.0.2.10/24 scope global sgsi1a\n    inet6 2001:db8:1::1/64 scope global\n'
        brief = b'sgsi1a@if3 DOWN 192.0.2.10/24 2001:0db8:0001::1/64\n'
        one_line = b'2: sgsi1a    inet 192.0.2.10/24 scope global sgsi1a\n2: sgsi1a    inet6 2001:db8:1::1/64 scope global\n'
        for text in (detailed, brief, one_line): self.assertEqual(lab.parse_addresses(text), expected)
        self.assertNotEqual(lab.parse_addresses(brief.replace(b'/24', b'/16')), expected)
        self.assertIsNone(lab.parse_addresses(b'192.0.2.10/24\n'))
        self.assertIsNone(lab.parse_addresses(brief + brief))

    def test_clock_properties_are_order_independent_but_not_duplicate(self):
        self.assertEqual(lab.parse_properties(b'NTP=yes\nNTPSynchronized=no\n'), {'NTP': 'yes', 'NTPSynchronized': 'no'})
        self.assertIsNone(lab.parse_properties(b'NTP=yes\nNTP=no\n'))
        self.assertEqual(lab.utc(300), b'1970-01-01T00:05:00Z\n')
        self.assertIsNone(lab.utc(None))

    def test_live_network_snapshot_survives_json_transport(self):
        output = [dict(ifname='lo', ifindex=1, flags=['UP'], mtu=65536, address='00:00:00:00:00:00',
                       addr_info=[dict(family='inet', local='127.0.0.1', prefixlen=8)])]
        with patch.object(lab, 'run') as run:
            run.return_value.stdout = json.dumps(output).encode()
            value = lab.network(); self.assertEqual(value, json.loads(json.dumps(value)))

    def test_clock_reading_is_not_claimed_as_rtc_or_ntp_success(self):
        unit = next(u for u in curriculum('real')[0] if u.key == 'system_clock')
        self.assertIn('RTC 읽기·NTP 동기화 성공을 보장하지', unit.explanation)
        self.assertIn('실제 종료 상태', make_mission('system_clock', 7251, 1).prompt)
        self.assertIn('조회 실패', make_mission('system_clock', 7251, 2).prompt)

    def test_clock_sync_transition_is_not_a_configuration_change(self):
        initial = dict(Timezone='Etc/UTC', LocalRTC='no', NTP='yes', NTPSynchronized='no')
        current = dict(initial, NTPSynchronized='yes')
        self.assertEqual(lab.clock_settings(initial), lab.clock_settings(current))
        for recorded in (initial, current): self.assertTrue(lab.clock_report_matches(recorded, initial, current))
        self.assertFalse(lab.clock_report_matches(dict(current, NTP='no'), initial, current))
        self.assertFalse(lab.clock_report_matches(dict(current, NTPSynchronized='maybe'), initial, current))
        self.assertFalse(lab.clock_report_matches(dict(current, Extra='yes'), initial, current))
        self.assertFalse(lab.clock_report_matches(current, initial, initial))

    def test_rtc_may_differ_from_system_clock_and_failure_is_not_success(self):
        observed = CompletedProcess([], 0, b'2001-01-01 01:00:30+00:00\n', b'')
        self.assertTrue(lab.rtc_report_matches(b'2001-01-01 01:00:00+00:00\n', 0, observed, 35))
        self.assertFalse(lab.rtc_report_matches(b'2001-01-01 00:59:00+00:00\n', 0, observed, 35))
        self.assertFalse(lab.rtc_report_matches(observed.stdout, 1, observed, 35))
        self.assertFalse(lab.rtc_report_matches(observed.stdout + b'extra\n', 0, observed, 35))
        failure = CompletedProcess([], 1, b'', b'No RTC\n')
        self.assertTrue(lab.rtc_report_matches(b'No RTC\n', 1, failure, 35))
        self.assertFalse(lab.rtc_report_matches(b'No RTC\n', 0, failure, 35))

    def test_unrestricted_links_accept_legacy_but_explicit_ip_does_not(self):
        text = b'lo: flags=73<UP,LOOPBACK,RUNNING> mtu 65536\n'
        self.assertEqual(lab.parse_links(text), {'lo': True})
        self.assertIsNone(lab.parse_links(text, legacy=False))

    def test_interface_alias_and_index_are_preserved(self):
        row = dict(ifname='sgsi1a', ifindex=2, ifalias='owned', flags=['UP'], mtu=1500)
        with patch.object(lab, 'run') as run:
            run.return_value.stdout = json.dumps([row]).encode(); initial = lab.network()
            for changed in (dict(row, ifalias='changed'), dict(row, ifindex=99)):
                run.return_value.stdout = json.dumps([changed]).encode()
                self.assertNotEqual(initial, lab.network())

    def test_alias_is_read_from_link_query_not_address_query(self):
        address = dict(ifname='sgsi1a', ifindex=2, flags=['UP'], mtu=1500)
        with patch.object(lab, 'run') as run:
            run.side_effect = [CompletedProcess([], 0, json.dumps([row]).encode(), b'') for row in
                               (address, dict(address, ifalias='owned'))]
            self.assertEqual(lab.network()['sgsi1a']['alias'], 'owned')


if __name__ == '__main__': unittest.main()
