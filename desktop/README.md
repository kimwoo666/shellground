# Shellground desktop 4.7.4

Native Qt learning application for Linux and Windows. [한국어 소개](../README.ko.md) · [English introduction](../README.md) · [Getting started](../docs/GETTING_STARTED.md)

The application switches Linux/Docker/ROS 2, Python, Conda and Jupyter courses within one main window. Python executes in a separate worker. Command-line courses and Jupyter run in the bundled, disposable Linux VM; they do not execute practice commands in the host shell or require WSL.

## Run the packaged application

Download your platform's App archive, all five shared PC-Guest parts and its Join script from the [release page](https://github.com/kimwoo666/shellground/releases/tag/v4.7.4-preview). Follow the [assembly guide](../docs/GETTING_STARTED.md) once, then keep `runtime` and, on Windows, `_internal` beside the executable in the assembled folder.

- Linux x86-64: run `Shellground`. Accessible KVM acceleration is required for the Linux VM.
- Windows x64: run `Shellground.exe`. This version was built using Wine; native Windows execution has **not** been verified. See [platform limitations](../docs/PLATFORMS.md).
- Android uses its own native app: [Android development](../android/README.md).

Completed learning and substep positions persist. Temporary VM files, shell sessions and Python variables do not persist across practice shutdown. Legacy lightweight simulation remains a separate desktop mode; it is not presented as real Linux.

## Curriculum and verification

The real command course contains Linux90, Docker25 and ROS2 23 units, plus27 reviews. Python/data contains95 learning/review items, Conda/pip20, and Jupyter6. See [current coverage](CURRENT_COVERAGE.md) and [Linux4.7.4 evidence](LINUX_474_REVIEW.md). Course counts do not mean that every option mentioned in every lecture has been implemented or that every case was rerun for this release.

Existing evidence is retained. Only changed behavior and platform integration boundaries are rechecked; repeated full-course replay is not the default. Older `*_REVIEW.md` files describe historical versions, not the current download or installation path.

## Develop from source

Use Python3.12 and an isolated environment:

```sh
python -m venv .venv
# Linux: . .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt -r python-requirements.txt
python shellground.py
```

Source dependencies alone do not provide the VM disk. Use a matching published runtime bundle, or build an app-owned image with the repository's guest-image tooling. Never substitute your personal Docker environment or a host root shell.

```text
shellground.py           application entry point
study_window.py          shared mode host
native_app.py            real-command learning UI
python_teaching/         Python lessons, quizzes and graders
conda_teaching/          Conda/pip lessons and guest-side grading
notebook_teaching/       actual Jupyter kernels and notebook grading
guest/                  disposable Linux guest integration
test_*.py                maintained regression checks
```

Build entry points are `build.sh` (Linux), `build-windows.ps1` (Windows), and `build.py`. `--verification build-only` deliberately produces a build receipt rather than claiming native platform acceptance. The final delivery utilities compress the VM disk without changing its logical contents and place large binaries in release assets, not Git history.

Run targeted tests for the module you change. Live-VM checks create owned temporary practice environments and must clean them afterward. Do not rerun all teaching exercises just to revise documentation.

## Distribution

Keep current application source, tests, matching runtime metadata and small verification receipts. SDKs, build caches, temporary disks, old packaged binaries, personal progress and signing keys are excluded from publication. Third-party corresponding sources and required licenses are distribution materials, not disposable caches: [notices](../THIRD_PARTY_NOTICES.md).
