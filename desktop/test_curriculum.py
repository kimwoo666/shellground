import unittest

from desktop.curriculum import COMBO_EXERCISES, LESSONS, normalize_command, review_pool, validate_curriculum


class CurriculumTests(unittest.TestCase):
    def test_every_declared_solution_is_accepted(self):
        self.assertEqual(validate_curriculum(), [])

    def test_whitespace_is_normalized(self):
        self.assertEqual(normalize_command("  grep   ERROR   app.log  "), "grep ERROR app.log")

    def test_review_pool_grows_with_learned_lessons(self):
        first = review_pool([LESSONS[0].key])
        all_lessons = review_pool(lesson.key for lesson in LESSONS)
        self.assertGreater(len(all_lessons), len(first))
        self.assertEqual(len(all_lessons), sum(len(lesson.practice) for lesson in LESSONS) + len(COMBO_EXERCISES))

    def test_locked_combo_is_not_in_early_pool(self):
        pool = review_pool(["pwd", "ls"])
        solutions = {exercise.solution for exercise in pool}
        self.assertNotIn("grep ERROR app.log | wc -l", solutions)


if __name__ == "__main__":
    unittest.main()
