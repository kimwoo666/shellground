# Single-download installers

Linux/Android and the shared guest disk remain at 4.7.4. The Windows compatibility update rebuilds the host application and refreshes the guest grading scripts at startup. This layer adds a self-contained Linux/Tk installer and a Windows NSIS installer using inbox PowerShell/.NET, pinned HTTPS URLs and SHA-256, streamed assembly, checkpoint resume, cancellation, an install lock and per-user Shellground shortcuts.

PC setup needs Internet once and about 9GB free. Remote segments are an internal transport detail, never a user-facing download step. The original `v4.7.4-preview` assets must remain available: their URLs and hashes are pinned. The simpler `v4.7.4-setup.1` release exposes the two PC installers and the unchanged Android APK.

`build.py` uses locally extracted Ubuntu NSIS/Tcl/Tk packages and PyInstaller in `.installer-build`, not global package installation. `build.py windows` compiles the NSIS wrapper; its C# helper is separately type-checked against .NET-compatible assemblies. `build.py linux` builds only setup, not the learning app. Focused tests use tiny in-memory downloads, not an 8GB redownload or course replay.

Files are unsigned. The Windows compatibility update uses absolute managed assembly references, avoiding NSIS System.dll shadowing. See the [Windows verification record](../../docs/WINDOWS_4.7.4.1_VERIFICATION.md). Native Linux UI, HTTPS and focused transfer checks are separate from that limitation. Bootstrap licenses are included. See the [setup guide](../../docs/GETTING_STARTED.md).
