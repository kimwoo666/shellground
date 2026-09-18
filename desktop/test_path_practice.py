"""Generated path choices retain the meaning of each shell command."""
import posixpath
import shlex
import unittest
from unittest.mock import patch

from missions import UNITS, make_mission
from path_practice import nearby_path


def semantic_commands(solution, start):
    cwd = start
    result = []
    for line in solution.splitlines():
        lexer = shlex.shlex(line, posix=True, punctuation_chars='|>')
        lexer.whitespace_split = True
        lexer.commenters = ''
        tokens = list(lexer)
        if tokens[0] == 'cd':
            cwd = posixpath.normpath(posixpath.join(cwd, tokens[1]))
            continue
        normalized = []
        for token in tokens:
            if token.startswith('/home/learner/'):
                normalized.append(posixpath.normpath(token))
            elif token.startswith(('./', '../')) or token == '.':
                normalized.append(posixpath.normpath(posixpath.join(cwd, token)))
            else:
                normalized.append(token)
        result.append((cwd, normalized))
    return result, cwd


class PathPracticeTests(unittest.TestCase):
    def test_long_5942_current_directory_goal_is_explicit_and_required(self):
        from sim_engine import SimEngine
        m = make_mission('long', 5942, 2)
        self.assertEqual(m.source, '/home/learner/archive/staging/release5942')
        self.assertIn('현재 디렉터리 절대경로를 한 줄로', m.prompt)
        self.assertIn(m.report + '.where 파일에 저장', m.prompt)
        self.assertNotIn('작업한 위치도', m.prompt)
        engine = SimEngine()
        engine.start(m)
        try:
            for command in m.solution.splitlines()[:-1]:
                result = engine.shell.execute(command)
                self.assertEqual(result.code, 0, result.err)
            self.assertFalse(engine.rpc('grade', m)['passed'])
            self.assertEqual(engine.shell.execute(m.solution.splitlines()[-1]).code, 0)
            self.assertEqual(engine.shell.fs.read(m.report + '.where'), (m.source + '\n').encode())
            self.assertTrue(engine.rpc('grade', m)['passed'])
        finally:
            engine.close()

    def test_mixed_8372_example_contains_only_required_steps(self):
        from sim_engine import SimEngine
        m = make_mission('mixed', 8372)
        self.assertEqual([line.split()[0] for line in m.solution.splitlines()], ['cd', 'ls'])
        engine = SimEngine()
        engine.start(m)
        try:
            for command in m.solution.splitlines():
                result = engine.shell.execute(command)
                self.assertEqual(result.code, 0, result.err)
            self.assertTrue(engine.rpc('grade', m)['passed'])
            self.assertEqual(engine.shell.cwd, m.source)
        finally:
            engine.close()

    def test_mixed_8133_backup_creation_and_source_are_explicit(self):
        from sim_engine import SimEngine
        m = make_mission('mixed', 8133, 2)
        self.assertEqual(m.start, '/home/learner/office/sessions/team7')
        self.assertEqual(m.source, '/home/learner/archive/staging/release8133')
        self.assertEqual(m.target, '/home/learner/work/output/result8133')
        self.assertIn('원본 파일은 ' + m.source + '/guide.txt', m.prompt)
        self.assertIn(m.target + ' 안에 backup 폴더를 새로 만드세요', m.prompt)
        self.assertIn(m.target + '/backup/guide.txt로 복사', m.prompt)
        self.assertNotIn('위치와 보고서 목표', m.prompt)
        self.assertNotIn('pwd', m.solution)
        engine = SimEngine()
        engine.start(m)
        try:
            original = engine.shell.fs.read(m.source + '/guide.txt')
            self.assertEqual(original, b'Release 8133 user guide\n')
            self.assertFalse(engine.shell.fs.exists(m.target + '/guide.txt'))
            self.assertFalse(engine.shell.fs.exists(m.target + '/backup'))
            for command in m.solution.splitlines():
                result = engine.shell.execute(command)
                self.assertEqual(result.code, 0, result.err)
            self.assertEqual(engine.shell.fs.read(m.source + '/guide.txt'), original)
            self.assertEqual(engine.shell.fs.read(m.target + '/backup/guide.txt'), original)
            self.assertTrue(engine.rpc('grade', m)['passed'])
            engine.shell.execute(f"printf changed > {m.source}/guide.txt")
            result = engine.rpc('grade', m)
            self.assertFalse(result['passed'])
            self.assertTrue(any(not check['passed'] and m.source + '/guide.txt' in check['label'] for check in result['checks']))
        finally:
            engine.close()

    def test_copy_3504_repair_names_the_actual_source_and_overwrite_target(self):
        from sim_engine import SimEngine
        m = make_mission('copy', 3504, 2)
        self.assertEqual(m.start, '/home/learner/delivery/result3504')
        self.assertEqual(m.source, '/home/learner/data/release3504')
        self.assertIn('복구 기준 파일은 ' + m.source + '/guide.txt', m.prompt)
        self.assertIn('손상된 ./manual.txt를 덮어쓰세요', m.prompt)
        self.assertNotIn('원본으로 복구', m.prompt)
        self.assertEqual(m.prompt.count('덮어쓰세요'), 1)
        engine = SimEngine()
        engine.start(m)
        try:
            self.assertEqual(engine.shell.fs.read(m.source + '/guide.txt'), b'Release 3504 user guide\n')
            self.assertFalse(engine.shell.fs.exists(m.source + '/manual.txt'))
            self.assertEqual(engine.shell.fs.read(m.target + '/manual.txt'), b'CORRUPTED\n')
            self.assertFalse(engine.rpc('grade', m)['passed'])
            for command in m.solution.splitlines():
                result = engine.shell.execute(command)
                self.assertEqual(result.code, 0, result.err)
            self.assertTrue(engine.rpc('grade', m)['passed'])
        finally:
            engine.close()

    def test_reported_copy_9280_has_draft_in_work_folder_not_source(self):
        from sim_engine import SimEngine
        m = make_mission('copy', 9280, 1)
        self.assertEqual(m.start, '/home/learner/work/output')
        self.assertEqual(m.source, '/home/learner/archive/staging/release9280')
        self.assertEqual(m.target, '/home/learner/work/output/result9280')
        self.assertIn('원본 폴더: ' + m.source, m.prompt)
        self.assertIn('작업 폴더: ' + m.target, m.prompt)
        self.assertIn('result9280/final.txt', m.prompt)
        engine = SimEngine()
        engine.start(m)
        try:
            self.assertFalse(engine.shell.fs.exists(m.source + '/draft.txt'))
            self.assertEqual(engine.shell.fs.read(m.target + '/draft.txt'), b'Draft 9280\n')
            # Same position as the user's transcript: use canonical paths
            # from there, not start-relative paths after changing cwd.
            self.assertEqual(engine.shell.execute('cd ' + m.source).code, 0)
            for command in (f'cp guide.txt {m.target}/manual.txt',
                            f'mv {m.target}/draft.txt {m.target}/final.txt',
                            f'rm {m.target}/obsolete.txt'):
                self.assertEqual(engine.shell.execute(command).code, 0)
            self.assertTrue(engine.rpc('grade', m)['passed'])
        finally:
            engine.close()

    def test_nearby_only_and_dotfiles(self):
        self.assertEqual(nearby_path('/work/.env', '/work'), '.env')
        self.assertEqual(nearby_path('/work/a.txt', '/work/docs'), '../a.txt')
        self.assertEqual(nearby_path('/work/docs', '/work/docs'), '.')
        self.assertEqual(nearby_path('/other/files', '/work/deep/docs'), '/other/files')

    def test_examples_match_working_location(self):
        self.assertEqual(make_mission('edit', 4242).solution, 'nano note.txt')
        self.assertEqual(make_mission('rename', 4242).solution, 'mv draft.txt final.txt')
        read = make_mission('read', 4242, 2)
        self.assertEqual(read.solution, "cat ../guide.txt\ncat 'read me.txt'")
        self.assertIn('../guide.txt', read.prompt)
        self.assertIn('시작 위치 기준', read.prompt)
        distant = make_mission('script', 4244)
        self.assertTrue(distant.solution.startswith('cd ' + distant.target + '\n'))
        self.assertIn('./received-setup.sh receipt.txt', distant.solution)
        self.assertIn('mkdir result4243/practice', make_mission('mkdir', 4243).solution)

    def test_absolute_paths_and_find_output_are_retained(self):
        m = make_mission('curl', 4244)
        self.assertIn('-o ' + m.target, m.solution)
        for seed in range(4242, 4245):
            for practice in [0, 1, 2]:
                m = make_mission('find', seed, practice)
                self.assertIn('find ' + m.source + ' ', m.solution)

    def test_all_templates_keep_path_operands_and_goals(self):
        # Treat the original absolute operands as the oracle. Resolve each
        # rendered operand at its actual cwd, including moves between commands.
        for unit in UNITS:
            for seed in range(12):
                for practice in [0, 1, 2]:
                    with self.subTest(kind=unit.key, seed=seed, practice=practice):
                        with patch('missions.natural_paths', side_effect=lambda m: m):
                            original = make_mission(unit.key, seed, practice)
                        rendered = make_mission(unit.key, seed, practice)
                        self.assertEqual(original.review, rendered.review)
                        before, before_cwd = semantic_commands(original.solution, original.start)
                        after, after_cwd = semantic_commands(rendered.solution, rendered.start)
                        self.assertEqual(len(before), len(after))
                        for (_, raw), (cwd, actual) in zip(before, after):
                            self.assertEqual(len(raw), len(actual))
                            for expected, value in zip(raw, actual):
                                if expected.startswith('/home/learner/'):
                                    value = posixpath.normpath(posixpath.join(cwd, value))
                                self.assertEqual(expected, value)
                        if unit.key in {'navigate', 'mixed', 'pwdpaths', 'report'}:
                            self.assertEqual(before_cwd, after_cwd)

    def test_starting_locations_vary_without_reducing_topics(self):
        for kind in ['edit', 'copy', 'archive', 'script']:
            local, adjacent, distant = [make_mission(kind, s) for s in [4242, 4243, 4244]]
            self.assertEqual(local.start, local.target)
            self.assertEqual(adjacent.start, posixpath.dirname(adjacent.target))
            self.assertNotEqual(distant.start, distant.target)
        self.assertEqual(len(UNITS), 40)
