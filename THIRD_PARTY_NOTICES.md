# Third-party components

Shellground combines independently licensed components. Their authors retain their copyrights; Shellground does not claim authorship of those components. Public source availability does not remove third-party license conditions.

| Component | License/source information |
| --- | --- |
| Python / CPython | PSF License; package license metadata is retained |
| Qt / PySide6 | LGPL/GPL/commercial upstream licensing; distributed as dynamically linked libraries on desktop |
| NumPy, pandas, SciPy, Matplotlib, Seaborn, scikit-learn and dependencies | Respective upstream licenses, included in package metadata and desktop license files |
| Chaquopy | Its upstream license and bundled Python/package notices |
| GNU/Linux guest packages | Package copyright notices under `/usr/share/doc` inside the guest; Ubuntu package source repositories |
| QEMU | GPL-2.0 with component exceptions; original COPYING files, sources and build patches retained |
| GLib / proxy-libintl | LGPL family; see pinned upstream source archives |
| libffi / PCRE2 / libfdt | MIT / BSD family as specified by each upstream component |
| FreeType | FreeType Project License, with attribution; [upstream](https://freetype.org/) |
| Noto Sans CJK | SIL Open Font License1.1; [copyright](desktop/assets/Noto-COPYRIGHT.txt) |
| Miniconda and included Conda packages | Anaconda and each package's own license/terms; app installation lessons show the source, license and checksum before batch installation |
| NSIS installer | zlib/libpng license and component notices; [included notices](desktop/installer/licenses/nsis.txt) |
| Linux setup: Tcl/Tk, BLT, CPython, PyInstaller | Original package notices and PyInstaller's bootloader exception are in [installer/licenses](desktop/installer/licenses), also included in the setup executable |

## Android native runtime source

The [4.7.4 native-source companion](https://github.com/kimwoo666/shellground/releases/download/v4.7.4-preview/Shellground-4.7.4-Native-Sources.tar) contains the exact pinned QEMU/GLib/libffi/PCRE2/libfdt/proxy-libintl source archives, Shellground Android patches, build instructions and license texts. This is corresponding source material, not a VM cache or an old executable. The easy-install release uses the unchanged APK and links this same companion rather than duplicating it.

The exact versions, official URLs and SHA-256 hashes are in [native-sources.json](android/runtime/native-sources.json). Android-specific changes are in [runtime/patches](android/runtime/patches); build scripts are in [android/runtime](android/runtime). FreeType is built from unmodified upstream source with NDKr27c and16KB ELF load alignment; its source, notices and script are included in the companion.

## Desktop runtime source

Windows QEMU11.1.0 is the vendor's2026-08-11 Windows distribution, not a new Shellground QEMU fork: [vendor downloads, version history and build instructions](https://qemu.weilnetz.de/w64/), [vendor source repository and build scripts](https://github.com/stweil/qemu/tree/ar7). Its identity and original URL are recorded in the runtime's `assembly.json`. This differs from the Android-specific QEMU version in the native-source companion. Linux QEMU is from the pinned Ubuntu packages described by the desktop runtime metadata. Their COPYING, COPYING.LIB and firmware notices remain in the runtime bundle.

PySide/Qt source: [PySide6.8.3](https://code.qt.io/cgit/pyside/pyside-setup.git/?h=v6.8.3) for this Windows build; the Linux package records its own version. Desktop bundles expose the dynamically linked Qt libraries rather than changing their license. See the distributed `licenses` directory and upstream notices for details.

Lecture PDFs, personal study notes, private signing keys and user progress are not redistributed in the source repository.
