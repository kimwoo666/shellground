#!/usr/bin/env python3
import sys

if __name__ == '__main__':
    from stdio_transport import prepare_internal_stdio
    prepare_internal_stdio(sys.argv[1] if len(sys.argv) > 1 else '')
    if sys.argv[1:2] == ['--sync-nas']:
        from nas_sync import main
        raise SystemExit(main(sys.argv[2:]))
    if sys.argv[1:2] == ['--self-test-windows-pipes']:
        from windows_pipe_diagnostics import main
        raise SystemExit(main(sys.argv[2:]))
    if sys.argv[1:2] == ['--internal-windows-pipe-probe']:
        from windows_pipe_diagnostics import probe
        raise SystemExit(probe())
    if sys.argv[1:2] == ['--self-test-release']:
        from release_smoke import main
        raise SystemExit(main(sys.argv[2:]))
    if sys.argv[1:2] == ['--self-test-notebook-package']:
        from notebook_teaching.package_smoke import main
        raise SystemExit(main(sys.argv[2:]))
    if sys.argv[1:2] == ['--self-test-ros-course']:
        from verify_ros_acceptance import main
        sys.argv.pop(1)
        raise SystemExit(main())
    if sys.argv[1:2] == ['--self-test-notebook']:
        from notebook_teaching.verify_course import main
        sys.argv.pop(1)
        raise SystemExit(main())
    if sys.argv[1:2] == ['--self-test-notebook-ui']:
        from notebook_teaching.ui_smoke import main
        sys.argv.pop(1)
        raise SystemExit(main())
    if sys.argv[1:2] == ['--self-test-study-ui']:
        from study_ui_diagnostics import main
        raise SystemExit(main(sys.argv[2:]))
    if sys.argv[1:2] == ['--internal-python-worker']:
        from stdio_transport import restore_worker_pipes
        restore_worker_pipes()
        from python_teaching.worker import main
        raise SystemExit(main(sys.argv[2]))
    if sys.argv[1:2] == ['--self-test-python']:
        from python_teaching.smoke import main
        raise SystemExit(main())
    if sys.argv[1:2] == ['--self-test-conda']:
        from conda_teaching.smoke import main
        raise SystemExit(main())
    if sys.argv[1:2] == ['--self-test-conda-setup']:
        from conda_teaching.setup_diagnostics import main
        raise SystemExit(main(sys.argv[2:]))
    if sys.argv[1:2] == ['--self-test-pip']:
        from conda_teaching.pip_ui_diagnostics import main
        raise SystemExit(main(sys.argv[2:]))
    if sys.argv[1:2] == ['--internal-vm-supervisor']:
        from vm_supervisor import main
        raise SystemExit(main(sys.argv[2:]))
    if sys.argv[1:2] == ['--internal-vm-crash-probe']:
        from vm_crash_diagnostics import crash_probe
        crash_probe('--during-startup' in sys.argv[2:])
    from native_app import main
    raise SystemExit(main())
