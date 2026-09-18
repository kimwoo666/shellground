import re
import unittest
from missions import UNITS, make_mission, lesson_text
from real_lessons import adapt_real_mission, real_text, UBUNTU, ALPINE


class RealLessonTests(unittest.TestCase):
    def test_all_legacy_docker_objectives_and_solutions_use_offline_references(self):
        from course_topics import DOCKER_KEYS
        pattern = r'(?<![\w/:-])(?:ubuntu:24\.04|alpine:latest)(?![A-Za-z0-9_./:@-])'
        for key in DOCKER_KEYS:
            for variant in (0, 1, 2):
                mission = adapt_real_mission(make_mission(key, 5131, variant))
                self.assertIsNone(re.search(pattern, mission.prompt), (key, mission.prompt))
                self.assertIsNone(re.search(pattern, mission.solution), (key, mission.solution))

    def test_korean_particles_do_not_leave_public_registry_targets(self):
        for particle in ('와', '과', '로', '를', '은', '의', '에서'):
            self.assertEqual(real_text('ubuntu:24.04' + particle), UBUNTU + particle)
            self.assertEqual(real_text('alpine:latest' + particle), ALPINE + particle)
        m = adapt_real_mission(make_mission('sim_images', 5131, 1))
        self.assertIn(UBUNTU + '와', m.prompt)
        self.assertIn(ALPINE, m.prompt)
        self.assertEqual(real_text(m.prompt), m.prompt)
        for reference in ('team/ubuntu:24.04', 'ubuntu:24.04-dev', 'ubuntu:24.041',
                          'alpine:latest-custom', 'ubuntu:24.04@sha256:abc'):
            self.assertEqual(real_text(reference), reference)

    def test_mapping_is_explicit_and_idempotent(self):
        for unit in UNITS:
            original = make_mission(unit.key, 4242)
            actual = adapt_real_mission(original)
            self.assertEqual(adapt_real_mission(actual), actual)
            self.assertEqual(real_text(real_text(unit.explanation)), real_text(unit.explanation))
            self.assertEqual(actual.kind, original.kind)
            self.assertEqual(actual.start, original.start)
        images = adapt_real_mission(make_mission('sim_images', 4242))
        self.assertIn('docker pull ' + UBUNTU, images.solution)
        self.assertIn('docker pull ' + ALPINE, images.solution)
        self.assertNotIn('localhost:5000/training/localhost:', images.solution)

    def test_mode_specific_explanation_matches_actual_examples(self):
        unit = next(u for u in UNITS if u.key == 'sim_images')
        self.assertIn(UBUNTU, lesson_text(unit, 'real'))
        self.assertNotIn(UBUNTU, lesson_text(unit))
