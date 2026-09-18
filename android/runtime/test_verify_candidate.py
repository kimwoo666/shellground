import unittest
from verify_candidate import validate_elf

ELF = '''
  Type: DYN (Position-Independent Executable file)
  Machine: AArch64
      [Requesting program interpreter: /system/bin/linker64]
  LOAD 0x000000 0x0000000000000000 0x0000000000000000 0x10000 0x10000 R 0x4000
  LOAD 0x010010 0x0000000000014010 0x0000000000014010 0x10000 0x10000 R E 0x4000
  0x0000000000000001 (NEEDED) Shared library: [libandroid.so]
  0x0000000000000001 (NEEDED) Shared library: [libc.so]
'''


class CandidateTests(unittest.TestCase):
    def test_system_only_aligned_pie(self):
        report = validate_elf(ELF, 'arm64-v8a')
        self.assertEqual(report['load_alignments'], [16384, 16384])
        self.assertEqual(report['needed_system_libraries'], ['libandroid.so', 'libc.so'])

    def test_wrong_machine_linker_and_non_pie(self):
        for text in (ELF.replace('AArch64', 'Advanced Micro Devices X86-64'),
                     ELF.replace('/system/bin/linker64', '/lib/ld-linux-aarch64.so.1'),
                     ELF.replace('Type: DYN', 'Type: EXEC')):
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate_elf(text, 'arm64-v8a')

    def test_alignment_requires_congruent_offsets(self):
        for text in (ELF.replace('0x4000', '0x1000'), ELF.replace('0x010010', '0x010011')):
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate_elf(text, 'arm64-v8a')

    def test_foreign_libraries_and_runtime_paths_rejected(self):
        for extra in (' (NEEDED) Shared library: [libglib-2.0.so.0]',
                      ' (NEEDED) Shared library: [/tmp/host/libc.so]',
                      ' (RUNPATH) Library runpath: [/tmp/build]', ' (TEXTREL) 0x0'):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                validate_elf(ELF + extra, 'arm64-v8a')


if __name__ == '__main__':
    unittest.main()
