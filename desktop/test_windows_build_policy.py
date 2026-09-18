import unittest
from build_verification import guest_pip_wheel_required


class WindowsBuildPolicyTests(unittest.TestCase):
    def test_linux_guest_wheel_is_required_for_conda_on_any_host(self):
        for system in ('linux', 'win32', 'darwin'):
            self.assertTrue(guest_pip_wheel_required(system, conda=True))
        self.assertTrue(guest_pip_wheel_required('linux', conda=False))
        self.assertFalse(guest_pip_wheel_required('win32', conda=False))
        self.assertFalse(guest_pip_wheel_required('darwin', conda=False))


if __name__ == '__main__': unittest.main()
