"""New concept UI/data only: no VM, Docker, Python kernel or old solve suite."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox
from native_app import Window, create_application
from system_concept_dialog import SystemConceptDialog
from system_concept_progress import ConceptProgress


class ConceptProgressTests(unittest.TestCase):
    def test_attempts_and_positions_survive_without_practical_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'system-concepts-v1.json'
            progress = ConceptProgress(path)
            progress.position('linux', 'question', 'second-card')
            progress.grade('question', False)
            self.assertFalse(ConceptProgress(path).data['quiz']['question']['passed'])
            progress.grade('question', True); progress.grade('question', False)
            actual = ConceptProgress(path).data
            self.assertEqual(actual['quiz']['question'], {'attempts': 3, 'passed': True})
            self.assertEqual(actual['positions']['linux'], {'question': 'question', 'card': 'second-card'})
            self.assertNotIn('completed', actual)
            self.assertNotIn('passed', actual)

    def test_corrupt_or_future_progress_is_not_overwritten(self):
        invalid = ('{broken', '{"schema": 2, "quiz": {}, "positions": {}}',
                   '{"schema": 1, "quiz": {"q": {"passed": "yes", "attempts": 1}}, "positions": {}}',
                   '{"schema": 1, "quiz": {}, "positions": {"linux": null}}')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'system-concepts-v1.json'
            for content in invalid:
                with self.subTest(content=content):
                    path.write_text(content)
                    progress = ConceptProgress(path)
                    self.assertTrue(progress.error)
                    with self.assertRaises(OSError): progress.grade('q', True)
                    self.assertEqual(path.read_text(), content)


class SystemConceptUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app, cls.ui, cls.mono = create_application()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / 'system-concepts-v1.json'
        self.dialogs = []; self.parents = []

    def events(self): self.app.processEvents()

    def tearDown(self):
        for dialog in self.dialogs: dialog.close(); dialog.deleteLater()
        for parent in self.parents:
            parent.simulation_timer.stop(); parent.close()
            end = time.monotonic() + 5
            while parent.isVisible() and time.monotonic() < end:
                self.events(); QTest.qWait(10)
            self.assertFalse(parent.isVisible()); parent.deleteLater()
        self.events(); self.folder.cleanup()

    def dialog(self, **kwargs):
        dialog = SystemConceptDialog(self.path, **kwargs)
        self.dialogs.append(dialog); dialog.show(); self.events()
        return dialog

    def parent(self):
        engine = Mock(); engine.name = ''; engine.close.return_value = None
        parent = Window(self.ui, self.mono, Path(self.folder.name) / 'progress-v3.json', mode='real', engine=engine)
        parent.simulation_timer.stop(); self.parents.append(parent); parent.show(); self.events()
        return parent, engine

    def select(self, dialog, key):
        index = next(i for i, q in enumerate(dialog.questions) if q['id'] == key)
        dialog.question_picker.setCurrentIndex(index); self.events()

    def test_all_new_questions_render_and_hide_feedback_until_submission(self):
        dialog = self.dialog()
        seen = set()
        for topic in (0, 1):
            dialog.topic_picker.setCurrentIndex(topic)
            for index in range(len(dialog.questions)):
                dialog.question_picker.setCurrentIndex(index); self.events()
                question = dialog.question; seen.add(question['id'])
                self.assertEqual(dialog.prompt.toPlainText(), question['prompt'])
                self.assertFalse(dialog.tabs.isTabEnabled(2))
                self.assertEqual(dialog.feedback.toPlainText(), '')
                self.assertEqual(dialog.group.checkedId(), -1)
                self.assertTrue(dialog.card_text.toPlainText())
                self.assertEqual([label.text() for label in dialog.option_labels], question['choices'])
                self.assertTrue(all(label.textFormat() == Qt.TextFormat.PlainText for label in dialog.option_labels))
        self.assertEqual(len(seen), 44)
        self.assertEqual(dialog.progress.data['quiz'], {})

    def test_added_io_questions_render_grade_and_resume_without_running_lab(self):
        dialog = self.dialog()
        keys = [q['id'] for q in dialog.questions if q['id'].startswith('io_')]
        self.assertEqual(len(keys), 6)
        for key in keys:
            self.select(dialog, key)
            self.assertEqual(dialog.prompt.toPlainText(), dialog.question['prompt'])
            self.assertEqual(dialog.feedback.toPlainText(), '')
            self.assertFalse(dialog.tabs.isTabEnabled(2))
            self.assertEqual([label.text() for label in dialog.option_labels], dialog.question['choices'])
            dialog.tabs.setCurrentIndex(1)
            dialog.options[dialog.question['answer']].click(); dialog.submit.click(); self.events()
            self.assertEqual(dialog.tabs.currentIndex(), 2)
            self.assertTrue(dialog.progress.data['quiz'][key]['passed'])
        dialog.close(); reopened = self.dialog()
        self.assertEqual(reopened.question['id'], keys[-1])
        self.assertEqual(reopened.group.checkedId(), -1)
        self.assertTrue(all(reopened.progress.data['quiz'][key]['passed'] for key in keys))

    def test_added_system_questions_render_grade_and_resume_without_running_lab(self):
        # Dedicated delta: do not revisit the previous 38 questions or open a VM.
        handler = Mock(return_value=True)
        dialog = self.dialog(practice_handler=handler)
        keys = [q['id'] for q in dialog.questions if q['id'].startswith('system_info_')]
        self.assertEqual(len(keys), 6)
        for key in keys:
            with self.subTest(question=key):
                self.select(dialog, key)
                question = dialog.question
                self.assertEqual(dialog.prompt.toPlainText(), question['prompt'])
                self.assertEqual(dialog.feedback.toPlainText(), '')
                self.assertFalse(dialog.tabs.isTabEnabled(2))
                self.assertEqual(dialog.group.checkedId(), -1)
                self.assertEqual([label.text() for label in dialog.option_labels], question['choices'])
                self.assertEqual([dialog.practice_picker.itemData(i) for i in range(dialog.practice_picker.count())], question['practice_keys'])
                self.assertEqual(dialog.practice_open.isEnabled(), bool(question['practice_keys']))
                for index, card in enumerate(question['cards']):
                    if index:
                        dialog.next_card.click(); self.events()
                    self.assertIn(card['explanation'], dialog.card_text.toPlainText())
                    for source in question['sources']:
                        self.assertIn(source['url'], dialog.card_text.toPlainText())
                if key == 'system_info_rtc_missing_and_ntp_active':
                    self.assertIn('조사 완료가 RTC 읽기 성공이나 NTP 동기화 완료를 뜻하지 않습니다', dialog.practice_text.toPlainText())
                if key == 'system_info_snap_client_is_not_installed_application':
                    self.assertIn('실제 snap 설치·실행 실습은 없습니다', dialog.practice_text.toPlainText())
                dialog.tabs.setCurrentIndex(1)
                dialog.options[(question['answer'] + 1) % 4].click(); dialog.submit.click(); self.events()
                self.assertFalse(dialog.progress.data['quiz'][key]['passed'])
                dialog.try_again.click()
                dialog.options[question['answer']].click(); dialog.submit.click(); self.events()
                self.assertEqual(dialog.tabs.currentIndex(), 2)
                self.assertEqual(dialog.progress.data['quiz'][key], {'attempts': 2, 'passed': True})
                for feedback in question['feedback']:
                    self.assertIn(feedback, dialog.feedback.toPlainText())
        self.assertEqual(set(dialog.progress.data['quiz']), set(keys))
        self.assertNotIn('completed', dialog.progress.data)
        handler.assert_not_called()
        dialog.close(); reopened = self.dialog()
        self.assertEqual(reopened.question['id'], keys[-1])
        self.assertEqual(reopened.group.checkedId(), -1)
        self.assertEqual(reopened.feedback.toPlainText(), '')
        self.assertFalse(reopened.tabs.isTabEnabled(2))
        self.assertTrue(all(reopened.progress.data['quiz'][key]['passed'] for key in keys))

    def test_wrong_answer_retry_and_reopen_restore_card_without_input(self):
        dialog = self.dialog()
        self.select(dialog, 'process_resume_pipeline_by_job_number')
        dialog.next_card.click(); self.events()
        card = dialog.question['cards'][dialog.card_index]['id']
        answer = dialog.question['answer']; key = dialog.question['id']
        dialog.tabs.setCurrentIndex(1)
        QTest.mouseClick(dialog.options[(answer + 1) % 4], Qt.MouseButton.LeftButton)
        dialog.submit.click(); self.events()
        self.assertEqual(dialog.tabs.currentIndex(), 2)
        self.assertFalse(dialog.progress.data['quiz'][key]['passed'])
        self.assertIn('재시도', dialog.feedback.toPlainText())
        dialog.try_again.click(); self.events()
        self.assertEqual(dialog.tabs.currentIndex(), 1)
        QTest.mouseClick(dialog.options[answer], Qt.MouseButton.LeftButton)
        dialog.submit.click(); self.events()
        self.assertTrue(dialog.progress.data['quiz'][key]['passed'])
        self.assertEqual(dialog.progress.data['quiz'][key]['attempts'], 2)
        dialog.close()
        resumed = self.dialog()
        self.assertEqual(resumed.question['id'], key)
        self.assertEqual(resumed.question['cards'][resumed.card_index]['id'], card)
        self.assertEqual(resumed.group.checkedId(), -1)
        self.assertFalse(resumed.tabs.isTabEnabled(2))

    def test_changed_docker_routes_open_explanations_without_marking_completion(self):
        handler = Mock(return_value=True)
        dialog = self.dialog(practice_handler=handler)
        dialog.topic_picker.setCurrentIndex(1); self.events()
        keys = ('docker_attach_exec_main_process', 'docker_attach_exec_keep_service',
                'docker_cpu_affinity_not_reservation', 'docker_cpu_limit_is_ceiling',
                'docker_io_weight_not_throughput_promise')
        for key in keys:
            self.select(dialog, key)
            routes = dialog.question['practice_keys']
            self.assertEqual([dialog.practice_picker.itemData(i) for i in range(dialog.practice_picker.count())], routes)
            for index, route in enumerate(routes):
                handler.reset_mock(); dialog.practice_picker.setCurrentIndex(index)
                dialog.practice_open.click(); self.events()
                handler.assert_called_once_with(route)
            self.assertFalse(dialog.tabs.isTabEnabled(2))
        self.assertFalse(dialog.progress.data['quiz'])
        self.assertNotIn('completed', dialog.progress.data)

    def test_topic_positions_are_independent_and_unfinished_is_not_locked(self):
        dialog = self.dialog(); dialog.question_picker.setCurrentIndex(3)
        linux_id = dialog.question['id']
        self.assertEqual(dialog.progress.data['quiz'], {})
        dialog.topic_picker.setCurrentIndex(1); dialog.question_picker.setCurrentIndex(2)
        docker_id = dialog.question['id']
        dialog.topic_picker.setCurrentIndex(0)
        self.assertEqual(dialog.question['id'], linux_id)
        dialog.topic_picker.setCurrentIndex(1)
        self.assertEqual(dialog.question['id'], docker_id)

    def test_native_menu_related_navigation_cancel_and_no_execution(self):
        parent, engine = self.parent()
        with patch('system_concept_dialog.SystemConceptDialog.exec', return_value=0) as show:
            parent.concept_action.trigger(); self.assertEqual(show.call_count, 1)
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.assertEqual(parent.findChildren(SystemConceptDialog), [])
        with patch('system_concept_dialog.SystemConceptDialog', side_effect=ValueError('자료 형식 오류')), \
                patch('native_app.QMessageBox.warning') as warning:
            parent.concept_action.trigger(); warning.assert_called_once()
        engine.start.assert_not_called()
        capture = os.environ.get('SHELLGROUND_CONCEPT_CAPTURE')
        if capture:
            destination = Path(capture); destination.mkdir(parents=True, exist_ok=True)
            parent.grab().save(str(destination / 'linux-concept-entry.png'))
        dialog = self.dialog(parent=parent, practice_handler=parent.open_concept_lesson)
        self.select(dialog, 'process_time_is_cpu_not_elapsed')
        dialog.tabs.setCurrentIndex(3); self.events()
        self.assertTrue(dialog.practice_open.isEnabled())
        old_index = parent.index
        parent.mission = object(); parent.phase = 'practice'; parent.passed = False
        with patch('native_app.QMessageBox.question', return_value=QMessageBox.StandardButton.No):
            dialog.practice_open.click(); self.events()
        self.assertTrue(dialog.isVisible()); self.assertEqual(parent.index, old_index)
        self.assertIsNotNone(parent.mission)
        with patch('native_app.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            dialog.practice_open.click(); self.events()
        self.assertFalse(dialog.isVisible()); self.assertEqual(parent.units[parent.index].key, 'process_list')
        self.assertEqual(parent.phase, 'learn'); self.assertIsNone(parent.mission)
        engine.start.assert_not_called(); engine.rpc.assert_not_called()
        self.assertEqual(parent.completed, []); self.assertEqual(dialog.progress.data['quiz'], {})
        parent.busy = True; parent.update_controls()
        self.assertFalse(parent.concept_action.isEnabled())
        self.assertFalse(parent.open_concept_lesson('process_threads'))
        parent.busy = False

    def test_existing_learning_files_preserved_by_concept_grading(self):
        paths = [Path(self.folder.name) / name for name in ('progress-v3.json', 'progress-v3-real.json', 'python-progress-v1.json')]
        for path in paths: path.write_text('{"existing": "unchanged"}')
        dialog = self.dialog(); dialog.tabs.setCurrentIndex(1)
        QTest.mouseClick(dialog.options[dialog.question['answer']], Qt.MouseButton.LeftButton)
        dialog.submit.click(); self.events()
        for path in paths: self.assertEqual(path.read_text(), '{"existing": "unchanged"}')

    def test_corrupt_progress_banner_and_visual_layout(self):
        self.path.write_text('{invalid')
        dialog = self.dialog()
        self.assertTrue(dialog.error.isVisible())
        self.assertIn('덮어쓰지', dialog.error.text())
        self.assertEqual(self.path.read_text(), '{invalid')
        capture = os.environ.get('SHELLGROUND_CONCEPT_CAPTURE')
        if capture:
            from app_settings import theme_palette
            destination = Path(capture); destination.mkdir(parents=True, exist_ok=True)
            dialog.close(); self.path = self.path.with_name('preview.json')
            dialog = self.dialog()
            self.select(dialog, 'process_resume_pipeline_by_job_number')
            dialog.resize(900, 760); dialog.tabs.setCurrentIndex(1); self.events()
            dialog.grab().save(str(destination / 'linux-concept-question.png'))
            dialog.setPalette(theme_palette('dark')); dialog.topic_picker.setCurrentIndex(1)
            dialog.tabs.setCurrentIndex(0); self.events()
            dialog.grab().save(str(destination / 'docker-concept-study-dark.png'))
            dialog.resize(640, 520); dialog.tabs.setCurrentIndex(1)
            QTest.mouseClick(dialog.options[0], Qt.MouseButton.LeftButton); dialog.submit.click(); self.events()
            self.assertEqual(dialog.tabs.currentIndex(), 2)
            dialog.grab().save(str(destination / 'concept-small-feedback.png'))


if __name__ == '__main__': unittest.main()
