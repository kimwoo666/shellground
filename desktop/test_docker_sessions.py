import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from docker_sessions_course import KEYS, make_mission
from guest.docker_sessions_lab import archive_signature
from mode_curriculum import curriculum
from course_topics import topic_of, unit_number
from learning_steps import learning_steps


class DockerSessionTests(unittest.TestCase):
    def test_real_only_five_units_distinct_variants_and_review(self):
        units, reviews = curriculum('real'); index = {u.key: i for i,u in enumerate(units)}
        for n,key in enumerate(KEYS, 16):
            self.assertEqual(unit_number(units, index[key]), n); self.assertEqual(topic_of(units[index[key]]), 'Docker')
            missions = [make_mission(key, 7251, v) for v in range(3)]
            self.assertEqual(len({m.prompt for m in missions}), 3)
            self.assertEqual(len({m.solution for m in missions}), 3)
            self.assertEqual(len(learning_steps(units[index[key]], 'real', missions[0])), 4)
            for m in missions: self.assertNotIn('F5', m.prompt)
        self.assertEqual(next(c for c in reviews if c.key == 'docker-checkpoint-sessions').units, tuple(units[index[k]] for k in KEYS))
        self.assertFalse(any(u.key in KEYS for u in curriculum('simulation')[0]))

    def test_terminal_context_and_destructive_scope_are_explicit(self):
        attach = make_mission(KEYS[1], 7251)
        self.assertIn('Ctrl+P 다음 Ctrl+Q', attach.solution); self.assertNotIn('exit\n', attach.solution)
        self.assertIn('재시작·종료하지', attach.prompt)
        for v in range(3):
            prune = make_mission(KEYS[4], 7251, v)
            self.assertIn('container prune --filter label=shellground.cleanup=7251', prune.solution)
            self.assertNotIn('system prune', prune.solution)
        self.assertIn('첫 줄을 보존', make_mission(KEYS[0], 7251, 1).prompt)
        self.assertIn('태그를 원래 이미지 ID', make_mission(KEYS[3], 7251, 1).prompt)

    def test_archive_members_and_actual_gzip_not_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'backup.tar.gz'
            def write(mode, layer=b'actual layer', duplicate=False):
                with tarfile.open(path, mode) as tar:
                    rows = [('config.json', b'{"actual":"config"}'), ('layer.tar', layer),
                            ('manifest.json', json.dumps([dict(Config='config.json', Layers=['layer.tar'], RepoTags=['training/a:v1'])]).encode())]
                    if duplicate: rows.append(rows[0])
                    for name,data in rows:
                        item = tarfile.TarInfo(name); item.size = len(data); tar.addfile(item, io.BytesIO(data))
            write('w:gz'); expected = archive_signature(path); self.assertIsNotNone(expected)
            write('w'); self.assertIsNone(archive_signature(path)); self.assertEqual(archive_signature(path, False), expected)
            write('w:gz', layer=b'wrong layer'); self.assertNotEqual(archive_signature(path), expected)
            write('w:gz', duplicate=True); self.assertIsNone(archive_signature(path))

    def test_new_microsteps_create_before_inspect_and_prune_targets_preserved_files(self):
        units = {u.key:u for u in curriculum('real')[0]}
        small = learning_steps(units[KEYS[0]], 'real', make_mission(KEYS[0], 7251))
        self.assertTrue(small[0].commands.startswith('docker run -it'))
        self.assertIn('exit\ndocker inspect', small[2].commands)
        self.assertIn('상태0', make_mission(KEYS[0], 7251, 2).prompt)
        self.assertNotIn('--rm', make_mission(KEYS[0], 7251, 2).solution)
        for v in range(3): self.assertIn('/keep-me.txt', make_mission(KEYS[4], 7251, v).prompt)


if __name__ == '__main__': unittest.main()
