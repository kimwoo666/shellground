"""Background startup ownership and exercise reset; no real VM required."""
import threading
import unittest
from unittest.mock import Mock

from real_vm import RealEngine


class PrewarmTests(unittest.TestCase):
    def test_startup_is_nonblocking_and_does_not_prepare_a_lesson(self):
        engine = RealEngine()
        entered, release = threading.Event(), threading.Event()
        engine.channel = Mock()
        engine.channel.request.return_value = {'code': 0}
        def boot():
            entered.set()
            if not release.wait(3): raise RuntimeError('test did not release boot')
        engine.boot = Mock(side_effect=boot)
        try:
            engine.prewarm()
            self.assertTrue(entered.wait(2))
            engine.prewarm()
            self.assertTrue(engine.warmup_thread.is_alive())
            self.assertFalse(engine._practice_active)
            release.set()
            engine.warmup_thread.join(3)
            self.assertFalse(engine.warmup_thread.is_alive())
            engine.boot.assert_called_once()
            self.assertIsNone(engine.warmup_error)
            engine.channel.request.assert_called_once()
            args = engine.channel.request.call_args
            self.assertEqual(args.args, ('exec',))
            self.assertIn('docker.service', args.kwargs['argv'])
            self.assertFalse(engine._practice_active)
        finally:
            release.set()
            engine.close()

    def test_exit_cancels_a_running_warmup_and_prevents_late_restart(self):
        engine = RealEngine()
        entered = threading.Event()
        def boot():
            entered.set()
            if not engine.cancelled.wait(3): raise RuntimeError('cancellation missing')
            raise RuntimeError('cancelled')
        engine.boot = Mock(side_effect=boot)
        engine.prewarm()
        self.assertTrue(entered.wait(2))
        engine.cancel_pending()
        engine.close()
        engine.prewarm()
        self.assertFalse(engine.warmup_thread.is_alive())
        engine.boot.assert_called_once()
        self.assertEqual(engine.warmup_error, 'cancelled')

    def test_failed_background_start_can_be_retried_by_normal_boot(self):
        engine = RealEngine()
        engine.boot = Mock(side_effect=RuntimeError('unavailable'))
        engine.prewarm(); engine.warmup_thread.join(3)
        self.assertEqual(engine.warmup_error, 'unavailable')
        self.assertFalse(engine.shutdown_requested)
        engine.close()

    def test_idle_transition_clears_exercise_but_keeps_the_same_vm(self):
        engine = RealEngine()
        engine.channel = Mock()
        engine.process = process = Mock()
        engine.name = 'private-linux'
        engine._practice_active = True
        engine.bridge = object()
        engine.observed_output.extend(b'old output')
        engine.cleanup_exercise = Mock()
        engine.release_practice()
        engine.cleanup_exercise.assert_called_once()
        engine.channel.request.assert_called_once_with('prepare', timeout=90, mission={'kind': '_idle'})
        self.assertIs(engine.process, process)
        self.assertEqual(engine.name, 'private-linux')
        self.assertIsNone(engine.bridge)
        self.assertFalse(engine._practice_active)
        self.assertFalse(engine.observed_output)
        process.terminate.assert_not_called()
        process.kill.assert_not_called()
        engine.release_practice()
        self.assertEqual(engine.channel.request.call_count, 1)

    def test_reset_during_warmup_waits_for_the_owned_startup(self):
        engine = RealEngine()
        acquired, release, finished = threading.Event(), threading.Event(), threading.Event()
        def startup():
            with engine._lifecycle:
                acquired.set(); release.wait(3)
        owner = threading.Thread(target=startup)
        owner.start(); self.assertTrue(acquired.wait(2))
        reset = threading.Thread(target=lambda: (engine.release_practice(), finished.set()))
        reset.start()
        self.assertFalse(finished.wait(.05))
        release.set(); owner.join(3); reset.join(3)
        self.assertTrue(finished.is_set())


if __name__ == '__main__': unittest.main()
