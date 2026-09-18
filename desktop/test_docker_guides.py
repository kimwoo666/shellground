import unittest
from docker_guides import GUIDES, REGISTRY_GUIDE, REPORT_GUIDE
from mode_curriculum import curriculum
from course_topics import topic_of
from missions import lesson_text, make_mission
from real_lessons import adapt_real_mission, ALPINE, UBUNTU, real_text


class DockerGuideTests(unittest.TestCase):
    def test_all_fifteen_lessons_explain_options_and_observation(self):
        units, _ = curriculum('real')
        docker = [unit for unit in units if topic_of(unit) == 'Docker']
        self.assertEqual(len(docker), 15)
        self.assertEqual(len(GUIDES), 15)
        for unit in docker:
            key = unit.key.removeprefix('sim_').removeprefix('docker_')
            self.assertIn(real_text(GUIDES[key]), unit.explanation)
            self.assertIn(unit.explanation, lesson_text(unit, 'real'))
            self.assertIn('직접 해볼 예시', lesson_text(unit, 'real'))
            self.assertTrue('결과 확인' in unit.explanation or '조사 순서' in unit.explanation)

    def test_registry_rationale_is_real_mode_only_and_explains_defaults(self):
        real = next(u for u in curriculum('real')[0] if u.key == 'sim_images')
        simulated = next(u for u in curriculum('simulation')[0] if u.key == 'sim_images')
        self.assertIn(REGISTRY_GUIDE, real.explanation)
        self.assertNotIn(REGISTRY_GUIDE, simulated.explanation)
        for text in ('왜 localhost:5000/training/', '외부 인터넷 없이', '접속 포트',
                     '이름 공간', 'Linux 파일 경로가 아니므로', 'Docker Hub', '항상 이 접두사'):
            self.assertIn(text, real.explanation)
        mission = adapt_real_mission(make_mission('sim_images', 5131, 1))
        self.assertIn(UBUNTU + '와 ' + ALPINE, mission.prompt)

    def test_guidance_is_not_injected_into_test_goals(self):
        for unit in curriculum('real')[0]:
            if topic_of(unit) == 'Docker':
                for variant in (1, 2):
                    m = make_mission(unit.key, 5131, variant)
                    self.assertNotIn('결과 확인과 흔한 실수', m.prompt)
                    self.assertNotIn('왜 localhost:5000/training/', m.prompt)

    def test_every_extra_report_objective_has_teaching_before_test(self):
        for mode in ('simulation', 'real'):
            for unit in curriculum(mode)[0]:
                if topic_of(unit) != 'Docker': continue
                m = make_mission(unit.key, 5131, 2)
                if '추가 조사:' not in m.prompt: continue
                self.assertIn(REPORT_GUIDE, unit.explanation)
                for phrase in ('docker ps -a > containers.txt', 'docker images > images.txt',
                               'cat containers.txt', 'cat images.txt', '시작 폴더', '저장한 순간'):
                    self.assertIn(phrase, lesson_text(unit, mode))
                self.assertNotIn('docker ps -a >', m.prompt)


if __name__ == '__main__': unittest.main()
