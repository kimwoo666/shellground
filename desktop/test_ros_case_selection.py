import unittest
from verify_ros_acceptance import selected_cases


class RosCaseSelectionTests(unittest.TestCase):
    def test_exact_case_and_review_selection_does_not_run_other_variants(self):
        requested = ['ros_play:1', 'checkpoint-60']
        rows = selected_cases(cases=requested)
        self.assertEqual([key for key, _ in rows], requested)
        self.assertEqual(rows[0][1]().practice, 1)
        self.assertEqual(rows[1][1]().review['checkpoint'], 'checkpoint-60')

    def test_key_selection_preserves_all_three_variants_without_reviews(self):
        self.assertEqual([key for key, _ in selected_cases(keys=['ros_action'])], ['ros_action:0', 'ros_action:1', 'ros_action:2'])

    def test_unknown_empty_duplicate_and_mixed_selection_fail_closed(self):
        for kwargs in ({'keys': ['typo']}, {'cases': ['typo']}, {'keys': []}, {'cases': []},
                       {'cases': ['ros_play:0', 'ros_play:0']}, {'keys': ['ros_play'], 'cases': ['ros_play:0']}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): selected_cases(**kwargs)


if __name__ == '__main__': unittest.main()
