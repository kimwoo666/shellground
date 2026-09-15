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
