# Getting started

[한국어](GETTING_STARTED.ko.md) · [Home](../README.md)

## Choose a package

Download from [Shellground Releases](https://github.com/kimwoo666/shellground/releases/tag/v4.7.4-preview). Use the packaged application, not GitHub's automatically generated “Source code” download, unless you intend to build it yourself.

- **Linux x86-64:** follow the desktop assembly instructions below and run `Join-Linux.sh` once. Then run `./Shellground` in the assembled folder, keeping `runtime` beside it. If needed, enable its executable permission (`chmod +x Shellground`).
- **Windows x64:** follow the desktop assembly instructions below and run `Join-Windows.cmd` once. Then double-click `Shellground.exe` in the assembled folder. Keep `_internal` and `runtime` beside it. This build does not use WSL. Native Windows execution has not been verified.
- **Android:** transfer/download the APK to the phone, open it and allow installation from that file-opening app if Android asks. No PC is needed to use the installed app. Python requires Android7+; the bundled Linux-based tracks require Android9+, a supported64-bit ABI and enough memory. Physical-phone compatibility remains unverified.

The Android APK is about2.10GB. Its Linux image is unpacked once into private app storage and needs about2GB more, plus practice files. Installation and updates also need temporary space; allow at least10GB free before installing. Linux practice allocates a2GiB guest in addition to Android/app memory; a6GB-or-more phone is preferable. Small/low-memory phones are not a validated target.

For desktop, download **your OS's App archive + every shared `PC-Guest.qcow2.partNN` file + your OS's Join script** into an empty folder. Run `Join-Windows.cmd` on Windows or `sh Join-Linux.sh` on Linux. It verifies inputs, extracts the application and assembles the guest. Launch the executable in the resulting `Shellground-Windows` or `Shellground-Linux` folder; assembly is only needed once. The two platforms share an identical guest, so it is published once. GitHub requires [each asset to be smaller than2GiB](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas), hence the numbered parts. After assembly, download parts can be deleted; keep the finished application's `runtime` folder. Android needs only its APK, not these PC files.

## Start a lesson

1. Select a track. On desktop, use the top mode tabs; Linux, Docker and ROS2 have their own category tabs. Jupyter is inside the Python mode. Android offers track choices from its menu.
2. Pick a unit and read its first concept step. You may practice while reading.
3. Start the example, then attempt the application tasks.
4. Run your command/code, then choose **채점** (Grade). Read each goal's result.
5. If a goal is incomplete, return to the task and continue. Reset only when you deliberately want the starting state again.

The practice environment starts lazily; simply browsing explanations does not need to boot it. The first Linux startup takes longer than opening a lesson. Do not interpret a boot/preparation phase as instant execution.

## Save and close

Completed lessons, concept progress and lesson substeps are saved automatically. Closing the application stops its own workers/guest. Your personal Docker/WSL setup is not used or deleted.

Typed code, shell history, variables and guest files are temporary. Jupyter's Save writes an `.ipynb` **inside that practice guest**, not a permanent phone/PC document. Keep anything important outside the disposable practice session before closing; this release does not promise a general notebook file-export workflow.

Only run trusted practice code. The Python worker is not a hardened sandbox for untrusted programs. See [platform notes](PLATFORMS.md) before using the preview build.
