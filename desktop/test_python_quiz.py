"""Quiz/card data contracts and optional real-library reference checks.

Run from the repository root: python3 -m unittest desktop.test_python_quiz
The JSON starter code is parsed, never executed. Optional numerical checks run
only authored reference code in fresh temporary working directories. No GUI,
Conda installation, network, VM, or account operations are required.
"""

import ast
from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest


DESKTOP = Path(__file__).resolve().parent
BANK_PATH = DESKTOP / 'python_teaching' / 'quiz_bank.json'
CARDS_PATH = DESKTOP / 'python_teaching' / 'concept_cards.json'
BLUEPRINT_PATH = DESKTOP / 'python_teaching' / 'quiz_blueprint.md'
PHYSICAL_PAGE_COUNTS = {
    'Week 1_1.pdf': 15,
    'week_1_2_handout.pdf': 34,
    'week_2_1_handout.pdf': 41,
    'week_2_2_handout.pdf': 42,
    'week_3_1_handout.pdf': 46,
}
QUESTION_FIELDS = {
    'id', 'topic', 'prerequisites', 'source', 'prompt', 'choices', 'answer',
    'explanation', 'misconception', 'practical_followup',
}
FOLLOWUP_FIELDS = {'goal', 'starter_code', 'expected', 'grading_notes'}
CARD_TEXT_FIELDS = ('title', 'why', 'explanation', 'example', 'misconception')
CARD_FIELDS = {'id', 'topic', *CARD_TEXT_FIELDS, 'quiz_ids', 'source'}


class QuizDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank = json.loads(BANK_PATH.read_text(encoding='utf-8'))
        cls.questions = cls.bank['questions']
        cls.by_id = {q['id']: q for q in cls.questions}
        cls.blueprint = BLUEPRINT_PATH.read_text(encoding='utf-8')

    def test_schema_and_required_fields(self):
        self.assertEqual(set(self.bank), {'schema', 'questions'})
        self.assertEqual(self.bank['schema'], 1)
        self.assertIsInstance(self.questions, list)
        self.assertGreaterEqual(len(self.questions), 60)
        for q in self.questions:
            with self.subTest(question=q.get('id')):
                self.assertEqual(set(q), QUESTION_FIELDS)
                self.assertEqual(set(q['practical_followup']), FOLLOWUP_FIELDS)

    def test_ids_prompts_and_choices_are_unique(self):
        self.assertEqual(len(self.by_id), len(self.questions))
        normalized_prompts = set()
        for q in self.questions:
            with self.subTest(question=q['id']):
                self.assertRegex(q['id'], r'^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$')
                normalized = re.sub(r'\s+', ' ', q['prompt']).strip()
                self.assertNotIn(normalized, normalized_prompts)
                normalized_prompts.add(normalized)
                self.assertIsInstance(q['choices'], list)
                self.assertEqual(len(q['choices']), 4)
                self.assertEqual(len({c.strip() for c in q['choices']}), 4)

    def test_answers_are_zero_based_and_distributed(self):
        for q in self.questions:
            with self.subTest(question=q['id']):
                self.assertIs(type(q['answer']), int)
                self.assertIn(q['answer'], range(4))
        distribution = Counter(q['answer'] for q in self.questions)
        self.assertEqual(set(distribution), {0, 1, 2, 3})
        self.assertGreaterEqual(min(distribution.values()), len(self.questions) // 8)

    def test_explanations_and_practical_contract_are_not_empty(self):
        for q in self.questions:
            with self.subTest(question=q['id']):
                values = [q[k] for k in ('topic', 'prompt', 'explanation', 'misconception')]
                values += q['choices'] + list(q['practical_followup'].values())
                for value in values:
                    self.assertIsInstance(value, str)
                    self.assertTrue(value.strip())
                self.assertNotEqual(q['explanation'], q['misconception'])
                self.assertNotEqual(q['practical_followup']['expected'],
                                    q['practical_followup']['grading_notes'])

    def test_source_pages_are_physical_pages(self):
        covered_documents = set()
        for q in self.questions:
            with self.subTest(question=q['id']):
                source = q['source']
                self.assertEqual(set(source), {'document', 'pages'})
                self.assertIsInstance(source['pages'], list)
                if source['document'] == 'supplement':
                    self.assertEqual(source['pages'], [])
                    continue
                self.assertIn(source['document'], PHYSICAL_PAGE_COUNTS)
                covered_documents.add(source['document'])
                self.assertTrue(source['pages'])
                self.assertEqual(source['pages'], sorted(set(source['pages'])))
                for page in source['pages']:
                    self.assertIs(type(page), int)
                    self.assertGreaterEqual(page, 1)
                    self.assertLessEqual(page, PHYSICAL_PAGE_COUNTS[source['document']])
        self.assertEqual(covered_documents, set(PHYSICAL_PAGE_COUNTS))
        self.assertEqual(self.by_id['pandas-weather-missing-group']['source']['pages'], [45, 46])

    def test_prerequisites_are_defined_concepts_not_question_ids(self):
        concepts = {q['topic'] for q in self.questions}
        for q in self.questions:
            with self.subTest(question=q['id']):
                self.assertRegex(q['topic'], r'^[a-z]+\.[a-z_]+$')
                self.assertIsInstance(q['prerequisites'], list)
                self.assertEqual(len(q['prerequisites']), len(set(q['prerequisites'])))
                self.assertLessEqual(set(q['prerequisites']), concepts)
                self.assertIn('| ' + q['topic'] + ' |', self.blueprint)

    def test_all_starter_code_parses_without_execution(self):
        for q in self.questions:
            with self.subTest(question=q['id']):
                ast.parse(q['practical_followup']['starter_code'], filename=q['id'])

    def test_blueprint_maps_every_question_and_review(self):
        for q in self.questions:
            with self.subTest(question=q['id']):
                self.assertIn('| ' + q['id'] + ' |', self.blueprint)
        for lab in range(9):
            self.assertIn('### L' + str(lab) + '.', self.blueprint)
        self.assertIn('## R5.', self.blueprint)
        self.assertIn('물리 페이지', self.blueprint)

    def test_representative_answer_keys_match_reviewed_semantics(self):
        # Deliberately pin independent facts; these catch accidental answer-index
        # changes when choices are edited or reordered.
        correct_fragments = {
            'notebook-execution-order': '24이며',
            'python-function-loop': '반복이 끝난 뒤 return',
            'python-method-sort': 'result는 None',
            'numpy-list-array-add': '배열은 [6, 6]',
            'numpy-dtype-memory': '12바이트',
            'numpy-broadcast-column-offsets': '[[11,24,37],[12,25,38]]',
            'numpy-broadcast-incompatible': 'delta.reshape(2,1)',
            'numpy-chained-slice': '1행과 2행 전체',
            'numpy-index-versus-slice-rank': '(4,), (4,1)',
            'numpy-reduction-axis': 'a.mean(axis=0)',
            'numpy-variance-ddof': '각각 3과 2',
            'plot-save-correct-figure': "fig1.savefig('first.png')",
            'plot-cumulative-count-proportion': '6이다.',
            'plot-boxplot-whisker': '13',
            'pandas-derived-recompute': '원본 열을 명시해 다시 계산',
            'pandas-loc-iloc': 'df.iloc[1]',
            'pandas-pivot-duplicate-aggregation': "aggfunc='mean'",
            'pandas-concat-labels': '공통인 열',
            'pandas-merge-key-values': '[1,2]',
        }
        for question_id, expected_fragment in correct_fragments.items():
            with self.subTest(question=question_id):
                q = self.by_id[question_id]
                self.assertIn(expected_fragment, q['choices'][q['answer']])
                self.assertEqual(sum(expected_fragment in c for c in q['choices']), 1)

    def test_android_and_install_plans_do_not_claim_success(self):
        q = self.by_id['conda-android-platform']
        self.assertEqual(q['source'], {'document': 'supplement', 'pages': []})
        self.assertIn('Android 네이티브 설치 성공을 보장하면 안 된다', q['choices'][q['answer']])
        self.assertIn('모의 성공 메시지', q['practical_followup']['grading_notes'])
        self.assertIn('실제 Conda 설치 또는 환경 생성 성공으로 표시하지 않는다',
                      self.by_id['conda-project-isolation']['practical_followup']['grading_notes'])

    def test_stdlib_reference_predictions_and_wrong_answers(self):
        price = 8
        total = price * 3
        price = 10
        self.assertEqual(total, 24)
        self.assertNotEqual(total, price * 3)
        values = [7, 2, 5]
        self.assertIsNone(values.sort())
        self.assertEqual(values, [2, 5, 7])
        seasons = ['봄', '여름', '가을', '겨울']
        self.assertEqual(seasons[1:3], ['여름', '가을'])
        self.assertNotEqual(seasons[1:4], ['여름', '가을'])
        self.assertEqual(4 * 6 * 8 // 8, 24)


class ConceptCardDataTests(unittest.TestCase):
    """Always-on, standard-library-only checks for pre-quiz teaching cards.

    Source anchors were reviewed against the actual PDF content, including its
    cover pages. The tests pin that review; they do not pretend that page bounds
    alone prove semantic attribution. Conda supplements were additionally checked
    against these official guides (tests never make network requests):
    https://docs.conda.io/projects/conda/en/stable/user-guide/install/
    https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html
    """

    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CARDS_PATH.read_text(encoding='utf-8'))
        cls.cards = cls.data['cards']
        cls.by_id = {card['id']: card for card in cls.cards}
        questions = json.loads(BANK_PATH.read_text(encoding='utf-8'))['questions']
        cls.questions = {question['id']: question for question in questions}

    def test_schema_and_instructional_fields(self):
        self.assertEqual(set(self.data), {'schema', 'cards'})
        self.assertIs(type(self.data['schema']), int)
        self.assertEqual(self.data['schema'], 1)
        self.assertIsInstance(self.cards, list)
        self.assertGreaterEqual(len(self.cards), 33)
        for card in self.cards:
            with self.subTest(card=card.get('id')):
                self.assertEqual(set(card), CARD_FIELDS)
                self.assertEqual(set(card['source']), {'document', 'pages'})

    def test_unique_stable_ids_and_concise_korean_text(self):
        self.assertEqual(len(self.by_id), len(self.cards))
        for field in ('title', 'explanation', 'example'):
            texts = [re.sub(r'\s+', ' ', card[field]).strip() for card in self.cards]
            self.assertEqual(len(texts), len(set(texts)), field)
        for card in self.cards:
            with self.subTest(card=card['id']):
                self.assertRegex(card['id'], r'^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$')
                self.assertRegex(card['topic'], r'^[a-z]+\.[a-z_]+$')
                for field in CARD_TEXT_FIELDS:
                    value = card[field]
                    self.assertIsInstance(value, str)
                    self.assertEqual(value, value.strip())
                    self.assertRegex(value, r'[가-힣]')
                    self.assertGreaterEqual(len(value), 8)
                    self.assertLessEqual(len(value), 240)
                self.assertLessEqual(sum(len(card[f]) for f in CARD_TEXT_FIELDS), 850)
                self.assertNotEqual(card['why'], card['explanation'])
                self.assertNotEqual(card['example'], card['misconception'])

    def test_every_link_resolves_to_a_quiz_on_the_same_topic(self):
        for card in self.cards:
            with self.subTest(card=card['id']):
                links = card['quiz_ids']
                self.assertIsInstance(links, list)
                self.assertTrue(links)
                self.assertEqual(len(links), len(set(links)))
                for question_id in links:
                    self.assertIn(question_id, self.questions)
                    self.assertEqual(card['topic'], self.questions[question_id]['topic'])

    def test_all_conceptual_quizzes_have_a_reading_path(self):
        expected = {
            'notebook-execution-order', 'cloud-session-storage', 'install-versus-import',
            'conda-project-isolation', 'conda-android-platform',
            'data-science-small-sample', 'bigdata-three-vs', 'data-versus-information',
            'digital-sample-quantize-encode', 'image-representation-storage',
            'science-four-paradigms', 'package-roles',
        }
        conceptual = {question_id for question_id, question in self.questions.items()
                      if question['topic'].startswith(('data.', 'notebook.', 'environment.'))}
        linked = {question_id for card in self.cards for question_id in card['quiz_ids']}
        self.assertLessEqual(expected, linked)
        self.assertEqual(linked, conceptual | {'numpy-parallelism-versus-vectorization','numpy-vectorization-benchmark'})

    def test_three_vs_four_paradigms_and_six_roles_have_separate_cards(self):
        groups = {
            'data.three_vs': {'bigdata-volume', 'bigdata-velocity', 'bigdata-variety'},
            'data.paradigms': {'science-empirical', 'science-theoretical',
                               'science-computational', 'science-data-intensive'},
            'environment.library_roles': {'library-numpy', 'library-pandas',
                                          'library-matplotlib', 'library-seaborn',
                                          'library-scikit-learn', 'library-tensorflow'},
        }
        for topic, expected in groups.items():
            with self.subTest(topic=topic):
                self.assertEqual({card['id'] for card in self.cards if card['topic'] == topic},
                                 expected)
        roles = {'library-numpy': '수치 배열', 'library-pandas': 'DataFrame',
                 'library-matplotlib': '그래프', 'library-seaborn': 'Matplotlib',
                 'library-scikit-learn': '머신러닝', 'library-tensorflow': '딥러닝'}
        for card_id, role in roles.items():
            self.assertIn(role, self.by_id[card_id]['explanation'])

    def test_source_anchors_match_reviewed_physical_pages(self):
        d1, d2 = 'Week 1_1.pdf', 'week_1_2_handout.pdf'
        # Group only cards whose underlying concept appears on the same pages.
        reviewed = [
            (d1, [11], ('notebook-kernel-state',)),
            (d1, [12, 14], ('cloud-python-location', 'cloud-temporary-files')),
            (d1, [13, 14], ('local-workspace-files',)),
            (d2, [29, 30, 34], ('package-install-import',)),
            ('supplement', [], ('python-selected-environment', 'conda-project-environment',
                                'android-native-versus-remote')),
            (d2, [2, 3, 7, 10], ('data-science-question',)),
            (d2, [11], ('data-to-information',)),
            (d2, [4], ('bigdata-volume', 'bigdata-velocity', 'bigdata-variety')),
            (d2, [12, 13], ('digital-discrete-values',)),
            (d2, [13], ('digitization-sampling', 'digitization-quantization',
                        'digitization-encoding')),
            (d2, [14, 15], ('image-bitmap-pixels',)),
            (d2, [14], ('image-vector-shapes',)),
            (d2, [16, 17], ('image-eight-bit-grayscale',)),
            (d2, [17], ('storage-bits-bytes',)),
            (d2, [15, 16, 17], ('image-raw-storage',)),
            (d2, [17, 18], ('storage-binary-prefix',)),
            (d2, [21, 22], ('science-empirical', 'science-theoretical')),
            (d2, [21, 23], ('science-computational', 'science-data-intensive')),
            (d2, [32, 33], ('library-numpy', 'library-pandas', 'library-matplotlib',
                            'library-seaborn', 'library-scikit-learn', 'library-tensorflow')),
            ('week_2_1_handout.pdf', [35], ('parallelism-data','parallelism-task')),
            ('supplement', [], ('vectorization-not-core-count',)),
        ]
        checked = set()
        for document, pages, card_ids in reviewed:
            for card_id in card_ids:
                with self.subTest(card=card_id):
                    checked.add(card_id)
                    self.assertEqual(self.by_id[card_id]['source'],
                                     {'document': document, 'pages': pages})
        self.assertEqual(checked, set(self.by_id))
        for card in self.cards:
            source = card['source']
            pages = source['pages']
            self.assertIsInstance(pages, list)
            self.assertEqual(pages, sorted(set(pages)))
            if source['document'] == 'supplement':
                self.assertEqual(pages, [])
                continue
            self.assertTrue(pages)
            self.assertIn(source['document'], PHYSICAL_PAGE_COUNTS)
            for page in pages:
                self.assertIs(type(page), int)
                self.assertIn(page, range(1, PHYSICAL_PAGE_COUNTS[source['document']] + 1))

    def test_examples_teach_without_copying_quiz_choices_or_answer_positions(self):
        def normalize(text):
            return re.sub(r'\s+', '', text).replace('`', '')
        for card in self.cards:
            with self.subTest(card=card['id']):
                text = '\n'.join(card[field] for field in CARD_TEXT_FIELDS)
                self.assertNotRegex(text, r'(?:정답|선택지|보기)\s*(?:은|는|:)?\s*[1-4]\s*번')
                for question_id in card['quiz_ids']:
                    question = self.questions[question_id]
                    candidates = [question['prompt'], *question['choices']]
                    for candidate in candidates:
                        # Short factual words such as Volume may legitimately recur.
                        if len(normalize(candidate)) >= 25:
                            self.assertNotIn(normalize(candidate), normalize(text))
                self.assertNotIn('answer', card)
                self.assertNotIn('choices', card)

    def test_environment_cards_do_not_fake_native_installation(self):
        card = self.by_id['android-native-versus-remote']
        self.assertEqual(card['source'], {'document': 'supplement', 'pages': []})
        for phrase in ('Windows', 'macOS', 'Linux', 'Android', '원격'):
            self.assertIn(phrase, card['explanation'])
        self.assertIn('간주하면 안 됩니다', card['explanation'])
        self.assertIn('설치 성공을 판정하지 않습니다', card['misconception'])
        self.assertIn('실제 환경을 생성하지 않습니다',
                      self.by_id['conda-project-environment']['misconception'])
        self.assertIn('노트북 문서', self.by_id['cloud-temporary-files']['explanation'])
        self.assertIn('임시 폴더', self.by_id['cloud-temporary-files']['explanation'])

    def test_small_numerical_examples_keep_units_and_steps_distinct(self):
        self.assertEqual(2 ** 8, 256)
        self.assertIn('0부터 255', self.by_id['image-eight-bit-grayscale']['explanation'])
        self.assertIn('256종류', self.by_id['image-eight-bit-grayscale']['explanation'])
        self.assertEqual(9 * 5, 45)
        self.assertIn('45개', self.by_id['image-bitmap-pixels']['example'])
        self.assertEqual(80 // 8, 10)
        self.assertIn('80비트의 데이터는 10바이트', self.by_id['storage-bits-bytes']['example'])
        self.assertEqual(12 * 5 * 8 // 8, 60)
        self.assertIn('12×5×1=60바이트', self.by_id['image-raw-storage']['example'])
        self.assertEqual(2048 / 1024, 2)
        self.assertEqual(2048 / 1000, 2.048)
        self.assertIn('2.048kB', self.by_id['storage-binary-prefix']['example'])
        self.assertEqual(format(5, 'b'), '101')
        self.assertIn('101', self.by_id['digitization-encoding']['example'])
        self.assertIn('시점', self.by_id['digitization-sampling']['explanation'])
        self.assertIn('단계', self.by_id['digitization-quantization']['explanation'])
        self.assertIn('기호', self.by_id['digitization-encoding']['explanation'])


class OptionalLibraryReferenceTests(unittest.TestCase):
    def run_reference(self, imports, code):
        """Skip missing optional dependencies, fail incorrect numerical results."""
        env = os.environ.copy()
        runtime = DESKTOP / '.python-runtime'
        if runtime.is_dir():
            paths = [str(runtime)]
            if env.get('PYTHONPATH'):
                paths.append(env['PYTHONPATH'])
            env['PYTHONPATH'] = os.pathsep.join(paths)
        env['MPLBACKEND'] = 'Agg'
        env['OPENBLAS_NUM_THREADS'] = '1'
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        prefix = ('import sys\ntry:\n' + textwrap.indent(imports, '    ') +
                  '\nexcept ImportError as exc:\n'
                  "    print('OPTIONAL_DEPENDENCY_UNAVAILABLE: ' + str(exc))\n"
                  '    sys.exit(77)\n')
        with tempfile.TemporaryDirectory(prefix='python-quiz-test-') as directory:
            env['MPLCONFIGDIR'] = str(Path(directory) / 'mplconfig')
            result = subprocess.run(
                [sys.executable, '-c', prefix + textwrap.dedent(code)],
                cwd=directory, env=env, text=True, capture_output=True, timeout=30,
            )
        if result.returncode == 77 and 'OPTIONAL_DEPENDENCY_UNAVAILABLE:' in result.stdout:
            self.skipTest(result.stdout.strip())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_numpy_shapes_broadcasting_and_rejected_alternatives(self):
        self.run_reference('import numpy as np', '''
            a = np.arange(12).reshape(4, 3)
            assert a[1:][0:2].tolist() == [[3,4,5],[6,7,8]]
            assert a[1:,0:2].tolist() == [[3,4],[6,7],[9,10]]
            assert a[:,1].shape == (4,) and a[:,1:2].shape == (4,1)
            readings = np.array([[2,4,6],[1,3,5]])
            offsets = np.array([10,20])
            try:
                readings + offsets
            except ValueError:
                pass
            else:
                raise AssertionError('Incompatible broadcasting did not fail')
            assert (readings + offsets.reshape(2,1)).tolist() == [[12,14,16],[21,23,25]]
            assert (np.array([[100],[200]]) + np.array([1,3,5,7])).shape == (2,4)
            b = np.append([[1,2],[3,4]], [5,6])
            assert b.shape == (6,) and b.reshape(-1,2).tolist() == [[1,2],[3,4],[5,6]]
            try:
                b.reshape(4,2)
            except ValueError:
                pass
            else:
                raise AssertionError('Invalid reshape did not fail')
        ''')

    def test_numpy_reductions_masks_memory_and_reproducibility(self):
        self.run_reference('import numpy as np', '''
            a = np.array([[2,4,6],[8,10,12]])
            assert a.mean(axis=0).tolist() == [5,7,9]
            assert a.sum(axis=1).tolist() == [12,30]
            assert a.mean(axis=1).tolist() != [5,7,9]
            b = np.array([[3,8],[10,1]])
            assert b[b>=5].tolist() == [8,10] and b[b>=5].mean() == 9
            assert (b>=5).mean() != b[b>=5].mean()
            x = np.array([2.,4.,6.])
            assert np.isclose(x.var(), 8/3) and x.var(ddof=1) == 4
            assert np.isclose(x.std(), np.sqrt(8/3))
            assert np.array([3,6,9], dtype=np.int32).nbytes == 12
            assert np.linspace(0,1,5).tolist() == [0,.25,.5,.75,1]
            assert np.logspace(0,3,4).tolist() == [1,10,100,1000]
            assert np.column_stack(([1,2,3],[4,5,6])).tolist() == [[1,4],[2,5],[3,6]]
            assert np.vstack(([1,2,3],[4,5,6])).shape == (2,3)
            assert np.array_equal(np.random.default_rng(12).integers(0,10,8),
                                  np.random.default_rng(12).integers(0,10,8))
        ''')

    def test_pandas_labels_missing_values_and_stale_totals(self):
        self.run_reference('import numpy as np\nimport pandas as pd', '''
            from io import StringIO
            source = StringIO('city,temp' + chr(10) + 'Seoul,21' + chr(10) + 'Busan,24')
            df = pd.read_csv(source, index_col=0)
            assert df.shape == (2,1) and df.index.tolist() == ['Seoul','Busan']
            scores = pd.DataFrame({'score':[60,75,90]}, index=[10,20,30])
            assert scores.loc[20,'score'] == scores.iloc[1,0] == 75
            assert len(scores.loc[10:20]) == 2 and len(scores.iloc[0:1]) == 1
            s = pd.Series([4,np.nan,8], index=['a','b','c'])
            assert s.isna().tolist() == [False,True,False]
            assert not (s == np.nan).any()
            df = pd.DataFrame({'A':[2,4], 'B':[3,6]})
            df['total'] = df[['A','B']].sum(axis=1)
            df.loc[0,'A'] = 20
            assert df['total'].tolist() == [5,10]
            assert df.sum(axis=1).tolist() == [28,20]  # rejected double count
            df['total'] = df[['A','B']].sum(axis=1)
            assert df['total'].tolist() == [23,10]
            dropped = df.drop('A', axis=1)
            assert 'A' in df and 'A' not in dropped
            assert df.drop('A', axis=1, inplace=True) is None
        ''')

    def test_pandas_pivot_concat_and_value_based_merge(self):
        self.run_reference('import numpy as np\nimport pandas as pd', '''
            df = pd.DataFrame({'item':['pen','pen','bag'], 'color':['blue','blue','red'], 'price':[2,6,9]})
            mean = df.pivot_table(index='item', columns='color', values='price', aggfunc='mean')
            total = df.pivot_table(index='item', columns='color', values='price', aggfunc='sum')
            assert mean.loc['pen','blue'] == 4 and total.loc['pen','blue'] == 8
            try:
                df.pivot(index='item', columns='color', values='price')
            except ValueError:
                pass
            else:
                raise AssertionError('Duplicate pivot did not fail')
            df['transaction'] = [1,2,3]
            assert df.pivot(index=['item','transaction'], columns='color', values='price').shape == (3,2)
            left = pd.DataFrame({'A':[1], 'B':[2]}, index=['r'])
            right = pd.DataFrame({'B':[3], 'C':[4]}, index=['r'])
            common = pd.concat([left,right], join='inner')
            assert common.shape == (2,1) and common.index.tolist() == ['r','r']
            assert common['B'].tolist() == [2,3]
            students = pd.DataFrame({'id':[1,2], 'name':['Ada','Bo']})
            attendance = pd.DataFrame({'id':[3,2], 'days':[7,9]})
            joined = students.merge(attendance, on='id', how='left')
            assert joined['id'].tolist() == [1,2]
            assert pd.isna(joined.loc[0,'days']) and joined.loc[1,'days'] == 9
            assert students.merge(attendance, on='id', how='inner')['id'].tolist() == [2]
            assert sorted(students.merge(attendance, on='id', how='outer')['id']) == [1,2,3]
        ''')

    def test_matplotlib_artist_data_and_correct_figure_export(self):
        self.run_reference('import numpy as np\nimport matplotlib.pyplot as plt', '''
            from pathlib import Path
            fig1, ax1 = plt.subplots()
            line, = ax1.plot([20,10,30], color='black', marker='o', linestyle='--')
            assert list(line.get_xdata()) == [0,1,2]
            assert list(line.get_ydata()) == [20,10,30]
            assert line.get_marker() == 'o' and line.get_linestyle() == '--'
            fig2, ax2 = plt.subplots()
            ax2.plot([0,1], [9,9])
            fig1.savefig('first.png')
            plt.savefig('current.png')
            first, current = Path('first.png').read_bytes(), Path('current.png').read_bytes()
            assert first.startswith(bytes([137,80,78,71,13,10,26,10]))
            assert len(first) > 100 and first != current
            fig, axes = plt.subplots(2,2, figsize=(8,6))
            axes[1,1].plot([0,1], [1,3])
            assert [len(ax.lines) for ax in axes.flat] == [0,0,0,1]
            assert fig.get_size_inches().tolist() == [8,6]
            plt.close('all')
        ''')

    def test_histogram_count_proportion_and_boxplot_whisker(self):
        self.run_reference('import numpy as np\nimport matplotlib.pyplot as plt\nfrom matplotlib.cbook import boxplot_stats', '''
            fig, axes = plt.subplots(1,2)
            values = [1,2,2,3,4,7]
            counts, edges = np.histogram(values, bins=[0,3,6,9])
            assert counts.tolist() == [3,2,1]
            cumulative, _, _ = axes[0].hist(values, bins=[0,3,6,9], cumulative=True)
            proportion, _, _ = axes[1].hist(values, bins=[0,3,6,9], cumulative=True, density=True)
            assert cumulative.tolist() == [3,5,6]
            assert np.allclose(proportion, [.5,5/6,1])
            assert cumulative[-1] != proportion[-1]
            box = boxplot_stats([2,3,4,5,6,7,30])[0]
            assert box['q1'] == 3.5 and box['q3'] == 6.5 and box['iqr'] == 3
            assert box['whislo'] == 2 and box['whishi'] == 7
            assert box['fliers'].tolist() == [30]
            assert box['whishi'] != box['q3'] + 1.5 * box['iqr']
            plt.close('all')
        ''')

    def test_optional_scipy_density_fit(self):
        self.run_reference('import numpy as np\nimport matplotlib.pyplot as plt\nfrom scipy.stats import norm', '''
            data = np.random.default_rng(17).normal(loc=5, scale=2, size=1000)
            fig, ax = plt.subplots()
            heights, edges, _ = ax.hist(data, bins=20, density=True)
            mu, sigma = norm.fit(data)
            x = np.linspace(edges[0], edges[-1], 200)
            line, = ax.plot(x, norm.pdf(x, mu, sigma))
            assert len(data) == 1000 and sigma > 0
            assert np.isclose(np.sum(heights * np.diff(edges)), 1)
            assert len(line.get_xdata()) == len(line.get_ydata()) == 200
            plt.close('all')
        ''')

    def test_first_five_lecture_review_preserves_missing_row_visits(self):
        self.run_reference('import numpy as np\nimport pandas as pd\nimport matplotlib.pyplot as plt', '''
            from io import StringIO
            rows = ['date,room,temp,visits', '2026-01-01,A,18,10', '2026-01-02,A,,14',
                    '2026-01-01,B,20,8', '2026-01-02,B,22,12', '2026-02-01,A,21,16',
                    '2026-02-01,B,24,18']
            df = pd.read_csv(StringIO(chr(10).join(rows)), parse_dates=['date'])
            assert df.shape == (6,4) and df['temp'].isna().sum() == 1
            wide = df.pivot(index='room', columns='date', values='visits').sort_index(axis=1)
            a = wide.to_numpy()
            assert a.tolist() == [[10,14,16],[8,12,18]]
            assert a.sum(axis=1).tolist() == [40,38] and a.mean(axis=0).tolist() == [9,13,17]
            assert df.groupby('room')['temp'].mean().to_dict() == {'A':19.5,'B':22.}
            assert df.groupby('room')['temp'].count().to_dict() == {'A':2,'B':3}
            monthly = df.groupby(df['date'].dt.month)['visits'].sum()
            assert monthly.to_dict() == {1:44,2:34}
            assert monthly[monthly>=40].index.tolist() == [1]
            wrong = df.dropna().groupby('room')['visits'].sum()
            assert wrong['A'] == 26 and wrong['A'] != a.sum(axis=1)[0]
            capacities = pd.DataFrame({'room':['B','A'], 'capacity':[30,20]})
            joined = df.merge(capacities, on='room', how='left')
            assert joined['capacity'].tolist() == [20,20,30,30,20,30]
            fig, axes = plt.subplots(1,2)
            axes[0].bar(monthly.index.astype(str), monthly.to_numpy())
            observed = df.dropna(subset=['temp'])
            points = axes[1].scatter(observed['temp'], observed['visits'])
            assert [bar.get_height() for bar in axes[0].patches] == [44,34]
            assert len(points.get_offsets()) == 5
            plt.close('all')
        ''')


if __name__ == '__main__':
    unittest.main()
