import unittest
from docker_runtime_course import KEYS, make_mission, launcher_lines
from guest.docker_runtime_lab import cpus, quota_matches, valid_stats, safe_security, output_snapshot
from mode_curriculum import curriculum
from course_topics import unit_number, topic_of
from learning_steps import learning_steps


class DockerRuntimeTests(unittest.TestCase):
    def test_new_five_units_variants_microsteps_and_review(self):
        units, reviews = curriculum('real'); index = {u.key: i for i, u in enumerate(units)}
        for n, key in enumerate(KEYS, 21):
            unit = units[index[key]]
            self.assertEqual(unit_number(units, index[key]), n)
            self.assertEqual(topic_of(unit), 'Docker')
            variants = [make_mission(key, 7251, v) for v in range(3)]
            self.assertEqual(len({m.prompt for m in variants}), 3)
            self.assertEqual(len({m.solution for m in variants}), 3)
            steps = learning_steps(unit, 'real', variants[0])
            self.assertEqual(len(steps), 5 if key.endswith('safe_launcher') else 4)
            for m in variants: self.assertNotIn('F5', m.prompt)
        review = next(r for r in reviews if r.key == 'docker-checkpoint-runtime')
        self.assertEqual(tuple(u.key for u in review.units), KEYS)
        self.assertFalse(set(KEYS) & {u.key for u in curriculum('simulation')[0]})

    def test_equivalent_cgroup_values_and_invalid_values(self):
        self.assertEqual(cpus('0-2,4'), {0, 1, 2, 4})
        self.assertEqual(cpus('0,1,2,4'), cpus('0-2,4'))
        for value in ('', '-1', '4-1', '0-999999', 'a'):
            self.assertIsNone(cpus(value))
        self.assertTrue(quota_matches('25000 50000', .5))
        self.assertTrue(quota_matches('max 100000', None))
        for value in ('max 100000', '50000 0', '1 100000', 'no'):
            self.assertFalse(quota_matches(value, .5))

    def test_stats_identity_and_configured_limit_not_fresh_usage_equality(self):
        header = 'CONTAINER ID   NAME   CPU %   MEM USAGE / LIMIT   MEM %   NET I/O   BLOCK I/O   PIDS\n'
        line = 'abcdef123456   service   0.00%   512KiB / 32MiB   1.56%   0B / 0B   0B / 0B   1\n'
        self.assertTrue(valid_stats(header + line, 'service', 'abcdef123456789', 33554432))
        self.assertTrue(valid_stats(header + line.replace('512KiB', '1MiB'), 'service', 'abcdef123456789', 33554432))
        for bad in (line.replace('32MiB', '512KiB'), line.replace('service', 'other'), line.replace('abcdef123456', 'ffffffffffff'), line.replace('32MiB', 'unknown')):
            self.assertFalse(valid_stats(header + bad, 'service', 'abcdef123456789', 33554432))

    def test_new_shell_syntax_and_no_load_generator(self):
        import subprocess
        for key in (*KEYS, 'docker_runtime_review'):
            for v in range(3 if key in KEYS else 1):
                m = make_mission(key, 7251, v)
                result = subprocess.run(['bash', '-n'], input=m.solution, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn('fio ', m.solution); self.assertNotIn('dd if=', m.solution)
        result = subprocess.run(['sh', '-n'], input='\n'.join(launcher_lines()), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_added_audit_boundaries(self):
        import tempfile
        from pathlib import Path
        self.assertTrue(safe_security(['no-new-privileges=true', 'apparmor=docker-default']))
        self.assertFalse(safe_security(['no-new-privileges', 'seccomp=unconfined']))
        self.assertFalse(safe_security(['no-new-privileges=false']))
        self.assertFalse(safe_security(['apparmor=docker-default']))
        header = 'CONTAINER ID   NAME   CPU %   MEM USAGE / LIMIT   MEM %   NET I/O   BLOCK I/O   PIDS\n'
        line = 'abcdef123456   service   0.00%   512KiB / 32MiB   1.56%   0B / 0B   0B / 0B   1\n'
        for bad in (line.replace('0.00%', 'inf%'), line.replace('0B / 0B', 'garbage'), line.replace('0.00%', 'nan%')):
            self.assertFalse(valid_stats(header + bad, 'service', 'abcdef123456789', 33554432))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder); (path / 'result.txt').write_text('same'); (path / 'uid.txt').write_text('1100\n')
            before = output_snapshot(path); (path / 'uid.txt').unlink()
            self.assertNotEqual(before, output_snapshot(path))


if __name__ == '__main__': unittest.main()
