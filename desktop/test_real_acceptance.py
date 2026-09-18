import unittest
from real_acceptance import expected_cases,validate
from verify_real_course import fingerprint


class AcceptanceGateTests(unittest.TestCase):
    def test_registered_counts_and_stale_or_partial_proof(self):
        self.assertEqual(len(expected_cases()),368)
        self.assertEqual(len(expected_cases(True)),73)
        for ros in (False,True):
            expected=sorted(expected_cases(ros))
            report=dict(state='complete',source_fingerprint=fingerprint(),expected=expected,
                        passed={key:{} for key in expected},failures={},vm_stopped=True,overlay_removed=True,
                        negative=['unfiltered_bag_playback_rejected','wrong_service_orientation_repaired',
                                  'stale_parameter_report_repaired'])
            validate(report,ros)
            for changes in ({'state':'failed'},{'source_fingerprint':'old'},{'vm_stopped':False},
                            {'overlay_removed':False},{'passed':{}},{'expected':expected[:-1]}):
                with self.subTest(ros=ros,changes=changes),self.assertRaises(RuntimeError):
                    validate(dict(report,**changes),ros)


if __name__=='__main__':unittest.main()
