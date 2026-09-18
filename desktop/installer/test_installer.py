import io
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import patch
from core import Setup, Cancelled, checksum, register_launcher


def item(name, data):
    return {'name': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='shellground-setup-test-')
        self.root = Path(self.temp.name)
        self.parts = [b'a' * 40, b'b' * 33, b'c' * 17]
        self.spec = {'version': '4.7.4',
            'base_url': 'https://github.com/kimwoo666/shellground/releases/download/v4.7.4-preview/',
            'disk': dict(item('base', b''.join(self.parts)), parts=[item(str(i), x) for i,x in enumerate(self.parts)])}
        self.calls = []

    def tearDown(self): self.temp.cleanup()

    def opener(self, request, timeout):
        name = request.full_url.rsplit('/', 1)[1]
        self.calls.append(name)
        return io.BytesIO(self.parts[int(name)])

    def setup(self, **kwargs):
        return Setup(self.root / 'install', self.spec, opener=self.opener, **kwargs)

    def test_streamed_disk_has_exact_content_no_retained_parts(self):
        path = self.root / 'base.qcow2'
        self.setup().download_disk(path)
        self.assertEqual(path.read_bytes(), b''.join(self.parts))
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_resume_skips_only_completed_verified_parts(self):
        path = self.root / 'base.qcow2'
        count = 0
        def flaky(request, timeout):
            nonlocal count
            count += 1
            if count == 2: raise OSError('connection lost')
            return self.opener(request, timeout)
        first = self.setup(); first.opener = flaky
        with self.assertRaises(OSError): first.download_disk(path)
        self.assertFalse(path.exists())
        self.assertEqual((self.root / 'base.qcow2.partial').read_bytes(), self.parts[0])
        self.calls.clear(); self.setup().download_disk(path)
        self.assertEqual(self.calls, ['1', '2'])
        self.assertEqual(checksum(path), self.spec['disk']['sha256'])

    def test_reject_corrupt_download(self):
        setup = self.setup(); setup.opener = lambda *a, **k: io.BytesIO(b'broken')
        with self.assertRaises(ValueError): setup.download_disk(self.root / 'base.qcow2')
        self.assertFalse((self.root / 'base.qcow2').exists())

    def test_corrupt_checkpoint_content_is_not_accepted(self):
        (self.root / 'base.qcow2.partial').write_bytes(b'x' * len(b''.join(self.parts)))
        (self.root / 'download-state.json').write_text(json.dumps({'sha256': self.spec['disk']['sha256'], 'completed': 3}))
        with self.assertRaises(ValueError): self.setup().download_disk(self.root / 'base.qcow2')
        self.assertEqual(json.loads((self.root / 'download-state.json').read_text())['completed'], 0)

    def test_cancel_and_lock(self):
        event = threading.Event(); event.set()
        with self.assertRaises(Cancelled): self.setup(cancel=event).download_disk(self.root / 'base.qcow2')
        with self.setup().locked():
            with self.assertRaises(ValueError):
                with self.setup().locked(): pass

    def test_does_not_overwrite_unowned_directory_or_link(self):
        target = self.root / 'install'; target.mkdir(); (target / 'user.txt').write_text('keep')
        with self.assertRaises(ValueError):
            with self.setup().locked(): pass
        self.assertEqual((target / 'user.txt').read_text(), 'keep')
        (self.root / 'base.qcow2').symlink_to(target / 'user.txt')
        with self.assertRaises(ValueError): self.setup().download_disk(self.root / 'base.qcow2')

    def test_install_and_menu_entry_without_touching_progress(self):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w') as archive:
            for name, content in [('Shellground', b'program'), ('runtime/linux-x86_64/runtime.json', b'{}')]:
                info = tarfile.TarInfo('Shellground-Linux/' + name); info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
        self.spec['linux'] = item('app.tar', data.getvalue())
        setup = self.setup()
        setup.opener = lambda request, timeout: io.BytesIO(data.getvalue()) if request.full_url.endswith('app.tar') else self.opener(request, timeout)
        installed = setup.install()
        self.assertEqual((installed / 'runtime/linux-x86_64/base.qcow2').read_bytes(), b''.join(self.parts))
        self.assertEqual(installed, setup.install())
        icon = self.root / 'icon.svg'; icon.write_text('<svg/>')
        launcher = register_launcher(installed, icon, self.root / 'data')
        self.assertIn('Name=Shellground', launcher.read_text())
        self.assertIn('Terminal=false', launcher.read_text())
        self.assertFalse((self.root / 'install/application.tar.partial').exists())

    def test_archive_traversal_is_rejected(self):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w') as archive:
            info = tarfile.TarInfo('Shellground-Linux/../../escaped'); info.size=1
            archive.addfile(info, io.BytesIO(b'x'))
        self.spec['linux'] = item('app.tar', data.getvalue())
        setup = self.setup(); setup.opener = lambda *a, **k: io.BytesIO(data.getvalue())
        with self.assertRaises(tarfile.FilterError): setup.install()
        self.assertFalse((self.root / 'escaped').exists())


if __name__ == '__main__': unittest.main()
