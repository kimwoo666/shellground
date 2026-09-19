# Getting started

[한국어](GETTING_STARTED.ko.md) · [Home](../README.md)

## Choose a package

Download **one file for your OS** from [Releases](https://github.com/kimwoo666/shellground/releases). GitHub's automatically generated “Source code” files are not the application.

- **Windows 10/11 x64:** download the [Windows compatibility update](https://github.com/kimwoo666/shellground/releases/download/v4.7.4-windows.3/Shellground-Windows-Setup.exe), double-click `Shellground-Windows-Setup.exe`, install, then use the **Shellground** Start-menu or desktop shortcut.
- **Linux x86-64:** open `Shellground-Linux-Setup.run` and install. Enable **Properties → Permissions → Allow executing as a program** if needed. If your file manager will not launch it, use `chmod +x Shellground-Linux-Setup.run` then `./Shellground-Linux-Setup.run`. Afterwards search for **Shellground** in the applications menu. Linux practice requires access to `/dev/kvm`.
- **Android:** transfer/download the APK to the phone, open it and allow installation from that file-opening app if Android asks. No PC is needed to use the installed app. Python requires Android7+; the bundled Linux-based tracks require Android9+, a supported64-bit ABI and enough memory. Physical-phone compatibility remains unverified.

The Android APK is about2.10GB. Its Linux image is unpacked once into private app storage and needs about2GB more, plus practice files. Installation and updates also need temporary space; allow at least10GB free before installing. Linux practice allocates a2GiB guest in addition to Android/app memory; a6GB-or-more phone is preferable. Small/low-memory phones are not a validated target.

**The PC files are online installers.** You download one setup file; it automatically downloads and verifies about **8.1GB** of application and practice data. First setup needs Internet and about **9GB free**. Included courses work offline afterwards. These are not completely offline installation packages.

No manual chunks, joining or extraction: data is streamed into the final disk. Cancel or lose connectivity? Run the same installer again to resume from verified segments. Afterwards open **Shellground**, not `Setup`. Personal Python/Docker/WSL environments and learning progress are untouched. Windows installation is per-user and removable through Settings. Linux installs to `~/.local/share/shellground-app` by default.

See the [native Windows verification record](WINDOWS_4.7.4.1_VERIFICATION.md). Physical Android-phone compatibility remains unverified. These unsigned/development-signed installers may trigger OS warnings.

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
