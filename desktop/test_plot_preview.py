"""Regression tests for stale first-Figure previews; no full-course replay."""
import base64
import io
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from python_teaching.course import lesson_by_key
from python_teaching.worker import Kernel
from python_teaching.values import grade_snapshot

USER_CODE = 'measured_2 = measured-2\nfig, ax = plt.subplots()\nax.plot(t, measured)\nax.plot(t, measured_2)'


class PreviewWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory(prefix='shellground-plot-preview-')
        cls.kernel=Kernel(cls.folder.name)

    @classmethod
    def tearDownClass(cls):
        cls.kernel.plt.close('all');cls.folder.cleanup()

    def setUp(self):
        self.k=self.kernel
        self.k.plt.close('all');self.k.namespace={'__name__':'__main__'}

    def run_code(self,code):
        result=self.k.execute(code)
        self.assertTrue(result['ok'],result['output'])

    def test_reported_code_shows_new_figure_not_old_empty_one(self):
        task=lesson_by_key('plot_line').problems[2]
        self.run_code(task.initial)
        self.run_code('old, old_ax = plt.subplots()')
        self.run_code(USER_CODE)
        state=self.k.inspect(task.targets)
        self.assertEqual(state['figure_numbers'],[2,1])
        self.assertTrue(grade_snapshot(state['values'],task.checks)['passed'])
        stream=io.BytesIO();self.k.namespace['fig'].savefig(stream,format='png',dpi=90)
        self.assertEqual(base64.b64decode(state['figures'][0]),stream.getvalue())
        self.assertNotEqual(state['figures'][0],state['figures'][1])
        self.assertEqual(state['preview_errors'],[])

    def test_more_than_six_figures_still_includes_current(self):
        self.run_code('import matplotlib.pyplot as plt\nfor n in range(1,9):\n    plt.figure(n)')
        state=self.k.inspect([])
        self.assertEqual(state['figure_count'],8)
        self.assertEqual(state['figure_numbers'],[8,7,6,5,4,3])
        self.assertEqual(self.k.plt.get_fignums(),list(range(1,9)))
        self.assertEqual(self.k.plt.gcf().number,8)

    def test_preview_preserves_explicit_selection_and_next_pyplot_target(self):
        self.run_code('import matplotlib.pyplot as plt\nplt.figure(10)\nplt.figure(2)')
        state=self.k.inspect([])
        self.assertEqual(state['figure_numbers'],[2,10])
        self.run_code('plt.plot([0,1],[2,4])')
        self.assertEqual(self.k.plt.gcf().number,2)
        self.assertEqual(len(self.k.plt.gcf().axes[0].lines),1)
        self.assertFalse(self.k.plt.figure(10).axes)

    def test_empty_session_and_close_all_do_not_recreate_a_figure(self):
        self.assertEqual(self.k.inspect([])['figures'],[])
        self.assertEqual(self.k.plt.get_fignums(),[])
        self.run_code("import matplotlib.pyplot as plt\nplt.subplots()\nplt.close('all')")
        self.assertEqual(self.k.inspect([])['figure_count'],0)
        self.assertEqual(self.k.plt.get_fignums(),[])

    def test_broken_preview_is_reported_without_losing_other_figures(self):
        self.run_code('import matplotlib.pyplot as plt\na=plt.figure(1)\nb=plt.figure(2)')
        with patch.object(self.k.namespace['b'],'savefig',side_effect=ValueError('render failed')):
            state=self.k.inspect([])
        self.assertEqual(state['figure_numbers'],[1])
        self.assertEqual(state['preview_errors'],[{'number':2,'error':'render failed'}])
        self.assertEqual(self.k.plt.gcf().number,2)


class PreviewUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from native_app import create_application
        cls.app,cls.ui,cls.mono=create_application()

    def setUp(self):
        from python_app import PythonWindow
        self.folder=tempfile.TemporaryDirectory(prefix='shellground-plot-ui-')
        self.window=PythonWindow(self.ui,self.mono,Path(self.folder.name)/'progress.json')
        self.w=self.window
        self.w.select_lesson(next(i for i,u in enumerate(self.w.units) if u.key=='plot_line'))
        self.w.phase,self.w.variant='practice2',2
        self.w.render();self.w.show();self.app.processEvents()

    def tearDown(self):
        self.idle();self.w.close();self.app.processEvents();self.folder.cleanup()

    def idle(self):
        from PySide6.QtTest import QTest
        deadline=time.monotonic()+20
        while self.w.busy and time.monotonic()<deadline:
            self.app.processEvents();QTest.qWait(10)
        self.app.processEvents()
        self.assertFalse(self.w.busy)

    def run_code(self,code):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.w.editor.setPlainText(code);self.w.editor.setFocus()
        QTest.keyClick(self.w.editor,Qt.Key.Key_Return,Qt.KeyboardModifier.ShiftModifier)
        self.idle()

    def test_exact_code_after_blank_and_repeated_execution_is_visible(self):
        w=self.w
        self.run_code('old, old_ax = plt.subplots()')
        blank=w.figure.pixmap().toImage()
        self.run_code(USER_CODE)
        self.assertEqual(w.figure_picker.currentData(),2)
        self.assertEqual(w.output_tabs.currentIndex(),1)
        self.assertFalse(w.figure.pixmap().isNull())
        plotted=w.figure.pixmap().toImage()
        self.assertNotEqual(plotted,blank)
        w.figure_picker.setCurrentIndex(1)
        self.assertEqual(w.figure.pixmap().toImage(),blank)
        w.figure_picker.setCurrentIndex(0)
        self.assertEqual(w.figure.pixmap().toImage(),plotted)
        w.grade();self.idle();self.assertTrue(w.solved,w.feedback.text())
        self.run_code(USER_CODE)
        self.assertEqual(w.figure_picker.currentData(),3)
        self.assertEqual(w.figure.pixmap().toImage(),plotted)
        self.run_code("plt.close('all')")
        self.assertEqual(w.figure_picker.count(),0)
        self.assertTrue(w.figure.pixmap().isNull())

    def test_inspection_errors_and_bad_images_are_not_silently_blank(self):
        w=self.w
        w.show_inspection({'ok':False,'error':'render failed'})
        self.assertIn('render failed',w.output.toPlainText())
        self.assertEqual(w.output_tabs.currentIndex(),0)
        w.show_inspection({'ok':True,'figures':['invalid png']})
        self.assertIn('이미지를 읽지 못했습니다',w.figure.text())
        w.show_inspection({'ok':True,'figures':[],
                           'preview_errors':[{'number':7,'error':'drawing failed'}]})
        self.assertIn('Figure 7 표시 실패: drawing failed',w.output.toPlainText())

    def test_execution_exception_remains_visible_even_with_an_old_figure(self):
        self.run_code(USER_CODE)
        self.run_code('raise ValueError("visible_error")')
        self.assertEqual(self.w.output_tabs.currentIndex(),0)
        self.assertIn('visible_error',self.w.output.toPlainText())
        self.assertEqual(self.w.figure_picker.count(),1)

    def test_screenshot_typos_show_errors_then_corrected_code_plots(self):
        w=self.w
        w.editor.clear()
        w.select_lesson(next(i for i,u in enumerate(w.units) if u.key=='plot_style'))
        self.run_code('fig.ax = plt.subplots()')
        self.assertEqual(w.output_tabs.currentIndex(),0)
        self.assertIn('NameError',w.output.toPlainText())
        self.run_code("fig, ax = plt.subplots()\nax.plot(x,t,color='red',marker='o',linestyle='--')")
        self.assertEqual(w.output_tabs.currentIndex(),0)
        self.assertIn("name 't' is not defined",w.output.toPlainText())
        self.run_code("fig, ax = plt.subplots()\nax.plot(x,y,color='red',marker='o',linestyle='--')")
        self.assertEqual(w.output_tabs.currentIndex(),1)
        self.assertEqual(w.figure_picker.currentData(),3)
        image=w.figure.pixmap()
        self.assertFalse(image.isNull())
        self.assertLessEqual(image.width(),w.figure_area.viewport().width())
        self.assertLessEqual(image.height(),w.figure_area.viewport().height())
        w.resize(900,700);self.app.processEvents()
        self.assertLessEqual(w.figure.pixmap().width(),w.figure_area.viewport().width())
        self.assertLessEqual(w.figure.pixmap().height(),w.figure_area.viewport().height())


if __name__=='__main__':unittest.main()
