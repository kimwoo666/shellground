import unittest
from platform_runtime import runtime_tag


class PlatformRuntimeTests(unittest.TestCase):
    def test_runtime_names_are_os_and_arch_specific(self):
        for system,arch,expected in [('linux','x86_64','linux-x86_64'),('linux','aarch64','linux-arm64'),
            ('win32','AMD64','windows-x86_64'),('win32','ARM64','windows-arm64'),
            ('darwin','arm64','macos-arm64'),('darwin','x86_64','macos-x86_64')]:
            with self.subTest(system=system,arch=arch):self.assertEqual(runtime_tag(system,arch),expected)
