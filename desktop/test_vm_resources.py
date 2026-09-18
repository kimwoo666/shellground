import unittest
from unittest.mock import patch

from engine import LabError
from vm_resources import accelerator_args, vcpu_count, kvm_usable


class ResourcePolicyTests(unittest.TestCase):
    def test_leaves_capacity_for_desktop(self):
        for host, guest in [(1, 1), (2, 1), (4, 2), (6, 3), (8, 4), (16, 4)]:
            self.assertEqual(vcpu_count(host), guest)

    def test_kvm_has_no_software_fallback(self):
        with patch('vm_resources.sys.platform', 'linux'), patch('vm_resources.kvm_usable', return_value=True):
            self.assertEqual(accelerator_args(), ['-accel', 'kvm', '-cpu', 'host'])

    def test_missing_or_inaccessible_kvm_does_not_start_emulator(self):
        with patch('vm_resources.sys.platform', 'linux'), patch('vm_resources.kvm_usable', return_value=False):
            with self.assertRaises(LabError):
                accelerator_args()
            self.assertIn('tcg,thread=multi', accelerator_args(allow_software=True))

    def test_windows_requests_whpx_when_available(self):
        with patch('vm_resources.sys.platform', 'win32'), patch('windows_vm.hypervisor_present', return_value=True):
            self.assertEqual(accelerator_args(), ['-accel', 'whpx', '-cpu', 'max'])

    def test_kvm_permission_error_is_not_success(self):
        with patch('vm_resources.sys.platform', 'linux'), patch('builtins.open', side_effect=PermissionError):
            self.assertFalse(kvm_usable())


if __name__ == '__main__':
    unittest.main()
