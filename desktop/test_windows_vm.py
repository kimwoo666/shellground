"""New Windows API contracts. Mocks are NOT actual Windows runtime proof."""
import ctypes
from pathlib import Path, PureWindowsPath
import tempfile
import unittest
from unittest.mock import Mock, patch

import windows_vm as vm


class WindowsVMContractTests(unittest.TestCase):
    def test_cpu_limit_means_point_six_core_not_sixty_percent_of_machine(self):
        for cpus, rate in ((1, 6000), (2, 3000), (4, 1500), (6, 1000), (8, 750), (16, 375), (128, 46)):
            self.assertEqual(vm.cpu_rate(cpus), rate)
            self.assertLessEqual(rate * cpus / 10000, .6)
        for invalid in (None, True, 0, -1, 1.5, 2048):
            with self.assertRaises(ValueError): vm.cpu_rate(invalid)

    def kernel(self):
        kernel = Mock()
        kernel.CreateJobObjectW.return_value = 42
        kernel.GetCurrentProcess.return_value = 101
        kernel.GetActiveProcessorCount.return_value = 8
        kernel.AssignProcessToJobObject.return_value = 1
        kernel.SetInformationJobObject.return_value = 1
        return kernel

    def test_hardware_budget_reserves_host_capacity_and_never_exceeds_four_cores(self):
        for cpus in range(2, 1025):
            rate = vm.cpu_rate(cpus, accelerated=True)
            self.assertLessEqual(rate * cpus / 10000, min(4, cpus // 2))
            self.assertLessEqual(rate, 5000)
        self.assertEqual(vm.cpu_rate(1, accelerated=True), 6000)
        self.assertEqual(vm.cpu_rate(12, accelerated=True), 3333)

    def test_hardware_job_keeps_lifetime_and_hard_cpu_limits(self):
        kernel = self.kernel(); recorded = []
        def info(handle, kind, pointer, size):
            if kind == 15:
                value = ctypes.cast(pointer, ctypes.POINTER(vm.CpuLimits)).contents
                recorded.append((value.flags, value.rate))
            return 1
        kernel.SetInformationJobObject.side_effect = info
        self.assertEqual(vm.create_guard_job(kernel, 12, accelerated=True), 42)
        self.assertEqual(recorded, [(5, 3333)])
        kernel.AssignProcessToJobObject.assert_called_once_with(42, 101)

    def test_both_limits_are_set_before_process_assignment(self):
        kernel = self.kernel(); recorded = []
        def info(handle, kind, pointer, size):
            structure = vm.ExtendedLimits if kind == 9 else vm.CpuLimits
            value = ctypes.cast(pointer, ctypes.POINTER(structure)).contents
            recorded.append((handle, kind, size, value.basic.flags if kind == 9 else (value.flags, value.rate)))
            return 1
        kernel.SetInformationJobObject.side_effect = info
        self.assertEqual(vm.create_guard_job(kernel), 42)
        self.assertEqual(recorded, [(42, 9, ctypes.sizeof(vm.ExtendedLimits), 0x2000), (42, 15, 8, (5, 750))])
        self.assertEqual([call[0] for call in kernel.method_calls],
                         ['GetActiveProcessorCount', 'CreateJobObjectW', 'SetInformationJobObject',
                          'SetInformationJobObject', 'GetCurrentProcess', 'AssignProcessToJobObject'])
        kernel.CloseHandle.assert_not_called()  # stays alive until OS teardown

    def test_each_api_failure_is_fatal_without_a_leaked_handle(self):
        for step in ('create', 'lifetime', 'cpu', 'assign'):
            with self.subTest(step=step):
                kernel = self.kernel()
                if step == 'create': kernel.CreateJobObjectW.return_value = 0
                if step == 'lifetime': kernel.SetInformationJobObject.side_effect = [0]
                if step == 'cpu': kernel.SetInformationJobObject.side_effect = [1, 0]
                if step == 'assign': kernel.AssignProcessToJobObject.return_value = 0
                with patch('windows_vm._error', return_value=OSError('denied')):
                    with self.assertRaisesRegex(OSError, 'denied'): vm.create_guard_job(kernel, 4)
                if step == 'create': kernel.CloseHandle.assert_not_called()
                else: kernel.CloseHandle.assert_called_once_with(42)
                if step != 'assign': kernel.AssignProcessToJobObject.assert_not_called()

    def test_capability_failure_missing_dll_false_and_true(self):
        for result, present, written, expected in ((0, 1, 4, True), (0, 0, 4, False),
                                                    (-1, 1, 4, False), (0, 1, 0, False)):
            dll = Mock()
            def query(code, output, size, returned):
                self.assertEqual((code, size), (0, 8))
                ctypes.cast(output, ctypes.POINTER(ctypes.c_uint64)).contents.value = present
                ctypes.cast(returned, ctypes.POINTER(vm.DWORD)).contents.value = written
                return result
            dll.WHvGetCapability.side_effect = query
            with patch('windows_vm.system_dll', return_value=dll):
                self.assertEqual(vm.hypervisor_present(), expected)
        with patch('windows_vm.system_dll', side_effect=OSError('missing')):
            self.assertFalse(vm.hypervisor_present())

    def test_no_setup_software_path_is_labelled_and_bounded(self):
        with patch('windows_vm.hypervisor_present', return_value=False):
            args = vm.accelerator_args()
            self.assertEqual(args, ['-accel', 'tcg,thread=multi', '-cpu', 'max'])
            self.assertEqual(vm.boot_timeout(args), 600)
            self.assertIn('소프트웨어 실행', vm.startup_description(args, 2))
        with patch('windows_vm.hypervisor_present', return_value=True):
            args = vm.accelerator_args()
            self.assertEqual(vm.boot_timeout(args), 120)
            self.assertNotIn('tcg', args)

    def test_only_windows_routes_through_new_guard(self):
        from vm_supervisor import windows_kill_job
        with patch('vm_supervisor.os.name', 'nt'), patch('windows_vm.create_guard_job', return_value=42) as guard:
            self.assertEqual(windows_kill_job(), 42)
            guard.assert_called_once_with(accelerated=False)
        with patch('vm_supervisor.os.name', 'posix'), patch('windows_vm.create_guard_job') as guard:
            self.assertIsNone(windows_kill_job())
            guard.assert_not_called()

    def test_guard_budget_follows_the_selected_qemu_accelerator(self):
        from vm_supervisor import windows_kill_job
        for args, expected in ((['-accel', 'whpx'], True),
                               (['-accel', 'tcg,thread=multi'], False),
                               (['-name', 'whpx'], False)):
            with patch('vm_supervisor.os.name', 'nt'), patch('windows_vm.create_guard_job') as guard:
                windows_kill_job(['qemu.exe', *args])
                guard.assert_called_once_with(accelerated=expected)

    def test_option_escaping_and_unicode_are_not_shell_quoted(self):
        self.assertEqual(vm.option_path(PureWindowsPath('C:/Users/김, 우/실습/practice.qcow2')),
                         'C:/Users/김,, 우/실습/practice.qcow2')

    def test_supervisor_output_does_not_hold_owned_log_open(self):
        with vm.supervisor_output() as output:
            output.write(b'guard error'); output.seek(0)
            self.assertEqual(output.read(), b'guard error')
        self.assertTrue(output.closed)

    def test_forwarded_error_is_bounded_and_not_a_whole_log_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'qemu.log'
            path.write_bytes(b'x' * 4000 + '오류'.encode())
            with patch('os.write') as write:
                vm.forward_qemu_error(path)
                descriptor, message = write.call_args.args
                self.assertEqual(descriptor, 2)
                self.assertEqual(len(message), 3000)
                self.assertTrue(message.endswith('오류'.encode()))


if __name__ == '__main__': unittest.main()
